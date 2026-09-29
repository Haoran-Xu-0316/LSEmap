import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';
test('LCH lower lights replace the opaque riser and preserve other released models',async()=>{
 const before=JSON.parse(await readFile('web/tests/fixtures/edition42-models.json','utf8'));
 const catalogue=JSON.parse(await readFile('dist/models/catalogue.json','utf8'));
 for(const b of catalogue.buildings){
  for(const key of ['detailedInterior','interiorSpaces'])expect(b[key]??null,`${b.code}:${key}`).toEqual(before[b.code][key]);
  if(b.code!=='LCH')expect(b.detailedExterior??null,b.code).toEqual(before[b.code].detailedExterior);
 }
 const b=catalogue.buildings.find(b=>b.code==='LCH');
 expect(b.detailedExterior.sha256).not.toBe(before.LCH.detailedExterior.sha256);
 const bytes=await readFile('dist'+b.detailedExterior.url);
 const gltf=JSON.parse(bytes.subarray(20,20+bytes.readUInt32LE(12)).toString());
 // Production export joins mesh nodes; the new grille material must remain assigned.
 const grille=gltf.materials.findIndex(m=>m.name.includes('LCH_V43_basement_metal'));
 expect(grille).toBeGreaterThanOrEqual(0);
 expect(gltf.meshes.flatMap(m=>m.primitives).some(p=>p.material===grille)).toBe(true);
});
