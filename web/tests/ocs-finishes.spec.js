import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';
test('saved OCS finishes retain geometry and all other building assets',async()=>{
 const a=JSON.parse(await readFile('result/blender/stage81/ocs-finish-audit.json'));
 expect(a.savedMeasurements.geometryUnchanged).toBeTruthy();
 expect(a.savedMeasurements.otherBuildingsAndInteriorsUnchanged).toBeTruthy();
 expect(a.savedMeasurements.upperFaces).toBeGreaterThan(0);
 const before=JSON.parse(await readFile('result/blender/stage81/catalogue-before.json'));
 const after=JSON.parse(await readFile('dist/models/catalogue.json'));
 for(const b of before.buildings){
  const current=after.buildings.find(c=>c.code===b.code);
  if(b.code!=='OCS')expect(current.detailedExterior?.url).toBe(b.detailedExterior?.url);
  expect(current.detailedInterior?.url).toBe(b.detailedInterior?.url);
  expect(current.interiorSpaces).toEqual(b.interiorSpaces);
 }
});
test('OCS overview and detail share the restored finish palette',async()=>{
 const a=JSON.parse(await readFile('result/blender/stage81/ocs-finish-audit.json'));
 const c=JSON.parse(await readFile('dist/models/catalogue.json'));
 for(const url of ['/models/campus.glb',c.buildings.find(b=>b.code==='OCS').detailedExterior.url]){
  const bytes=await readFile('dist'+url);
  const doc=JSON.parse(bytes.subarray(20,20+bytes.readUInt32LE(12)));
  const node=doc.nodes.find(n=>n.extras?.buildingCode==='OCS')??doc.nodes.find(n=>n.mesh!==undefined);
  const materials=doc.meshes[node.mesh].primitives.map(p=>doc.materials[p.material]);
  for(const [key,color]of Object.entries(a.palette)){
   const m=materials.find(m=>m.name.endsWith('OCS_V81_'+key));
   expect(m,key).toBeTruthy();
   color.forEach((v,i)=>expect(m.pbrMetallicRoughness.baseColorFactor[i]).toBeCloseTo(v,5));
  }
 }
});
test('restored OCS exterior and close gallery load without errors',async({page})=>{
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('/#OCS');
 await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-OCS',{timeout:60000});
 await expect(page.locator('#fallback')).toBeHidden();
 await page.locator('.detail-gallery img[src*="ocs-roof"]').click();
 await expect(page.locator('#gallery-image')).toBeVisible();
 expect(await page.locator('#gallery-image').evaluate(i=>i.complete&&i.naturalWidth>0)).toBeTruthy();
 expect(errors).toEqual([]);
});
