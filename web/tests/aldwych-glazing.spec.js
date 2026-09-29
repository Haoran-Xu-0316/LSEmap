import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';

test('COL and CON glass colours change without altering geometry or any interior',async()=>{
 const before=JSON.parse(await readFile('web/tests/fixtures/edition40-models.json','utf8'));
 const catalogue=JSON.parse(await readFile('dist/models/catalogue.json','utf8'));
 expect(catalogue.version).toBe('43');
 for(const b of catalogue.buildings){
  for(const key of ['detailedInterior','interiorSpaces'])expect(b[key]??null,`${b.code}:${key}`).toEqual(before[b.code][key]);
  if(['COL','CON'].includes(b.code)){
   expect(b.detailedExterior.sha256).not.toBe(before[b.code].detailedExterior.sha256);
   expect(b.detailedExterior.bounds).toEqual(before[b.code].detailedExterior.bounds);
   expect(b.detailedExterior.triangles).toBe(before[b.code].detailedExterior.triangles);
   const bytes=await readFile('dist'+b.detailedExterior.url);
   const gltf=JSON.parse(bytes.subarray(20,20+bytes.readUInt32LE(12)).toString());
   const glass=gltf.materials.filter(m=>m.name.includes(`${b.code}_V41_neutral_glass`));
   expect(glass.length).toBe(b.code==='CON'?2:1);
   for(const material of glass){
    const colour=material.pbrMetallicRoughness.baseColorFactor;
    [.10,.115,.12,1].forEach((value,index)=>expect(colour[index]).toBeCloseTo(value,4));
   }
  }else if(b.code==='LCH')expect(b.detailedExterior.sha256).not.toBe(before.LCH.detailedExterior.sha256);
  else expect(b.detailedExterior??null,b.code).toEqual(before[b.code].detailedExterior);
 }
});
