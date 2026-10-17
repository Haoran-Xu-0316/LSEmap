import {test,expect} from '@playwright/test';
import {createServer} from 'vite';
import {readFile,mkdir,writeFile} from 'node:fs/promises';

test('current streets and static daylight render without extra orbit downloads',async({page})=>{
 test.setTimeout(150000);
 const errors=[],requests=[];
 page.on('pageerror',e=>errors.push(e.message));
 page.on('console',m=>{if(m.type()==='error')errors.push(m.text());});
 page.on('request',r=>{if(r.url().includes('/environment/'))requests.push(r.url());});
 const server=await createServer({server:{host:'127.0.0.1',port:0},logLevel:'error',plugins:[{name:'outdoor207',configureServer(s){s.middlewares.use('/__outdoor207',(_,res)=>{
  res.setHeader('Content-Type','text/html');res.end(`<!doctype html><style>body{margin:0}#stage{width:100vw;height:100vh}#labels{display:none}</style><div id="stage"></div><div id="labels"></div><script type="module">
  import {CampusViewer} from '/src/viewer.js';
  const c=await(await fetch('/models/catalogue.json')).json();
  const v=new CampusViewer(document.querySelector('#stage'),document.querySelector('#labels'),c.buildings,()=>{},()=>{throw Error('Context lost')},()=>{},c.sourceModelSha256);
  await v.load();await v.environmentReady;await Promise.all(c.buildings.filter(b=>b.detailedExterior).map(b=>v.loadExterior(b)));
  cancelAnimationFrame(v.frame);v.transition=null;v.controls.enableDamping=false;window.viewer=v;window.ready=true;
  </script>`);
 });}}]});
 const folder='result/blender/stage207/outdoor';await mkdir(folder,{recursive:true});
 const jobs=JSON.parse(await readFile('web/tools/gallery-views.json','utf8'));
 const views=jobs.filter(j=>['lse-square-paving','portsmouth-street'].includes(j.name)).concat([{name:'skyline',view:{position:[-43,3.2,29],target:[-49,10,7],fov:58}}]);
 try{
  await server.listen();await page.goto('http://127.0.0.1:'+server.httpServer.address().port+'/__outdoor207');await page.waitForFunction(()=>window.ready,null,{timeout:100000});
  const requestsBefore=requests.length,proof=[];
  for(const width of [1440,390]){
   await page.setViewportSize({width,height:960});
   for(const job of views){
    const record=await page.evaluate(job=>{
     const v=window.viewer;v.resize();v.home(false);v.toggleContext(true);v.camera.fov=job.view.fov;v.updateCameraProjection();
     v.moveCamera(v.camera.position.clone().fromArray(job.view.position),v.controls.target.clone().fromArray(job.view.target),false);
     v.transition=null;v.controls.update();v.camera.updateMatrixWorld();v.renderPipeline.resetHistory();v.renderer.shadowMap.needsUpdate=true;
     for(let i=0;i<6;i++)v.renderPipeline.render({moving:false});
     const times=[];for(let i=0;i<5;i++){const start=performance.now();v.renderPipeline.render({moving:true});v.renderer.getContext().finish();times.push(performance.now()-start);}
     const finishes=new Set();v.scene.traverse(o=>{for(const m of Array.isArray(o.material)?o.material:[o.material])if(m&&/CBG(?:203_ROOF|205_PODIUM)_paving|LRB_NEXT_PLAZA155_stone/.test(m.name))finishes.add(m.customProgramCacheKey());});
     return{name:job.name,sky:Boolean(v.scene.background.isTexture),skyReady:v.canvas.dataset.skyReady,backdropReady:v.canvas.dataset.skyBackdropReady,groundReady:v.canvas.dataset.groundReady,reliefReady:v.canvas.dataset.groundReliefReady,medianMs:times.sort((a,b)=>a-b)[2],finishes:[...finishes],meshes:v.renderer.info.memory.geometries};
    },job);
    expect(record.skyReady).toBe('true');expect(record.backdropReady).toBe('true');expect(record.groundReady).toBe('true');expect(record.reliefReady).toBe('true');expect(record.sky).toBe(true);expect(record.finishes.length).toBeGreaterThan(0);expect(record.finishes.every(key=>key.includes('captured'))).toBe(true);
    await page.screenshot({path:folder+'/'+job.name+'-'+width+'.png'});proof.push({width,...record});
   }
  }
  expect(requests.length).toBe(requestsBefore);expect(errors).toEqual([]);
  await writeFile(folder+'/verification.json',JSON.stringify({proof,environmentRequests:requests.length,noOrbitDownloads:true,errors},null,2)+'\n');
  await page.evaluate(()=>window.viewer.dispose());
 }finally{await server.close();}
});
