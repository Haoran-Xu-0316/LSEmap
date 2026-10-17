import {test,expect} from '@playwright/test';
import {createServer} from 'vite';
import {mkdir,writeFile} from 'node:fs/promises';

/** Exercise actual OrbitControls and the actual viewer queue, with controlled clocks. */
test('orbit inertia follows elapsed time across display and input-event rates',async({page})=>{
 const server=await createServer({logLevel:'error',server:{host:'127.0.0.1',port:0}});
 try{await server.listen();await page.route('**/__interaction239',r=>r.fulfill({contentType:'text/html',body:'<!doctype html><body></body>'}));await page.goto('http://127.0.0.1:'+server.httpServer.address().port+'/__interaction239');
 const result=await page.evaluate(async()=>{
  const {THREE,OrbitControls,useTimeBasedDamping,stopControlInertia}=await import('/tests/interaction239-fixture.js');
  const records=[];
  for(const timed of [false,true])for(const hz of [30,60,120])for(const extraInputs of [0,2]){
   const canvas=document.createElement('canvas');canvas.style.cssText='width:800px;height:600px';document.body.append(canvas);canvas.setPointerCapture=()=>{};canvas.releasePointerCapture=()=>{};
   const camera=new THREE.PerspectiveCamera(38,4/3,.02,6000);camera.position.set(0,3,12);
   const controls=new OrbitControls(camera,canvas);controls.target.set(0,0,0);controls.enableDamping=true;controls.dampingFactor=.08;controls.update();
   let now=0;if(timed)useTimeBasedDamping(controls,()=>now);
   const initial=controls.getAzimuthalAngle();
   // Dispatch one drag impulse through real OrbitControls, then vary update cadence.
   canvas.dispatchEvent(new PointerEvent('pointerdown',{pointerId:1,pointerType:'mouse',button:0,buttons:1,clientX:300,clientY:200,bubbles:true}));
   canvas.dispatchEvent(new PointerEvent('pointermove',{pointerId:1,pointerType:'mouse',button:0,buttons:1,clientX:390,clientY:200,bubbles:true}));
   canvas.dispatchEvent(new PointerEvent('pointerup',{pointerId:1,pointerType:'mouse',button:0,buttons:0,clientX:390,clientY:200,bubbles:true}));
   for(let frame=1;frame<=hz*.3;frame++){
    const start=(frame-1)*1000/hz;
    for(let extra=1;extra<=extraInputs;extra++){now=start+(1000/hz)*extra/(extraInputs+1);controls.update();}
    now=frame*1000/hz;controls.update();
   }
   const angle=controls.getAzimuthalAngle()-initial,position=camera.position.clone(),target=controls.target.clone();stopControlInertia(controls);const stopPoseError=camera.position.distanceTo(position)+controls.target.distanceTo(target);for(let i=0;i<20;i++){now+=1000/hz;controls.update();}const resumedAngle=Math.abs(controls.getAzimuthalAngle()-initial-angle);records.push({timed,hz,extraInputs,angle,stopPoseError,resumedAngle});controls.dispose();canvas.remove();
  }
  return records;
 });
 const spread=rows=>Math.max(...rows.map(r=>r.angle))-Math.min(...rows.map(r=>r.angle));
 const before=spread(result.filter(r=>!r.timed)),after=spread(result.filter(r=>r.timed));
 expect(before).toBeGreaterThan(.1);expect(after).toBeLessThan(.000001);for(const row of result){expect(row.stopPoseError).toBeLessThan(1e-9);expect(row.resumedAngle).toBeLessThan(1e-9);}
 await mkdir('result/blender/stage239/browser',{recursive:true});await writeFile('result/blender/stage239/browser/inertia-consistency.json',JSON.stringify({records:result,beforeSpreadRadians:before,afterSpreadRadians:after,actualOrbitControls:true,scope:'Deterministic camera response; not a device FPS claim'},null,2)+'\n');
 }finally{await server.close();}
});

test('background attachment waits for inertia and rechecks a late wheel gesture',async({page})=>{
 const server=await createServer({logLevel:'error',server:{host:'127.0.0.1',port:0}});
 try{await server.listen();await page.route('**/__interaction239',r=>r.fulfill({contentType:'text/html',body:'<!doctype html><body></body>'}));await page.goto('http://127.0.0.1:'+server.httpServer.address().port+'/__interaction239');
 const result=await page.evaluate(async()=>{
  const {CampusViewer}=await import('/src/viewer.js');
  // Use the production queue and its production camera-change listener.
  const stage=document.createElement('div');stage.style.cssText='width:400px;height:300px';document.body.append(stage);const labels=document.createElement('div');document.body.append(labels);
  const viewer=new CampusViewer(stage,labels,[],()=>{},()=>{});cancelAnimationFrame(viewer.frame);viewer.transition=null;
  const originalIdle=window.requestIdleCallback,originalCancel=window.cancelIdleCallback;let pending=null;
  window.requestIdleCallback=callback=>{pending=callback;return 1;};window.cancelIdleCallback=()=>{pending=null;};
  const wait=ms=>new Promise(r=>setTimeout(r,ms));
  try{
   viewer.lastNavigationAt=performance.now()-1000;let resolved=false;
   const deferred=viewer.waitForBackgroundFrame().then(value=>{resolved=value;});
   const queued=pending;pending=null;
   // A complete wheel start/end may happen while the idle callback is pending.
   viewer.canvas.dispatchEvent(new WheelEvent('wheel',{deltaY:100,bubbles:true,cancelable:true}));queued();await wait(60);
   const lateWheelBlocked=!resolved;
   // Camera changes after pointerup are real damping motion, not a held gesture.
   viewer.camera.position.x+=.05;viewer.controls.update();await wait(160);const inertiaBlocked=!resolved;
   await wait(100);if(pending){const ready=pending;pending=null;ready();}await deferred;
   viewer.interacting=true;viewer.lastNavigationAt=performance.now();const priority=await viewer.waitForBackgroundFrame(()=>true);
   viewer.interacting=false;viewer.lastNavigationAt=performance.now();let abortedValue=null;const aborted=viewer.waitForBackgroundFrame().then(v=>{abortedValue=v;});viewer.dispose();await aborted;
   return {lateWheelBlocked,inertiaBlocked,resumesWhenSettled:resolved,selectedBuildingPriority:priority,abortCancels:abortedValue===false};
  }finally{window.requestIdleCallback=originalIdle;window.cancelIdleCallback=originalCancel;if(!viewer.disposed)viewer.dispose();stage.remove();labels.remove();}
 });
 expect(result).toEqual({lateWheelBlocked:true,inertiaBlocked:true,resumesWhenSettled:true,selectedBuildingPriority:true,abortCancels:true});
 await mkdir('result/blender/stage239/browser',{recursive:true});await writeFile('result/blender/stage239/browser/background-navigation.json',JSON.stringify(result,null,2)+'\n');
 }finally{await server.close();}
});


test('wheel input uses one scene draw and restores a sharp still without resizing',async({page})=>{
 const server=await createServer({logLevel:'error',server:{host:'127.0.0.1',port:0}});
 try{await server.listen();await page.route('**/__wheel239',r=>r.fulfill({contentType:'text/html',body:'<!doctype html><body></body>'}));await page.goto('http://127.0.0.1:'+server.httpServer.address().port+'/__wheel239');
 const result=await page.evaluate(async()=>{
  const {CampusViewer}=await import('/src/viewer.js');
  const stage=document.createElement('div');stage.style.cssText='width:800px;height:600px';document.body.append(stage);const labels=document.createElement('div');document.body.append(labels);
  const viewer=new CampusViewer(stage,labels,[],()=>{},()=>{});cancelAnimationFrame(viewer.frame);viewer.transition=null;
  const render=viewer.renderer.render.bind(viewer.renderer);let draws=0;viewer.renderer.render=(scene,camera)=>{if(scene===viewer.scene)draws++;return render(scene,camera);};
  const pixels=viewer.canvas.width*viewer.canvas.height;
  viewer.canvas.dispatchEvent(new WheelEvent('wheel',{deltaY:100,bubbles:true,cancelable:true}));
  viewer.tick(performance.now());cancelAnimationFrame(viewer.frame);const wheelDraws=draws,motionSamples=2**viewer.renderPipeline.scenePass.sampleLevel;
  await new Promise(r=>setTimeout(r,250));const settleDraws=[];for(let i=0;i<4;i++){draws=0;viewer.tick(performance.now());cancelAnimationFrame(viewer.frame);settleDraws.push(draws);}
  const result={wheelDraws,motionSamples,settleDraws,idleSamples:2**viewer.renderPipeline.scenePass.sampleLevel,pixelsUnchanged:pixels===viewer.canvas.width*viewer.canvas.height,settled:!viewer.renderPipeline.needsSettle};
  viewer.dispose();stage.remove();labels.remove();return result;
 });
 expect(result).toEqual({wheelDraws:1,motionSamples:1,settleDraws:[1,1,1,1],idleSamples:4,pixelsUnchanged:true,settled:true});
 await mkdir('result/blender/stage239/browser',{recursive:true});await writeFile('result/blender/stage239/browser/wheel-render-budget.json',JSON.stringify(result,null,2)+'\n');
 }finally{await server.close();}
});
