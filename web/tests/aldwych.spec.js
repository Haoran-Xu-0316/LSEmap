import { test, expect } from '@playwright/test';

for (const width of [1440, 390]) {
  test(`61A exposes the developed exterior with a historical reception and uncalibrated footprint at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: width === 390 ? 844 : 1000 });
    await page.goto('/#61A');
    await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready', 'exterior-61A', { timeout: 60000 });
    await expect(page.locator('.model-state')).toHaveText('轮廓边界待校准');
    await expect(page.locator('#interior-view')).toBeEnabled();
    await page.locator('.detail-note summary').click();
    await expect(page.locator('.detail-note')).toContainText('改造前归档照片');
    await expect(page.locator('.detail-note')).toContainText('已确认为LSE物业');
    await expect(page.locator('.detail-note')).toContainText('模型占地边界及与邻楼衔接仍待校准');
    await page.waitForTimeout(1100);
    await page.screenshot({ path: `result/web/edition07/61a-${width}.png` });
    await page.locator('.detail-photo').click();
    await expect(page.locator('#gallery-image')).toHaveAttribute('src', new RegExp('^' + '/images/61a-exterior.webp'.replace('.webp', '\\.webp') + '\\?v=[0-9]+-[a-f0-9]{12}$'));
    await expect.poll(() => page.locator('#gallery-image').evaluate(image => image.complete && image.naturalWidth >= 800)).toBe(true);
    await page.keyboard.press('Escape');
    await page.locator('#interior-view').click();
    await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','interior-61A',{timeout:60000});
    await expect(page.locator('.room-study-caption')).toContainText('2021');
    await page.waitForTimeout(1100);
    await page.screenshot({path:`result/web/release24/61a-interior-${width}.png`});
    await page.locator('#overview').click();
    await expect(page.locator('#detail-panel')).toBeHidden();
  });
}
