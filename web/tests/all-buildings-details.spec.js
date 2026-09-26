import { test, expect } from '@playwright/test';
import { readFile } from 'node:fs/promises';
const catalogue = JSON.parse(await readFile('web/public/models/catalogue.json', 'utf8'));
const before = JSON.parse(await readFile('web/tests/fixtures/edition16-digests.json', 'utf8'));

test('all 31 records retain refined geometry; three unchanged public interiors retain their hashes', () => {
  expect(catalogue.version).toBe('24');
  expect(catalogue.buildings).toHaveLength(31);
  for (const building of catalogue.buildings) {
    expect(building.localRefinement.newComponents).toBeGreaterThan(0);
    const original = before.buildings.find(item => item.code === building.code);
    expect(building.status).toBe(original.status);
    if (building.detailedExterior) expect(building.detailedExterior.sha256).not.toBe(original.detailedExterior.sha256);
    if (original.detailedInterior && !['SAW', 'LRB'].includes(building.code)) expect(building.detailedInterior.sha256).toBe(original.detailedInterior.sha256);
  }
});

test('every refined exterior loads and remains inspectable', async ({ page }) => {
  test.setTimeout(300000);
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.goto('/#MAR');
  await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready', 'exterior-MAR', { timeout: 60000 });
  for (const building of catalogue.buildings) {
    await page.locator('#overview').click();
    await page.locator('#building-search').fill(building.code);
    await page.locator(`.building-row[data-code="${building.code}"]`).click();
    if (building.detailedExterior) {
      await page.locator('#exterior-view').click();
      await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready', `exterior-${building.code}`, { timeout: 60000 });
    }
    await page.waitForTimeout(1050);
    await page.screenshot({ path: `result/web/all-buildings/${building.code.toLowerCase()}-desktop.png` });
  }
  expect(errors).toEqual([]);
});

for (const width of [1440, 390]) {
  test(`POR corner and historical shopfront gallery at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: width === 390 ? 844 : 1000 });
    await page.goto('/#POR');
    await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready', 'exterior-POR', { timeout: 60000 });
    await page.locator('#detail-view').click();
    await expect(page.locator('#view-mode')).toHaveText('转角细节');
    await page.waitForTimeout(1100);
    await page.screenshot({ path: `result/web/all-buildings/por-corner-${width}.png` });
    await page.locator('.detail-photo').click();
    await page.locator('#gallery-next').click();
    await expect(page.locator('#gallery-image')).toHaveAttribute('src', new RegExp('^' + '/images/por-entrance.webp'.replace('.webp', '\\.webp') + '\\?v=24-[a-f0-9]{12}$'));
    await expect.poll(() => page.locator('#gallery-image').evaluate(image => image.complete && image.naturalWidth >= 1000)).toBe(true);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  });
}
