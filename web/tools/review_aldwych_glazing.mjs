/** Compare two exterior glass candidates in the production viewer. */
import {createServer} from 'vite';
import {chromium} from 'playwright';
import {readFile,writeFile} from 'node:fs/promises';
const candidates=Object.fromEntries(await Promise.all(['COL','CON'].flatMap(code=>['before','after'].map(async phase=>[`${code}-${phase}`,await readFile(`result/blender/stage41/${code.toLowerCase()}-${phase}.glb`)]))));
let phase='before';
const source=await readFile('web/tools/render_web_gallery.mjs','utf8');
const html=source.split('const html = `')[1].split('`;\nconst server')[0].replace('const viewer=new CampusViewer',"for(const code of ['COL','CON'])catalogue.buildings.find(b=>b.code===code).detailedExterior.url='/__candidate-'+code+'.glb';\nconst viewer=new CampusViewer");
const server=await createServer({server:{host:'127.0.0.1',port:0},logLevel:'error',plugins:[{name:'clm-candidate',configureServer(s){
 for(const code of ['COL','CON'])s.middlewares.use('/__candidate-'+code+'.glb',(_q,r)=>{r.setHeader('Content-Type','model/gltf-binary');r.end(candidates[`${code}-${phase}`]);});
 s.middlewares.use('/__candidate',(_q,r)=>{r.setHeader('Content-Type','text/html');r.end(html);});
}}]});
let browser;
try{
 await server.listen();browser=await chromium.launch({args:['--use-angle=metal']});
 const page=await browser.newPage({viewport:{width:1400,height:1120},reducedMotion:'reduce'});
 await page.goto(`http://127.0.0.1:${server.httpServer.address().port}/__candidate`);
 await page.waitForFunction(()=>window.galleryReady,null,{timeout:120000});
 for(const nextPhase of ['before','after']){
  phase=nextPhase;
  await page.reload();
  await page.waitForFunction(()=>window.galleryReady,null,{timeout:120000});
  for(const code of ['COL','CON']){
   const r=await page.evaluate(job=>window.renderGalleryView(job),{code,name:code.toLowerCase()+'-exterior'});
   await writeFile(`result/blender/stage41/${code.toLowerCase()}-${phase}.webp`,Buffer.from(r.image,'base64'));
  }
 }

}finally{await browser?.close();await server.close();}
