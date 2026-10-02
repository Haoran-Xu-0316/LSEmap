import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';

test('survey roof preserves every unrelated exterior and interior asset',async()=>{
 const verification=JSON.parse(await readFile('result/blender/stage109/saved-verification.json'));
 expect(verification.roofVoidProbes).toBe(72);
 const before=JSON.parse(await readFile('result/blender/stage109/catalogue-before.json'));
 const after=JSON.parse(await readFile('dist/models/catalogue.json'));
 expect(after.version).toBe('109');
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

test('overview and library detail share the stepped roof and heat pump layout',async()=>{
 const catalogue=JSON.parse(await readFile('dist/models/catalogue.json'));
 const lrb=catalogue.buildings.find(b=>b.code==='LRB');
 const signatures=[];
 for(const url of ['/models/campus.glb',lrb.detailedExterior.url,lrb.detailedInterior.url]){
  const bytes=await readFile('dist'+url);
  const gltf=JSON.parse(bytes.subarray(20,20+bytes.readUInt32LE(12)));
  const parts=[];
  expect(gltf.materials.some(m=>m.name.endsWith('LRB_V60_slate'))).toBe(false);
  for(const suffix of ['LRB_V31_light_metal_roof','LRB_V109_roof','LRB_V109_plant','LRB_V109_panel']){
   const materialIndex=gltf.materials.findIndex(m=>m.name.endsWith(suffix));
   expect(materialIndex).toBeGreaterThanOrEqual(0);
   const primitives=gltf.meshes.flatMap(m=>m.primitives).filter(p=>p.material===materialIndex);
   expect(primitives.length).toBe(1);
   const accessor=gltf.accessors[primitives[0].attributes.POSITION];
   parts.push({position:{min:accessor.min,max:accessor.max,count:accessor.count,type:accessor.type},
    material:gltf.materials[materialIndex].pbrMetallicRoughness});
   if(suffix.endsWith('light_metal_roof')){
    expect(accessor.max[0]-accessor.min[0]).toBeCloseTo(13.78,2);
    expect(accessor.max[1]-accessor.min[1]).toBeCloseTo(6.89,2);
   }
  }
  signatures.push(parts);
 }
 expect(signatures[0]).toEqual(signatures[1]);
 expect(signatures[1]).toEqual(signatures[2]);
});

test('library survey roof and shared interior load on desktop and mobile',async({page})=>{
 const errors=[];page.on('pageerror',error=>errors.push(error.message));
 for(const width of [1440,390]){
  await page.setViewportSize({width,height:1000});await page.goto('/#LRB');
  await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-LRB',{timeout:60000});
  await expect(page.locator('#fallback')).toBeHidden();
  await page.locator('.detail-gallery img[src*="lrb-exterior"]').click();
  await expect(page.locator('#gallery-image')).toBeVisible();
  expect(await page.locator('#gallery-image').evaluate(i=>i.complete&&i.naturalWidth>0)).toBe(true);
  await page.locator('#gallery-dialog [data-close]').click();
  await page.locator('#interior-view').click();
  await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','interior-LRB',{timeout:60000});
  await expect(page.locator('#fallback')).toBeHidden();
 }
 expect(errors).toEqual([]);
});
