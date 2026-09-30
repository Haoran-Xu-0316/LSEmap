import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';
test('saved Columbia entry has two lower oval mouldings and an inset tablet',async()=>{
 const a=JSON.parse(await readFile('result/blender/stage67/columbia-entry-audit.json'));
 expect(a.changedOtherObjects).toEqual([]);
 expect(a.changedExistingObjects.sort()).toEqual(['COL_D4_double_timber_door','COL_D4_portal_name']);
 expect(a.savedMeasurements.ovalPanels).toHaveLength(2);expect(a.savedMeasurements.tabletBorderMembers).toBe(8);
 for(const panel of a.savedMeasurements.ovalPanels){expect(panel.width).toBeCloseTo(.47,4);expect(panel.height).toBeCloseTo(.58,4)}
});
test('Columbia overview and close entrance share panel materials',async()=>{
 const c=JSON.parse(await readFile('dist/models/catalogue.json'));const b=c.buildings.find(b=>b.code==='COL');
 for(const path of ['/models/campus.glb',b.detailedExterior.url]){
  const bytes=await readFile('dist'+path);const d=JSON.parse(bytes.subarray(20,20+bytes.readUInt32LE(12)));
  const node=d.nodes.find(n=>n.extras?.buildingCode==='COL')??d.nodes.find(n=>n.mesh!==undefined);
  const names=d.meshes[node.mesh].primitives.map(p=>d.materials[p.material].name);
  for(const key of ['wood','recess','trim','stone','brass'])expect(names.some(n=>n.endsWith('COL_V67_'+key))).toBeTruthy();
 }
});
test('Columbia entrance opens with the live exterior model',async({page})=>{
 const errors=[];page.on('pageerror',e=>errors.push(e.message));await page.goto('/#COL');
 await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-COL',{timeout:60000});
 await expect(page.locator('#fallback')).toBeHidden();await page.locator('.detail-gallery img[src*="col-entrance"]').click();
 await expect(page.locator('#gallery-image')).toHaveAttribute('src',/col-entrance\.webp\?v=/);expect(errors).toEqual([]);
});
