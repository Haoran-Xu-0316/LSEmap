/** Real CampusViewer regression for authored room entry and mobile projection.
 * A private Vite harness uses production assets without exposing test controls
 * in the public app. Fixed editor-friendly configuration; no CLI parameters.
 */
import {createServer} from 'vite';
import {chromium} from 'playwright';
import {readFile,mkdir,writeFile} from 'node:fs/promises';
import assert from 'node:assert/strict';

const output='result/blender/stage228/browser';
const catalogue=JSON.parse(await readFile('web/public/models/catalogue.json','utf8'));
const requested=[['OLD','old-606'],['CKK','ckk-115'],['CLM','clm-g03'],['MAR','mar-108']];
const cases=requested.flatMap(([code,id])=>{
 const building=catalogue.buildings.find(item=>item.code===code);
 const room=building?.interiorSpaces?.find(item=>item.id===id);
 if(!room){assert(!['old-606','ckk-115'].includes(id),id+' required room missing');return [];}
 assert(room.interiorView&&room.interiorBounds,id+' authored entry or bounds missing');
 return [{code,id}];
});
const html=`<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><style>
html,body{margin:0;width:100%;height:100%;overflow:hidden}#scene{width:100vw;height:100vh}#labels{display:none}
</style></head><body><div id="scene"></div><div id="labels"></div><script type="module">
import {CampusViewer} from '/src/viewer.js';
const buildings=${JSON.stringify(catalogue.buildings)};
const viewer=new CampusViewer(document.querySelector('#scene'),document.querySelector('#labels'),buildings,()=>{},()=>{throw Error('Context lost')},()=>{},${JSON.stringify(catalogue.sourceModelSha256)});
window.viewer=viewer;
await viewer.load();await viewer.environmentReady;
const distance=(a,b)=>Math.sqrt(a.reduce((sum,v,i)=>sum+(v-b[i])**2,0));
const snapshot=()=>({position:viewer.camera.position.toArray(),target:viewer.controls.target.toArray(),fov:viewer.camera.fov,transition:viewer.transition?{kind:viewer.transition.kind??'navigation',duration:viewer.transition.duration}:null,mode:viewer.mode,space:viewer.canvas.dataset.interiorSpace,distance:viewer.camera.position.distanceTo(viewer.controls.target)});
const frame=()=>new Promise(resolve=>requestAnimationFrame(resolve));
function assertRoomPose(snapshot,room,label){
 if(snapshot.transition)throw Error(label+' retained camera flight '+JSON.stringify(snapshot.transition));
 if(distance(snapshot.position,room.interiorView.position)>0.0001||distance(snapshot.target,room.interiorView.target)>0.0001)throw Error(label+' changed authored room pose '+JSON.stringify(snapshot));
 if(Math.abs(snapshot.fov-room.interiorView.fov)>0.0001)throw Error(label+' changed authored fov');
 const bounds=room.interiorBounds;
 if(!snapshot.position.every((v,i)=>v>=bounds.min[i]-.001&&v<=bounds.max[i]+.001))throw Error(label+' eye outside room bounds');
 if(snapshot.distance>=14)throw Error(label+' retained fourteen metre exterior shell fit');
 if(snapshot.mode!=='interior'||snapshot.space!==room.id)throw Error(label+' wrong interior');
}
function visibleModel(){
 const key=viewer.activeInterior.key;
 const group=viewer.activeDetail?.kind==='interior'&&viewer.activeDetail.spaceId===viewer.activeInterior.spaceId?viewer.activeDetail.group:viewer.interiors.get(key);
 let meshes=0;group?.traverseVisible(object=>{if(object.isMesh)meshes++;});
 if(!group?.visible||!meshes||viewer.campus.visible)throw Error('Interior did not replace campus with visible room geometry');
 return meshes;
}
function pixels(){
 // Read the actual rendered WebGL canvas within this same JS task.
 viewer.renderPipeline.render({moving:false,time:performance.now()});
 const canvas=document.createElement('canvas');canvas.width=64;canvas.height=64;
 const context=canvas.getContext('2d');context.drawImage(viewer.canvas,0,0,64,64);
 const rgba=context.getImageData(0,0,64,64).data;let sum=0,squares=0,opaque=0;const colours=new Set();
 for(let i=0;i<rgba.length;i+=4){const l=(rgba[i]+rgba[i+1]+rgba[i+2])/3;sum+=l;squares+=l*l;if(rgba[i+3])opaque++;colours.add([rgba[i]>>3,rgba[i+1]>>3,rgba[i+2]>>3].join(','));}
 const deviation=Math.sqrt(Math.max(0,squares/4096-(sum/4096)**2));
 if(opaque<4000||colours.size<6||deviation<3)throw Error('Blank or featureless rendered room '+JSON.stringify({opaque,colours:colours.size,deviation}));
 return {opaquePixels:opaque,quantizedColours:colours.size,luminanceDeviation:deviation};
}
window.enterRoom=async(code,id)=>{
 const building=buildings.find(item=>item.code===code),room=building.interiorSpaces.find(item=>item.id===id);
 // Production select + showInterior; cached switches resolve in the same task.
 viewer.select(building);const accepted=await viewer.showInterior(building,id);if(!accepted)throw Error(id+' entry rejected');
 const immediate=snapshot();assertRoomPose(immediate,room,id+' immediate');
 const samples=[];
 for(let i=0;i<12;i++){await frame();const pose=snapshot();assertRoomPose(pose,room,id+' frame '+i);samples.push({position:pose.position,target:pose.target,transition:pose.transition,visibleMeshes:visibleModel()});}
 const projected=viewer.controls.target.clone().project(viewer.camera);const projectedY=(1-projected.y)/2;const mobile=matchMedia('(max-width:700px)').matches;
 if(mobile&&(projectedY<.15||projectedY>.36))throw Error(id+' mobile target not above sheet '+projectedY);
 if(!mobile&&Math.abs(projectedY-.5)>.001)throw Error(id+' desktop target no longer centred');
 return {code,id,authored:room.interiorView,bounds:room.interiorBounds,immediate,samples,projectedTarget:{x:(projected.x+1)/2,y:projectedY},viewOffset:viewer.camera.view,pixels:pixels(),visibleMeshes:visibleModel()};
};
window.checkZoom=async()=>{
 const before=snapshot();viewer.zoom(.8);const started=snapshot();
 if(started.transition?.kind!=='zoom'||started.transition.duration!==180)throw Error('Same-room zoom lost180ms animation');
 await new Promise(resolve=>setTimeout(resolve,55));const during=snapshot();if(during.transition?.kind!=='zoom')throw Error('Zoom ended before expected animation interval');
 await new Promise(resolve=>setTimeout(resolve,260));const after=snapshot();
 if(after.transition||Math.abs(after.distance-before.distance*.8)>.001||distance(after.target,before.target)>.0001)throw Error('Zoom did not settle at requested distance');
 return {before,started,during,after};
};
window.pose=snapshot;
window.disposeHarness=()=>viewer.dispose();window.ready=true;
</script></body></html>`;
const server=await createServer({server:{host:'127.0.0.1',port:0},logLevel:'error',plugins:[{
 name:'interior-entry228-private',configureServer(server){server.middlewares.use('/__interior-entry228',(_request,response)=>{response.setHeader('Content-Type','text/html');response.end(html);});}
}]});
let browser;
const proof={sourceModelSha256:catalogue.sourceModelSha256,realViewerAndAssets:true,reducedMotion:'no-preference',cases,runs:[],errors:[]};
try{
 await mkdir(output,{recursive:true});await server.listen();const port=server.httpServer.address().port;
 browser=await chromium.launch({args:process.platform==='darwin'?['--use-angle=metal']:['--enable-unsafe-swiftshader']});
 for(const viewport of [{width:1280,height:900},{width:390,height:844}]){
  const name=viewport.width===390?'mobile390':'desktop1280';
  const context=await browser.newContext({viewport,reducedMotion:'no-preference'});const page=await context.newPage();
  const run={name,viewport,entries:[],switches:[],errors:[]};proof.runs.push(run);
  page.on('pageerror',error=>run.errors.push(error.message));
  try{
   await page.goto('http://127.0.0.1:'+port+'/__interior-entry228');await page.waitForFunction(()=>window.ready,null,{timeout:120000});
   assert.equal(await page.evaluate(()=>matchMedia('(prefers-reduced-motion:reduce)').matches),false);
   for(const item of cases){
    const record=await page.evaluate(({code,id})=>window.enterRoom(code,id),item);run.entries.push(record);
    await page.screenshot({path:output+'/interior-entry-'+name+'-'+item.id+'.png'});
   }
   // Repeat already loaded rooms without waiting for the usual900ms navigation.
   for(const item of [cases[0],cases[1],cases[0],...cases.slice(2),cases[1]])run.switches.push(await page.evaluate(({code,id})=>window.enterRoom(code,id),item));
   const before=await page.evaluate(()=>window.pose());const rect=await page.locator('canvas').first().boundingBox();assert(rect);
   await page.mouse.move(rect.x+rect.width*.48,rect.y+rect.height*.32);await page.mouse.down();
   await page.mouse.move(rect.x+rect.width*.63,rect.y+rect.height*.40,{steps:5});await page.mouse.up();
   const dragged=await page.evaluate(()=>window.pose());
   assert(Math.hypot(...dragged.position.map((v,i)=>v-before.position[i]))>.01,name+' drag did not alter real controls');
   const next=cases[0];const restored=await page.evaluate(({code,id})=>window.enterRoom(code,id),next);
   run.afterDrag={before,dragged,restored,dampingResidueCleared:true};
   run.zoom=await page.evaluate(()=>window.checkZoom());
   await page.screenshot({path:output+'/interior-entry-'+name+'-after-drag-zoom.png'});
   assert.deepEqual(run.errors,[]);
   console.log('INTERIOR_ENTRY_VERIFIED',name,run.entries.length,run.switches.length);
  }finally{await page.evaluate(()=>window.disposeHarness?.()).catch(()=>{});await context.close();}
 }
 await writeFile(output+'/interior-entry228.json',JSON.stringify(proof,null,2)+'\n');
} catch(error){
 proof.errors.push(error.stack??String(error));await writeFile(output+'/interior-entry228.json',JSON.stringify(proof,null,2)+'\n');throw error;
} finally{await browser?.close();await server.close();}
