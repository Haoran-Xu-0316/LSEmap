import {test,expect} from '@playwright/test';
import {readFile,mkdir,writeFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
const read=async p=>JSON.parse(await readFile(p,'utf8'));

test('edition212 retains unrelated buildings and seventeen unchanged room studies',async()=>{
 const before=await read('result/blender/stage212/catalogue-before.json'),current=await read('web/public/models/catalogue.json'),native=await read('result/blender/stage212/reopened-verification.json'),realm=await read('result/blender/stage212/public-realm-verification.json');
 expect(current.version).toBe('212');expect(native.originalsVerified).toBe(7421);expect(native.addedObjectsVerified).toBe(16);expect(native.completeModelReopened).toBe(true);
 expect(createHash('sha256').update(await readFile('result/blender/LSE_campus_detailed_v212.blend')).digest('hex')).toBe(current.sourceModelSha256);
 let retained=0;
 for(const b of current.buildings){const previous=before.buildings.find(x=>x.code===b.code);
  expect(b.detailedInterior??null,b.code+' default room').toEqual(previous.detailedInterior??null);
  if(b.code==='OLD')expect(b.detailedExterior.sha256).not.toBe(previous.detailedExterior.sha256);
  else expect(b.detailedExterior??null,b.code+' exterior').toEqual(previous.detailedExterior??null);
  for(const room of previous.interiorSpaces??[]){const now=b.interiorSpaces.find(s=>s.id===room.id);if(room.id==='old-foyer'){expect(now.detailedInterior.sha256).not.toBe(room.detailedInterior.sha256);expect(now.scope).toContain('75.14');}else{expect(now).toEqual(room);retained++;}}
 }
 expect(retained).toBe(17);expect(realm.originalMaterialsVerified).toBe(1933);expect(realm.courtWalkingProbes).toBeGreaterThan(250);expect(realm.churchMappedFootprintVerified).toBe(true);expect(realm.churchTowerTopZ).toBeCloseTo(42.3,4);expect(realm.oldCorridorSharedWithExterior).toBe(true);
 const gallery=await read('web/public/gallery-manifest.json');expect(gallery.images).toHaveLength(135);
});

test('production viewer displays whole sports surface, landmark and connected OLD foyer',async({page})=>{
 test.setTimeout(150000);const directory='result/blender/stage212/browser';await mkdir(directory,{recursive:true});
 const release=await read('dist/release.json'),module=Object.keys(release.assets).find(p=>/\/viewer-[\w-]+\.js$/.test(p)),proof=await read('result/blender/stage212/public-realm-verification.json');
 const html=`<!doctype html><style>html,body{margin:0}#scene{width:100vw;height:100vh}#labels{display:none}</style><div id="scene"></div><div id="labels"></div><script type="module">
 import{CampusViewer}from '${module}';const catalogue=await(await fetch('/models/catalogue.json')).json();const viewer=new CampusViewer(document.querySelector('#scene'),document.querySelector('#labels'),catalogue.buildings,()=>{},()=>{throw Error('Context lost')},()=>{},catalogue.sourceModelSha256);window.viewer=viewer;await viewer.load();await viewer.environmentReady;cancelAnimationFrame(viewer.frame);viewer.controls.enableDamping=false;viewer.home(false);viewer.toggleContext(true);viewer.transition=null;viewer.scene.updateMatrixWorld(true);window.ready=true;</script>`;
 const errors=[];page.on('pageerror',e=>errors.push(e.message));await page.route('**/__realm212',r=>r.fulfill({contentType:'text/html',body:html}));await page.goto('/__realm212');await page.waitForFunction(()=>window.ready,null,{timeout:80000});
 const probes=proof.courtProbes.filter((_,i)=>i%Math.ceil(proof.courtProbes.length/20)===0);
 const hits=await page.evaluate(probes=>probes.map(p=>{viewer.raycaster.set(viewer.camera.position.clone().set(p.x,.25,-p.y),viewer.camera.position.clone().set(0,-1,0));const hit=viewer.raycaster.intersectObject(viewer.campus,true)[0];const material=hit?(Array.isArray(hit.object.material)?hit.object.material[hit.face.materialIndex]:hit.object.material):null;return{height:hit?.point.y,material:material?.name};}),probes);
 for(const hit of hits){expect(hit.height).toBeGreaterThan(.0569);expect(hit.height).toBeLessThan(.0581);expect(hit.material).toContain('COURTS212_');}
 const center=probes.reduce((p,v)=>[p[0]+v.x/probes.length,p[1]-v.y/probes.length],[0,0]);const views={courts:[[center[0]-12,45,center[1]+50],[center[0],0,center[1]]],church:[[160,40,235],[195,15,164]]};const frames=[];
 for(const width of [1440,390]){await page.setViewportSize({width,height:960});for(const view of ['courts','church']){
  const info=await page.evaluate(({view,views})=>{viewer.resize();const [position,target]=views[view];viewer.camera.fov=48;viewer.updateCameraProjection();viewer.moveCamera(viewer.camera.position.clone().fromArray(position),viewer.controls.target.clone().fromArray(target),false);viewer.transition=null;viewer.controls.update();viewer.camera.updateMatrixWorld();viewer.renderPipeline.resetHistory();viewer.renderPipeline.render({moving:true});viewer.renderer.getContext().finish();const times=[];for(let i=0;i<7;i++){viewer.camera.position.x+=.025;viewer.camera.lookAt(viewer.controls.target);viewer.camera.updateMatrixWorld();const t=performance.now();viewer.renderPipeline.render({moving:true});viewer.renderer.getContext().finish();times.push(performance.now()-t);}viewer.renderPipeline.render();return{medianFrameMs:times.sort((a,b)=>a-b)[3]};},{view,views});expect(info.medianFrameMs).toBeLessThan(80);await page.locator('canvas').screenshot({path:directory+'/'+view+'-'+width+'.png'});frames.push({width,view,...info});
 }}await page.evaluate(()=>viewer.dispose());
 for(const width of [1440,390]){await page.setViewportSize({width,height:960});await page.goto('/#OLD');await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-OLD',{timeout:60000});await page.locator('#interior-view').click();await page.locator('#interior-space').selectOption('old-foyer');await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','interior-OLD:old-foyer',{timeout:60000});await page.waitForTimeout(1000);await page.screenshot({path:directory+'/old-foyer-'+width+'.png'});await page.locator('#interior-space').selectOption('default');await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','interior-OLD',{timeout:60000});await page.locator('#overview').click();await expect(page.locator('#fallback')).toBeHidden();}
 expect(errors).toEqual([]);await writeFile(directory+'/acceptance.json',JSON.stringify({hits,frames,oldFoyer:true,defaultRoomRetained:true,errors},null,2)+'\n');
});
