import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';

test('OLD saved entrance refinement preserves other exteriors and interiors',async()=>{
 const audit=JSON.parse(await readFile('result/blender/stage97/old-portal-depth-audit.json'));
 expect(audit.savedMeasurements.originalObjectsUnchanged).toBeTruthy();
 expect(audit.savedMeasurements.unchangedFrontageAndHeight).toBeTruthy();
 expect(audit.savedMeasurements.mountedSignsVerified).toBeTruthy();
 expect(audit.savedMeasurements.independentDoorGlassMaterial).toBeTruthy();
 const before=JSON.parse(await readFile('result/blender/stage97/catalogue-before.json'));
 const after=JSON.parse(await readFile('dist/models/catalogue.json'));
 expect(after.version).toBe('97');
 for(const building of before.buildings){
  const current=after.buildings.find(b=>b.code===building.code);
  if(building.code!=='OLD')expect(current.detailedExterior?.url).toBe(building.detailedExterior?.url);
  expect(current.detailedInterior?.url).toBe(building.detailedInterior?.url);
  expect(current.interiorSpaces).toEqual(building.interiorSpaces);
 }
 expect(after.buildings.find(b=>b.code==='OLD').detailedExterior.url).not.toBe(before.buildings.find(b=>b.code==='OLD').detailedExterior.url);
});

test('OLD overview and detailed door panes share reflective transparency',async()=>{
 const c=JSON.parse(await readFile('dist/models/catalogue.json'));
 const old=c.buildings.find(b=>b.code==='OLD');
 for(const url of ['/models/campus.glb',old.detailedExterior.url]){
  const bytes=await readFile('dist'+url);
  const doc=JSON.parse(bytes.subarray(20,20+bytes.readUInt32LE(12)));
  const material=doc.materials.find(m=>m.name.replace(/^WEB_(?:DETAIL_)?/,'')==='OLD_V97_entry_glass');
  expect(material).toBeTruthy();
  expect(material.alphaMode).toBe('BLEND');
  expect(material.pbrMetallicRoughness.baseColorFactor[3]).toBeCloseTo(.46,5);
  expect(material.pbrMetallicRoughness.roughnessFactor).toBeCloseTo(.17,5);
 }
});
