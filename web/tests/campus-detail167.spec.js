import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';
const read=async path=>JSON.parse(await readFile(path,'utf8'));

test('edition167 preserves existing interiors and scopes the new room samples',async()=>{
 const before=await read('result/blender/stage167/catalogue-before.json');
 const current=await read('dist/models/catalogue.json');
 const proof=await read('result/blender/stage167/building-refinement.json');
 const native=await read('result/blender/stage167/reopened-verification.json');
 expect(current.version).toBe('167');expect(current.buildings).toHaveLength(31);
 expect(current.sourceModelSha256).toBe(proof.sourceModelSha256);
 expect(native.sourceModelSha256).toBe(proof.sourceModelSha256);
 expect(native.idempotent).toBe(true);expect(native.roomsOutsideCampus).toBe(true);
 expect(native.allOriginalShapesAndUVsPreserved).toBe(true);
 const newIds=['cbg-104','ckk-107'];let found=[];
 for(const building of current.buildings){
  const old=before.buildings.find(b=>b.code===building.code);
  if(building.code==='COL')expect(building.detailedExterior.sha256).not.toBe(old.detailedExterior.sha256);
  else expect(building.detailedExterior,building.code).toEqual(old.detailedExterior);
  expect(building.detailedInterior,building.code).toEqual(old.detailedInterior);
  const spaces=building.interiorSpaces||[];
  expect(spaces.filter(s=>!newIds.includes(s.id)),building.code).toEqual(old.interiorSpaces||[]);
  found.push(...spaces.filter(s=>newIds.includes(s.id)).map(s=>s.id));
 }
 expect(found.sort()).toEqual(newIds.sort());
 const gallery=await read('dist/gallery-manifest.json');
 expect(JSON.stringify(gallery)).toContain('cbg-104-interior');
 expect(JSON.stringify(gallery)).toContain('ckk-107-interior');
});

for(const width of [1440,390])for(const [code,space] of [['CBG','cbg-104'],['CKK','ckk-107']]){
 test(`${code} new room loads at${width}px`,async({page})=>{
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.setViewportSize({width,height:1000});await page.goto('/#'+code);
  await page.waitForFunction(code=>document.querySelector('canvas')?.dataset.detailReady==='exterior-'+code,code);
  await page.locator('#interior-view').click();
  await page.locator('#interior-space').selectOption(space);
  await page.waitForFunction(id=>document.querySelector('canvas')?.dataset.interiorSpace===id,space);
  expect(await page.locator('#fallback').isVisible()).toBe(false);
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  expect(errors).toEqual([]);
 });
}
