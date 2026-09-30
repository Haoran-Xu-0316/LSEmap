import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';

test('saved LAK sashes have three equal columns and preserve other buildings',async()=>{
 const audit=JSON.parse(await readFile('result/blender/stage59/lakatos-sash-audit.json'));
 expect(audit.protectedGeometryAfter).toBe(audit.protectedGeometryBefore);
 expect(audit.oldBars).toBe(90);expect(audit.newBars).toBe(60);expect(audit.newHorizontalBars).toBe(80);expect(audit.rowsByStorey).toEqual([6,4,4]);
 expect(audit.savedWindowMeasurements).toHaveLength(30);
 for(const window of audit.savedWindowMeasurements){
  expect(window.fractions).toHaveLength(2);expect(window.horizontalFractions).toHaveLength(window.rows-2);
  const expected=window.rows===6?[1/6,2/6,4/6,5/6]:[.25,.75];
  expected.forEach((fraction,index)=>expect(window.horizontalFractions[index]).toBeCloseTo(fraction,4));
  expect(window.fractions[0]).toBeCloseTo(-1/6,4);expect(window.fractions[1]).toBeCloseTo(1/6,4);
 }
});

test('LAK overview and detail use the corrected sashes and isolated facade palette',async()=>{
 const catalogue=JSON.parse(await readFile('dist/models/catalogue.json'));const building=catalogue.buildings.find(b=>b.code==='LAK');
 for(const url of ['/models/campus.glb',building.detailedExterior.url]){
  const bytes=await readFile('dist'+url);const doc=JSON.parse(bytes.subarray(20,20+bytes.readUInt32LE(12)));
  const node=doc.nodes.find(n=>n.extras?.buildingCode==='LAK')??doc.nodes.find(n=>n.mesh!==undefined);
  const materials=doc.meshes[node.mesh].primitives.map(p=>doc.materials[p.material]);
  for(const key of ['brick','stone','frame','glass'])expect(materials.some(m=>m.name.endsWith('LAK_V59_'+key))).toBeTruthy();
  const brick=materials.find(m=>m.name.endsWith('LAK_V59_brick'));
  expect(brick.extras.surfaceDetail.colorA[0]).toBeCloseTo(.46);
  expect(brick.extras.surfaceDetail.brickWidth).toBeCloseTo(.225);
  const frame=materials.find(m=>m.name.endsWith('LAK_V59_frame')).pbrMetallicRoughness.baseColorFactor;
  expect(frame[0]-frame[2]).toBeLessThan(.045);
 }
});

test('LAK exterior and revised upper-window gallery load without errors',async({page})=>{
 const errors=[];page.on('pageerror',e=>errors.push(e.message));await page.goto('/#LAK');
 await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-LAK',{timeout:60000});
 await expect(page.locator('#fallback')).toBeHidden();await page.locator('.detail-gallery img[src*="lak-windows"]').click();
 await expect(page.locator('#gallery-image')).toHaveAttribute('src',/lak-windows\.webp\?v=/);
 const gallery=JSON.parse(await readFile('dist/gallery-manifest.json'));const view=gallery.images.find(i=>i.name==='lak-windows').view;
 expect(view.target[1]).toBeCloseTo(6);expect(view.position[1]).toBeCloseTo(6.5);expect(errors).toEqual([]);
});
