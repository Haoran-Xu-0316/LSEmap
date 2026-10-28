/** Compare identical mobile geometry over a bounded local link in real WebKit. */
import {preview} from 'vite';
import {webkit,devices} from 'playwright';
import {readFile,writeFile,mkdir} from 'node:fs/promises';
import assert from 'node:assert/strict';
const out='result/web/loading282';await mkdir(out,{recursive:true});
const mobile=JSON.parse(await readFile('dist/models/mobile-campus.json'));
const payloads=new Map();for(const url of [mobile.url,mobile.transport.url])payloads.set(url,await readFile('dist'+url));
const server=await preview({preview:{host:'127.0.0.1',port:0},logLevel:'error',plugins:[{
 name:'verified-mobile-transfer-benchmark',configurePreviewServer(server){
  server.middlewares.use((req,res,next)=>{
   const path=new URL(req.url,'http://localhost').pathname;
   if(path==='/models/mobile-campus.json'&&req.headers['x-benchmark-mode']==='raw'){
    const value={...mobile};delete value.transport;res.setHeader('Content-Type','application/json');res.end(JSON.stringify(value));return;
   }
   const bytes=payloads.get(path);if(!bytes){next();return;}
   const compressed=path===mobile.transport.url;
   res.setHeader('Content-Type','model/gltf-binary');res.setHeader('Content-Length',bytes.length);res.setHeader('Cache-Control','no-store');
   if(compressed)res.setHeader('Content-Encoding','gzip');
   // 64KiB every40ms: identical controlled link for raw and lossless gzip.
   let offset=0,timer;
   const send=()=>{if(res.destroyed)return;if(offset===bytes.length){res.end();return;}res.write(bytes.subarray(offset,offset+65536));offset=Math.min(bytes.length,offset+65536);timer=setTimeout(send,40);};
   res.on('close',()=>clearTimeout(timer));send();
  });
 },
}]});
const origin='http://127.0.0.1:'+server.httpServer.address().port;
let browser;const rows=[],errors=[];
try{
 browser=await webkit.launch();
 for(const mode of ['raw','gzip']){
  const context=await browser.newContext({...devices['iPhone 13'],extraHTTPHeaders:{'X-Benchmark-Mode':mode},userAgent:devices['iPhone 13'].userAgent+' EdgiOS/131.0'});
  try{
   const page=await context.newPage();let requests=[];page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>requests.push(new URL(r.url()).pathname));
   const open=async(label)=>{requests=[];const start=Date.now();await page.goto(origin,{waitUntil:'domcontentloaded'});await page.waitForFunction(()=>document.querySelector('canvas')?.dataset.ready==='true',null,{timeout:60000});
    const modelRequests=requests.filter(p=>payloads.has(p));const state=await page.locator('canvas').evaluate(c=>({profile:c.dataset.resourceProfile,lost:c.getContext('webgl2').isContextLost(),pixelRatio:c.width/c.clientWidth}));
    const fullUrls=await page.evaluate(()=>performance.getEntriesByType('resource').filter(e=>/campus-mobile-.*glb/.test(e.name)).map(e=>e.name));const row={label,fullUrls,ms:Date.now()-start,modelRequests,transferBytes:modelRequests.reduce((n,p)=>n+payloads.get(p).length,0),catalogueRequests:requests.filter(p=>p==='/models/catalogue.json').length,...state};
    assert.equal(state.profile,'mobile');assert.equal(state.lost,false);assert(state.pixelRatio>1.7);assert.equal(row.catalogueRequests,1);rows.push(row);await page.screenshot({path:out+'/'+label+'.png'});return row;
   };
   const cold=await open(mode+'-cold');assert.deepEqual(cold.modelRequests,[mode==='raw'?mobile.url:mobile.transport.url]);
   if(mode==='gzip'){
    let cached=false;
    const states=[];
    for(let attempt=0;attempt<60;attempt++){
     const state=await page.evaluate(()=>new Promise(resolve=>{const r=indexedDB.open('lsemap-model-bytes',1);r.onerror=()=>resolve({error:'open'});r.onsuccess=()=>{const db=r.result;try{const q=db.transaction('current-model').objectStore('current-model').get('campus');q.onsuccess=()=>{resolve({sha:q.result?.sha256,size:q.result?.buffer?.byteLength??q.result?.blob?.size});db.close();};q.onerror=()=>{db.close();resolve({error:'read'});};}catch{db.close();resolve({error:'store'});}};}));
     states.push(state);if(state.sha===mobile.sha256&&state.size===mobile.bytes){cached=true;break;}
     await new Promise(resolve=>setTimeout(resolve,100));
    }
    await writeFile(out+'/cache-diagnostic.json',JSON.stringify({cached,states},null,2));assert(cached,'Verified mobile bytes were not persisted');
    const warm=await open('gzip-cached');await writeFile(out+'/partial-transfer.json',JSON.stringify(rows,null,2));assert.equal(warm.modelRequests.length,0);assert.equal(warm.transferBytes,0);
   }
  }finally{await context.close();}
 }
 assert.deepEqual(errors,[]);
 const raw=rows.find(r=>r.label==='raw-cold'),compressed=rows.find(r=>r.label==='gzip-cold');
 assert(compressed.transferBytes<raw.transferBytes*.7);
 const report={passed:true,engine:'WebKit with iPhone touch and EdgiOS UA',controlledLink:'64KiB per40ms',rows,errors,byteReduction:1-compressed.transferBytes/raw.transferBytes,modelSha256:mobile.sha256,limitations:'Local controlled-link results do not establish physical iPhone timing or fix network reachability to the domain.'};
 await writeFile(out+'/mobile-transfer.json',JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report));
}finally{await browser?.close();await server.httpServer.close();}
