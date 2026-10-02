import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';

test('OLD facade relocates the entry and keeps all unrelated assets',async()=>{
 const audit=JSON.parse(await readFile('result/blender/stage112/saved-verification.json'));
 expect(audit.originalGeometryRetained).toBeTruthy();
 expect(audit.unrelatedVisibilityRetained).toBeTruthy();
 expect(audit.entranceAtConnaughtEnd).toBeTruthy();
 expect(audit.mansardWindows).toBe(12);
 expect(audit.triangularPediments).toBe(6);
 expect(audit.clearWindowProbes).toBe(88);
 expect(audit.artworkTopologyRetained).toBeTruthy();
 expect(audit.exposedStepHeights).toHaveLength(8);
 expect(audit.exposedStepHeights[5]).toBeCloseTo(1.245,4);
 for(let i=1;i<6;i++)expect(audit.exposedStepHeights[i]-audit.exposedStepHeights[i-1]).toBeCloseTo(1.245/6,4);
 const before=JSON.parse(await readFile('result/blender/stage112/catalogue-before.json'));
 const after=JSON.parse(await readFile('dist/models/catalogue.json'));
 expect(after.version).toBe('112');
 for(const b of before.buildings){
  const current=after.buildings.find(x=>x.code===b.code);
  if(b.code==='OLD')expect(current.detailedExterior.url).not.toBe(b.detailedExterior.url);
  else expect(current.detailedExterior?.url).toBe(b.detailedExterior?.url);
  expect(current.detailedInterior?.url).toBe(b.detailedInterior?.url);
  expect(current.interiorSpaces).toEqual(b.interiorSpaces);
 }
 const views=JSON.parse(await readFile('web/tools/gallery-views.json'));
 const entrance=views.find(v=>v.name==='old-houghton-entrance');
 const target=entrance.view.target;
 expect(target[2]).toBeGreaterThan(85);
});

test('OLD desktop and mobile show the new facade, gallery and existing room',async({page})=>{
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

test('OLD overview and detail share the rebuilt facade geometry and finishes',async()=>{
 const catalogue=JSON.parse(await readFile('dist/models/catalogue.json'));
 const old=catalogue.buildings.find(b=>b.code==='OLD');
 const compared=[];
 for(const url of ['/models/campus.glb',old.detailedExterior.url]){
  const bytes=await readFile('dist'+url);
  const doc=JSON.parse(bytes.subarray(20,20+bytes.readUInt32LE(12)));
  const families=[];
  for(const mesh of doc.meshes)for(const p of mesh.primitives){
   const m=doc.materials[p.material];
   if(!m.name.includes('OLD_V112_'))continue;
   const position=doc.accessors[p.attributes.POSITION];
   families.push({family:m.name.replace(/^WEB_(DETAIL_)?/,''),indices:doc.accessors[p.indices].count,min:position.min,max:position.max,pbr:m.pbrMetallicRoughness});
  }
  expect(families.length).toBeGreaterThanOrEqual(6);
  compared.push(families.sort((a,b)=>a.family.localeCompare(b.family)));
 }
 expect(compared[0]).toEqual(compared[1]);
});
