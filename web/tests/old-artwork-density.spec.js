import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';

test('OLD artwork retains open strands, topology and unrelated buildings',async()=>{
 const audit=JSON.parse(await readFile('result/blender/stage111-old/old-artwork-density-audit.json'));
 expect(audit.savedMeasurements.allOriginalObjectsUnchanged).toBeTruthy();
 expect(audit.savedMeasurements.openLatticeRetained).toBeTruthy();
 for(const family of audit.savedMeasurements.families){
  expect(family.topologyUnchanged).toBeTruthy();
  expect(family.afterHits).toBeGreaterThan(family.beforeHits*1.1);
  expect(family.afterHits).toBeLessThan(family.samples*.75);
 }
 const before=JSON.parse(await readFile('result/blender/stage111-old/catalogue-before.json'));
 const after=JSON.parse(await readFile('dist/models/catalogue.json'));
 for(const b of before.buildings){
  const current=after.buildings.find(x=>x.code===b.code);
  if(b.code==='OLD')expect(current.detailedExterior.url).not.toBe(b.detailedExterior.url);
  else expect(current.detailedExterior?.url).toBe(b.detailedExterior?.url);
  expect(current.detailedInterior?.url).toBe(b.detailedInterior?.url);
  expect(current.interiorSpaces).toEqual(b.interiorSpaces);
 }
});

test('OLD overview and detail share the same artwork geometry',async()=>{
 const catalogue=JSON.parse(await readFile('dist/models/catalogue.json'));
 const old=catalogue.buildings.find(b=>b.code==='OLD');
 const compared=[];
 for(const url of ['/models/campus.glb',old.detailedExterior.url]){
  const bytes=await readFile('dist'+url);
  const doc=JSON.parse(bytes.subarray(20,20+bytes.readUInt32LE(12)));
  const families=[];
  for(const mesh of doc.meshes)for(const p of mesh.primitives){
   const m=doc.materials[p.material];
   if(!/OLD_V106_double_sided_plastic|OLD_V84_FinalSale_products/.test(m.name))continue;
   const position=doc.accessors[p.attributes.POSITION];
   // Detail export splits vertices at shading boundaries. Triangle counts and
   // geometric bounds are invariant; raw attribute vertex counts are not.
   families.push({family:m.name.replace(/^WEB_(DETAIL_)?/,''),indices:doc.accessors[p.indices].count,min:position.min,max:position.max,pbr:m.pbrMetallicRoughness});
  }
  expect(families).toHaveLength(2);
  compared.push(families.sort((a,b)=>a.family.localeCompare(b.family)));
 }
 expect(compared[0]).toEqual(compared[1]);
});

test('OLD entrance works on desktop and mobile with latest gallery',async({page})=>{
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 for(const width of [1440,390]){
  await page.setViewportSize({width,height:1000});
  await page.goto('/#OLD');
  await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-OLD',{timeout:60000});
  await expect(page.locator('#fallback')).toBeHidden();
  expect(await page.locator('.brand-mark').evaluate(i=>i.complete&&i.naturalWidth>0)).toBeTruthy();
  await page.locator('.detail-gallery img[src*="old-houghton-entrance"]').click();
  await expect(page.locator('#gallery-image')).toBeVisible();
  expect(await page.locator('#gallery-image').evaluate(i=>i.complete&&i.naturalWidth>0)).toBeTruthy();
  await page.locator('#gallery-dialog [data-close]').click();
 }
 expect(errors).toEqual([]);
});
