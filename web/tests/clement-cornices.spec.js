import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';

test('curved Clement cornices preserve all other exteriors and every interior',async()=>{
 const before=JSON.parse(await readFile('web/tests/fixtures/edition39-models.json','utf8'));
 const catalogue=JSON.parse(await readFile('dist/models/catalogue.json','utf8'));
 expect(catalogue.version).toBe('43');
 for(const building of catalogue.buildings){
  for(const key of ['detailedInterior','interiorSpaces'])
   expect(building[key]??null,`${building.code}:${key}`).toEqual(before[building.code][key]);
  if(building.code==='CLM'){
   expect(building.detailedExterior.sha256).not.toBe(before.CLM.detailedExterior.sha256);
   expect(building.detailedExterior.triangles).toBeGreaterThan(before.CLM.detailedExterior.triangles);
  }else if(['COL','CON','LCH'].includes(building.code))expect(building.detailedExterior.sha256).not.toBe(before[building.code].detailedExterior.sha256);
  else expect(building.detailedExterior??null,building.code).toEqual(before[building.code].detailedExterior);
 }
});
