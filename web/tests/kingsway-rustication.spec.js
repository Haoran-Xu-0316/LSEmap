import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';

test('KSW lower block revision preserves source objects and other detailed references',async()=>{
 const audit=JSON.parse(await readFile('result/blender/stage90/kingsway-rustication-audit.json'));
 expect(audit.savedMeasurements.originalObjectsUnchanged).toBeTruthy();
 expect(audit.savedMeasurements.retainedVerticesOutsideJoints).toBeTruthy();
 expect(audit.savedMeasurements.copies).toHaveLength(4);
 expect(audit.savedMeasurements.visibleGrooves).toHaveLength(7);
 for(const groove of audit.savedMeasurements.visibleGrooves)expect(groove.depth).toBeCloseTo(.055,4);
 const before=JSON.parse(await readFile('result/blender/stage90/catalogue-before.json'));
 const after=JSON.parse(await readFile('dist/models/catalogue.json'));
 for(const b of before.buildings){
  const current=after.buildings.find(c=>c.code===b.code);
  if(b.code!=='KSW')expect(current.detailedExterior?.url).toBe(b.detailedExterior?.url);
  expect(current.detailedInterior?.url).toBe(b.detailedInterior?.url);
  expect(current.interiorSpaces).toEqual(b.interiorSpaces);
 }
});

test('overview and KSW detail use block finish beside retained fine brick and glass',async()=>{
 const catalogue=JSON.parse(await readFile('dist/models/catalogue.json'));
 const ksw=catalogue.buildings.find(b=>b.code==='KSW');
 for(const url of ['/models/campus.glb',ksw.detailedExterior.url]){
  const bytes=await readFile('dist'+url);
  const doc=JSON.parse(bytes.subarray(20,20+bytes.readUInt32LE(12)));
  const node=doc.nodes.find(n=>n.extras?.buildingCode==='KSW')??doc.nodes.find(n=>n.mesh!==undefined);
  const mats=doc.meshes[node.mesh].primitives.map(p=>doc.materials[p.material]);
  const red=mats.find(m=>m.name.includes('KSW_V90_red_block_face'));
  expect(red).toBeTruthy();
  expect(red.extras.surfaceDetail.kind).toBe('noise');
  expect(mats.some(m=>m.name.includes('KSW_V90_recessed_red_joint'))).toBeTruthy();
  expect(mats.some(m=>m.name.includes('KSW_D3_brick')&&m.extras?.surfaceDetail?.kind==='brick')).toBeTruthy();
  expect(mats.some(m=>m.name.includes('KSW_D3_recessed_glass'))).toBeTruthy();
 }
});

test('KSW exterior and current facade gallery load without fallback',async({page})=>{
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('/#KSW');
 await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-KSW',{timeout:60000});
 await expect(page.locator('#fallback')).toBeHidden();
 await page.locator('.detail-gallery img[src*="ksw-exterior"]').click();
 await expect(page.locator('#gallery-image')).toBeVisible();
 expect(await page.locator('#gallery-image').evaluate(i=>i.complete&&i.naturalWidth>0)).toBeTruthy();
 expect(errors).toEqual([]);
});
