/** Inspect the native CKK candidate before paying for a full campus export. */
import {createServer} from 'vite';
import {chromium} from 'playwright';
import {readFile,writeFile} from 'node:fs/promises';
const candidate=await readFile('result/blender/stage34/ckk-preview.glb');
const source=await readFile('web/tools/render_web_gallery.mjs','utf8');
const html=source.split('const html = `')[1].split('`;\nconst server')[0].replace('const viewer=new CampusViewer',"catalogue.buildings.find(b=>b.code==='CKK').detailedExterior.url='/__candidate.glb';\nconst viewer=new CampusViewer");
const server=await createServer({server:{host:'127.0.0.1',port:0},logLevel:'error',plugins:[{name:'ckk-candidate',configureServer(s){
 s.middlewares.use('/__candidate.glb',(_q,r)=>{r.setHeader('Content-Type','model/gltf-binary');r.end(candidate);});
 s.middlewares.use('/__candidate',(_q,r)=>{r.setHeader('Content-Type','text/html');r.end(html);});
}}]});
let browser;
try{
 await server.listen();browser=await chromium.launch({args:['--use-angle=metal']});
 const page=await browser.newPage({viewport:{width:1400,height:1120},reducedMotion:'reduce'});
 await page.goto(`http://127.0.0.1:${server.httpServer.address().port}/__candidate`);
 await page.waitForFunction(()=>window.galleryReady,null,{timeout:120000});
 for(const job of [
  {code:'CKK',name:'ckk-courtyard',view:{position:[-88,38,-86],target:[-121,21,-75],fov:38}},
  {code:'CKK',name:'ckk-portal',view:{position:[-73,8,-93],target:[-89,4,-86],fov:38}},
 ]){
  const r=await page.evaluate(job=>window.renderGalleryView(job),job);
  await writeFile(`result/blender/stage34/${job.name}.webp`,Buffer.from(r.image,'base64'));
 }
}finally{await browser?.close();await server.close();}
