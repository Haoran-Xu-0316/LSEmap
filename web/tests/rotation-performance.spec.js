import {test,expect} from '@playwright/test';
import {createServer} from 'vite';
import {mkdir,writeFile} from 'node:fs/promises';

test('rotation reduces measured scene work and restores sharp idle rendering',async({page})=>{
 test.setTimeout(150000);
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 const server=await createServer({server:{host:'127.0.0.1',port:0},logLevel:'error',plugins:[{name:'rotation-performance',configureServer(server){server.middlewares.use('/__rotation',(_,res)=>{
 res.setHeader('Content-Type','text/html');res.end(`<!doctype html><style>body{margin:0}#stage{width:960px;height:768px}#labels{display:none}</style><div id="stage"></div><div id="labels"></div><script type="module">
 import {CampusViewer} from '/src/viewer.js';
 const catalogue=await(await fetch('/models/catalogue.json')).json();
 const viewer=new CampusViewer(document.querySelector('#stage'),document.querySelector('#labels'),catalogue.buildings,()=>{},()=>{throw Error('Context lost')},()=>{},catalogue.sourceModelSha256);
 await viewer.load();await Promise.all(catalogue.buildings.filter(b=>b.detailedExterior).map(b=>viewer.loadExterior(b)));
 cancelAnimationFrame(viewer.frame);viewer.transition=null;viewer.controls.enableDamping=false;viewer.home(false);
 window.viewer=viewer;window.catalogue=catalogue;window.ready=true;
 </script>`);});}}]});
 try{
 await server.listen();await page.goto('http://127.0.0.1:'+server.httpServer.address().port+'/__rotation');
 await page.waitForFunction(()=>window.ready,null,{timeout:90000});
 const proof=await page.evaluate(async()=>{
  const {renderer,camera,renderPipeline:pipeline}=viewer;const gl=renderer.getContext();
  const records=[];let sceneDraws=0;const render=renderer.render.bind(renderer);
  renderer.render=(scene,camera)=>{if(scene===viewer.scene)sceneDraws++;return render(scene,camera);};
  const median=a=>a.slice().sort((x,y)=>x-y)[Math.floor(a.length/2)];
  for(const code of ['CAMPUS','CBG']){
   if(code==='CBG'){const building=catalogue.buildings.find(b=>b.code===code);viewer.select(building);await viewer.upgradeModel(building,'exterior');viewer.transition=null;viewer.fit(building.bounds,false);}
   const position=camera.position.clone(),projection=camera.projectionMatrix.clone();
   const times={idle:[],motion:[]};const draws={};
   for(let pair=0;pair<9;pair++)for(const moving of (pair%2?[true,false]:[false,true])){
    pipeline.resetHistory();pipeline.render({moving});gl.finish();sceneDraws=0;
    const start=performance.now();pipeline.render({moving});gl.finish();
    const key=moving?'motion':'idle';times[key].push(performance.now()-start);draws[key]=sceneDraws;
   }
   pipeline.render({moving:false});
   records.push({code,idleMs:median(times.idle),motionMs:median(times.motion),sceneDraws:draws,idleSamples:2**pipeline.scenePass.sampleLevel,settled:!pipeline.needsSettle,ratio:renderer.getPixelRatio(),cameraUnchanged:position.equals(camera.position)&&projection.equals(camera.projectionMatrix),times});
  }
  viewer.controls.enableDamping=true;viewer.needsRender=true;viewer.frame=requestAnimationFrame(viewer.tick);
  return records;
 });
 await mkdir('result/web/rotation-performance',{recursive:true});await writeFile('result/web/rotation-performance/measurement.json',JSON.stringify(proof,null,2));
 for(const record of proof){expect(record.sceneDraws.idle).toBe(4);expect(record.sceneDraws.motion).toBe(1);expect(record.motionMs).toBeLessThan(record.idleMs*.9);expect(record.idleSamples).toBe(4);expect(record.settled).toBe(true);expect(record.cameraUnchanged).toBe(true);}
 const canvas=page.locator('canvas'),box=await canvas.boundingBox();
 await page.mouse.move(box.x+500,box.y+300);await page.mouse.down();await page.mouse.move(box.x+660,box.y+340,{steps:16});
 expect(await page.evaluate(()=>viewer.renderPipeline.scenePass.sampleLevel)).toBe(0);
 await page.mouse.up();await page.waitForFunction(()=>!viewer.needsRender&&!viewer.renderPipeline.needsSettle);
 expect(await page.evaluate(()=>viewer.renderPipeline.scenePass.sampleLevel)).toBe(2);
 const idle=await page.evaluate(()=>viewer.renderPipeline.temporalPass.frame);await page.waitForTimeout(300);expect(await page.evaluate(()=>viewer.renderPipeline.temporalPass.frame)).toBe(idle);
 await canvas.screenshot({path:'result/web/rotation-performance/restored.png'});expect(errors).toEqual([]);
 await page.evaluate(()=>viewer.dispose());
 }finally{await server.close();}
});
