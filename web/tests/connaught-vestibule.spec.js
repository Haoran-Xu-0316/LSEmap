import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';
test('saved Connaught street portal opens into a recessed passage',async()=>{
 const a=JSON.parse(await readFile('result/blender/stage68/connaught-vestibule-audit.json'));
 expect(a.changedOtherObjects).toEqual([]);expect(a.changedExistingObjects).toEqual(['CON_D4_bronze_fanlight']);
 expect(a.savedMeasurements.streetDoorRemoved).toBeTruthy();expect(a.savedMeasurements.clearHallWidth).toBeCloseTo(1.95,4);
 for(const d of a.savedMeasurements.doorPanelDepths)expect(d).toBeCloseTo(-2.78,4);
});
test('Connaught overview and close model share the warm vestibule and translucent inner glazing',async()=>{
 const c=JSON.parse(await readFile('dist/models/catalogue.json'));const b=c.buildings.find(b=>b.code==='CON');
 for(const path of ['/models/campus.glb',b.detailedExterior.url]){
  const bytes=await readFile('dist'+path);const d=JSON.parse(bytes.subarray(20,20+bytes.readUInt32LE(12)));
  const node=d.nodes.find(n=>n.extras?.buildingCode==='CON')??d.nodes.find(n=>n.mesh!==undefined);
  const materialIds=d.meshes[node.mesh].primitives.map(p=>p.material);
  for(const key of ['granite','stone','wall','floor','bronze','light','glass'])expect(materialIds.some(i=>d.materials[i].name.endsWith('CON_V68_'+key))).toBeTruthy();
  const glass=d.materials.find(m=>m.name.endsWith('CON_V68_glass'));
  expect(glass.pbrMetallicRoughness.baseColorFactor[3]).toBeCloseTo(.18,3);
  expect(glass.alphaMode).toBe('BLEND');
 }
});
test('Connaught entrance gallery opens with the live exterior',async({page})=>{
 const errors=[];page.on('pageerror',e=>errors.push(e.message));await page.goto('/#CON');
 await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-CON',{timeout:60000});
 await expect(page.locator('#fallback')).toBeHidden();await page.locator('.detail-gallery img[src*="con-entrance"]').click();
 await expect(page.locator('#gallery-image')).toHaveAttribute('src',/con-entrance\.webp\?v=/);expect(errors).toEqual([]);
});
