import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';

test('OLD figure refinement retains every other building and public interior',async()=>{
 const verification=JSON.parse(await readFile('result/blender/stage106/saved-verification.json'));
 expect(verification.originalsRetained).toBe(true);
 const before=JSON.parse(await readFile('result/blender/stage106/catalogue-before.json'));
 const after=JSON.parse(await readFile('dist/models/catalogue.json'));
 expect(after.version).toBe('106');
 for(const old of before.buildings){
  const current=after.buildings.find(b=>b.code===old.code);
  if(old.code==='OLD'){
   expect(current.detailedExterior.url).not.toBe(old.detailedExterior.url);
   expect(current.detailedExterior.bytes).toBeLessThan(23*1024*1024);
   expect(current.detailedExterior.triangles).toBeLessThan(2100000);
  }else expect(current.detailedExterior).toEqual(old.detailedExterior);
  expect(current.detailedInterior).toEqual(old.detailedInterior);
  expect(current.interiorSpaces).toEqual(old.interiorSpaces);
 }
});

test('OLD overview and close view share opaque double-sided plastic strands',async()=>{
 const catalogue=JSON.parse(await readFile('dist/models/catalogue.json'));
 const building=catalogue.buildings.find(b=>b.code==='OLD');
 const finishes=[];
 for(const url of ['/models/campus.glb',building.detailedExterior.url]){
  const bytes=await readFile('dist'+url);
  const document=JSON.parse(bytes.subarray(20,20+bytes.readUInt32LE(12)));
  const material=document.materials.find(m=>m.name.includes('OLD_V106_double_sided_plastic'));
  expect(material).toBeTruthy();
  expect(material.doubleSided).toBe(true);
  expect(material.alphaMode??'OPAQUE').toBe('OPAQUE');
  finishes.push(material.pbrMetallicRoughness);
 }
 expect(finishes[0]).toEqual(finishes[1]);
});

test('OLD sculpture gallery loads on desktop and mobile without fallback',async({page})=>{
 const errors=[];page.on('pageerror',error=>errors.push(error.message));
 for(const width of [1440,390]){
  await page.setViewportSize({width,height:1000});
  await page.goto('/#OLD');
  await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-OLD',{timeout:60000});
  await expect(page.locator('#fallback')).toBeHidden();
  await page.locator('.detail-gallery img[src*="old-relief"]').click();
  await expect(page.locator('#gallery-image')).toBeVisible();
  expect(await page.locator('#gallery-image').evaluate(i=>i.complete&&i.naturalWidth>0)).toBeTruthy();
  await page.locator('#gallery-dialog [data-close]').click();
 }
 expect(errors).toEqual([]);
});
