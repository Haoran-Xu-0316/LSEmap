import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';

test('POR photo-guided masonry preserves all other objects and uses two visible stacks',async()=>{
 const audit=JSON.parse(await readFile('result/blender/stage51/por-audit.json'));
 expect(audit.changedOtherObjects).toEqual([]);
 expect(audit.metricWallUVObjects.length).toBeGreaterThan(4);
 expect(audit.hiddenStackArchives.length).toBeGreaterThan(0);
 expect(audit.visibleStackCount).toBe(2);expect(audit.openFlueCount).toBe(2);
 expect(audit.sourceDate).toBeNull();
 expect(audit.bookshopName).toBe('The Gilded Acorn');
 expect(audit.updatedSigns.length).toBeGreaterThan(1);
 expect(audit.redFieldFaces).toBeGreaterThan(100);
 expect(audit.palette.frame[0]-audit.palette.frame[2]).toBeLessThan(.1);
});

test('POR overview and detailed model contain current roof stacks and material palette',async()=>{
 const catalogue=JSON.parse(await readFile('dist/models/catalogue.json'));
 const por=catalogue.buildings.find(b=>b.code==='POR');
 expect(por.interior).toBeFalsy();
 expect(por.facadeScope).toContain('Undated image');
 for(const url of ['/models/campus.glb',por.detailedExterior.url]){
  const bytes=await readFile('dist'+url);
  const doc=JSON.parse(bytes.subarray(20,20+bytes.readUInt32LE(12)).toString());
  const node=doc.nodes.find(n=>n.extras?.buildingCode==='POR')??doc.nodes.find(n=>n.mesh!==undefined);
  const materials=doc.meshes[node.mesh].primitives.map(p=>doc.materials[p.material]);
  for(const key of ['brick','redbrick','weathered_red','cream','frame','roof_metal'])expect(materials.some(m=>m.name.includes('POR_V51_'+key))).toBeTruthy();
  if(url!== '/models/campus.glb'){
   const brick=materials.find(m=>m.name.endsWith('POR_V51_brick'));
   expect(brick.extras.surfaceDetail.kind).toBe('brick');
   expect(brick.extras.surfaceDetail.brickWidth).toBeCloseTo(.225,3);
   for(const primitive of doc.meshes[node.mesh].primitives.filter(p=>/POR_V51_(brick|redbrick)$/.test(doc.materials[p.material].name)))expect(primitive.attributes.TEXCOORD_0).toBeDefined();
  }
 }
});

test('POR roof gallery loads the same current model without errors',async({page})=>{
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('/#POR');
 await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-POR',{timeout:60000});
 const image=page.locator('.detail-gallery img[src*="por-roof"]');
 await expect(image).toHaveAttribute('src',/v=51-/);await image.click();
 await expect(page.locator('#gallery-image')).toHaveAttribute('src',/por-roof/);
 expect(errors).toEqual([]);
});
