import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';

test('Connaught base revision and subsequent library revision preserve other exteriors and unrelated interiors',async()=>{
 const before=JSON.parse(await readFile('web/tests/fixtures/edition29-models.json','utf8'));
 const after=JSON.parse(await readFile('dist/models/catalogue.json','utf8'));
 for(const b of after.buildings){
  for(const key of (b.code==='LRB'?['interiorSpaces']:['detailedInterior','interiorSpaces']))expect(b[key]??null,`${b.code}:${key}`).toEqual(before[b.code][key]);
  if(['CON','LRB','CKK'].includes(b.code))expect(b.detailedExterior.sha256).not.toBe(before[b.code].detailedExterior.sha256);
  else if(b.code==='CLM') expect(b.detailedExterior.sha256).not.toBe(before[b.code].detailedExterior.sha256);
  else expect(b.detailedExterior??null,b.code).toEqual(before[b.code].detailedExterior);
 }
});

test('Connaught entrance presents the revised base on desktop and phone',async({page})=>{
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('/#CON');
 await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-CON',{timeout:60000});
 await page.locator('#detail-view').click();
 await page.waitForLoadState('networkidle');await page.waitForTimeout(1000);
 await page.screenshot({path:'result/web/release30/CON-entrance-desktop.png'});
 await page.setViewportSize({width:390,height:844});
 await page.locator('#detail-view').click();
 await expect(page.locator('#detail-view')).toHaveAttribute('aria-pressed','true');
 await page.waitForTimeout(1000);
 await page.screenshot({path:'result/web/release30/CON-entrance-phone.png'});
 expect(errors).toEqual([]);
});
