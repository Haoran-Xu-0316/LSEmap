import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';

test('saved OLD entrance has four leaves and rectangular straight stairs',async()=>{
 const a=JSON.parse(await readFile('result/blender/stage65/old-entry-joinery-audit.json'));
 expect(a.changedExistingGeometry).toEqual(['OLD_V52_Houghton_iron']);
 expect(a.removedDoorMembers).toBe(8);
 expect(a.savedMeasurements.glassLeaves).toBe(4);
 expect(a.savedMeasurements.transomLights).toBe(4);
 expect(a.savedMeasurements.stairBounds).toHaveLength(4);
 for(const [i,b] of a.savedMeasurements.stairBounds.entries()){
  expect(b[0][0]).toBeCloseTo(-4.4,3);expect(b[0][1]).toBeCloseTo(3.2,3);
  expect(b[2][1]).toBeCloseTo(.69-i*.1675,4);
 }
});

test('OLD overview and close model share entry materials and retain earlier relief',async()=>{
 const catalogue=JSON.parse(await readFile('dist/models/catalogue.json'));
 const old=catalogue.buildings.find(b=>b.code==='OLD');
 for(const url of ['/models/campus.glb',old.detailedExterior.url]){
  const bytes=await readFile('dist'+url);const doc=JSON.parse(bytes.subarray(20,20+bytes.readUInt32LE(12)));
  const node=doc.nodes.find(n=>n.extras?.buildingCode==='OLD')??doc.nodes.find(n=>n.mesh!==undefined);
  const names=doc.meshes[node.mesh].primitives.map(p=>doc.materials[p.material].name);
  for(const key of ['stone','frame','steel','glass'])expect(names.some(n=>n.endsWith('OLD_V65_'+key))).toBeTruthy();
  expect(names.some(n=>n.endsWith('OLD_V56_stone'))).toBeTruthy();
  expect(names.some(n=>n.endsWith('OLD_V53_blue'))).toBeTruthy();
 }
});

test('OLD entrance gallery and model load with a working logo',async({page})=>{
 const errors=[];page.on('pageerror',error=>errors.push(error.message));
 await page.goto('/#OLD');
 await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-OLD',{timeout:60000});
 await expect(page.locator('#fallback')).toBeHidden();
 expect(await page.locator('.brand-mark').evaluate(image=>image.complete&&image.naturalWidth>0)).toBeTruthy();
 await page.locator('.detail-gallery img[src*="old-houghton-entrance"]').click();
 await expect(page.locator('#gallery-image')).toHaveAttribute('src',/old-houghton-entrance\.webp\?v=/);
 expect(errors).toEqual([]);
});
