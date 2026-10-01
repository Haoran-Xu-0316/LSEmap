import {test, expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';

test('Clare Market relief additions preserve every original object and other model reference', async () => {
 const audit=JSON.parse(await readFile('result/blender/stage89/old-clare-reliefs-audit.json'));
 expect(audit.savedMeasurements.originalObjectsUnchanged).toBeTruthy();
 expect(audit.savedMeasurements.interpretedPanels).toEqual([1,2,3,4,5]);
 expect(audit.savedMeasurements.unresolvedPanels).toEqual(['side']);
 expect(audit.savedMeasurements.closedPositiveVolumes.every(p=>p.volume>0)).toBeTruthy();
 expect(new Set(audit.panels.map(p=>JSON.stringify(p.outline))).size).toBe(5);
 expect(audit.frontageOrder).toEqual(['G','E','F','D','H']);
 const before=JSON.parse(await readFile('result/blender/stage89/catalogue-before.json'));
 const current=JSON.parse(await readFile('dist/models/catalogue.json'));
 for(const building of before.buildings){
  const after=current.buildings.find(b=>b.code===building.code);
  if(building.code!=='OLD')expect(after.detailedExterior?.url).toBe(building.detailedExterior?.url);
  expect(after.detailedInterior?.url).toBe(building.detailedInterior?.url);
  expect(after.interiorSpaces).toEqual(building.interiorSpaces);
 }
 const old=current.buildings.find(b=>b.code==='OLD');
 for(const url of ['/models/campus.glb',old.detailedExterior.url]){
  const bytes=await readFile('dist'+url);
  const doc=JSON.parse(bytes.subarray(20,20+bytes.readUInt32LE(12)));
  const node=doc.nodes.find(n=>n.extras?.buildingCode==='OLD')??doc.nodes.find(n=>n.mesh!==undefined);
  const materials=doc.meshes[node.mesh].primitives.map(p=>doc.materials[p.material]);
  const previousUrl=url==='/models/campus.glb'?null:before.buildings.find(b=>b.code==='OLD').detailedExterior.url;
  const previousBytes=await readFile(previousUrl?'web/public'+previousUrl:'result/blender/stage89/campus-before.glb');
  const previousDoc=JSON.parse(previousBytes.subarray(20,20+previousBytes.readUInt32LE(12)));
  const previousNode=previousDoc.nodes.find(n=>n.extras?.buildingCode==='OLD')??previousDoc.nodes.find(n=>n.mesh!==undefined);
  const count=(model,mesh)=>mesh.primitives.reduce((total,p)=>total+model.accessors[p.attributes.POSITION].count,0);
  expect(count(doc,doc.meshes[node.mesh])).toBeGreaterThan(count(previousDoc,previousDoc.meshes[previousNode.mesh]));
  expect(materials.some(m=>m.name.includes('OLD_V86_limestone_OLD_V53_edge'))).toBeTruthy();
  expect(materials.some(m=>m.name.includes('OLD_V87_Clare_four_column_blue'))).toBeTruthy();
 }
});

test('OLD Clare Market gallery and exterior load successfully',async({page})=>{
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('/#OLD');
 await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-OLD',{timeout:60000});
 await expect(page.locator('#fallback')).toBeHidden();
 await page.locator('.detail-gallery img[src*="old-clare-market"]').click();
 await expect(page.locator('#gallery-image')).toBeVisible();
 expect(await page.locator('#gallery-image').evaluate(i=>i.complete&&i.naturalWidth>0)).toBeTruthy();
 expect(errors).toEqual([]);
});
