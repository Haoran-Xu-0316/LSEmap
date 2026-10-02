import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';

test('OLD arch finish preserves geometry and unrelated assets',async()=>{
 const audit=JSON.parse(await readFile('result/blender/stage103/old-arch-finish-audit.json'));
 expect(audit.savedMeasurements.originalObjectsUnchanged).toBeTruthy();
 expect(audit.savedMeasurements.identicalGeometry).toBeTruthy();
 expect(audit.savedMeasurements.smoothCurvedFaces).toBe(240);
 expect(audit.savedMeasurements.verifiedNormalCorners).toBe(960);
 const before=JSON.parse(await readFile('result/blender/stage103/catalogue-before.json'));
 const after=JSON.parse(await readFile('dist/models/catalogue.json'));
 for(const b of before.buildings){
  const current=after.buildings.find(x=>x.code===b.code);
  if(b.code==='OLD')expect(current.detailedExterior.url).not.toBe(b.detailedExterior.url);
  else expect(current.detailedExterior?.url).toBe(b.detailedExterior?.url);
  expect(current.detailedInterior?.url).toBe(b.detailedInterior?.url);
  expect(current.interiorSpaces).toEqual(b.interiorSpaces);
 }
});

test('overview and OLD detail use identical five stone finishes',async()=>{
 const catalogue=JSON.parse(await readFile('dist/models/catalogue.json'));
 const old=catalogue.buildings.find(b=>b.code==='OLD');
 const finishes=[];
 for(const url of ['/models/campus.glb',old.detailedExterior.url]){
  const bytes=await readFile('dist'+url);
  const doc=JSON.parse(bytes.subarray(20,20+bytes.readUInt32LE(12)));
  const selected=doc.materials.filter(m=>m.name.includes('OLD_V103_arch_limestone_'));
  expect(selected).toHaveLength(5);
  const normalized=selected.map(m=>({name:m.name.split('OLD_V103_')[1],pbr:m.pbrMetallicRoughness,surface:m.extras.surfaceDetail})).sort((a,b)=>a.name.localeCompare(b.name));
  for(const m of normalized){expect(m.surface.scale).toBe(3.5);expect(m.pbr.roughnessFactor).toBeCloseTo(.88,5);}
  finishes.push(normalized);
 }
 expect(finishes[0]).toEqual(finishes[1]);
});

test('OLD entrance gallery opens on desktop and mobile',async({page})=>{
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 for(const width of [1440,390]){
  await page.setViewportSize({width,height:1000});
  await page.goto('/#OLD');
  await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-OLD',{timeout:60000});
  await expect(page.locator('#fallback')).toBeHidden();
  await page.locator('.detail-gallery img[src*="old-houghton-entrance"]').click();
  await expect(page.locator('#gallery-image')).toBeVisible();
  expect(await page.locator('#gallery-image').evaluate(i=>i.complete&&i.naturalWidth>0)).toBeTruthy();
  await page.locator('#gallery-dialog [data-close]').click();
  await expect(page.locator('#gallery-dialog')).not.toBeVisible();
 }
 expect(errors).toEqual([]);
});
