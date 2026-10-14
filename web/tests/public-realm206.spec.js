import {test,expect} from '@playwright/test';
import {readFile,mkdir,writeFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {outdoorSurfaceKind}from '../src/surface-materials.js';
const read=async path=>JSON.parse(await readFile(path,'utf8'));

test('edition206 preserves rooms and unrelated buildings while correcting SAW glass and square paving',async()=>{
 const before=await read('result/blender/stage206/catalogue-before.json'),current=await read('web/public/models/catalogue.json');
 const saved=await read('result/blender/stage206/reopened-verification.json');
 const glass=await read('result/blender/saw-exterior206/verification.json'),ground=await read('result/blender/cbg-ground206/audit.json'),reopen=await read('result/blender/cbg-ground206/reopen-test.json');
 expect(current.version).toBe('206');expect(saved.originalsVerified).toBe(7249);expect(saved.addedObjectsVerified).toBe(8);expect(saved.completeModelReopened).toBe(true);
 const native=await readFile('result/blender/LSE_campus_detailed_v206.blend');expect(createHash('sha256').update(native).digest('hex')).toBe(current.sourceModelSha256);
 expect(glass.rayCount).toBe(489);expect(glass.allFrontFacesExposed).toBe(true);expect(glass.allBackInterferenceIdenticalToSource).toBe(true);expect(glass.rayFailures).toEqual([]);
 for(const material of ground.materialPaletteCopies)expect(outdoorSurfaceKind('WEB_'+material.target)).toBe('stone');
 expect(ground.addedPavingAreaM2).toBeCloseTo(716.7122,3);expect(ground.mappedTreePoolCount).toBe(6);expect(ground.otherBuildingOverlapM2).toBe(0);expect(ground.registeredCBGGroundFootprintOverlapM2).toBe(0);
 expect(reopen.componentReopened).toBe(true);expect(reopen.noPavingAboveWalkingPlane).toBe(true);expect(reopen.reopenWalkingRays).toHaveLength(697);
 for(const building of current.buildings){
  const previous=before.buildings.find(b=>b.code===building.code);
  for(const key of ['detailedInterior','interiorSpaces','interiorView'])expect(building[key]??null,building.code+key).toEqual(previous[key]??null);
  if(building.code==='SAW')expect(building.detailedExterior.sha256).not.toBe(previous.detailedExterior.sha256);
  else expect(building.detailedExterior??null,building.code).toEqual(previous.detailedExterior??null);
 }
 const saw=current.buildings.find(b=>b.code==='SAW'),bytes=await readFile('web/public'+saw.detailedExterior.url);const doc=JSON.parse(bytes.subarray(20,20+bytes.readUInt32LE(12)));
 const panes=doc.materials.filter(m=>m.name.includes('SAW206_'));expect(panes).toHaveLength(6);
 for(const m of panes){expect(m.alphaMode).toBe('BLEND');expect(m.pbrMetallicRoughness.metallicFactor).toBe(0);expect(m.extensions?.KHR_materials_transmission).toBeUndefined();expect(m.pbrMetallicRoughness.baseColorFactor[3]).toBeCloseTo(m.name.includes('roof')?.62:.55,4);}
});

test('production viewer renders mapped paving with correct first-hit heights',async({page})=>{
 const release=await read('dist/release.json'),viewerPath=Object.keys(release.assets).find(p=>/\/viewer-[\w-]+\.js$/.test(p));
 const probe=await read('result/blender/cbg-ground206/reopen-test.json'),samples=probe.reopenWalkingRays.filter((_,i)=>i%98===0);
 const html=`<!doctype html><style>body{margin:0}#scene{width:1400px;height:1000px}#labels{display:none}</style><div id="scene"></div><div id="labels"></div><script type="module">
 import {CampusViewer}from '${viewerPath}';
 const c=await(await fetch('/models/catalogue.json')).json();
 const v=new CampusViewer(document.querySelector('#scene'),document.querySelector('#labels'),c.buildings,()=>{},()=>{throw Error('Context lost')},()=>{},c.sourceModelSha256);
 window.viewer=v;await v.load();await v.environmentReady;v.home(false);v.transition=null;v.camera.position.set(20,30,40);v.controls.target.set(38,.1,45);v.controls.update();v.needsRender=true;
 const palette=new Map();v.campus.traverse(o=>{for(const m of Array.isArray(o.material)?o.material:[o.material])if(m?.name.includes('pale_gray_stone'))palette.set(m.name,{name:m.name,program:m.customProgramCacheKey(),roughness:m.roughness,transparent:m.transparent});});window.stoneMaterials=[...palette.values()];
 const samples=${JSON.stringify(samples)};
 window.proof=samples.map(s=>{v.raycaster.set(v.camera.position.clone().set(s.point[0],.5,-s.point[1]),v.camera.position.clone().set(0,-1,0));const h=v.raycaster.intersectObject(v.campus,true)[0];return{point:s.point,expectedZ:s.z,hitY:h?.point.y,normalY:h?.face.normal.clone().transformDirection(h.object.matrixWorld).y};});
 </script>`;
 await page.route('**/__paving206',route=>route.fulfill({contentType:'text/html',body:html}));
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('/__paving206');await page.waitForFunction(()=>window.proof,null,{timeout:65000});const hits=await page.evaluate(()=>window.proof),stoneMaterials=await page.evaluate(()=>window.stoneMaterials);expect(stoneMaterials).toHaveLength(5);for(const m of stoneMaterials){expect(m.program).toContain('captured');expect(m.transparent).toBe(false);}
 for(const hit of hits){expect(hit.hitY,JSON.stringify(hit)).toBeCloseTo(hit.expectedZ,3);expect(hit.normalY).toBeGreaterThan(.9);}
 await page.waitForTimeout(1300);await mkdir('result/blender/stage206/browser',{recursive:true});await page.screenshot({path:'result/blender/stage206/browser/paving.png'});await page.evaluate(()=>window.viewer.dispose());expect(errors).toEqual([]);
 await writeFile('result/blender/stage206/browser/paving-rays.json',JSON.stringify({hits,stoneMaterials,errors},null,2)+'\n');
});

test('SAW glass exterior and unchanged public interior render on desktop and mobile',async({page})=>{
 const errors=[];page.on('pageerror',e=>errors.push(e.message));await mkdir('result/blender/stage206/browser',{recursive:true});
 for(const width of [1440,390]){
  await page.setViewportSize({width,height:1000});await page.goto('/#SAW');const canvas=page.locator('canvas');await expect(canvas).toHaveAttribute('data-detail-ready','exterior-SAW',{timeout:65000});await page.waitForTimeout(1300);await page.screenshot({path:'result/blender/stage206/browser/saw-'+width+'.png'});
  await page.locator('#interior-view').click();await expect(canvas).toHaveAttribute('data-interior-space','default',{timeout:65000});
  await page.locator('#overview').click();await page.waitForTimeout(1300);await expect(canvas).toHaveAttribute('data-campus-details',/SAW/);
 }
 expect(errors).toEqual([]);await writeFile('result/blender/stage206/browser/acceptance.json',JSON.stringify({widths:[1440,390],sawExterior:true,publicInterior:true,overview:true,errors},null,2)+'\n');
});
