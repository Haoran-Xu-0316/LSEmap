import {test,expect} from '@playwright/test';
import {createServer} from 'vite';
import {mkdir,writeFile} from 'node:fs/promises';

// This acceptance fixture owns its browser/server and renders the real viewer.
test('sharp outdoor sky and dry metre-scale roads remain stable on desktop and mobile',async({page})=>{
 test.setTimeout(150000);
 const directory='result/web/outdoor202';await mkdir(directory,{recursive:true});
 const errors=[];page.on('pageerror',error=>errors.push(error.message));page.on('console',message=>{if(message.type()==='error')errors.push(message.text());});
 const server=await createServer({server:{host:'127.0.0.1',port:0},logLevel:'error',plugins:[{
  name:'outdoor202-acceptance',configureServer(server){server.middlewares.use('/__outdoor202',(_,response)=>{
   response.setHeader('Content-Type','text/html');response.end(`<!doctype html><style>body{margin:0}#stage{width:100vw;height:100vh}#labels{display:none}</style><div id="stage"></div><div id="labels"></div><script type="module">
   import {CampusViewer} from '/src/viewer.js';
   const catalogue=await(await fetch('/models/catalogue.json')).json();
   const viewer=new CampusViewer(document.querySelector('#stage'),document.querySelector('#labels'),catalogue.buildings,()=>{},()=>{throw Error('WebGL context lost')},()=>{},catalogue.sourceModelSha256);
   await viewer.load();await viewer.environmentReady;
   await Promise.all(['STC','OLD','MAR','SAW'].map(code=>viewer.loadExterior(catalogue.buildings.find(item=>item.code===code))));
   cancelAnimationFrame(viewer.frame);viewer.controls.enableDamping=false;viewer.transition=null;
   window.viewer=viewer;window.catalogue=catalogue;window.ready=true;
   </script>`);
  });}
 }]});
 const records=[];
 try{
  await server.listen();await page.goto('http://127.0.0.1:'+server.httpServer.address().port+'/__outdoor202');
  await page.waitForFunction(()=>window.ready,null,{timeout:110000});
  for(const width of [1440,390]){
   await page.setViewportSize({width,height:960});
   for(const view of ['overview','street','road','sky-probe','interior-background']){
    const record=await page.evaluate(({view,width})=>{
     viewer.resize();viewer.home(false);viewer.toggleContext(true);
     if(view==='street')viewer.moveCamera(viewer.camera.position.clone().set(-43,3.2,28),viewer.controls.target.clone().set(-52,18,7),false);
     if(view==='road')viewer.moveCamera(viewer.camera.position.clone().set(-28.22,7,-89),viewer.controls.target.clone().set(-21.03,0,-79),false);
     if(view==='sky-probe'){viewer.camera.fov=70;viewer.updateCameraProjection();viewer.moveCamera(viewer.camera.position.clone().set(0,100,0),viewer.controls.target.clone().set(0,120,-80),false);}
     if(view==='interior-background')viewer.mode='interior';
     viewer.transition=null;viewer.controls.update();viewer.camera.updateMatrixWorld();viewer.renderPipeline.resetHistory();
     const environment=viewer.scene.environment.uuid,textureVersion=viewer.skyTexture.version;
     viewer.renderPipeline.render({moving:true});viewer.renderer.getContext().finish();
     const times=[];for(let i=0;i<7;i++){
      const start=performance.now();viewer.renderPipeline.render({moving:true});viewer.renderer.getContext().finish();times.push(performance.now()-start);
     }
     viewer.renderPipeline.render({moving:false});viewer.renderer.getContext().finish();
     return {view,width,skyReady:viewer.canvas.dataset.skyReady,backdropReady:viewer.canvas.dataset.skyBackdropReady,backdropUsed:viewer.scene.background===viewer.skyBackdrop,background:viewer.scene.background.isTexture?'sky':'neutral',environmentUnchanged:environment===viewer.scene.environment.uuid,textureUnchanged:textureVersion===viewer.skyTexture.version,motionMs:times.sort((a,b)=>a-b)[3],textures:viewer.renderer.info.memory.textures};
    },{view,width});
    await page.locator('canvas').screenshot({path:directory+'/'+view+'-'+width+'.png'});records.push(record);
    expect(record.skyReady).toBe('true');expect(record.backdropReady).toBe('true');expect(record.environmentUnchanged).toBe(true);expect(record.textureUnchanged).toBe(true);expect(record.motionMs).toBeLessThan(80);
   }
  }
  await writeFile(directory+'/measurement.json',JSON.stringify({records,errors},null,2)+'\n');
  expect(errors).toEqual([]);
  for(const record of records){const sky=['street','sky-probe'].includes(record.view);expect(record.background).toBe(sky?'sky':'neutral');expect(record.backdropUsed).toBe(sky);}
  await page.evaluate(()=>viewer.dispose());
  // Losing only the optional photograph must retain the HDR sky and lighting.
  await page.route('**/environment/daylight-sky-2k.webp', route=>route.abort());
  await page.goto('http://127.0.0.1:'+server.httpServer.address().port+'/__outdoor202');
  await page.waitForFunction(()=>window.ready,null,{timeout:110000});
  const fallback=await page.evaluate(()=>{
   viewer.home(false);viewer.moveCamera(viewer.camera.position.clone().set(0,100,0),viewer.controls.target.clone().set(0,120,-80),false);
   viewer.transition=null;viewer.controls.update();viewer.renderPipeline.render({moving:true});
   return {ready:viewer.canvas.dataset.skyReady,backdrop:viewer.canvas.dataset.skyBackdropReady,hdrBackground:viewer.scene.background===viewer.skyTexture};
  });
  expect(fallback).toEqual({ready:'true',backdrop:'fallback',hdrBackground:true});
  await writeFile(directory+'/fallback.json',JSON.stringify(fallback,null,2)+'\n');
  await page.evaluate(()=>viewer.dispose());
 }finally{await page.evaluate(()=>{if(window.viewer&&!window.viewer.disposed)window.viewer.dispose();}).catch(()=>{});await server.close();}
});
