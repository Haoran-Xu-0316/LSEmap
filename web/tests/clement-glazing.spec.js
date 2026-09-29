import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';

test('Clement glazing changes one exterior while every interior and room remains identical',async()=>{
 const before=JSON.parse(await readFile('web/tests/fixtures/edition38-models.json','utf8'));
 const catalogue=JSON.parse(await readFile('dist/models/catalogue.json','utf8'));
 expect(catalogue.version).toBe('43');
 for(const b of catalogue.buildings){
  for(const key of ['detailedInterior','interiorSpaces'])expect(b[key]??null,`${b.code}:${key}`).toEqual(before[b.code][key]);
  if(b.code==='CLM'){
   expect(b.detailedExterior.sha256).not.toBe(before.CLM.detailedExterior.sha256);
   expect(b.detailedExterior.bounds).toEqual(before.CLM.detailedExterior.bounds);
   expect(b.detailedExterior.triangles).toBeGreaterThan(before.CLM.detailedExterior.triangles);
  }else if(['COL','CON','LCH'].includes(b.code))expect(b.detailedExterior.sha256).not.toBe(before[b.code].detailedExterior.sha256);
  else expect(b.detailedExterior??null,b.code).toEqual(before[b.code].detailedExterior);
 }
 const asset=catalogue.buildings.find(b=>b.code==='CLM').detailedExterior;
 const bytes=await readFile('dist'+asset.url);
 const gltf=JSON.parse(bytes.subarray(20,20+bytes.readUInt32LE(12)).toString());
 const glass=gltf.materials.find(m=>m.name.includes('CLM_V39_neutral_recessed_glass'));
 expect(glass).toBeTruthy();
 const colour=glass.pbrMetallicRoughness.baseColorFactor;
 expect(colour[0]).toBeCloseTo(.075,4);
 expect(colour[1]).toBeCloseTo(.085,4);
 expect(colour[2]).toBeCloseTo(.088,4);
});
