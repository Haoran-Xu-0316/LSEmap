import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';

test('library frontage leaves other exteriors and unrelated interiors unchanged',async()=>{
 const before=JSON.parse(await readFile('web/tests/fixtures/edition34-models.json','utf8'));
 const after=JSON.parse(await readFile('dist/models/catalogue.json','utf8'));
 expect(after.version).toBe('43');
 for(const b of after.buildings){
  // Edition36 deliberately corrects LRB G furniture; its room samples remain protected.
  if(b.code==='LRB')expect(b.detailedInterior.sha256).not.toBe(before[b.code].detailedInterior.sha256);
  for(const key of (b.code==='LRB'?['interiorSpaces']:['detailedInterior','interiorSpaces']))expect(b[key]??null,`${b.code}:${key}`).toEqual(before[b.code][key]??null);
  if(b.code==='LRB'){
   expect(b.detailedExterior.sha256).not.toBe(before[b.code].detailedExterior.sha256);
   expect(b.exteriorDirection[0]).toBeLessThan(0);
   expect(b.exteriorDirection[2]).toBeGreaterThan(0);
  }else if(b.code==='CLM') expect(b.detailedExterior.sha256).not.toBe(before[b.code].detailedExterior.sha256);
  else expect(b.detailedExterior??null,b.code).toEqual(before[b.code].detailedExterior??null);
 }
});

test('library revised frontage is available on desktop and phone',async({page})=>{
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('/#LRB');
 await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-LRB',{timeout:60000});
 await expect(page.locator('.detail-photo img')).toHaveAttribute('src',/lrb-exterior\.webp\?v=43-/);
 await page.waitForLoadState('networkidle');
 await page.screenshot({path:'result/web/release35/LRB-desktop.png'});
 await page.setViewportSize({width:390,height:844});
 await page.waitForTimeout(600);
 await page.screenshot({path:'result/web/release35/LRB-phone.png'});
 expect(errors).toEqual([]);
});
