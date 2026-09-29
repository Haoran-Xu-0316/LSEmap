/** Inspect the native CLM candidate before paying for a full campus export. */
import {createServer} from 'vite';
import {chromium} from 'playwright';
import {readFile,writeFile} from 'node:fs/promises';
const candidates=Object.fromEntries(await Promise.all(['before','after'].map(async name=>[name,await readFile(`result/blender/stage40/cornices-${name}.glb`)])));
let candidate=candidates.before;
const source=await readFile('web/tools/render_web_gallery.mjs','utf8');
const html=source.split('const html = `')[1].split('`;\nconst server')[0].replace('const viewer=new CampusViewer',"catalogue.buildings.find(b=>b.code==='CLM').detailedExterior.url='/__candidate.glb';\nconst viewer=new CampusViewer");
const server=await createServer({server:{host:'127.0.0.1',port:0},logLevel:'error',plugins:[{name:'clm-candidate',configureServer(s){
 s.middlewares.use('/__candidate.glb',(_q,r)=>{r.setHeader('Content-Type','model/gltf-binary');r.end(candidate);});
 s.middlewares.use('/__candidate',(_q,r)=>{r.setHeader('Content-Type','text/html');r.end(html);});
}}]});
let browser;
try{
 await server.listen();browser=await chromium.launch({args:['--use-angle=metal']});
 const page=await browser.newPage({viewport:{width:1400,height:1120},reducedMotion:'reduce'});
 await page.goto(`http://127.0.0.1:${server.httpServer.address().port}/__candidate`);
 await page.waitForFunction(()=>window.galleryReady,null,{timeout:120000});
 for(const phase of ['before','after']){
  candidate=candidates[phase];
  await page.reload();
  await page.waitForFunction(()=>window.galleryReady,null,{timeout:120000});
  const job={code:'CLM',name:'clm-exterior'};
  const r=await page.evaluate(job=>window.renderGalleryView(job),job);
  await writeFile(`result/blender/stage40/cornices-${phase}.webp`,Buffer.from(r.image,'base64'));
  const close=await page.evaluate(job=>window.renderGalleryView(job),{code:'CLM',name:'clm-close',view:{position:[111,10,175],target:[114,8.5,154],fov:38}});
  await writeFile(`result/blender/stage40/inscription-${phase}.webp`,Buffer.from(close.image,'base64'));
 }

}finally{await browser?.close();await server.close();}
