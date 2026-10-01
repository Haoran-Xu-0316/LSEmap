import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';

test('saved OLD fan masonry faces the street and retains earlier entrance work',async()=>{
 const audit=JSON.parse(await readFile('result/blender/stage69/old-arch-masonry-audit.json'));
 expect(audit.changedExistingGeometry).toEqual([]);
 expect(audit.savedMeasurements.frontFacingFanStones).toBe(20);
 expect(audit.savedMeasurements.mottoVerified).toBeTruthy();
 expect(audit.savedMeasurements.joineryAndEarlierReliefRetained).toBeTruthy();
});

test('OLD overview and close models share radial stone and shield materials',async()=>{
 const catalogue=JSON.parse(await readFile('dist/models/catalogue.json'));
 const old=catalogue.buildings.find(b=>b.code==='OLD');
 for(const url of ['/models/campus.glb',old.detailedExterior.url]){
  const bytes=await readFile('dist'+url);
  const doc=JSON.parse(bytes.subarray(20,20+bytes.readUInt32LE(12)));
  const node=doc.nodes.find(n=>n.extras?.buildingCode==='OLD')??doc.nodes.find(n=>n.mesh!==undefined);
  const names=doc.meshes[node.mesh].primitives.map(p=>doc.materials[p.material].name);
  for(const key of ['stone','recess','joint','letter'])expect(names.some(n=>n.endsWith('OLD_V69_'+key))).toBeTruthy();
  expect(names.some(n=>n.endsWith('OLD_V65_glass'))).toBeTruthy();
  expect(names.some(n=>n.endsWith('OLD_V71_stone'))).toBeTruthy();
 }
});

test('OLD revised entrance opens with working 3D, logo and gallery',async({page})=>{
 const errors=[];page.on('pageerror',error=>errors.push(error.message));
 await page.goto('/#OLD');
 await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-OLD',{timeout:60000});
 await expect(page.locator('#fallback')).toBeHidden();
 expect(await page.locator('.brand-mark').evaluate(image=>image.complete&&image.naturalWidth>0)).toBeTruthy();
 await page.locator('.detail-gallery img[src*="old-houghton-entrance"]').click();
 await expect(page.locator('#gallery-image')).toHaveAttribute('src',/old-houghton-entrance\.webp\?v=/);
 expect(errors).toEqual([]);
});
