import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';
const read=async path=>JSON.parse(await readFile(path,'utf8'));

test('edition172 refines three buildings while preserving room samples',async()=>{
 const before=await read('result/blender/stage172/catalogue-before.json');
 const current=await read('dist/models/catalogue.json');
 const proof=await read('result/blender/stage172/building-refinement.json');
 const native=await read('result/blender/stage172/reopened-verification.json');
 expect(current.version).toBe('172');expect(current.buildings).toHaveLength(31);
 expect(current.sourceModelSha256).toBe(proof.sourceModelSha256);
 expect(native.idempotent).toBe(true);expect(native.allOriginalShapesAndUVsPreserved).toBe(true);
 expect(native.sourceModelSha256).toBe(proof.sourceModelSha256);
 for(const building of current.buildings){
  const old=before.buildings.find(b=>b.code===building.code);
  if(['OLD','LRB','SAW'].includes(building.code)){
   expect(building.detailedExterior.sha256).not.toBe(old.detailedExterior.sha256);
   expect(building.detailedExterior.bounds).toEqual(old.detailedExterior.bounds);
  }else expect(building.detailedExterior,building.code).toEqual(old.detailedExterior);
  if(!['LRB','SAW'].includes(building.code))expect(building.detailedInterior,building.code).toEqual(old.detailedInterior);
  expect(building.interiorSpaces,building.code).toEqual(old.interiorSpaces);
 }
 const door=proof.changes.find(c=>c.singlePaneCount);
 expect(door.singlePaneCount).toBe(8);expect(door.doorTintPreserved).toBe(true);
 expect(proof.changes.find(c=>c.materialBindings)?.materialBindings).toHaveLength(16);
});
for(const width of [1440,390])for(const code of ['OLD','LRB','SAW']){
 test(`${code} edition172 loads at${width}px`,async({page})=>{
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.setViewportSize({width,height:1000});await page.goto('/#'+code);
  await page.waitForFunction(code=>document.querySelector('canvas')?.dataset.detailReady==='exterior-'+code,code);
  if(code==='SAW'){
   await page.locator('#interior-view').click();
   await page.waitForFunction(()=>document.querySelector('canvas')?.dataset.detailReady==='interior-SAW');
  }
  expect(await page.locator('#fallback').isVisible()).toBe(false);
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  expect(errors).toEqual([]);
 });
}
