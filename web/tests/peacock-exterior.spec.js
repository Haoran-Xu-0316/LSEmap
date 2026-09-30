import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';
test('saved Peacock has a low podium and a three-column upper wing',async()=>{
 const a=JSON.parse(await readFile('result/blender/stage62/peacock-exterior-audit.json'));
 expect(a.protectedBefore).toBe(a.protectedAfter);expect(a.savedMeasurements.podium.high).toBeCloseTo(6.6,4);expect(a.savedMeasurements.upper.high).toBeCloseTo(19.5,4);
 expect(a.savedMeasurements.windows).toBe(9);expect(a.savedMeasurements.posters).toBe(3);expect(a.savedMeasurements.starbursts).toBe(19);expect(a.savedMeasurements.signObjects).toBe(17);
 expect(a.upperFootprint.every(p=>p[0]>=-.001)).toBeTruthy();expect(Math.min(...a.lowerFootprint.map(p=>p[0]))).toBeLessThan(-5);
});
test('Peacock materials match in the campus and detailed model',async()=>{
 const c=JSON.parse(await readFile('dist/models/catalogue.json'));const b=c.buildings.find(b=>b.code==='PEA');
 for(const path of ['/models/campus.glb',b.detailedExterior.url]){
  const bytes=await readFile('dist'+path);const d=JSON.parse(bytes.subarray(20,20+bytes.readUInt32LE(12)));const node=d.nodes.find(n=>n.extras?.buildingCode==='PEA')??d.nodes.find(n=>n.mesh!==undefined);const names=d.meshes[node.mesh].primitives.map(p=>d.materials[p.material].name);
  for(const k of ['stone','panel','brick','glass','gold','lamp'])expect(names.some(n=>n.endsWith('PEA_V62_'+k))).toBeTruthy();
 }
});
test('Peacock frontage gallery and existing interior remain available',async({page})=>{
 const errors=[];page.on('pageerror',e=>errors.push(e.message));await page.goto('/#PEA');await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-PEA',{timeout:60000});await expect(page.locator('#fallback')).toBeHidden();
 await page.locator('.detail-gallery img[src*="pea-frontage"]').click();await expect(page.locator('#gallery-image')).toHaveAttribute('src',/pea-frontage\.webp\?v=/);await page.keyboard.press('Escape');await page.locator('#interior-view').click();await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','interior-PEA',{timeout:60000});expect(errors).toEqual([]);
});
