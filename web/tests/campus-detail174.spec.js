import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';
const read=async path=>JSON.parse(await readFile(path,'utf8'));

test('edition174 integrates independent facade, entrance and public-realm corrections',async()=>{
 const before=await read('result/blender/stage174/catalogue-before.json');
 const current=await read('dist/models/catalogue.json');
 const proof=await read('result/blender/stage174/building-refinement.json');
 const native=await read('result/blender/stage174/reopened-verification.json');
 expect(current.version).toBe('174');expect(current.buildings).toHaveLength(31);
 expect(current.sourceModelSha256).toBe(proof.sourceModelSha256);
 expect(native.savedSceneReopened).toBe(true);expect(native.idempotent).toBe(true);
 expect(native.allOriginalShapesAndUVsPreserved).toBe(true);
 expect(native.entranceFoyerRegisteredToCampus).toBe(true);
 for(const building of current.buildings){
  const old=before.buildings.find(b=>b.code===building.code);
  if(['MAR','LRB','OLD'].includes(building.code))expect(building.detailedExterior.sha256,building.code).not.toBe(old.detailedExterior.sha256);
  else expect(building.detailedExterior,building.code).toEqual(old.detailedExterior);
  for(const room of old.interiorSpaces||[])
   expect(building.interiorSpaces.find(r=>r.id===room.id),room.id).toEqual(room);
 }
 const old=current.buildings.find(b=>b.code==='OLD');
 const foyer=old.interiorSpaces.find(r=>r.id==='old-foyer');
 expect(foyer.interiorStudy.kind).toBe('registered-historical-space');
 expect(foyer.scope).toContain('2011');expect(foyer.scope).toContain('估计');
 expect(foyer.interiorBounds.min[2]).toBeGreaterThan(70);
 expect(foyer.detailedInterior.triangles).toBeGreaterThan(300);
 const bytes=await readFile('dist'+foyer.detailedInterior.url);
 const document=JSON.parse(bytes.toString('utf8',20,20+bytes.readUInt32LE(12)));
 const glassIndex=document.materials.findIndex(m=>m.name.includes('foyer_glass'));
 expect(glassIndex).toBeGreaterThanOrEqual(0);
 expect(document.materials[glassIndex].alphaMode).toBe('BLEND');
 expect(document.materials[glassIndex].pbrMetallicRoughness.baseColorFactor[3]).toBeCloseTo(.20,6);
 const panes=document.meshes.flatMap(m=>m.primitives).filter(p=>p.material===glassIndex);
 expect(panes.reduce((sum,p)=>sum+document.accessors[p.indices].count,0)).toBe(12);

 const baselineOld=before.buildings.find(b=>b.code==='OLD');
 expect(old.detailedInterior).toEqual(baselineOld.detailedInterior);
 expect(current.buildings.find(b=>b.code==='SAW').detailedInterior).toEqual(before.buildings.find(b=>b.code==='SAW').detailedInterior);
 const entrance=proof.changes.find(c=>c.code==='OLD');
 expect(entrance.levels.risers).toBe(4);
 expect(entrance.levels.lower+entrance.levels.rise*4).toBeCloseTo(entrance.levels.upper,6);
 expect(entrance.archivedObjects).toContain('OLD_NEXT_ACCESS_foyer_four_steps');
 const collisions=await read('result/blender/old_foyer174/audit.json');
 expect(collisions.collisionCandidatesHits).toEqual([]);
});
for(const width of [1440,390])for(const code of ['MAR','LRB','OLD']){
 test(`${code} edition174 loads at${width}px`,async({page})=>{
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.setViewportSize({width,height:1000});await page.goto('/#'+code);
  await page.waitForFunction(code=>document.querySelector('canvas')?.dataset.detailReady==='exterior-'+code,code);
  if(code==='OLD'){
   await page.locator('#interior-view').click();
   await page.waitForFunction(()=>document.querySelector('canvas')?.dataset.detailReady==='interior-OLD');
   await expect(page.locator('#interior-space')).toBeEnabled();
   await page.locator('#interior-space').selectOption('old-foyer');
   await page.waitForFunction(()=>document.querySelector('canvas')?.dataset.detailReady==='interior-OLD:old-foyer');
   await expect(page.locator('#interior-space')).toHaveValue('old-foyer');
  }
  expect(await page.locator('#fallback').isVisible()).toBe(false);
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  expect(errors).toEqual([]);
 });
}
