import { test, expect } from '@playwright/test';
import { createServer } from 'vite';
import { mkdir } from 'node:fs/promises';

const screenshotDirectory = 'result/blender/stage240/browser';

for (const width of [1440, 890, 390]) {
  test(`building thumbnails keep usable sizes and scroll at ${width}px`, async ({ page }) => {
    const server = await createServer({
      logLevel: 'error',
      server: { host: '127.0.0.1', port: 0 },
    });
    try {
      await server.listen();
      await page.setViewportSize({ width, height: width === 390 ? 844 : 1000 });
      await page.goto(`http://127.0.0.1:${server.httpServer.address().port}/#OLD`);
      const strip = page.locator('.detail-gallery');
      const buttons = strip.locator('button');
      await expect(buttons).toHaveCount(18);

      const dimensions = await strip.evaluate(element => ({
        client: element.clientWidth,
        scroll: element.scrollWidth,
        gap: parseFloat(getComputedStyle(element).gap),
        buttons: [...element.querySelectorAll('button')].map(button => ({
          width: button.getBoundingClientRect().width,
          height: button.getBoundingClientRect().height,
        })),
      }));
      expect(dimensions.scroll).toBeGreaterThan(dimensions.client);
      expect(dimensions.gap).toBeGreaterThanOrEqual(8);
      for (const button of dimensions.buttons) {
        expect(button.width).toBeCloseTo(65, 0);
        expect(button.height).toBeGreaterThanOrEqual(48);
      }

      // Keyboard navigation must reveal the focused thumbnail inside the strip.
      await buttons.last().focus();
      await expect.poll(() => strip.evaluate(element => element.scrollLeft)).toBeGreaterThan(0);
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
      await buttons.last().click();
      await expect(page.locator('#gallery-dialog')).toBeVisible();
      await expect(page.locator('#gallery-image')).toHaveAttribute('src', /old-127-teaching-interior\.webp\?v=/);
      await page.keyboard.press('Escape');
      await expect(page.locator('#gallery-dialog')).toBeHidden();
      await mkdir(screenshotDirectory, { recursive: true });
      await page.screenshot({ path: `${screenshotDirectory}/gallery-strip-${width}.png` });
    } finally {
      await server.close();
    }
  });
}
