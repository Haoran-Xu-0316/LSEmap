import { test, expect } from '@playwright/test';

const studies = [
  { code: 'LCH', label: '入口细节', image: 'lch-entrance', images: 2 },
  { code: 'LAK', label: '窗饰细节', image: 'lak-windows', images: 2 },
  { code: 'MAR', label: '入口细节', image: 'mar-entrance', images: 4 },
];
for (const study of studies) {
  for (const width of [1440, 390]) {
    test(`${study.code} refined close-up and gallery work at ${width}px`, async ({ page }) => {
      const errors = [];
      page.on('pageerror', error => errors.push(error.message));
      page.on('console', message => { if (message.type() === 'error') errors.push(message.text()); });
      await page.setViewportSize({ width, height: width === 390 ? 844 : 1000 });
      await page.goto(`/#${study.code}`);
      await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready', `exterior-${study.code}`, { timeout: 60000 });
      await page.locator('#detail-view').click();
      await expect(page.locator('#view-mode')).toHaveText(study.label);
      await expect(page.locator('#context-toggle')).toBeDisabled();
      await expect(page.locator('.map-label:visible')).toHaveCount(0);
      await page.waitForTimeout(1100);
      await page.screenshot({ path: `result/web/three-rounds/${study.code.toLowerCase()}-closeup-${width}.png` });
      await page.locator('.detail-photo').click();
      await page.locator('#gallery-next').click();
      await expect(page.locator('#gallery-position')).toHaveText(`2 / ${study.images}`);
      await expect(page.locator('#gallery-image')).toHaveAttribute('src', new RegExp('^' + `/images/${study.image}.webp`.replace('.webp', '\\.webp') + '\\?v=17-[a-f0-9]{12}$'));
      await expect.poll(() => page.locator('#gallery-image').evaluate(image => image.complete && image.naturalWidth >= 1000)).toBe(true);
      await page.keyboard.press('Escape');
      if (study.code === 'MAR') {
        await page.locator('#interior-view').click();
        await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready', 'interior-MAR', { timeout: 60000 });
        await expect(page.locator('#view-mode')).toHaveText('公共内部');
        await page.waitForTimeout(1100);
        await page.screenshot({ path: `result/web/three-rounds/mar-interior-${width}.png` });
      }
      await page.locator('#exterior-view').click();
      await expect(page.locator('#view-mode')).toHaveText('建筑外观');
      await page.waitForTimeout(1100);
      await page.screenshot({ path: `result/web/three-rounds/${study.code.toLowerCase()}-exterior-${width}.png` });
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
      expect(errors).toEqual([]);
    });
  }
}
