import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';

test('MAR podium correction retains unrelated facades and room models',async()=>{
 const audit=JSON.parse(await readFile('result/blender/stage104/mar-podium-audit.json'));
 for(const key of ['originalObjectsUnchanged','otherFrameVerticesUnchanged','threePaneMeshesRetained','threeSingleColumnTwoPaneWindows','onlyThreePaneAssignmentsChanged','obsoleteSillOverlapsRemoved','mezzanineSlabClearOfWindows'])expect(audit.savedMeasurements[key],key).toBeTruthy();
 expect(audit.savedMeasurements.closedJoineryRails).toBe(15);
 expect(audit.savedMeasurements.slabHeightUnchanged).toBeTruthy();
 expect(audit.savedMeasurements.retainedSlabAndVoidProbes).toBe(476);
 const before=JSON.parse(await readFile('result/blender/stage104/catalogue-before.json'));
 const after=JSON.parse(await readFile('dist/models/catalogue.json'));
 for(const b of before.buildings){
  const current=after.buildings.find(x=>x.code===b.code);
  if(b.code==='MAR')expect(current.detailedExterior.url).not.toBe(b.detailedExterior.url);
  else expect(current.detailedExterior?.url).toBe(b.detailedExterior?.url);
  if(b.code==='MAR')expect(current.detailedInterior.url).not.toBe(b.detailedInterior.url);
  else expect(current.detailedInterior?.url).toBe(b.detailedInterior?.url);
  expect(current.interiorSpaces).toEqual(b.interiorSpaces);
 }
});

test('campus and MAR detail share the same podium glass finish',async()=>{
 const catalogue=JSON.parse(await readFile('dist/models/catalogue.json'));
 const mar=catalogue.buildings.find(b=>b.code==='MAR');
 const finishes=[];
 for(const url of ['/models/campus.glb',mar.detailedExterior.url]){
  const bytes=await readFile('dist'+url);
  const doc=JSON.parse(bytes.subarray(20,20+bytes.readUInt32LE(12)));
  const selected=doc.materials.filter(m=>m.name.includes('MAR_V104_podium_glass'));
  expect(selected).toHaveLength(1);
  expect(selected[0].pbrMetallicRoughness.baseColorFactor[3]).toBeCloseTo(1,5);
  expect(selected[0].pbrMetallicRoughness.roughnessFactor).toBeCloseTo(.15,5);
  finishes.push(selected[0].pbrMetallicRoughness);
 }
 expect(finishes[0]).toEqual(finishes[1]);
});

test('MAR exterior and podium gallery load on desktop and mobile',async({page})=>{
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 for(const width of [1440,390]){
  await page.setViewportSize({width,height:1000});await page.goto('/#MAR');
  await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-MAR',{timeout:60000});
  await expect(page.locator('#fallback')).toBeHidden();
  await page.locator('.detail-gallery img[src*="mar-podium-windows"]').click();
  await expect(page.locator('#gallery-image')).toBeVisible();
  expect(await page.locator('#gallery-image').evaluate(i=>i.complete&&i.naturalWidth>0)).toBeTruthy();
  await page.locator('#gallery-dialog [data-close]').click();
  await expect(page.locator('#gallery-dialog')).not.toBeVisible();
 }
 expect(errors).toEqual([]);
});
