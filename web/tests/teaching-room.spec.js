import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';
const catalogue=JSON.parse(await readFile('web/public/models/catalogue.json','utf8'));
const previous=JSON.parse(await readFile('web/tests/fixtures/edition21-models.json','utf8'));
const mar=catalogue.buildings.find(b=>b.code==='MAR');
test('additional Marshall room preserves every existing exterior and interior',()=>{
 expect(catalogue.version).toBe('24');
 expect(mar.interiorSpaces).toHaveLength(1);
 expect(mar.interiorSpaces[0].id).toBe('mar-104');
 expect(mar.interiorSpaces[0].scope).toContain('90');
 for(const old of previous.buildings){
  const current=catalogue.buildings.find(b=>b.code===old.code);
  for(const key of ['detailedExterior','detailedInterior'])if(old[key])expect(current[key].sha256).toBe(old[key].sha256);
 }
});
for(const width of [1440,390])test(`Marshall hall and classroom switch independently at ${width}px`,async({page})=>{
 await page.setViewportSize({width,height:width===390?844:1000});
 const errors=[];page.on('pageerror',error=>errors.push(error.message));
 await page.goto('/#MAR');await expect(page.locator('#interior-view')).toBeEnabled({timeout:60000});
 await page.locator('#interior-view').click();await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','interior-MAR',{timeout:60000});
 await page.locator('#interior-space').selectOption('mar-104');
 await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','interior-MAR:mar-104',{timeout:60000});
 await expect(page.locator('#interior-space-scope')).toContainText('90');
 await page.waitForTimeout(1100);await page.screenshot({path:`result/web/teaching-room/mar-104-${width}.png`});
 await page.locator('#interior-space').selectOption('default');await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','interior-MAR');
 await page.locator('#exterior-view').click();await expect(page.locator('#interior-spaces')).toBeHidden();await expect(page.locator('canvas')).not.toHaveAttribute('data-interior-space',/.+/);
 await page.locator('#interior-view').click();await expect(page.locator('#interior-space')).toHaveValue('default');
 await page.locator('#overview').click();await expect(page.locator('canvas')).not.toHaveAttribute('data-interior-space',/.+/);
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);expect(errors).toEqual([]);
});
test('failed additional room remains retryable without losing the hall',async({page})=>{
 const room=mar.interiorSpaces[0];let failing=true;
 await page.route(`**${room.interiorAsset}`,route=>failing?route.abort():route.continue());
 await page.goto('/#MAR');await expect(page.locator('#interior-view')).toBeEnabled({timeout:60000});await page.locator('#interior-view').click();await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','interior-MAR',{timeout:60000});
 await page.locator('#interior-space').selectOption('mar-104');await expect(page.locator('#interior-view')).toHaveText('加载失败，重试');await expect(page.locator('#interior-space')).toBeEnabled();
 failing=false;await page.locator('#interior-view').click();await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','interior-MAR:mar-104',{timeout:60000});
});
test('a late classroom response cannot replace another selected building',async({page})=>{
 let release;const gate=new Promise(resolve=>{release=resolve});let started=false;
 await page.route(`**${mar.interiorSpaces[0].interiorAsset}`,async route=>{started=true;await gate;await route.continue();});
 await page.goto('/#MAR');await expect(page.locator('#interior-view')).toBeEnabled({timeout:60000});await page.locator('#interior-view').click();await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','interior-MAR',{timeout:60000});
 await page.locator('#interior-space').selectOption('mar-104');await expect.poll(()=>started).toBe(true);
 await page.evaluate(()=>{location.hash='OLD'});release();
 await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-OLD',{timeout:60000});await page.waitForTimeout(500);
 await expect(page.locator('canvas')).not.toHaveAttribute('data-interior-space',/.+/);await expect(page.locator('#interior-spaces')).toHaveCount(0);
});
