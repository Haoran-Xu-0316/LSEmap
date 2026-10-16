import {test,expect} from '@playwright/test';

for(const width of [1440,390])test(`gallery follows building and overview history at ${width}px`,async({page})=>{
 await page.setViewportSize({width,height:width===390?844:1000});
 await page.goto('/#LRB');
 await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-LRB',{timeout:90000});
 const dialog=page.locator('#gallery-dialog');
 await page.getByRole('button',{name:'图书馆坡道与楼层连接',exact:true}).click();
 await expect(dialog).toBeVisible();
 await expect(page.locator('#gallery-title')).toHaveText('图书馆坡道与楼层连接');
 // A browser hash/history change keeps the same document and reproduces the
 // stale-image issue; reloading would hide it without exercising the router.
 await page.evaluate(()=>{location.hash='SAL';});
 await expect(dialog).toBeHidden();
 await expect(page.locator('#detail-panel h2')).toHaveText('Sir Arthur Lewis Building');
 await page.getByRole('button',{name:'玻璃入口亭与公共接待',exact:true}).click();
 await expect(dialog).toBeVisible();
 await expect(page.locator('#gallery-title')).toHaveText('玻璃入口亭与公共接待');
 await page.goBack();
 await expect(dialog).toBeHidden();
 await expect(page.locator('#detail-panel h2')).toHaveText('Lionel Robbins Building，Library');
 await page.getByRole('button',{name:'图书馆坡道与楼层连接',exact:true}).click();
 await expect(dialog).toBeVisible();
 await page.evaluate(()=>{location.hash='';});
 await expect(dialog).toBeHidden();
 await expect(page.locator('#detail-panel')).toBeHidden();
 if(width===390){
  await expect(page.locator('#index-toggle')).toHaveAttribute('aria-expanded','false');
  await page.locator('#index-toggle').click();
 }
 await expect(page.locator('#index-panel')).toBeVisible();
 await expect(page.locator('#building-search')).toBeVisible();
});
