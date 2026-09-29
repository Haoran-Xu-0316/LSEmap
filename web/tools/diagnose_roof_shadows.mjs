/** Isolated shadow diagnostics; never publishes gallery images or model changes. */
import {createServer} from 'vite';
import {chromium} from 'playwright';
import {readFile,writeFile,mkdir} from 'node:fs/promises';
const source=await readFile('web/tools/render_web_gallery.mjs','utf8');
const html=source.split('const html = `')[1].split('`;\nconst server')[0].replace('window.galleryReady=true;', 'window.roofViewer=viewer;window.galleryReady=true;');
const server=await createServer({server:{host:'127.0.0.1',port:0},logLevel:'error',plugins:[{name:'roof-diagnostic',configureServer(server){server.middlewares.use('/__roof',(_req,res)=>{res.setHeader('Content-Type','text/html');res.end(html);});}}]});
let browser;
try{
 await server.listen();browser=await chromium.launch({args:['--use-angle=metal']});
 const page=await browser.newPage({viewport:{width:1400,height:1120},reducedMotion:'reduce'});
 await page.goto(`http://127.0.0.1:${server.httpServer.address().port}/__roof`);
 await page.waitForFunction(()=>window.galleryReady,null,{timeout:120000});
 await mkdir('result/web/roof-diagnostic',{recursive:true});
 for(const code of ['KSW']) for(const mode of ['current','no-shadow','offset','normal','bias','front']) {
  const capture=await page.evaluate(async({code,mode})=>{
   const v=window.roofViewer;
   await window.renderGalleryView({code,name:code.toLowerCase()+'-exterior'});
   v.renderer.shadowMap.enabled=mode!=='no-shadow';
   v.scene.traverse(o=>{if(o.isMesh){o.receiveShadow=mode!=='no-shadow';for(const m of Array.isArray(o.material)?o.material:[o.material]){m.shadowSide=mode==='front'?0:null;m.needsUpdate=true;}}});
   v.sun.shadow.normalBias=['offset','normal'].includes(mode)?.12:.04;
   v.sun.shadow.bias=['offset','bias'].includes(mode)?-.0005:-.0002;
   v.renderer.shadowMap.needsUpdate=true;
   v.renderer.render(v.scene,v.camera);
   return v.canvas.toDataURL('image/png').split(',')[1];
  },{code,mode});
  await writeFile(`result/web/roof-diagnostic/${code}-${mode}.png`,Buffer.from(capture,'base64'));
  console.log(code,mode);
 }
}finally{await browser?.close();await server.close();}
