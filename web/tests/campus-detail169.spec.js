import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';
const read=async path=>JSON.parse(await readFile(path,'utf8'));

test('edition169 preserves unrelated assets and isolates the LRB floor correction',async()=>{
 const before=await read('result/blender/stage169/catalogue-before.json');
 const current=await read('dist/models/catalogue.json');
 const proof=await read('result/blender/stage169/building-refinement.json');
 const native=await read('result/blender/stage169/reopened-verification.json');
 expect(current.version).toBe('169');expect(current.buildings).toHaveLength(31);
 expect(current.sourceModelSha256).toBe(proof.sourceModelSha256);
 expect(native.sourceModelSha256).toBe(proof.sourceModelSha256);
 expect(native.idempotent).toBe(true);expect(native.roomsOutsideCampus).toBe(true);
 expect(native.allOriginalShapesAndUVsPreserved).toBe(true);
 for(const building of current.buildings){
  const old=before.buildings.find(b=>b.code===building.code);
  if(['OLD','MAR','OCS'].includes(building.code))expect(building.detailedExterior.sha256).not.toBe(old.detailedExterior.sha256);
  else expect(building.detailedExterior,building.code).toEqual(old.detailedExterior);
  if(building.code==='LRB')expect(building.detailedInterior.sha256).not.toBe(old.detailedInterior.sha256);
  else expect(building.detailedInterior,building.code).toEqual(old.detailedInterior);
  expect(building.interiorSpaces,building.code).toEqual(old.interiorSpaces);
 }
});
for(const width of [1440,390])for(const code of ['OLD','MAR','OCS','LRB']){
 test(`${code} refined model loads at${width}px`,async({page})=>{
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.setViewportSize({width,height:1000});await page.goto('/#'+code);
  await page.waitForFunction(code=>document.querySelector('canvas')?.dataset.detailReady==='exterior-'+code,code);
  if(code==='LRB'){
   await page.locator('#interior-view').click();
   await page.waitForFunction(()=>document.querySelector('canvas')?.dataset.detailReady==='interior-LRB');
  }
  expect(await page.locator('#fallback').isVisible()).toBe(false);
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  expect(errors).toEqual([]);
 });
}
