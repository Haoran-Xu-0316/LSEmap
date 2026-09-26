import { test, expect } from '@playwright/test';
import { readFile } from 'node:fs/promises';

const catalogue = JSON.parse(await readFile('web/public/models/catalogue.json', 'utf8'));

test('5LF opens at its attributed northern address and remains usable on mobile', async ({ page }) => {
  const house = catalogue.buildings.find(building => building.code === '5LF');
  const point = house.footprintSource.sourcePoint;
  // Independent geographic check: the official address must land inside the model bounds.
  const x = (point.longitude - catalogue.origin[0]) * 111320 * Math.cos(catalogue.origin[1] * Math.PI / 180);
  const z = -(point.latitude - catalogue.origin[1]) * 111320;
  expect(x).toBeGreaterThan(house.bounds.min[0]);
  expect(x).toBeLessThan(house.bounds.max[0]);
  expect(z).toBeGreaterThan(house.bounds.min[2]);
  expect(z).toBeLessThan(house.bounds.max[2]);
  expect(house.bounds.max[0] - house.bounds.min[0]).toBeLessThan(20);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/#5LF');
  await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready', 'exterior-5LF', { timeout: 60000 });
  await expect(page.locator('#detail-panel h2')).toContainText('5 Lincoln');
  await expect(page.locator('#interior-view')).toHaveText('室内样本');
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.waitForTimeout(1100);
  await page.screenshot({ path: 'result/web/edition06/5lf-mobile.png' });
  await page.locator('#overview').click();
  await expect(page.locator('#detail-panel')).toBeHidden();
  await expect(page.locator('canvas')).not.toHaveAttribute('data-detail-ready');
});
