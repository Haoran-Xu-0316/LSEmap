import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';
const catalogue=JSON.parse(await readFile('web/public/models/catalogue.json','utf8'));
const previous=JSON.parse(await readFile('web/tests/fixtures/edition23-models.json','utf8'));
test('Denning addition preserves every edition 23 model',()=>{
 expect(catalogue.version).toBe('24');
 for(const old of previous.buildings){
  const current=catalogue.buildings.find(b=>b.code===old.code);
  for(const key of ['detailedExterior','detailedInterior'])if(old[key])expect(current[key].sha256).toBe(old[key].sha256);
  for(const room of old.interiorSpaces||[])expect(current.interiorSpaces.find(s=>s.id===room.id).detailedInterior.sha256).toBe(room.detailedInterior.sha256);
 }
 const saw=catalogue.buildings.find(b=>b.code==='SAW');expect(saw.interiorSpaces).toHaveLength(1);expect(saw.interiorSpaces[0].scope).toContain('2014');
});
for(const width of [1440,390])test(`Denning corner, public stairs and gallery at ${width}px`,async({page})=>{
 const errors=[];page.on('pageerror',e=>errors.push(e.message));await page.setViewportSize({width,height:width===390?844:1000});
 await page.goto('/#SAW');await expect(page.locator('#interior-view')).toBeEnabled({timeout:60000});await page.locator('#interior-view').click();await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','interior-SAW',{timeout:60000});
 await expect(page.locator('#interior-space option').first()).toHaveText('公共楼梯');await page.locator('#interior-space').selectOption('saw-denning');
 await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','interior-SAW:saw-denning',{timeout:60000});await expect(page.locator('#interior-space-scope')).toContainText('2014');
 await page.waitForTimeout(1100);await page.screenshot({path:`result/web/denning-room/saw-denning-${width}.png`});
 await page.locator('#interior-space').selectOption('default');await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','interior-SAW');
 await page.locator('#exterior-view').click();await expect(page.locator('#interior-spaces')).toBeHidden();await expect(page.locator('canvas')).not.toHaveAttribute('data-interior-space',/.+/);
 await page.locator('.detail-gallery button').last().click();await expect(page.locator('#gallery-image')).toHaveAttribute('src',/saw-denning-interior\.webp\?v=24-/);await expect.poll(()=>page.locator('#gallery-image').evaluate(i=>i.complete&&i.naturalWidth>=1000)).toBe(true);
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);expect(errors).toEqual([]);
});
