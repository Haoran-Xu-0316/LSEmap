import {test,expect} from '@playwright/test';
for(const width of [1440,724,390])test(`clean glass interface at ${width}px`,async({page})=>{
 await page.setViewportSize({width,height:900});
 const errors=[];page.on('pageerror',error=>errors.push(error.message));
 await page.goto('/');
 if(width<=700)await page.locator('#index-toggle').click();
 await expect(page.locator('.building-row')).toHaveCount(31);
 await expect(page.locator('#detail-filter,.model-state,.interior-hint')).toHaveCount(0);
 await page.getByRole('searchbox',{name:'搜索楼名或代码'}).fill('CBG');
 await expect(page.locator('.building-row')).toHaveCount(1);
 await page.locator('.building-row').click();
 await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-CBG',{timeout:60000});
 await expect(page.locator('.detail-quality')).toBeHidden();
 await expect(page.locator('#exterior-view')).toBeVisible();
 await expect(page.locator('#interior-view')).toBeVisible();
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
 await page.screenshot({path:`result/web/ui-polish/glass-${width}.png`});
 expect(errors).toEqual([]);
});
