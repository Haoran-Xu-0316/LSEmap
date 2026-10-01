import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';
test('saved CKK pavilion retains the other buildings, atrium and room assets',async()=>{
 const a=JSON.parse(await readFile('result/blender/stage80/ckk-roof-pavilion-audit.json'));
 expect(a.savedMeasurements.glazingPanels).toBe(18);
 expect(a.savedMeasurements.sunshadeLouvres).toBe(14);
 expect(a.savedMeasurements.loggiaPosts).toBe(5);
 expect(a.savedMeasurements.diagonalBraces).toBe(4);
 expect(a.savedMeasurements.originalGeometryUnchanged).toBeTruthy();
 expect(a.savedMeasurements.otherBuildingsAndInteriorsUnchanged).toBeTruthy();
 const before=JSON.parse(await readFile('result/blender/stage80/catalogue-before.json'));
 const after=JSON.parse(await readFile('dist/models/catalogue.json'));
 for(const old of before.buildings){
  const current=after.buildings.find(b=>b.code===old.code);
  if(old.code!=='CKK')expect(current.detailedExterior?.url).toBe(old.detailedExterior?.url);
  expect(current.detailedInterior?.url).toBe(old.detailedInterior?.url);
  expect(current.interiorSpaces).toEqual(old.interiorSpaces);
 }
});
test('overview and detail both expose pavilion materials and translucent glazing',async()=>{
 const c=JSON.parse(await readFile('dist/models/catalogue.json'));
 for(const url of ['/models/campus.glb',c.buildings.find(b=>b.code==='CKK').detailedExterior.url]){
  const bytes=await readFile('dist'+url);
  const doc=JSON.parse(bytes.subarray(20,20+bytes.readUInt32LE(12)));
  const node=doc.nodes.find(n=>n.extras?.buildingCode==='CKK')??doc.nodes.find(n=>n.mesh!==undefined);
  const materials=doc.meshes[node.mesh].primitives.map(p=>doc.materials[p.material]);
  for(const key of ['frame','steel','roof','paving','glass'])
   expect(materials.some(m=>m.name.endsWith('CKK_V80_'+key)),key).toBeTruthy();
  const glass=materials.find(m=>m.name.endsWith('CKK_V80_glass'));
  expect(glass.alphaMode).toBe('BLEND');
  expect(glass.pbrMetallicRoughness.baseColorFactor[3]).toBeCloseTo(.55);
 }
});
test('CKK roof gallery and 3D exterior load without errors',async({page})=>{
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('/#CKK');
 await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-CKK',{timeout:60000});
 await expect(page.locator('#fallback')).toBeHidden();
 await page.locator('.detail-gallery img[src*="ckk-roof-pavilion"]').click();
 await expect(page.locator('#gallery-image')).toBeVisible();
 expect(await page.locator('#gallery-image').evaluate(i=>i.complete&&i.naturalWidth>0)).toBeTruthy();
 expect(errors).toEqual([]);
});
