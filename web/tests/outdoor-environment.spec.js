import {test,expect} from '@playwright/test';
import {createServer} from 'vite';
import {mkdir,writeFile} from 'node:fs/promises';

test('outdoor surfaces and optional sky render on desktop and mobile with bounded scene work',async({page})=>{
 test.setTimeout(160000);
 const errors=[];page.on('pageerror',e=>errors.push(e.message));page.on('console',m=>{if(m.type()==='error')errors.push(m.text());});
 const server=await createServer({server:{host:'127.0.0.1',port:0},logLevel:'error',plugins:[{name:'outdoor-acceptance',configureServer(server){server.middlewares.use('/__outdoor',(_,res)=>{
 res.setHeader('Content-Type','text/html');res.end(`<!doctype html><style>body{margin:0}#stage{width:100vw;height:100vh}#labels{display:none}</style><div id="stage"></div><div id="labels"></div><script type="module">
 import {CampusViewer} from '/src/viewer.js';
 const catalogue=await(await fetch('/models/catalogue.json')).json();
 const viewer=new CampusViewer(document.querySelector('#stage'),document.querySelector('#labels'),catalogue.buildings,()=>{},()=>{throw Error('Context lost')},()=>{},catalogue.sourceModelSha256);
 await viewer.load();await viewer.environmentReady;
 await Promise.all(['OLD','MAR','CBG','SAW'].map(code=>viewer.loadExterior(catalogue.buildings.find(b=>b.code===code))));
 cancelAnimationFrame(viewer.frame);viewer.transition=null;viewer.controls.enableDamping=false;
 window.viewer=viewer;window.ready=true;
 </script>`);});}}]});
 const directory='result/web/outdoor-acceptance';await mkdir(directory,{recursive:true});
 try{
 await server.listen();await page.goto('http://127.0.0.1:'+server.httpServer.address().port+'/__outdoor');
 await page.waitForFunction(()=>window.ready,null,{timeout:110000});
 const proof=[];
 for(const width of [1440,390]) {
  await page.setViewportSize({width,height:960});
  for(const view of ['overview','houghton','mar-approach','skyline']) {
   const record=await page.evaluate(({view,width})=>{
    viewer.resize();viewer.toggleContext(true);viewer.home(false);
    if(view==='houghton')viewer.moveCamera(viewer.camera.position.clone().set(3,3.2,94),viewer.controls.target.clone().set(24,8.5,44),false);
    if(view==='skyline')viewer.moveCamera(viewer.camera.position.clone().set(0,5,127),viewer.controls.target.clone().set(22,28,48),false);
    if(view==='mar-approach')viewer.moveCamera(viewer.camera.position.clone().set(-28.22,5.2,-83.5),viewer.controls.target.clone().set(-21.03,4.3,-65.7),false);
    viewer.transition=null;viewer.controls.update();viewer.camera.updateMatrixWorld();
    viewer.renderPipeline.resetHistory();viewer.renderer.shadowMap.needsUpdate=true;
    viewer.renderPipeline.render({moving:true});viewer.renderer.getContext().finish();
    const times=[];
    for(let i=0;i<7;i++) {
     const start=performance.now();viewer.renderPipeline.render({moving:true});viewer.renderer.getContext().finish();times.push(performance.now()-start);
    }
    viewer.renderPipeline.render({moving:false});
    let triangles=0;viewer.scene.traverse(o=>{if(o.isMesh&&o.visible)triangles+=(o.geometry.index?.count??o.geometry.attributes.position.count)/3;});
    return {view,width,skyReady:viewer.canvas.dataset.skyReady,background:viewer.scene.background.isTexture?'sky':'neutral',motionMs:times.sort((a,b)=>a-b)[3],triangles,programs:viewer.renderer.info.programs.length};
   },{view,width});
   expect(record.skyReady).toBe('true');expect(record.background).toBe(view==='overview'?'neutral':'sky');
   expect(record.motionMs).toBeLessThan(80);
   await page.locator('canvas').screenshot({path:directory+'/'+view+'-'+width+'.png'});proof.push(record);
  }
 }
 expect(errors).toEqual([]);await writeFile(directory+'/measurement.json',JSON.stringify(proof,null,2)+'\n');
 await page.evaluate(()=>viewer.dispose());
 }finally{await server.close();}
});
