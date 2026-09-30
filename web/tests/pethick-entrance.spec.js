import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';
test('saved PEL entrance retains the other buildings and verified facade dimensions',async()=>{
 const a=JSON.parse(await readFile('result/blender/stage61/pethick-entrance-audit.json'));
 expect(a.protectedBefore).toBe(a.protectedAfter);expect(Object.keys(a.removedMembers).length).toBeGreaterThan(10);
 expect(a.savedMeasurements.canopy.width).toBeCloseTo(5.68,4);expect(a.savedMeasurements.canopy.frontDepth).toBeCloseTo(1.6,4);
 expect(a.savedMeasurements.upperGlass.zMin).toBeCloseTo(4.07,4);expect(a.savedMeasurements.revolvingFaces).toBe(20);
});
test('PEL overview and detailed exterior share the corrected entrance materials',async()=>{
 const catalogue=JSON.parse(await readFile('dist/models/catalogue.json'));const b=catalogue.buildings.find(b=>b.code==='PEL');
 for(const url of ['/models/campus.glb',b.detailedExterior.url]){
  const bytes=await readFile('dist'+url);const doc=JSON.parse(bytes.subarray(20,20+bytes.readUInt32LE(12)));
  const node=doc.nodes.find(n=>n.extras?.buildingCode==='PEL')??doc.nodes.find(n=>n.mesh!==undefined);
  const names=doc.meshes[node.mesh].primitives.map(p=>doc.materials[p.material].name);
  for(const key of ['silver','yellow','glass','dark','red','white'])expect(names.some(n=>n.endsWith('PEL_V61_'+key))).toBeTruthy();
 }
});
test('PEL entry gallery loads with the detailed building',async({page})=>{
 const errors=[];page.on('pageerror',e=>errors.push(e.message));await page.goto('/#PEL');
 await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-PEL',{timeout:60000});await expect(page.locator('#fallback')).toBeHidden();
 await page.locator('.detail-gallery img[src*="pel-entrance"]').click();await expect(page.locator('#gallery-image')).toHaveAttribute('src',/pel-entrance\.webp\?v=/);expect(errors).toEqual([]);
});
