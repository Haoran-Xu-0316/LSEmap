import {createServer} from 'vite';
import {chromium} from 'playwright';
import {readFile,writeFile,mkdir} from 'node:fs/promises';
const directory='result/blender/old-exterior-colour-review';
await mkdir(directory,{recursive:true});
const sourceVersion=JSON.parse(await readFile('web/public/models/catalogue.json','utf8')).version;
const jobs=JSON.parse(await readFile('web/tools/gallery-views.json','utf8')).filter(j=>['old-houghton-entrance','old-exterior'].includes(j.name));
jobs.push({code:'OLD',name:'old-door-close',view:{position:[1.56,2.9,94.56],target:[-8.13,2.1,89.34],fov:34}});
const html=`<!doctype html><style>html,body{margin:0}#canvas{width:1400px;height:1120px}#labels{display:none}</style><div id="canvas"></div><div id="labels"></div><script type="module">
import {CampusViewer} from '/src/viewer.js';
const variant=new URLSearchParams(location.search).get('variant');
const catalogue=await(await fetch('/models/catalogue.json')).json();
const building=catalogue.buildings.find(b=>b.code==='OLD');
const viewer=new CampusViewer(document.querySelector('#canvas'),document.querySelector('#labels'),catalogue.buildings,()=>{},()=>{throw Error('WebGL context lost')},()=>{},catalogue.sourceModelSha256);
await viewer.load();viewer.toggleLabels(false);viewer.select(building);await viewer.upgradeModel(building,'exterior');
const changed=new Set();
viewer.scene.traverse(object=>{
 if(!object.isMesh)return;
 for(const material of Array.isArray(object.material)?object.material:[object.material]){
  if(!material||!/(?:OLD172_clear_dielectric_door_glass|OLD_ENTRANCE192_clear_glass)$/.test(material.name)||changed.has(material))continue;
  material.color.setRGB(...(variant==='after'?[.15,.18,.18]:[.29,.325,.315]));
  const luminance=material.color.r*.2126+material.color.g*.7152+material.color.b*.0722;
  material.color.lerp(new material.color.constructor(luminance,luminance,luminance),.28);
  material.opacity=variant==='after'?.28:.46;material.needsUpdate=true;changed.add(material);
 }
});
window.capture=async job=>{
 if(viewer.canvas.dataset.detailReady!=='exterior-OLD')throw Error('Detail unavailable');
 if(job.view){viewer.camera.fov=job.view.fov;viewer.updateCameraProjection();viewer.moveCamera(viewer.camera.position.clone().fromArray(job.view.position),viewer.controls.target.clone().fromArray(job.view.target),false);}
 else viewer.select(building);
 viewer.transition=null;viewer.controls.update();viewer.camera.updateMatrixWorld();viewer.renderer.shadowMap.needsUpdate=true;viewer.renderPipeline.resetHistory();viewer.renderPipeline.render();
 return {image:viewer.canvas.toDataURL('image/webp',.95).split(',')[1],detail:viewer.canvas.dataset.detailReady,changedMaterials:changed.size};
};window.ready=true;</script>`;
const server=await createServer({server:{host:'127.0.0.1',port:0},logLevel:'error',plugins:[{name:'old-private-glass-review',configureServer(server){server.middlewares.use('/__old-glass-review',(_req,res)=>{res.setHeader('Content-Type','text/html');res.end(html);});}}]});
let browser;
try{
 await server.listen();browser=await chromium.launch({args:['--use-angle=metal']});const records=[];
 for(const variant of ['before','after']){
  const page=await browser.newPage({viewport:{width:1400,height:1120},reducedMotion:'reduce'});const errors=[];
  page.on('pageerror',error=>errors.push(error.message));
  await page.goto('http://127.0.0.1:'+server.httpServer.address().port+'/__old-glass-review?variant='+variant);
  await page.waitForFunction(()=>window.ready,null,{timeout:120000});
  for(const job of jobs){const capture=await page.evaluate(job=>window.capture(job),job);
   if(errors.length)throw Error(errors.join('\n'));
   if(capture.changedMaterials!==2)throw Error('Unexpected material scope: '+capture.changedMaterials);
   const bytes=Buffer.from(capture.image,'base64');await writeFile(directory+'/'+variant+'-'+job.name+'.webp',bytes);
   records.push({variant,view:job.name,detail:capture.detail,changedMaterials:capture.changedMaterials,bytes:bytes.length});
  }
  await page.close();
 }
 await writeFile(directory+'/optical-preview.json',JSON.stringify({sourceVersion,nativeSourceUnchanged:true,renderer:'Production CampusViewer',records},null,2)+'\n');
 console.log('OLD_GLASS_PRIVATE_PREVIEW_COMPLETE',records.length);
}catch(error){throw error;}finally{await browser?.close();await server.close();}
