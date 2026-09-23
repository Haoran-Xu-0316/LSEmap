import { test, expect } from '@playwright/test';

for (const code of ['COW', 'KGS']) {
  for (const width of [1440, 390]) {
    test(`${code} heritage model and entrance stay usable at ${width}px`, async ({ page }) => {
      const errors = [];
      page.on('pageerror', error => errors.push(error.message));
      page.on('console', message => { if (message.type() === 'error') errors.push(message.text()); });
      await page.setViewportSize({ width, height: width === 390 ? 844 : 1000 });
      await page.goto(`/#${code}`);
      await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready', `exterior-${code}`, { timeout: 60000 });
      await page.locator('#detail-view').click();
      await expect(page.locator('#view-mode')).toHaveText('入口细节');
      await expect(page.locator('#context-toggle')).toBeDisabled();
      await expect(page.locator('.map-label:visible')).toHaveCount(0);
      await page.waitForTimeout(1100);
      await page.screenshot({ path: `result/web/local09/${code.toLowerCase()}-entrance-${width}.png` });
      await page.locator('.detail-photo').click();
      await page.locator('#gallery-next').click();
      await expect(page.locator('#gallery-position')).toHaveText('2 / 2');
      await expect(page.locator('#gallery-image')).toHaveAttribute('src', new RegExp('^' + `/images/${code.toLowerCase()}-entrance.webp`.replace('.webp', '\\.webp') + '\\?v=16-[a-f0-9]{12}$'));
      await expect.poll(() => page.locator('#gallery-image').evaluate(image => image.complete && image.naturalWidth >= 1000)).toBe(true);
      await page.keyboard.press('Escape');
      await page.locator('#exterior-view').click();
      await expect(page.locator('#view-mode')).toHaveText('建筑外观');
      await page.waitForTimeout(1100);
      await page.screenshot({ path: `result/web/local09/${code.toLowerCase()}-exterior-${width}.png` });
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
      expect(errors).toEqual([]);
    });
  }
}
