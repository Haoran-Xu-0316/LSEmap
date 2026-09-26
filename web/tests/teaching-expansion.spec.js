import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';
const catalogue=JSON.parse(await readFile('web/public/models/catalogue.json','utf8'));
const previous=JSON.parse(await readFile('web/tests/fixtures/edition22-models.json','utf8'));
test('new CBG and CKK classrooms preserve all edition 22 model assets',()=>{
 expect(catalogue.version).toBe('24');
 expect(catalogue.buildings.flatMap(b=>b.interiorSpaces||[])).toHaveLength(4);
 for(const old of previous.buildings){
  const current=catalogue.buildings.find(b=>b.code===old.code);
  for(const key of ['detailedExterior','detailedInterior'])if(old[key])expect(current[key].sha256).toBe(old[key].sha256);
  for(const space of old.interiorSpaces||[])expect(current.interiorSpaces.find(s=>s.id===space.id).detailedInterior.sha256).toBe(space.detailedInterior.sha256);
 }
});
for(const [code,id,seats] of [['CBG','cbg-102','42'],['CKK','ckk-104','80']])for(const width of [1440,390])test(`${code} classroom and atrium remain distinct at ${width}px`,async({page})=>{
 const errors=[];page.on('pageerror',e=>errors.push(e.message));await page.setViewportSize({width,height:width===390?844:1000});
 await page.goto('/#'+code);await expect(page.locator('#interior-view')).toBeEnabled({timeout:60000});await page.locator('#interior-view').click();
 await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','interior-'+code,{timeout:60000});
 await expect(page.locator('#interior-space option').first()).toHaveText('公共中庭与楼梯');
 await page.locator('#interior-space').selectOption(id);await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready',`interior-${code}:${id}`,{timeout:60000});
 await expect(page.locator('#interior-space-scope')).toContainText(seats);await page.waitForTimeout(1100);await page.screenshot({path:`result/web/teaching-expansion/${id}-${width}.png`});
 await page.locator('#interior-space').selectOption('default');await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','interior-'+code);
 await page.locator('#exterior-view').click();await expect(page.locator('#interior-spaces')).toBeHidden();await expect(page.locator('canvas')).not.toHaveAttribute('data-interior-space',/.+/);
 await page.locator('.detail-gallery button').last().click();await expect(page.locator('#gallery-image')).toHaveAttribute('src',new RegExp(id+'-interior\\.webp\\?v=24-'));await expect.poll(()=>page.locator('#gallery-image').evaluate(i=>i.complete&&i.naturalWidth>=1000)).toBe(true);
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);expect(errors).toEqual([]);
});
