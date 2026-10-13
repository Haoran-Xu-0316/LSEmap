import {test,expect} from '@playwright/test';
import {createServer} from 'vite';
import {mkdir,writeFile} from 'node:fs/promises';

test('captured ground finishes work on streets and mobile and survive unavailable assets',async({page})=>{
 test.setTimeout(160000);
 const errors=[];page.on('pageerror',error=>errors.push(error.message));
 const server=await createServer({server:{host:'127.0.0.1',port:0},logLevel:'error',plugins:[{name:'ground-proof',configureServer(server){server.middlewares.use('/__ground',(_,res)=>{
  res.setHeader('Content-Type','text/html');res.end(`<!doctype html><style>body{margin:0}#stage{width:100vw;height:100vh}#labels{display:none}</style><div id="stage"></div><div id="labels"></div><script type="module">
  import {CampusViewer} from '/src/viewer.js';
  const catalogue=await(await fetch('/models/catalogue.json')).json();
  const viewer=new CampusViewer(document.querySelector('#stage'),document.querySelector('#labels'),catalogue.buildings,()=>{},()=>{throw Error('Context lost')},()=>{},catalogue.sourceModelSha256);
  await viewer.load();await viewer.environmentReady;await Promise.all(catalogue.buildings.filter(b=>b.detailedExterior).map(b=>viewer.loadExterior(b)));cancelAnimationFrame(viewer.frame);viewer.transition=null;viewer.controls.enableDamping=false;
  window.viewer=viewer;window.ready=true;
  </script>`);
 });}}]});
 const folder='result/web/ground-acceptance';await mkdir(folder,{recursive:true});
 try{
  await server.listen();const url='http://127.0.0.1:'+server.httpServer.address().port+'/__ground';
  await page.goto(url);await page.waitForFunction(()=>window.ready,null,{timeout:100000});
  const proof=[];
  for(const width of [1440,390]){
   await page.setViewportSize({width,height:960});
   for(const captured of [false,true]){
    const record=await page.evaluate(({width,captured})=>{
     viewer.resize();viewer.home(false);viewer.moveCamera(viewer.camera.position.clone().set(-28.22,7,-89),viewer.controls.target.clone().set(-21.03,0,-79),false);
     viewer.transition=null;viewer.controls.update();viewer.groundTextures.ready.value=Number(captured);viewer.renderPipeline.resetHistory();
     viewer.renderer.shadowMap.needsUpdate=true;viewer.renderPipeline.render({moving:true});viewer.renderer.getContext().finish();
     const times=[];for(let i=0;i<7;i++){const start=performance.now();viewer.renderPipeline.render({moving:true});viewer.renderer.getContext().finish();times.push(performance.now()-start);}
     viewer.renderer.info.autoReset=false;viewer.renderer.info.reset();
     viewer.renderPipeline.render({moving:true});const triangles=viewer.renderer.info.render.triangles;viewer.renderer.info.autoReset=true;
     for(let i=0;i<6;i++)viewer.renderPipeline.render({moving:false});
     return {width,captured,groundReady:viewer.canvas.dataset.groundReady,medianMs:times.sort((a,b)=>a-b)[3],triangles,textureCount:viewer.renderer.info.memory.textures,compiledPrograms:viewer.renderer.info.programs.length};
    },{width,captured});
    expect(record.groundReady).toBe('true');proof.push(record);
    await page.screenshot({path:`${folder}/street-${width}-${captured?'captured':'fallback'}.png`});
   }
  }
  for(const width of [1440,390]){
   const [fallback,captured]=proof.filter(item=>item.width===width);
   expect(captured.triangles).toBe(fallback.triangles);expect(captured.textureCount-fallback.textureCount).toBeLessThanOrEqual(2);
   expect(captured.medianMs).toBeLessThan(200);
  }
  await page.route('**/environment/*-finish-512.webp',route=>route.fulfill({status:404,body:'unavailable'}));
  await page.goto(url);await page.waitForFunction(()=>window.ready,null,{timeout:100000});
  const fallback=await page.evaluate(()=>({groundReady:viewer.canvas.dataset.groundReady,ready:viewer.canvas.dataset.ready,slotsReady:viewer.groundTextures.ready.value}));
  expect(fallback).toEqual({groundReady:'fallback',ready:'true',slotsReady:0});expect(errors).toEqual([]);
  await writeFile(folder+'/verification.json',JSON.stringify({proof,fallback,errors},null,2)+'\n');
 }finally{await server.close();}
});
