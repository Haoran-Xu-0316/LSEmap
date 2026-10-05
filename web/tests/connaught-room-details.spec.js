import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';
const read=async p=>JSON.parse(await readFile(p,'utf8'));

test('CON2025 refinement changes only two glazed room assets',async()=>{
 const before=await read('result/blender/stage162/catalogue-before.json');
 const current=await read('dist/models/catalogue.json');
 const proof=await read('result/blender/stage162/building-refinement.json');
 const native=await read('result/blender/stage162/reopened-verification.json');
 expect(native.apertureProbes).toHaveLength(2);for(const probes of native.apertureProbes){expect(probes.clearSamples).toBe(9);expect(probes.glassSamples).toBe(9);}
 expect(current.version).toBe('162');expect(current.sourceModelSha256).toBe(proof.sourceModelSha256);
 expect(proof.allUnrelatedMeshesPreserved).toBe(true);
 expect(proof.changes[0].changedObjects).toEqual(expect.arrayContaining(['CON_NEXT_con_methodology_rear_wall_white','CON_NEXT_con_methodology_rear_glazed_partition_glass','CON_NEXT_con_tea_point_rear_wall_white','CON_NEXT_con_tea_point_rear_window_glass']));
 expect(proof.changes[0].changedObjects).toHaveLength(4);expect(proof.changes[0].addedObjects).toEqual([]);
 for(const room of proof.changes[0].rooms){expect(room.wallBoundsUnchanged).toBe(true);expect(room.apertureHasNoOpaqueWallHit).toBe(true);expect(room.glazingRayHit).toBe(true);expect(room.glassFaces).toBe(1);}
 expect((await read('dist/release.json')).campusTransport).toEqual((await read('result/blender/stage162/release-before.json')).campusTransport);
 for(const building of current.buildings){
  const old=before.buildings.find(b=>b.code===building.code);
  expect(building.detailedExterior,building.code).toEqual(old.detailedExterior);
  expect(building.detailedInterior,building.code).toEqual(old.detailedInterior);
  for(const room of building.interiorSpaces??[]){
   const previous=old.interiorSpaces.find(s=>s.id===room.id);
   if(room.id.startsWith('con-'))expect(room.detailedInterior.sha256).not.toBe(previous.detailedInterior.sha256);
   else expect(room).toEqual(previous);
  }
 }
 for(const room of current.buildings.find(b=>b.code==='CON').interiorSpaces){
  const bytes=await readFile('dist'+room.detailedInterior.url);
  const glb=JSON.parse(bytes.subarray(20,20+bytes.readUInt32LE(12)));
  const panes=glb.materials.filter(m=>m.name.includes('CON_GLAZING162_'));
  expect(panes).toHaveLength(1);
  expect(panes[0].alphaMode).toBe('BLEND');
  expect(panes[0].pbrMetallicRoughness.baseColorFactor[3]).toBeCloseTo(.18,4);
  expect(panes[0].pbrMetallicRoughness.metallicFactor??0).toBe(0);
  expect(panes[0].extensions?.KHR_materials_transmission).toBeUndefined();
 }

});

for(const width of [1440,390])test(`CON2025 room switching remains usable at ${width}px`,async({page})=>{
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.setViewportSize({width,height:1000});await page.goto('/#CON');
 await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-CON',{timeout:60000});
 await page.locator('#interior-view').click();
 for(const id of ['con-methodology','con-tea-point','default']){
  await page.locator('#interior-space').selectOption(id);
  await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','interior-CON'+(id==='default'?'':':'+id),{timeout:60000});
  await expect(page.locator('#fallback')).toBeHidden();
 }
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
 expect(errors).toEqual([]);
});
