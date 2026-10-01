import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';
import {buildingDetails} from '../src/content.js';

test('Clare Market window revision preserves other exterior and interior assets', async () => {
 const a=JSON.parse(await readFile('result/blender/stage87/old-clare-casement-audit.json'));
 expect(a.savedMeasurements.allOriginalObjectsUnchanged).toBeTruthy();
 expect(a.savedMeasurements.retainedFrameGeometryUnchanged).toBeTruthy();
 expect(a.savedMeasurements.ordinaryFourColumnWindows).toBe(8);
 expect(a.savedMeasurements.upperHeavyTransoms).toBe(5);
 const before=JSON.parse(await readFile('result/blender/stage87/catalogue-before.json'));
 const after=JSON.parse(await readFile('dist/models/catalogue.json'));
 for(const b of before.buildings){
  const current=after.buildings.find(c=>c.code===b.code);
  if(b.code!=='OLD')expect(current.detailedExterior?.url).toBe(b.detailedExterior?.url);
  expect(current.detailedInterior?.url).toBe(b.detailedInterior?.url);
  expect(current.interiorSpaces).toEqual(b.interiorSpaces);
 }
});

test('overview and OLD detail retain both independently corrected window families',async()=>{
 const c=JSON.parse(await readFile('dist/models/catalogue.json'));
 for(const url of ['/models/campus.glb',c.buildings.find(b=>b.code==='OLD').detailedExterior.url]){
  const bytes=await readFile('dist'+url);
  const doc=JSON.parse(bytes.subarray(20,20+bytes.readUInt32LE(12)));
  const node=doc.nodes.find(n=>n.extras?.buildingCode==='OLD')??doc.nodes.find(n=>n.mesh!==undefined);
  const names=doc.meshes[node.mesh].primitives.map(p=>doc.materials[p.material].name);
  expect(names.some(n=>n.includes('OLD_V87_Clare_four_column_blue'))).toBeTruthy();
  expect(names.some(n=>n.includes('OLD_V85_four_column_blue'))).toBeTruthy();
  expect(names.some(n=>n.includes('OLD_V84_FinalSale_figures'))).toBeTruthy();
  expect(names.some(n=>n.includes('OLD_V86_limestone_'))).toBeTruthy();
 }
});

test('FAW gallery uses its own building, and OLD entrance views load',async({page})=>{
 const gallery=JSON.parse(await readFile('dist/gallery-manifest.json'));
 expect(gallery.images.find(i=>i.name==='faw-exterior').code).toBe('FAW');
 expect(buildingDetails.FAW.images[0][0]).toBe('faw-exterior');
 expect(buildingDetails.PAN.images[0][1]).toBe('Pankhurst House外观');
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('/#FAW');
 await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-FAW',{timeout:60000});
 await page.locator('.detail-gallery img[src*="faw-exterior"]').click();
 await expect(page.locator('#gallery-image')).toBeVisible();
 expect(await page.locator('#gallery-image').evaluate(i=>i.complete&&i.naturalWidth>0)).toBeTruthy();
 await page.keyboard.press('Escape');
 await expect(page.locator('#gallery-dialog')).not.toBeVisible();
 await page.goto('/#OLD');
 await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-OLD',{timeout:60000});
 await expect(page.locator('#fallback')).toBeHidden();
 await page.locator('.detail-gallery img[src*="old-clare-market"]').click();
 await expect(page.locator('#gallery-image')).toBeVisible();
 expect(errors).toEqual([]);
});
