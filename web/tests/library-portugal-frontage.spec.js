import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';

test('Portugal Street rebuild retains unrelated building and room assets',async()=>{
 const before=JSON.parse(await readFile('result/blender/stage110/catalogue-before.json'));
 const after=JSON.parse(await readFile('dist/models/catalogue.json'));
 const saved=JSON.parse(await readFile('result/blender/stage110/saved-verification.json'));
 expect(after.version).toBe('110');expect(saved.originalGeometryRetained).toBe(true);
 expect(saved.tripleUpperLights).toBe(63);expect(saved.mansardWindows).toBe(18);
 expect(saved.clearWindowProbes).toBe(102);
 for(const old of before.buildings){
  const current=after.buildings.find(b=>b.code===old.code);
  if(old.code==='LRB'){
   expect(current.detailedExterior.url).not.toBe(old.detailedExterior.url);
   expect(current.detailedInterior.url).not.toBe(old.detailedInterior.url);
  }else{
   expect(current.detailedExterior).toEqual(old.detailedExterior);
   expect(current.detailedInterior).toEqual(old.detailedInterior);
  }
  expect(current.interiorSpaces).toEqual(old.interiorSpaces);
 }
});

test('overview detail and interior share the historic mansard surface',async()=>{
 const catalogue=JSON.parse(await readFile('dist/models/catalogue.json'));
 const lrb=catalogue.buildings.find(b=>b.code==='LRB');const records=[];
 for(const url of ['/models/campus.glb',lrb.detailedExterior.url,lrb.detailedInterior.url]){
  const bytes=await readFile('dist'+url);const gltf=JSON.parse(bytes.subarray(20,20+bytes.readUInt32LE(12)));
  const parts=[];
  for(const name of ['LRB_V110_roof','LRB_V110_roof_glass','LRB_V110_roof_stone','LRB_V110_roof_frame','LRB_V110_roof_rail']){
   const index=gltf.materials.findIndex(m=>m.name.endsWith(name));expect(index).toBeGreaterThanOrEqual(0);
   const primitive=gltf.meshes.flatMap(m=>m.primitives).filter(p=>p.material===index);expect(primitive).toHaveLength(1);
   const p=gltf.accessors[primitive[0].attributes.POSITION];parts.push({name,count:p.count,min:p.min,max:p.max,material:gltf.materials[index].pbrMetallicRoughness});
  }
  records.push(parts);
 }
 expect(records[0]).toEqual(records[1]);expect(records[1]).toEqual(records[2]);
});

test('Portugal Street view and full library exterior remain available on desktop and mobile',async({page})=>{
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 for(const width of [1440,390]){
  await page.setViewportSize({width,height:1000});await page.goto('/#LRB');
  await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-LRB',{timeout:60000});
  await expect(page.locator('#fallback')).toBeHidden();
  await page.locator('.detail-gallery img[src*="lrb-portugal-street"]').click();
  await expect(page.locator('#gallery-image')).toBeVisible();
  expect(await page.locator('#gallery-image').evaluate(i=>i.complete&&i.naturalWidth>0)).toBe(true);
  await page.locator('#gallery-dialog [data-close]').click();
  await page.locator('#interior-view').click();
  await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','interior-LRB',{timeout:60000});
  await expect(page.locator('#fallback')).toBeHidden();
 }
 expect(errors).toEqual([]);
});
