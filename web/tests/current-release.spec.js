import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';
const read = async path => JSON.parse(await readFile(path,'utf8'));
const glb = async path => {
 const bytes = await readFile(path);
 return JSON.parse(bytes.toString('utf8',20,20+bytes.readUInt32LE(12)));
};

test('edition184 joins SAL coping and recesses glass without changing unrelated models',async()=>{
 const before=await read('result/blender/stage184/catalogue-before.json');
 const current=await read('dist/models/catalogue.json');
 const proof=await read('result/blender/stage184/building-refinement.json');
 const native=await read('result/blender/stage184/reopened-verification.json');
 expect(current.version).toBe('184');
 expect(current.sourceModelSha256).toBe(proof.sourceModelSha256);
 expect(native.savedSceneReopened&&native.idempotent&&native.paneSilhouettesAndFinishesRetained).toBe(true);
 expect(native.brickScaleAndMortarRetained).toBe(true);
 expect(native.closedPositiveCopingChains).toBe(7);
 expect(native.recessedGablePanes).toBe(7);
 expect(native.visibleThroughWindowApertures).toBe(7);
 expect(native.windowGlassOverlaps).toEqual([]);
 expect(native.internalEndCapsRemoved).toBe(294);
 for(const building of current.buildings){
  const old=before.buildings.find(item=>item.code===building.code);
  if(building.code==='SAL') {
   expect(building.detailedExterior.sha256).not.toBe(old.detailedExterior.sha256);
   expect(building.detailedExterior.triangles).toBeLessThan(old.detailedExterior.triangles);
   const document=await glb('dist'+building.detailedExterior.url);
   const materials=document.materials.filter(m=>m.name?.includes('SAL183_'));
   expect(materials.length).toBe(2);
   for(const material of materials){
    const colour=material.pbrMetallicRoughness.baseColorFactor;
    expect(colour[0]).toBeCloseTo(.53,5);expect(colour[1]).toBeCloseTo(.285,5);expect(colour[2]).toBeCloseTo(.14,5);
   }
  } else expect(building.detailedExterior,building.code).toEqual(old.detailedExterior);
  expect(building.detailedInterior,building.code).toEqual(old.detailedInterior);
  expect(building.interiorSpaces,building.code).toEqual(old.interiorSpaces);
 }
 expect(proof.changes[0].recessedGablePanes).toHaveLength(7);
 expect(proof.changes[0].newFaces).toBe(938);
 expect(proof.changes[0].originalFaces).toBe(1232);
});

for(const width of [1440,390]) for(const code of ['SAL','OLD','CBG','CKK']){
 test(`${code} edition184 loads at${width}px`,async({page})=>{
  const errors=[];page.on('pageerror',error=>errors.push(error.message));
  await page.setViewportSize({width,height:1000});await page.goto('/#'+code);
  await page.waitForFunction(code=>document.querySelector('canvas')?.dataset.detailReady==='exterior-'+code,code);
  expect(await page.locator('#fallback').isVisible()).toBe(false);
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  expect(errors).toEqual([]);
 });
}
