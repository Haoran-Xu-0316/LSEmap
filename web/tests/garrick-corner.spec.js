import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';

test('Garrick corner correction preserves original apertures and other building assets',async()=>{
 const audit=JSON.parse(await readFile('result/blender/stage99/garrick-corner-audit.json'));
 for(const key of ['originalObjectsUnchanged','entryApertureVerticesUnchanged','otherWindowVerticesUnchanged','mountedSignVerified','closedPullHandles'])expect(audit.savedMeasurements[key],key).toBeTruthy();
 expect(audit.savedMeasurements.cornerFrameComponents).toBe(6);
 expect(audit.savedMeasurements.cornerPaneComponents).toBe(1);
 const before=JSON.parse(await readFile('result/blender/stage99/catalogue-before.json'));
 const after=JSON.parse(await readFile('dist/models/catalogue.json'));
 expect(after.version).toBe('99');
 for(const building of before.buildings){
  const current=after.buildings.find(b=>b.code===building.code);
  if(building.code!=='COL')expect(current.detailedExterior?.url).toBe(building.detailedExterior?.url);
  expect(current.detailedInterior?.url).toBe(building.detailedInterior?.url);
  expect(current.interiorSpaces).toEqual(building.interiorSpaces);
 }
 const col=after.buildings.find(b=>b.code==='COL');
 expect(col.detailedExterior.url).not.toBe(before.buildings.find(b=>b.code==='COL').detailedExterior.url);
 for(const url of ['/models/campus.glb',col.detailedExterior.url]){
  const bytes=await readFile('dist'+url);
  const doc=JSON.parse(bytes.subarray(20,20+bytes.readUInt32LE(12)));
  const glass=doc.materials.find(m=>m.name.replace(/^WEB_(?:DETAIL_)?/,'')==='COL_V99_garrick_glass');
  expect(glass.alphaMode).toBe('BLEND');
  expect(glass.pbrMetallicRoughness.baseColorFactor[3]).toBeCloseTo(.52,5);
 }
});

test('Garrick corner close view loads alongside the main Columbia entrance',async({page})=>{
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('/#COL');
 await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-COL',{timeout:60000});
 await expect(page.locator('#fallback')).toBeHidden();
 await expect(page.locator('.detail-gallery img[src*="col-entrance"]')).toHaveCount(1);
 await page.locator('.detail-gallery img[src*="col-garrick-entrance"]').click();
 await expect(page.locator('#gallery-image')).toBeVisible();
 expect(await page.locator('#gallery-image').evaluate(i=>i.complete&&i.naturalWidth>0)).toBeTruthy();
 expect(errors).toEqual([]);
});
