import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';

test('PAN and FAW finish changes preserve other buildings and close facade gaps with isolated materials',async()=>{
 const audit=JSON.parse(await readFile('result/blender/stage58/pankhurst-finish-audit.json'));
 expect(audit.outsideGeometryAfter).toBe(audit.outsideGeometryBefore);
 expect(audit.closedHeadMeshes).toEqual(['PAN_D3_window_heads_and_sills','FAW_D3_window_heads_and_sills']);
 for(const code of ['PAN','FAW']){
  expect(audit.savedHeadMeasurements[code].count).toBeGreaterThan(0);
  expect(audit.savedHeadMeasurements[code].minimum/2).toBeGreaterThan(.05);
  expect(audit.savedHeadMeasurements[code].maximum).toBeCloseTo(.11,4);
 }
 expect(audit.changes).toHaveLength(10);
 for(const change of audit.changes){
  expect(change.owners.length).toBeGreaterThan(0);
  expect(change.owners.every(name=>/^(PAN|FAW)_D3_/.test(name))).toBeTruthy();
 }
});

test('PAN and FAW overview and details share warm aggregate, opaque glass and matte curtains',async()=>{
 const catalogue=JSON.parse(await readFile('dist/models/catalogue.json'));
 for(const code of ['PAN','FAW']){
  const b=catalogue.buildings.find(b=>b.code===code);
  for(const url of ['/models/campus.glb',b.detailedExterior.url]){
   const bytes=await readFile('dist'+url);const doc=JSON.parse(bytes.subarray(20,20+bytes.readUInt32LE(12)));
   const node=doc.nodes.find(n=>n.extras?.buildingCode===code)??doc.nodes.find(n=>n.mesh!==undefined);
   const materials=doc.meshes[node.mesh].primitives.map(p=>doc.materials[p.material]);
   const mat=key=>materials.find(m=>m.name.endsWith(code+key));
   const aggregate=mat('_D3_aggregate');const color=aggregate.pbrMetallicRoughness.baseColorFactor;
   expect(color[0]).toBeGreaterThan(color[1]);expect(color[1]).toBeGreaterThan(color[2]);
   expect(aggregate.extras.surfaceDetail.colorA[0]).toBeCloseTo(.4);
   expect(mat('_D3_glass').pbrMetallicRoughness.baseColorFactor[3]).toBeCloseTo(.76);
   expect(mat('_D3_clear_glass').pbrMetallicRoughness.baseColorFactor[3]).toBeCloseTo(.56);
   expect(mat('_V58_curtain').pbrMetallicRoughness.metallicFactor).toBe(0);
   expect(mat('_V58_curtain').pbrMetallicRoughness.roughnessFactor).toBeCloseTo(.94);
  }
 }
});

test('PAN exterior and shared entrance gallery load without fallback or errors',async({page})=>{
 const errors=[];page.on('pageerror',e=>errors.push(e.message));await page.goto('/#PAN');
 await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-PAN',{timeout:60000});
 await expect(page.locator('#fallback')).toBeHidden();await page.locator('.detail-gallery img[src*="pan-faw-entrance"]').click();
 await expect(page.locator('#gallery-image')).toHaveAttribute('src',/pan-faw-entrance\.webp\?v=/);expect(errors).toEqual([]);
});
