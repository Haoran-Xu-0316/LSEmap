/** Review the native site candidate using the same renderer as the website. */
import {createServer} from 'vite';
import {chromium} from 'playwright';
import {readFile,writeFile} from 'node:fs/promises';
const candidate=await readFile('result/blender/stage44/site-preview.glb');
const source=await readFile('web/tools/render_web_gallery.mjs','utf8');
let html=source.split('const html = `')[1].split('`;\nconst server')[0];
html=html.replace('viewer.toggleLabels(false);',`viewer.toggleLabels(false);
viewer.groups.get('SITE').visible=false;
const site=await viewer.loadAsset('/__site.glb');
site.scene.traverse(o=>{if(o.isMesh){o.castShadow=false;o.receiveShadow=true;}});
viewer.scene.add(site.scene);
viewer.needsRender=true;`);
html=html.replace("if(job.code==='CAMPUS') viewer.home(false);","if(job.code==='CAMPUS'){viewer.home(false);viewer.groups.get('SITE').visible=false;}");
const server=await createServer({server:{host:'127.0.0.1',port:0},logLevel:'error',plugins:[{name:'site-review',configureServer(s){
 s.middlewares.use('/__site.glb',(_q,r)=>{r.setHeader('Content-Type','model/gltf-binary');r.end(candidate);});
 s.middlewares.use('/__site',(_q,r)=>{r.setHeader('Content-Type','text/html');r.end(html);});
}}]});
let browser;
try{
 await server.listen();browser=await chromium.launch({args:['--use-angle=metal']});
 const page=await browser.newPage({viewport:{width:1400,height:1120},reducedMotion:'reduce'});
 await page.goto(`http://127.0.0.1:${server.httpServer.address().port}/__site`);
 await page.waitForFunction(()=>window.galleryReady,null,{timeout:120000});
 for(const job of [{code:'CAMPUS',name:'campus'}, {code:'CAMPUS',name:'sheffield',view:{position:[-50,65,12.5],target:[-50,0,12],fov:38}}, {code:'CAMPUS',name:'houghton',view:{position:[10,70,75.5],target:[10,0,75],fov:38}}, {code:'CAMPUS',name:'portsmouth',view:{position:[-37,65,-32.5],target:[-37,0,-33],fov:38}}, {code:'CAMPUS',name:'plaza',view:{position:[34,70,-4.5],target:[34,0,-5],fov:38}}]){
  const result=await page.evaluate(job=>window.renderGalleryView(job),job);
  await writeFile(`result/blender/stage44/${job.name}.webp`,Buffer.from(result.image,'base64'));
 }
}finally{await browser?.close();await server.close();}
