import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';
const read=async p=>JSON.parse(await readFile(p,'utf8'));

test('CON2025 refinement changes only two acoustic room assets',async()=>{
 const before=await read('result/blender/stage161/catalogue-before.json');
 const current=await read('dist/models/catalogue.json');
 const proof=await read('result/blender/stage161/building-refinement.json');
 expect(current.version).toBe('161');expect(current.sourceModelSha256).toBe(proof.sourceModelSha256);
 expect(proof.allUnrelatedMeshesPreserved).toBe(true);
 expect(proof.changes[0].changedObjects).toEqual(['CON_NEXT_con_methodology_panel_joint_blue']);
 expect(proof.changes[0].addedObjects).toEqual(['CON_ACOUSTICS161_tea_panel_joints']);
 expect(proof.changes[0].learningSegments).toBe(24);expect(proof.changes[0].teaSegments).toBe(10);
 expect((await read('dist/release.json')).campusTransport).toEqual((await read('result/blender/stage161/release-before.json')).campusTransport);
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
 const learning=current.buildings.find(b=>b.code==='CON').interiorSpaces.find(s=>s.id==='con-methodology');
 expect(learning.interiorView.position[0]).toBeGreaterThan(0);
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
