/** Actual WebKit engine coverage; narrow desktop Chrome is not an iOS substitute. */
import {webkit,devices} from 'playwright';
import {createServer} from 'vite';
import {readFile,writeFile,mkdir} from 'node:fs/promises';
import assert from 'node:assert/strict';
const catalogueIdentity=JSON.parse(await readFile('web/public/models/catalogue.json'));
const out='result/web/release'+catalogueIdentity.version+'/webkit';await mkdir(out,{recursive:true});
const server=await createServer({server:{host:'127.0.0.1',port:0},logLevel:'error',plugins:[{name:'ios-viewer-proof',configureServer(server){server.middlewares.use('/__ios-viewer',(_,response)=>{response.setHeader('Content-Type','text/html');response.end(`<!doctype html><link rel="icon" href="data:,"><style>body{margin:0}#stage{width:100vw;height:100vh}</style><div id="stage"></div><div id="labels"></div><script type="module">
import {CampusViewer} from '/src/viewer.js';const c=await(await fetch('/models/catalogue.json')).json();const v=new CampusViewer(document.querySelector('#stage'),document.querySelector('#labels'),c.buildings,()=>{},()=>{window.contextLost=true;},()=>{},c.sourceModelSha256);window.viewer=v;window.catalogue=c;await v.load();await v.environmentReady;window.ready=true;
</script>`);});}}]});
let browser;
try{
 await server.listen();const origin='http://127.0.0.1:'+server.httpServer.address().port;
 browser=await webkit.launch({headless:true});
 const context=await browser.newContext({...devices['iPhone 13'],userAgent:devices['iPhone 13'].userAgent+' EdgiOS/131.0'});
 await context.addInitScript(()=>{AbortSignal.any=undefined;AbortSignal.prototype.throwIfAborted=undefined;});
 let page=await context.newPage();const errors=[],requests=[];page.on('pageerror',e=>{errors.push(e.message);console.error(e.message);});page.on('request',r=>requests.push(new URL(r.url()).pathname));
 await page.goto(origin);await page.waitForFunction(()=>document.querySelector('canvas')?.dataset.ready==='true',null,{timeout:90000});
 await page.waitForTimeout(500);
 assert.equal(await page.locator('canvas').getAttribute('data-resource-profile'),'mobile');
 assert(!requests.includes('/models/campus.glb'));assert.equal(requests.filter(p=>/exterior-/.test(p)).length,0);
 await page.screenshot({path:out+'/webkit-mobile-overview.png'});
 await page.locator('#index-toggle').click();await page.locator('#building-search').fill('OLD');await page.locator('#building-list button').filter({hasText:'Old Building'}).click();
 await page.waitForFunction(()=>document.querySelector('canvas')?.dataset.detailReady==='exterior-OLD',null,{timeout:60000});
 await page.locator('#interior-view').click();await page.waitForFunction(()=>document.querySelector('canvas')?.dataset.detailReady==='interior-OLD',null,{timeout:60000});
 assert.deepEqual(errors,[]);await page.screenshot({path:out+'/webkit-mobile-old-interior.png'});
 await page.close();
 page=await context.newPage();page.on('pageerror',e=>{errors.push(e.message);console.error(e.message);});
 await page.goto(origin+'/__ios-viewer');await page.waitForFunction(()=>window.ready,null,{timeout:90000});
 const rows=[];
 for(const code of ['OLD','SAW','MAR']){
  const result=await page.evaluate(async code=>{const b=catalogue.buildings.find(b=>b.code===code);viewer.select(b);await viewer.upgradeModel(b,'exterior');await viewer.localContext.ready;return {code,profile:viewer.budget,cachedExteriors:viewer.exteriors.size,detail:viewer.canvas.dataset.detailReady,geometries:viewer.renderer.info.memory.geometries,shadowSize:viewer.sun.shadow.mapSize.toArray(),hasComposer:!!viewer.renderPipeline.composer,lost:viewer.renderer.getContext().isContextLost()};},code);
  assert.equal(result.lost,false);assert(result.cachedExteriors<=2);assert.equal(result.detail,'exterior-'+code);assert.deepEqual(result.shadowSize,[1024,1024]);assert.equal(result.hasComposer,false);rows.push(result);
 }
 await page.setViewportSize({width:844,height:390});await page.waitForTimeout(350);
 const landscape=await page.evaluate(()=>({profile:viewer.budget,shadow:viewer.sun.shadow.mapSize.toArray(),sampleLevel:viewer.renderPipeline.scenePass.sampleLevel,hasHistory:!!viewer.renderPipeline.temporalPass.history}));
 assert(landscape.profile.mobile);assert.deepEqual(landscape.shadow,[1024,1024]);assert.equal(landscape.sampleLevel,0);assert.equal(landscape.hasHistory,false);
 await page.screenshot({path:out+'/webkit-mobile-landscape.png'});
 await page.evaluate(()=>viewer.dispose());assert.deepEqual(errors,[]);
 await writeFile(out+'/webkit-verification.json',JSON.stringify({passed:true,engine:'WebKit',device:'iPhone13 touch emulation with EdgiOS UA',missingApis:['AbortSignal.any','AbortSignal.throwIfAborted'],rows,landscape,errors,requests,limit:'Desktop WebKit emulation does not reproduce iPhone memory pressure or prove the physical device result.'},null,2)+'\n');
 console.log(JSON.stringify({passed:true,rows,landscape,errors}));await context.close();
}finally{await browser?.close();await server.close();}
