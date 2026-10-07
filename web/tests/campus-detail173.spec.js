import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';
const read=async path=>JSON.parse(await readFile(path,'utf8'));

test('edition173 replaces misregistered stairs and duplicate panes without altering other rooms',async()=>{
 const before=await read('result/blender/stage173/catalogue-before.json');
 const current=await read('dist/models/catalogue.json');
 const proof=await read('result/blender/stage173/building-refinement.json');
 const native=await read('result/blender/stage173/reopened-verification.json');
 expect(current.version).toBe('173');expect(current.buildings).toHaveLength(31);
 expect(current.sourceModelSha256).toBe(proof.sourceModelSha256);
 expect(native.idempotent).toBe(true);expect(native.allOriginalShapesAndUVsPreserved).toBe(true);
 for(const building of current.buildings){
  const old=before.buildings.find(b=>b.code===building.code);
  if(['CKK','SAW'].includes(building.code)) expect(building.detailedExterior.sha256).not.toBe(old.detailedExterior.sha256);
  else expect(building.detailedExterior,building.code).toEqual(old.detailedExterior);
  expect(building.interiorSpaces,building.code).toEqual(old.interiorSpaces);
 }
 const stair=proof.changes.find(c=>c.flights);
 expect(stair.flights).toHaveLength(6);
 expect(stair.archivedObjects).toContain("SAW_spiral_stair_treads");
});
for(const width of [1440,390])for(const code of ['CKK','SAW']){
 test(`${code} edition173 loads at${width}px`,async({page})=>{
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
