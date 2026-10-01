import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';

test('51L roof revision retains all source objects and other model references',async()=>{
 const audit=JSON.parse(await readFile('result/blender/stage93/lincolns-roof-audit.json'));
 expect(audit.savedMeasurements.originalObjectsUnchanged).toBeTruthy();
 expect(audit.savedMeasurements.closedNewMeshes).toBeTruthy();
 expect(audit.savedMeasurements.clearWindowSightlines).toBeTruthy();
 expect(audit.savedMeasurements.dormerWindows).toHaveLength(3);
 expect(audit.dormers.map(d=>d.pediment)).toEqual(['segmental','triangular','triangular']);
 const before=JSON.parse(await readFile('result/blender/stage93/catalogue-before.json'));
 const after=JSON.parse(await readFile('dist/models/catalogue.json'));
 for(const b of before.buildings){
  const current=after.buildings.find(c=>c.code===b.code);
  if(b.code!=='51L')expect(current.detailedExterior?.url).toBe(b.detailedExterior?.url);
  expect(current.detailedInterior?.url).toBe(b.detailedInterior?.url);
  expect(current.interiorSpaces).toEqual(b.interiorSpaces);
 }
 const old=before.buildings.find(b=>b.code==='51L'),current=after.buildings.find(b=>b.code==='51L');
 expect(current.detailedExterior.url).not.toBe(old.detailedExterior.url);
 expect(current.bounds.max[1]).toBeGreaterThan(old.bounds.max[1]+1);
});

test('51L overview and detail contain roof materials and current gallery loads',async({page})=>{
 const c=JSON.parse(await readFile('dist/models/catalogue.json'));
 const building=c.buildings.find(b=>b.code==='51L');
 for(const url of ['/models/campus.glb',building.detailedExterior.url]){
  const bytes=await readFile('dist'+url);
  const doc=JSON.parse(bytes.subarray(20,20+bytes.readUInt32LE(12)));
  const node=doc.nodes.find(n=>n.extras?.buildingCode==='51L')??doc.nodes.find(n=>n.mesh!==undefined);
  const names=doc.meshes[node.mesh].primitives.map(p=>doc.materials[p.material].name.replace(/^WEB_(?:DETAIL_)?/,''));
  for(const name of ['51L_V93_slate','51L_V93_stone','51L_V93_frame','51L_V93_recess','51L_V93_metal'])expect(names).toContain(name);
 }
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('/#51L');
 await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-51L',{timeout:60000});
 await expect(page.locator('#fallback')).toBeHidden();
 await page.locator('.detail-gallery img[src*="51l-exterior"]').click();
 await expect(page.locator('#gallery-image')).toBeVisible();
 expect(await page.locator('#gallery-image').evaluate(i=>i.complete&&i.naturalWidth>0)).toBeTruthy();
 expect(errors).toEqual([]);
});
