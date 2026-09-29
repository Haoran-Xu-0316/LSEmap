import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';

test('library and CKK roof revisions preserve unrelated assets',async()=>{
 const before=JSON.parse(await readFile('web/tests/fixtures/edition30-models.json','utf8'));
 const after=JSON.parse(await readFile('dist/models/catalogue.json','utf8'));
 expect(Number(after.version)).toBeGreaterThanOrEqual(31);
 for(const b of after.buildings){
  for(const key of (b.code==='LRB'?['interiorSpaces']:['detailedInterior','interiorSpaces']))expect(b[key]??null,`${b.code}:${key}`).toEqual(before[b.code][key]??null);
  if(b.code==='LRB'){
   expect(b.detailedExterior.sha256).not.toBe(before[b.code].detailedExterior.sha256);
   expect(b.detailedInterior.sha256).not.toBe(before[b.code].detailedInterior.sha256);
   expect(b.detailedInterior.bounds.max[1]).toBeGreaterThan(31.9);
  }
  else if(['CKK','CON'].includes(b.code))expect(b.detailedExterior.sha256).not.toBe(before[b.code].detailedExterior.sha256);
  else if(b.code==='CLM') expect(b.detailedExterior.sha256).not.toBe(before[b.code].detailedExterior.sha256);
  else expect(b.detailedExterior??null,b.code).toEqual(before[b.code].detailedExterior??null);
 }
});

test('library detailed roof loads and remains available after returning to campus',async({page})=>{
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('/#LRB');
 await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-LRB',{timeout:60000});
 await page.waitForLoadState('networkidle');
 await page.screenshot({path:'result/web/release31/LRB-exterior.png'});
 await page.locator('#overview').click();
 await expect(page.locator('canvas')).toHaveAttribute('data-campus-details',/LRB/);
 await expect(page.locator('#view-mode')).toHaveText('校园全景');
 await page.locator('.building-row[data-code="LRB"]').first().click();
 await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-LRB');
 expect(errors).toEqual([]);
});
