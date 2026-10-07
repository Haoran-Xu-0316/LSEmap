import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';
const read=async path=>JSON.parse(await readFile(path,'utf8'));

test('edition171 isolates the upper stair and new teaching room',async()=>{
 const before=await read('result/blender/stage171/catalogue-before.json');
 const current=await read('dist/models/catalogue.json');
 const proof=await read('result/blender/stage171/building-refinement.json');
 const native=await read('result/blender/stage171/reopened-verification.json');
 expect(current.version).toBe('171');expect(current.buildings).toHaveLength(31);
 expect(current.sourceModelSha256).toBe(proof.sourceModelSha256);
 expect(native.sourceModelSha256).toBe(proof.sourceModelSha256);
 expect(native.idempotent).toBe(true);expect(native.roomsOutsideCampus).toBe(true);
 expect(native.allOriginalShapesAndUVsPreserved).toBe(true);
 for(const building of current.buildings){
  const old=before.buildings.find(b=>b.code===building.code);
  if(building.code==='SAW'){
   expect(building.detailedExterior.sha256).not.toBe(old.detailedExterior.sha256);
   expect(building.detailedInterior.sha256).not.toBe(old.detailedInterior.sha256);
  }else{
   expect(building.detailedExterior,building.code).toEqual(old.detailedExterior);
   expect(building.detailedInterior,building.code).toEqual(old.detailedInterior);
  }
  for(const room of old.interiorSpaces??[]){
   expect(building.interiorSpaces.find(s=>s.id===room.id),room.id).toEqual(room);
  }
 }
 const cbg=current.buildings.find(b=>b.code==='CBG');
 expect(cbg.interiorSpaces.find(s=>s.id==='cbg-205')).toBeTruthy();
 expect(proof.changes.find(c=>c.roomAudits)?.roomAudits[0].studentSeatCount).toBe(42);
});
for(const width of [1440,390])for(const code of ['SAW','CBG']){
 test(`${code} edition171 interior loads at${width}px`,async({page})=>{
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.setViewportSize({width,height:1000});await page.goto('/#'+code);
  await page.waitForFunction(code=>document.querySelector('canvas')?.dataset.detailReady==='exterior-'+code,code);
  await page.locator('#interior-view').click();
  await page.waitForFunction(code=>document.querySelector('canvas')?.dataset.detailReady==='interior-'+code,code);
  if(code==='CBG'){
   await page.locator('#interior-space').selectOption('cbg-205');
   await page.waitForFunction(()=>document.querySelector('canvas')?.dataset.detailReady==='interior-CBG:cbg-205');
  }
  expect(await page.locator('#fallback').isVisible()).toBe(false);
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  expect(errors).toEqual([]);
 });
}
