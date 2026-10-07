import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';
const read=async path=>JSON.parse(await readFile(path,'utf8'));
const glb=async path=>{const bytes=await readFile(path);return JSON.parse(bytes.toString('utf8',20,20+bytes.readUInt32LE(12)));};

test('edition177 retains rooms and scopes three exterior corrections and MAR glazing',async()=>{
 const before=await read('result/blender/stage177/catalogue-before.json');
 const current=await read('dist/models/catalogue.json');
 const proof=await read('result/blender/stage177/building-refinement.json');
 const native=await read('result/blender/stage177/reopened-verification.json');
 expect(current.version).toBe('177');expect(current.buildings).toHaveLength(31);
 expect(current.sourceModelSha256).toBe(proof.sourceModelSha256);
 expect(native.savedSceneReopened).toBe(true);expect(native.idempotent).toBe(true);
 expect(native.allOriginalShapesAndUVsPreserved).toBe(true);
 for(const building of current.buildings){
  const old=before.buildings.find(b=>b.code===building.code);
  if(['COW','61A','MAR'].includes(building.code))expect(building.detailedExterior.sha256,building.code).not.toBe(old.detailedExterior.sha256);
  else expect(building.detailedExterior,building.code).toEqual(old.detailedExterior);
  if(building.code==='MAR')expect(building.detailedInterior.sha256).not.toBe(old.detailedInterior.sha256);
  else expect(building.detailedInterior,building.code).toEqual(old.detailedInterior);
  for(const room of old.interiorSpaces||[])expect(building.interiorSpaces.find(r=>r.id===room.id),room.id).toEqual(room);
 }
 expect(proof.changes).toHaveLength(3);
 expect(proof.changes.every(c=>!c.alreadyApplied&&c.addedObjects.length)).toBe(true);
 expect(proof.archivedObjects).toContain('COW_D5_window_glass_glass');
 expect(proof.archivedObjects).toContain('MAR_D3_ground_glass_panes');
 const mar=current.buildings.find(b=>b.code==='MAR');
 const document=await glb('dist'+mar.detailedInterior.url);
 for(const [part,panes,opacity] of [['ground_glass_panes',107,.30],['mezzanine_guard_glass',54,.22]]){
  const index=document.materials.findIndex(m=>m.name?.endsWith('MAR177_'+part+'_dielectric'));
  expect(index).toBeGreaterThanOrEqual(0);
  const material=document.materials[index];expect(material.alphaMode).toBe('BLEND');
  expect(material.pbrMetallicRoughness.baseColorFactor[3]).toBeCloseTo(opacity);
  expect(material.pbrMetallicRoughness.metallicFactor).toBe(0);
  const primitives=document.meshes.flatMap(m=>m.primitives).filter(p=>p.material===index);
  expect(primitives).toHaveLength(1);
  expect(document.accessors[primitives[0].indices].count).toBe(panes*6);
 }
});
for(const width of [1440,390])for(const code of ['COW','61A','MAR']){
 test(`${code} edition177 loads at${width}px`,async({page})=>{
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.setViewportSize({width,height:1000});await page.goto('/#'+code);
  await page.waitForFunction(code=>document.querySelector('canvas')?.dataset.detailReady==='exterior-'+code,code);
  if(code==='MAR'){
   await page.locator('#interior-view').click();
   await page.waitForFunction(()=>document.querySelector('canvas')?.dataset.detailReady==='interior-MAR');
  }
  expect(await page.locator('#fallback').isVisible()).toBe(false);
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  expect(errors).toEqual([]);
 });
}
