import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';

test('slate and brick UV repairs preserve unrelated exteriors and unrelated interiors',async()=>{
 const before=JSON.parse(await readFile('web/tests/fixtures/edition27-models.json','utf8'));
 const after=JSON.parse(await readFile('dist/models/catalogue.json','utf8'));
 for(const b of after.buildings){
  for(const key of (b.code==='LRB'?['interiorSpaces']:['detailedInterior','interiorSpaces'])) expect(b[key]??null,`${b.code}:${key}`).toEqual(before[b.code][key]);
  if(['OLD','SAL','KSW', 'CON', 'LRB', 'CKK'].includes(b.code))expect(b.detailedExterior.sha256).not.toBe(before[b.code].detailedExterior.sha256);
  else if(b.code==='CLM') expect(b.detailedExterior.sha256).not.toBe(before[b.code].detailedExterior.sha256);
  else expect(b.detailedExterior??null,b.code).toEqual(before[b.code].detailedExterior);
 }
});
