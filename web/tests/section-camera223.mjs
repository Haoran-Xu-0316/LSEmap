/** Check authored public-level cameras with the real viewer and model assets.
 * The temporary harness and GPU context are closed after the check. Nothing is
 * added to the public build or exposed by the production page.
 */
import {createServer} from 'vite';
import {chromium} from 'playwright';
import {readFile,mkdir,writeFile} from 'node:fs/promises';
import assert from 'node:assert/strict';
const catalogue=JSON.parse(await readFile('web/public/models/catalogue.json','utf8'));
const authoring=JSON.parse(await readFile('web/tools/building-metadata.json','utf8'));
const buildings=catalogue.buildings;
for(const building of buildings){
 const authored=authoring.buildings.find(item=>item.code===building.code);
 assert.deepEqual(building.interiorSections||[],authored.interiorSections||[],building.code+' authored section cameras');
}
const html=`<!doctype html><style>body{margin:0}#scene{width:100vw;height:100vh}#labels{display:none}</style>
<div id="scene"></div><div id="labels"></div><script type="module">
import {CampusViewer} from '/src/viewer.js';
const buildings=${JSON.stringify(buildings)};
const viewer=new CampusViewer(document.querySelector('#scene'),document.querySelector('#labels'),buildings,()=>{},()=>{throw Error('Context lost')},()=>{},${JSON.stringify(catalogue.sourceModelSha256)});
await viewer.load();await viewer.environmentReady;
window.checkPublicCameras=async()=>{
 const records=[];
 const pose=()=>({position:viewer.camera.position.toArray(),target:viewer.controls.target.toArray(),fov:viewer.camera.fov});
 const close=(a,b)=>a.every((value,index)=>Math.abs(value-b[index])<.0001);
 for(const building of buildings.filter(item=>item.interiorSections?.some(level=>level.view))){
  const code=building.code;
  viewer.select(building);await viewer.showInterior(building);await viewer.upgradeModel(building,'interior');
  const entry=pose();
  for(const level of building.interiorSections){
   if(!level.view)continue;
   if(!viewer.setInteriorSection(building,level.id))throw Error('Level rejected: '+code+level.id);
   const actual=pose();
   if(!close(actual.position,level.view.position)||!close(actual.target,level.view.target)||actual.fov!==level.view.fov)
    throw Error('Level camera differs from authored gallery view: '+code+level.id);
   const clipping=viewer.renderer.clippingPlanes.map(plane=>[...plane.normal.toArray(),plane.constant]);
   const section=viewer.canvas.dataset.interiorSection;
   if(clipping.length!==2||viewer.renderer.shadowMap.enabled)throw Error('Invalid level clipping/shadows');
   const invalid={...level,id:'invalid-test',minHeight:level.maxHeight+1};
   building.interiorSections.push(invalid);
   const accepted=viewer.setInteriorSection(building,invalid.id);building.interiorSections.pop();
   if(accepted||JSON.stringify(clipping)!==JSON.stringify(viewer.renderer.clippingPlanes.map(plane=>[...plane.normal.toArray(),plane.constant]))||viewer.canvas.dataset.interiorSection!==section)
    throw Error('Rejected level destroyed the current slice');
   records.push({code,level:level.id,...actual,invalidSlicePreservesCurrentView:true});
  }
  if(!viewer.setInteriorSection(building,'all'))throw Error('Unable to restore all levels');
  const actual=pose(),expected=building.interiorView||entry;
  if(viewer.renderer.clippingPlanes.length||!viewer.renderer.shadowMap.enabled||!close(actual.position,expected.position)||!close(actual.target,expected.target)||actual.fov!==expected.fov)
   throw Error('All levels failed to restore the default public camera');
 }
 return records;
};window.ready=true;
</script>`;
const server=await createServer({server:{host:'127.0.0.1',port:0},logLevel:'error',plugins:[{
 name:'section-camera-check',configureServer(server){server.middlewares.use('/__section-camera',(_request,response)=>{response.setHeader('Content-Type','text/html');response.end(html);});}
}]});
let browser;
try{
 await server.listen();const port=server.httpServer.address().port;
 browser=await chromium.launch({args:process.platform==='darwin'?['--use-angle=metal']:['--enable-unsafe-swiftshader']});
 const page=await browser.newPage({viewport:{width:1280,height:900},reducedMotion:'reduce'});
 const errors=[];page.on('pageerror',error=>errors.push(error.message));
 await page.goto(`http://127.0.0.1:${port}/__section-camera`);
 await page.waitForFunction(()=>window.ready,null,{timeout:120000});
 const records=await page.evaluate(()=>window.checkPublicCameras());
 const expected=buildings.flatMap(building=>(building.interiorSections||[]).filter(level=>level.view));
 assert.equal(records.length,expected.length);assert(records.length>0);assert.deepEqual(errors,[]);
 const output='result/blender/stage223/browser';await mkdir(output,{recursive:true});
 await writeFile(output+'/section-cameras.json',JSON.stringify({sourceModelSha256:catalogue.sourceModelSha256,realViewerAndAssets:true,records,errors},null,2)+'\n');
 await page.screenshot({path:output+'/section-camera-default.png'});
 console.log('PUBLIC_SECTION_CAMERAS_VERIFIED',records.length);
}finally{await browser?.close();await server.close();}
