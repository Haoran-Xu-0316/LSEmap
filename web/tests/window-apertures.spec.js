import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';

test('window openings affect only three exteriors and preserve unrelated interior assets',async()=>{
 const before=JSON.parse(await readFile('web/tests/fixtures/edition33-models.json','utf8'));
 const after=JSON.parse(await readFile('dist/models/catalogue.json','utf8'));
 expect(after.version).toBe('43');
 for(const building of after.buildings){
  // Edition36 deliberately corrects LRB G furniture; its room samples remain protected.
  if(building.code==='LRB')expect(building.detailedInterior.sha256).not.toBe(before[building.code].detailedInterior.sha256);
  for(const key of (building.code==='LRB'?['interiorSpaces']:['detailedInterior','interiorSpaces']))expect(building[key]??null,`${building.code}:${key}`).toEqual(before[building.code][key]??null);
  if(['CKK','LRB','CON'].includes(building.code))expect(building.detailedExterior.sha256).not.toBe(before[building.code].detailedExterior.sha256);
  else if(building.code==='CLM') expect(building.detailedExterior.sha256).not.toBe(before[building.code].detailedExterior.sha256);
  else expect(building.detailedExterior??null,building.code).toEqual(before[building.code].detailedExterior??null);
 }
});
