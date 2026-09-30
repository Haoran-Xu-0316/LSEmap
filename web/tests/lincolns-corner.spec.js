import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';

test('51L replaces obsolete corner members while preserving other buildings',async()=>{
 const audit=JSON.parse(await readFile('result/blender/stage57/lincolns-corner-audit.json'));
 expect(audit.changedOtherObjects).toEqual([]);expect(audit.hiddenPreviousObjects).toHaveLength(4);
 expect(audit.hiddenPreviousObjects.some(name=>name.includes('segmental_pediment'))).toBeTruthy();
 expect(audit.labelBasisDeterminant).toBeCloseTo(1);
 expect(audit.windowColumns).toBe(3);expect(audit.windowRows).toBe(3);
 expect(Math.max(...audit.pedimentSamples.map(p=>p[1]))).toBeCloseTo(3.72);
 for(const [name,count]of Object.entries(audit.removedOldFaces))if(name.includes('corner_quoins'))expect(count%6).toBe(0);
});

test('51L overview and detail contain the revised stone, window and entrance materials',async()=>{
 const catalogue=JSON.parse(await readFile('dist/models/catalogue.json'));const building=catalogue.buildings.find(b=>b.code==='51L');
 for(const url of ['/models/campus.glb',building.detailedExterior.url]){
  const bytes=await readFile('dist'+url);const doc=JSON.parse(bytes.subarray(20,20+bytes.readUInt32LE(12)));
  const node=doc.nodes.find(n=>n.extras?.buildingCode==='51L')??doc.nodes.find(n=>n.mesh!==undefined);
  const names=doc.meshes[node.mesh].primitives.map(p=>doc.materials[p.material].name);
  for(const key of ['stone','frame','dark'])expect(names.some(name=>name.endsWith('51L_V57_'+key))).toBeTruthy();
 }
});

test('51L exterior and full corner gallery load without browser errors',async({page})=>{
 const errors=[];page.on('pageerror',e=>errors.push(e.message));await page.goto('/#51L');
 await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-51L',{timeout:60000});
 await expect(page.locator('#fallback')).toBeHidden();await page.locator('.detail-gallery img[src*="51l-entrance"]').click();
 await expect(page.locator('#gallery-image')).toHaveAttribute('src',/51l-entrance\.webp\?v=/);expect(errors).toEqual([]);
});
