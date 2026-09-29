import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';

test('CKK roof and frontage and window openings change only affected exteriors and keeps unrelated interior assets',async()=>{
 const before=JSON.parse(await readFile('web/tests/fixtures/edition31-models.json','utf8'));
 const after=JSON.parse(await readFile('dist/models/catalogue.json','utf8'));
 expect(after.version).toBe('43');
 for(const b of after.buildings){
  // Edition36 deliberately corrects LRB G furniture; its room samples remain protected.
  if(b.code==='LRB')expect(b.detailedInterior.sha256).not.toBe(before[b.code].detailedInterior.sha256);
  for(const key of (b.code==='LRB'?['interiorSpaces']:['detailedInterior','interiorSpaces']))expect(b[key]??null,`${b.code}:${key}`).toEqual(before[b.code][key]??null);
  if(b.code==='CKK'){
   expect(b.detailedExterior.sha256).not.toBe(before[b.code].detailedExterior.sha256);
   expect(b.detailedExterior.bounds.max[1]).toBeGreaterThan(32);
  }else if(['LRB','CON'].includes(b.code))expect(b.detailedExterior.sha256).not.toBe(before[b.code].detailedExterior.sha256);
  else if(b.code==='CLM') expect(b.detailedExterior.sha256).not.toBe(before[b.code].detailedExterior.sha256);
  else expect(b.detailedExterior??null,b.code).toEqual(before[b.code].detailedExterior??null);
 }
});

test('CKK roof survives exterior interior and overview transitions',async({page})=>{
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('/#CKK');
 await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-CKK',{timeout:60000});
 await page.waitForLoadState('networkidle');
 await page.screenshot({path:'result/web/release34/CKK-exterior.png'});
 await page.locator('#interior-view').click();
 await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','interior-CKK',{timeout:60000});
 await page.locator('#overview').click();
 await expect(page.locator('canvas')).toHaveAttribute('data-campus-details',/CKK/);
 await page.locator('.building-row[data-code="CKK"]').click();
 await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-CKK');
 expect(errors).toEqual([]);
});
