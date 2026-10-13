/** Private paint comparison using the current production viewer and assets. */
import {createServer} from 'vite';
import {chromium} from 'playwright';
import {readFile,writeFile,mkdir} from 'node:fs/promises';
const directory='result/blender/old-painted-frame-review';
const audit=JSON.parse(await readFile(directory+'/inspection.json','utf8'));
const finishes=audit.filter(m=>m.metallic>0).map(m=>({name:m.material,metallic:m.metallic,roughness:m.roughness}));
const catalogue=JSON.parse(await readFile('web/public/models/catalogue.json','utf8'));
const jobs=JSON.parse(await readFile('web/tools/gallery-views.json','utf8')).filter(j=>['old-exterior','old-clare-market','old-houghton-entrance','old-entablature'].includes(j.name));
jobs.push({code:'CAMPUS',name:'campus-overview'});
await mkdir(directory,{recursive:true});
const html=`<!doctype html><style>html,body{margin:0}#canvas{width:1400px;height:1120px}#labels{display:none}</style><div id="canvas"></div><div id="labels"></div><script type="module">
import {CampusViewer} from '/src/viewer.js';
const variant=new URLSearchParams(location.search).get('variant');
const finishes=${JSON.stringify(finishes)};
const catalogue=await(await fetch('/models/catalogue.json')).json();
const building=catalogue.buildings.find(b=>b.code==='OLD');
const viewer=new CampusViewer(document.querySelector('#canvas'),document.querySelector('#labels'),catalogue.buildings,()=>{},()=>{throw Error('WebGL context lost')},()=>{},catalogue.sourceModelSha256);
await viewer.load();viewer.toggleLabels(false);viewer.select(building);await viewer.upgradeModel(building,'exterior');
const changed=new Set();const names=[];
viewer.scene.traverse(object=>{
 if(!object.isMesh)return;
 for(const material of Array.isArray(object.material)?object.material:[object.material]){
  if(!material||changed.has(material))continue;
  const name=material.name.replace(/^WEB_(?:DETAIL_)?/,'').replace(/^OLD_PAINT193_/,'');
  const finish=finishes.find(f=>f.name===name);if(!finish)continue;
  material.metalness=variant==='after'?0:finish.metallic;
  material.roughness=variant==='after'?.46:finish.roughness;
  material.needsUpdate=true;changed.add(material);names.push(material.name);
 }
});
window.capture=async job=>{
 if(job.code==='CAMPUS')viewer.home(false);else {viewer.select(building);await viewer.upgradeModel(building,'exterior');}
 if(job.view){viewer.camera.fov=job.view.fov;viewer.updateCameraProjection();viewer.moveCamera(viewer.camera.position.clone().fromArray(job.view.position),viewer.controls.target.clone().fromArray(job.view.target),false);}
 viewer.transition=null;viewer.controls.update();viewer.camera.updateMatrixWorld();viewer.renderer.shadowMap.needsUpdate=true;viewer.renderPipeline.resetHistory();viewer.renderPipeline.render();
 return {image:viewer.canvas.toDataURL('image/webp',.95).split(',')[1],changedMaterials:names,view:{position:viewer.camera.position.toArray(),target:viewer.controls.target.toArray(),fov:viewer.camera.fov}};
};window.ready=true;</script>`;
const server=await createServer({server:{host:'127.0.0.1',port:0},logLevel:'error',plugins:[{name:'old-private-paint-review',configureServer(server){server.middlewares.use('/__old-paint-review',(_req,res)=>{res.setHeader('Content-Type','text/html');res.end(html);});}}]});
let browser;
try{
 await server.listen();browser=await chromium.launch({args:['--use-angle=metal']});const records=[];
 for(const variant of ['before','after']){
  const page=await browser.newPage({viewport:{width:1400,height:1120},reducedMotion:'reduce'});const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto('http://127.0.0.1:'+server.httpServer.address().port+'/__old-paint-review?variant='+variant);
  await page.waitForFunction(()=>window.ready,null,{timeout:120000});
  for(const job of jobs){const capture=await page.evaluate(job=>window.capture(job),job);
   if(errors.length)throw Error(errors.join('\n'));
   if(capture.changedMaterials.length!==finishes.length*2)throw Error('Unexpected material scope: '+capture.changedMaterials.length);
   const bytes=Buffer.from(capture.image,'base64');await writeFile(directory+'/'+variant+'-'+job.name+'.webp',bytes);
   records.push({variant,view:job.name,changedMaterials:capture.changedMaterials,camera:capture.view,bytes:bytes.length});
  }await page.close();
 }
 await writeFile(directory+'/preview.json',JSON.stringify({sourceVersion:catalogue.version,nativeSourceUnchanged:true,renderer:'Production CampusViewer',finishes,records},null,2)+'\n');
 console.log('OLD_PAINT_PRIVATE_PREVIEW_COMPLETE',records.length);
}finally{await browser?.close();await server.close();}
