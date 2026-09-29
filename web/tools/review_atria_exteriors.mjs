/** Private exterior review using exactly the production gallery renderer. */
import {createServer} from 'vite';
import {chromium} from 'playwright';
import {readFile,writeFile,mkdir} from 'node:fs/promises';
const source=await readFile('web/tools/render_web_gallery.mjs','utf8');
const html=source.split('const html = `')[1].split('`;\nconst server')[0];
const server=await createServer({server:{host:'127.0.0.1',port:0},logLevel:'error',plugins:[{name:'exterior-review',configureServer(s){s.middlewares.use('/__review',(_q,r)=>{r.setHeader('Content-Type','text/html');r.end(html);});}}]});
let browser;
try{
 await server.listen();browser=await chromium.launch({args:['--use-angle=metal']});
 const page=await browser.newPage({viewport:{width:1400,height:1120},reducedMotion:'reduce'});
 await page.goto(`http://127.0.0.1:${server.httpServer.address().port}/__review`);
 await page.waitForFunction(()=>window.galleryReady,null,{timeout:120000});
 await mkdir('result/web/atria-exteriors',{recursive:true});
 const jobs=[
  {code:'LRB',name:'lrb-exterior'},
  {code:'LRB',name:'lrb-plaza-close',view:{position:[26,14,27],target:[45.5,11,.88],fov:38}},
  {code:'LRB',name:'lrb-north-roof',view:{position:[95,62,-90],target:[70,23,-14],fov:38}},
  {code:'LRB',name:'lrb-interior'},
  {code:'CKK',name:'ckk-exterior'},
  {code:'CKK',name:'ckk-front-roof',view:{position:[-48,49,-101],target:[-94,26,-84],fov:38}},
 ];
 for(const job of jobs){
  const r=await page.evaluate(job=>window.renderGalleryView(job),job);
  await writeFile(`result/web/atria-exteriors/${job.name}.webp`,Buffer.from(r.image,'base64'));
 }
}finally{await browser?.close();await server.close();}
