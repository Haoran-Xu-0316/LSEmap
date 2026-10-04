import {test,expect} from '@playwright/test';
import {createServer} from 'vite';
import {readFile,writeFile} from 'node:fs/promises';

// Inspect real decoded vertices, rather than trusting generated camera metadata.
test('every exterior and the shared PAN FAW frontage fit desktop and phone',async({page})=>{
 test.setTimeout(120000);
 const html=`<!doctype html><style>body{margin:0}#canvas{width:100vw;height:100vh}#labels{display:none}</style><div id="canvas"></div><div id="labels"></div><script type="module">
 import {CampusViewer} from '/src/viewer.js';
 const catalogue=await(await fetch('/models/catalogue.json')).json();
 const viewer=new CampusViewer(document.querySelector('#canvas'),document.querySelector('#labels'),catalogue.buildings,()=>{},()=>{throw Error('Context lost')},()=>{},catalogue.sourceModelSha256);
 await viewer.load();await Promise.all(catalogue.buildings.filter(b=>b.detailedExterior).map(b=>viewer.loadExterior(b)));
 const inspect=codes=>{let vertices=0,xmin=Infinity,xmax=-Infinity,ymin=Infinity,ymax=-Infinity,zmax=-Infinity;viewer.camera.updateMatrixWorld();
  for(const code of codes){const group=viewer.exteriors.get(code);group.updateMatrixWorld(true);group.traverse(o=>{if(!o.isMesh)return;const position=o.geometry.attributes.position;const point=viewer.camera.position.clone();for(let i=0;i<position.count;i++){point.fromBufferAttribute(position,i).applyMatrix4(o.matrixWorld).project(viewer.camera);vertices++;xmin=Math.min(xmin,point.x);xmax=Math.max(xmax,point.x);ymin=Math.min(ymin,point.y);ymax=Math.max(ymax,point.y);zmax=Math.max(zmax,point.z);}});}
  return {vertices,xmin,xmax,ymin,ymax,zmax,area:(xmax-xmin)*(ymax-ymin),distance:viewer.camera.position.distanceTo(viewer.controls.target)};
 };
 window.inspectExteriors=async()=>{const records=[];for(const building of catalogue.buildings.filter(b=>b.detailedExterior)){
  viewer.select(building);await viewer.upgradeModel(building,'exterior');viewer.transition=null;viewer.controls.update();
  const codes=[building.code];if(building.code==='PAN')codes.push('FAW');if(building.code==='FAW')codes.push('PAN');
  const fitted=inspect(codes),direction=viewer.camera.position.clone().sub(viewer.controls.target).normalize();
  viewer.fit(building.bounds,false,direction);const former=inspect([building.code]);
  records.push({code:building.code,codes,corners:building.exteriorFramingCorners.length,fitted,former});
 }return {version:catalogue.version,records};};window.ready=true;
 </script>`;
 const server=await createServer({server:{host:'127.0.0.1',port:0},logLevel:'error',plugins:[{name:'exterior-frame-check',configureServer(s){s.middlewares.use('/__frame-check',(_,res)=>{res.setHeader('Content-Type','text/html');res.end(html);});}}]});
 const errors=[],proof=[];page.on('pageerror',e=>errors.push(e.message));
 try{
  await server.listen();
  for(const width of [1440,390]){
   await page.setViewportSize({width,height:1000});await page.emulateMedia({reducedMotion:'reduce'});
   await page.goto(`http://127.0.0.1:${server.httpServer.address().port}/__frame-check`);await page.waitForFunction(()=>window.ready,null,{timeout:90000});
   const result=await page.evaluate(()=>window.inspectExteriors());expect(result.version).toBe('145');expect(result.records).toHaveLength(30);
   for(const record of result.records){const p=record.fitted;expect(record.corners,record.code).toBe(8);expect(p.vertices,record.code).toBeGreaterThan(0);
    expect(Math.max(Math.abs(p.xmin),Math.abs(p.xmax)),record.code+' horizontal '+width).toBeLessThan(.95);
    expect(Math.max(Math.abs(p.ymin),Math.abs(p.ymax)),record.code+' vertical '+width).toBeLessThan(.95);expect(p.zmax,record.code).toBeLessThan(1);
   }
   proof.push({width,...result});
  }
  expect(errors).toEqual([]);
  for(const code of ['OLD','61A','LRB']){const record=proof[0].records.find(r=>r.code===code);expect(record.fitted.area,code+' reduced empty space').toBeGreaterThan(record.former.area);}
  await writeFile('result/blender/stage145/camera-framing-verification.json',JSON.stringify({proof,errors},null,2)+'\n');
 }finally{await server.close();}
});
