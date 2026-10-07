import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';
const read = async path => JSON.parse(await readFile(path,'utf8'));
const glb = async path => {
 const bytes = await readFile(path);
 return JSON.parse(bytes.toString('utf8',20,20+bytes.readUInt32LE(12)));
};

test('edition182 shares the OLD stone bench support and preserves unrelated assets',async()=>{
 const before=await read('result/blender/stage182/catalogue-before.json');
 const current=await read('dist/models/catalogue.json');
 const proof=await read('result/blender/stage182/building-refinement.json');
 const native=await read('result/blender/stage182/reopened-verification.json');
 expect(current.version).toBe('182');
 expect(current.sourceModelSha256).toBe(proof.sourceModelSha256);
 expect(native.savedSceneReopened&&native.idempotent&&native.benchSeatAndFloorTouching).toBe(true);
 for(const building of current.buildings){
  const old=before.buildings.find(item=>item.code===building.code);
  if(building.code==='OLD') expect(building.detailedExterior.sha256).not.toBe(old.detailedExterior.sha256);
  else expect(building.detailedExterior,building.code).toEqual(old.detailedExterior);
  expect(building.detailedInterior,building.code).toEqual(old.detailedInterior);
  for(const space of building.interiorSpaces??[]){
   const previous=old.interiorSpaces.find(item=>item.id===space.id);
   if(space.id==='old-foyer')expect(space.detailedInterior.sha256).not.toBe(previous.detailedInterior.sha256);
   else expect(space,space.id).toEqual(previous);
  }
 }
 const old=current.buildings.find(item=>item.code==='OLD');
 const previous=before.buildings.find(item=>item.code==='OLD');
 const foyer=old.interiorSpaces.find(s=>s.id==='old-foyer');
 const oldFoyer=previous.interiorSpaces.find(s=>s.id==='old-foyer');
 // Export merges object names. The two twelve-triangle feet are replaced by
 // one twelve-triangle plinth in both independently generated assets.
 expect(old.detailedExterior.triangles).toBe(previous.detailedExterior.triangles-12);
 expect(foyer.detailedInterior.triangles).toBe(oldFoyer.detailedInterior.triangles-12);

});

for(const width of [1440,390]) for(const code of ['CKK','LRB','CBG','OLD']){
 test(`${code} edition182 loads at${width}px`,async({page})=>{
  const errors=[];page.on('pageerror',error=>errors.push(error.message));
  await page.setViewportSize({width,height:1000});await page.goto('/#'+code);
  await page.waitForFunction(code=>document.querySelector('canvas')?.dataset.detailReady==='exterior-'+code,code);
  expect(await page.locator('#fallback').isVisible()).toBe(false);
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  expect(errors).toEqual([]);
 });
}
