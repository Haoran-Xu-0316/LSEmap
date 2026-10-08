/** Private before/after review using the production renderer; no published assets are overwritten. */
import {createServer} from 'vite';
import {chromium} from 'playwright';
import {readFile,writeFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
const directory='result/blender/saw-screen-review';
const jobs=JSON.parse(await readFile('web/tools/gallery-views.json','utf8')).filter(j=>['saw-brick','saw-exterior'].includes(j.name));
const assets={};
for(const variant of ['before','after']){
 const bytes=await readFile(`${directory}/${variant}.glb`);
 assets[variant]={bytes,sha256:createHash('sha256').update(bytes).digest('hex')};
}
const html=`<!doctype html><style>html,body{margin:0}#canvas{width:1400px;height:1120px}#labels{display:none}</style><div id="canvas"></div><div id="labels"></div><script type="module">
import {CampusViewer} from '/src/viewer.js';
const variant=new URLSearchParams(location.search).get('variant');
const catalogue=await (await fetch('/models/catalogue.json')).json();
const building=catalogue.buildings.find(b=>b.code==='SAW');
const asset=await(await fetch('/__saw-review/metadata?variant='+variant)).json();
building.detailedExterior={...building.detailedExterior,url:'/__saw-review/'+variant+'.glb',sha256:asset.sha256,bytes:asset.bytes};
const viewer=new CampusViewer(document.querySelector('#canvas'),document.querySelector('#labels'),catalogue.buildings,()=>{},()=>{throw Error('WebGL context lost')},()=>{},catalogue.sourceModelSha256);
await viewer.load();viewer.toggleLabels(false);viewer.select(building);await viewer.upgradeModel(building,'exterior');
window.capture=async(job)=>{
 if(viewer.canvas.dataset.detailReady!=='exterior-SAW')throw Error('Detail unavailable');
 if(job.view){viewer.camera.fov=job.view.fov;viewer.updateCameraProjection();viewer.moveCamera(viewer.camera.position.clone().fromArray(job.view.position),viewer.controls.target.clone().fromArray(job.view.target),false);}
 viewer.transition=null;viewer.controls.update();viewer.camera.updateMatrixWorld();viewer.renderer.shadowMap.needsUpdate=true;viewer.renderPipeline.resetHistory();viewer.renderPipeline.render();
 return {image:viewer.canvas.toDataURL('image/webp',.95).split(',')[1],detail:viewer.canvas.dataset.detailReady};
};window.ready=true;</script>`;
const server=await createServer({server:{host:'127.0.0.1',port:0},logLevel:'error',plugins:[{name:'saw-private-review',configureServer(s){s.middlewares.use('/__saw-review',(req,res)=>{
 const url=new URL(req.url,'http://local');
 if(url.pathname==='/metadata'){const a=assets[url.searchParams.get('variant')];res.setHeader('Content-Type','application/json');res.end(JSON.stringify({sha256:a.sha256,bytes:a.bytes.length}));}
 else if(/^\/(before|after)\.glb$/.test(url.pathname)){res.setHeader('Content-Type','model/gltf-binary');res.end(assets[url.pathname.slice(1,-4)].bytes);}
 else{res.setHeader('Content-Type','text/html');res.end(html);}
});}}]});
let browser;
try{
 await server.listen();browser=await chromium.launch({args:['--use-angle=metal']});
 const records=[];
 for(const variant of ['before','after']){
  const page=await browser.newPage({viewport:{width:1400,height:1120},reducedMotion:'reduce'});const errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  await page.goto(`http://127.0.0.1:${server.httpServer.address().port}/__saw-review/?variant=${variant}`);
  await page.waitForFunction(()=>window.ready,null,{timeout:120000});
  for(const job of jobs){const capture=await page.evaluate(j=>window.capture(j),job);if(errors.length)throw Error(errors.join('\n'));
   const bytes=Buffer.from(capture.image,'base64');await writeFile(`${directory}/${variant}-${job.name}.webp`,bytes);
   records.push({variant,view:job.name,detail:capture.detail,assetSha256:assets[variant].sha256,bytes:bytes.length});
  }await page.close();
 }
 await writeFile(`${directory}/web-review.json`,JSON.stringify({renderer:'Production CampusViewer',records},null,2)+'\n');
 console.log('SAW_SCREEN_REVIEW_COMPLETE',records.length);
}finally{await browser?.close();await server.close();}
