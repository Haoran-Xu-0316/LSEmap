import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
const catalogue=JSON.parse(await readFile('web/public/models/catalogue.json','utf8'));
const previous=JSON.parse(await readFile('web/tests/fixtures/edition20-models.json','utf8'));
test('edition 24 adds OCS and extends only the intended library assets',async()=>{
 expect(catalogue.version).toBe('24');
 expect(catalogue.buildings.filter(b=>b.interior)).toHaveLength(25);
 expect(catalogue.buildings.find(b=>b.code==='OCS').interiorStudy.scope).toContain('日期');
 const lrb=catalogue.buildings.find(b=>b.code==='LRB');
 expect(lrb.interiorSections.find(s=>s.id==='4').maxHeight).toBeLessThan(23);
 expect(lrb.interiorSections.map(s=>s.id)).toEqual(['LG','G','1','2','3','4']);
 for(const section of lrb.interiorSections){expect(section.maxHeight).toBeGreaterThan(section.minHeight);}
 for(const b of previous.buildings){
  const current=catalogue.buildings.find(r=>r.code===b.code);
  for(const key of ['detailedExterior','detailedInterior'])if(b[key]){
   if(b.code==='LRB')expect(current[key].sha256).not.toBe(b[key].sha256);
   else expect(current[key].sha256).toBe(b[key].sha256);
  }
 }
});
for(const width of [1440,390])test(`library floor sections render and reset at ${width}px`,async({page})=>{
 test.setTimeout(120000);const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.setViewportSize({width,height:width===390?844:1000});await page.goto('/#LRB');
 await expect(page.locator('#interior-sections')).toBeHidden();await expect(page.locator('#interior-view')).toBeEnabled({timeout:60000});await page.locator('#interior-view').click();
 await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','interior-LRB',{timeout:60000});
 await expect(page.locator('#interior-sections')).toBeVisible();const hashes=[];
 for(const id of ['LG','G','1','2','3','4']){
  await page.locator('#interior-level').selectOption(id);await expect(page.locator('canvas')).toHaveAttribute('data-interior-section',id);await page.waitForTimeout(1100);
  const pixels=await page.locator('canvas').screenshot();hashes.push(createHash('sha256').update(pixels).digest('hex'));
  if(['LG','3'].includes(id))await page.screenshot({path:`result/web/extension/lrb-${id}-${width}.png`});
 }
 expect(new Set(hashes).size).toBe(6);
 await page.locator('#exterior-view').click();await expect(page.locator('#interior-sections')).toBeHidden();await expect(page.locator('canvas')).not.toHaveAttribute('data-interior-section',/.+/);
 await page.locator('#interior-view').click();await expect(page.locator('#interior-level')).toHaveValue('all');
 await page.locator('#overview').click();await expect(page.locator('canvas')).not.toHaveAttribute('data-interior-section',/.+/);
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);expect(errors).toEqual([]);
});
for(const width of [1440,390])test(`OCS interior retains Roboto without section clipping at ${width}px`,async({page})=>{
 await page.setViewportSize({width,height:width===390?844:1000});await page.goto('/#OCS');await expect(page.locator('#interior-view')).toBeEnabled({timeout:60000});await page.locator('#interior-view').click();
 await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','interior-OCS',{timeout:60000});await page.evaluate(()=>document.fonts.ready);expect(await page.evaluate(()=>document.fonts.check('500 24px Roboto'))).toBe(true);
 await expect(page.locator('#interior-sections')).toHaveCount(0);await expect(page.locator('canvas')).not.toHaveAttribute('data-interior-section',/.+/);await page.waitForTimeout(1100);await page.screenshot({path:`result/web/extension/ocs-${width}.png`});
 await page.locator('.detail-gallery button').last().click();await expect(page.locator('#gallery-image')).toHaveAttribute('src',/ocs-interior\.webp\?v=24-/);await expect.poll(()=>page.locator('#gallery-image').evaluate(i=>i.complete&&i.naturalWidth>1000)).toBe(true);
});
