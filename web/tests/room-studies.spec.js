import { test, expect } from '@playwright/test';
import { readFile } from 'node:fs/promises';

const catalogue = JSON.parse(await readFile('web/public/models/catalogue.json', 'utf8'));
const rooms = catalogue.buildings.filter(building => ['OLD','CLM','CON'].includes(building.code));

test('the original three room samples remain available', () => {
  expect(catalogue.buildings.filter(building => building.interior)).toHaveLength(25);
  expect(rooms.map(room => room.code).sort()).toEqual(['CLM', 'CON', 'OLD']);
  for (const room of rooms) {
    expect(room.interiorStudy.kind).toBe('room-sample');
    expect(room.interiorStudy.scope).toContain('不代表整栋内部');
    expect(room.detailedInterior.triangles).toBeGreaterThan(1000);
    expect(room.detailedInterior.bytes).toBeLessThan(2 * 1024 * 1024);
    // Independent cutaways belong at the local origin, never inside the campus shell.
    expect(Math.max(...room.interiorBounds.max.map(Math.abs))).toBeLessThan(20);
  }
});

for (const room of rooms) {
  for (const width of [1440, 390]) {
    test(`${room.code} room sample loads, frames and returns to its exterior at ${width}px`, async ({ page }) => {
      const errors = [];
      page.on('pageerror', error => errors.push(error.message));
      page.on('console', message => { if (message.type() === 'error') errors.push(message.text()); });
      await page.setViewportSize({ width, height: width === 390 ? 844 : 1000 });
      await page.goto(`/#${room.code}`);
      await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready', `exterior-${room.code}`, { timeout: 60000 });
      await expect(page.locator('#interior-view')).toHaveText('室内样本');
      await expect(page.locator('.room-study-caption')).toBeVisible();
      await expect(page.locator('.room-study-caption')).toContainText(room.interiorStudy.label);
      await page.locator('#interior-view').click();
      await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready', `interior-${room.code}`);
      await expect(page.locator('#scene-subtitle')).toContainText(room.interiorStudy.label);
      await expect(page.locator('#view-mode')).toHaveText('室内样本');
      await page.waitForTimeout(1200);
      await page.screenshot({ path: `result/web/room-studies/${room.code.toLowerCase()}-${width}.png` });
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
      await page.locator('.detail-gallery button').last().click();
      await expect(page.locator('#gallery-image')).toHaveAttribute('src', new RegExp(`/images/${room.code.toLowerCase()}-interior\\.webp\\?v=${catalogue.version}-`));
      await expect.poll(() => page.locator('#gallery-image').evaluate(image => image.complete && image.naturalWidth >= 1000)).toBe(true);
      await page.keyboard.press('Escape');
      await page.locator('#exterior-view').click();
      await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready', `exterior-${room.code}`);
      expect(errors).toEqual([]);
    });
  }
}
