import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';

test('5LF saved refinement preserves original architecture and other model references',async()=>{
 const audit=JSON.parse(await readFile('result/blender/stage91/five-rainwater-audit.json'));
 expect(audit.savedMeasurements.originalObjectsUnchanged).toBeTruthy();
 expect(audit.savedMeasurements.stackGeometryPreserved).toBeTruthy();
 expect(audit.savedMeasurements.pipes).toHaveLength(2);
 for(const p of audit.savedMeasurements.pipes){expect(p.closed).toBeTruthy();expect(p.heightSpan).toBeCloseTo(13.37,4);}
 const before=JSON.parse(await readFile('result/blender/stage91/catalogue-before.json'));
 const after=JSON.parse(await readFile('dist/models/catalogue.json'));
 for(const b of before.buildings){
  const current=after.buildings.find(c=>c.code===b.code);
  if(b.code!=='5LF')expect(current.detailedExterior?.url).toBe(b.detailedExterior?.url);
  expect(current.detailedInterior?.url).toBe(b.detailedInterior?.url);
  expect(current.interiorSpaces).toEqual(b.interiorSpaces);
 }
});

test('5LF overview and detailed facade separate dark chimneys from yellow main brick',async()=>{
 const catalogue=JSON.parse(await readFile('dist/models/catalogue.json'));
 const building=catalogue.buildings.find(b=>b.code==='5LF');
 for(const url of ['/models/campus.glb',building.detailedExterior.url]){
  const bytes=await readFile('dist'+url);
  const doc=JSON.parse(bytes.subarray(20,20+bytes.readUInt32LE(12)));
  const node=doc.nodes.find(n=>n.extras?.buildingCode==='5LF')??doc.nodes.find(n=>n.mesh!==undefined);
  const mats=doc.meshes[node.mesh].primitives.map(p=>doc.materials[p.material]);
  const main=mats.find(m=>m.name.replace(/^WEB_(?:DETAIL_)?/,'')==='5LF_brick'),stack=mats.find(m=>m.name.replace(/^WEB_(?:DETAIL_)?/,'')==='5LF_V91_weathered_chimney_brick');
  expect(main).toBeTruthy();expect(stack).toBeTruthy();
  expect(stack.extras.surfaceDetail.kind).toBe('brick');
  expect(stack.pbrMetallicRoughness.baseColorFactor[0]).toBeLessThan(main.pbrMetallicRoughness.baseColorFactor[0]);
  expect(mats.some(m=>m.name.replace(/^WEB_(?:DETAIL_)?/,'')==='5LF_V91_black_rainwater_metal')).toBeTruthy();
 }
});
