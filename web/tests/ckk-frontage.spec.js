import {test,expect} from '@playwright/test';

test('CKK entrance and gallery remain aligned on desktop and phone',async({page})=>{
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('/#CKK');
 await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-CKK',{timeout:60000});
 await expect(page.locator('.detail-photo img')).toHaveAttribute('src',/ckk-exterior\.webp\?v=43-/);
 await expect(page.locator('#detail-view')).toHaveText('入口细节');
 await page.locator('#detail-view').click();
 await expect(page.locator('#detail-view')).toHaveAttribute('aria-pressed','true');
 await page.waitForLoadState('networkidle');await page.waitForTimeout(500);
 await page.screenshot({path:'result/web/release34/CKK-entrance-desktop.png'});
 await page.setViewportSize({width:390,height:844});
 await expect(page.locator('#detail-view')).toHaveText('入口细节');
 await page.locator('#detail-view').click();
 await expect(page.locator('#detail-view')).toHaveAttribute('aria-pressed','true');
 await page.waitForTimeout(500);
 await page.screenshot({path:'result/web/release34/CKK-entrance-phone.png'});
 expect(errors).toEqual([]);
});
