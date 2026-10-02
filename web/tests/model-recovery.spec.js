import {test,expect} from '@playwright/test';

test('failed campus transfer recovers to OLD without a stale error or broken logo',async({page})=>{
 let requests=0;
 await page.route('**/models/campus.glb*',async route=>{
  requests++;
  if(requests===1)await route.abort('failed');else await route.continue();
 });
 await page.goto('/#OLD');
 await expect(page.locator('#fallback')).toBeVisible();
 await page.locator('#retry').click();
 await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-OLD',{timeout:60000});
 await expect(page.locator('#fallback')).toBeHidden();
 await expect(page.locator('canvas')).toHaveCount(1);
 expect(await page.locator('.brand-mark').evaluate(i=>i.complete&&i.naturalWidth>0)).toBe(true);
 await page.locator('.detail-gallery img[src*="old-houghton-entrance"]').click();
 await expect(page.locator('#gallery-image')).toBeVisible();
 expect(await page.locator('#gallery-image').evaluate(i=>i.complete&&i.naturalWidth>0)).toBe(true);
});

test('OLD exterior and interior remain usable on mobile after loader changes',async({page})=>{
 const errors=[];page.on('pageerror',error=>errors.push(error.message));
 await page.setViewportSize({width:390,height:844});await page.goto('/#OLD');
 await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-OLD',{timeout:60000});
 await expect(page.locator('#fallback')).toBeHidden();
 await page.locator('#interior-view').click();
 await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','interior-OLD',{timeout:60000});
 await expect(page.locator('#fallback')).toBeHidden();expect(errors).toEqual([]);
});
