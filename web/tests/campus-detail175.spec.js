import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';
const read=async path=>JSON.parse(await readFile(path,'utf8'));

test('edition175 shares street and facade corrections without replacing existing rooms',async()=>{
 const before=await read('result/blender/stage175/catalogue-before.json');
 const current=await read('dist/models/catalogue.json');
 const proof=await read('result/blender/stage175/building-refinement.json');
 const native=await read('result/blender/stage175/reopened-verification.json');
 expect(current.version).toBe('175');expect(current.buildings).toHaveLength(31);
 expect(current.sourceModelSha256).toBe(proof.sourceModelSha256);
 expect(native.savedSceneReopened).toBe(true);expect(native.idempotent).toBe(true);
 expect(native.allOriginalShapesAndUVsPreserved).toBe(true);
 for(const building of current.buildings){
  const old=before.buildings.find(b=>b.code===building.code);
  if(['COL','CLM','OLD'].includes(building.code))expect(building.detailedExterior.sha256,building.code).not.toBe(old.detailedExterior.sha256);
  else expect(building.detailedExterior,building.code).toEqual(old.detailedExterior);
  expect(building.detailedInterior,building.code).toEqual(old.detailedInterior);
  for(const room of old.interiorSpaces||[])
   expect(building.interiorSpaces.find(r=>r.id===room.id),room.id).toEqual(room);
 }
 expect(proof.changes).toHaveLength(3);
 expect(proof.changes.every(c=>!c.alreadyApplied&&c.addedObjects.length)).toBe(true);
 expect(proof.archivedObjects).toContain('OLD_NEXT_APPROACH_tapered_stone_sidewall');
 expect(proof.archivedObjects).toContain('COL_D4_rustication_recesses');
 const clm=current.buildings.find(b=>b.code==='CLM');
 const bytes=await readFile('dist'+clm.detailedExterior.url);
 const document=JSON.parse(bytes.toString('utf8',20,20+bytes.readUInt32LE(12)));
 const guardMaterial=document.materials.findIndex(m=>m.name?.includes('CLM_EXTERIOR175'));
 expect(guardMaterial).toBeGreaterThanOrEqual(0);
 const guards=document.meshes.flatMap(m=>m.primitives).filter(p=>p.material===guardMaterial);
 expect(guards.reduce((n,p)=>n+document.accessors[p.indices].count,0)).toBe(4896);
});
for(const width of [1440,390])for(const code of ['COL','CLM','OLD']){
 test(`${code} edition175 loads at${width}px`,async({page})=>{
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.setViewportSize({width,height:1000});await page.goto('/#'+code);
  await page.waitForFunction(code=>document.querySelector('canvas')?.dataset.detailReady==='exterior-'+code,code);
  expect(await page.locator('#fallback').isVisible()).toBe(false);
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  expect(errors).toEqual([]);
 });
}
