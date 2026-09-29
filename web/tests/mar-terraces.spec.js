import { test, expect } from '@playwright/test';
import { readFile } from 'node:fs/promises';

// Editions 25–29 refine MAR geometry, exterior palettes, slate UVs and KSW brick UVs.
// MAR hall inherits its exterior ground glazing; LRB interior inherits its revised roof; unrelated interiors stay identical.
test('terrace and palette revisions preserve unrelated buildings and room assets', async () => {
  const baseline = JSON.parse(await readFile('web/tests/fixtures/edition24-models.json', 'utf8'));
  const catalogue = JSON.parse(await readFile('dist/models/catalogue.json', 'utf8'));
  expect(catalogue.buildings.map(b => b.code).sort()).toEqual(Object.keys(baseline).sort());
  for (const building of catalogue.buildings) {
    const previous = baseline[building.code];
    for (const key of ['detailedInterior', 'interiorSpaces']) {
      if (['MAR','LRB'].includes(building.code) && key === 'detailedInterior') {
        expect(building[key]).not.toEqual(previous[key]);
      } else expect(building[key] ?? null, `${building.code}: ${key}`).toEqual(previous[key]);
    }
    if (['MAR', 'CBG', 'SAW', 'OLD', 'SAL', 'KGS', 'KSW', 'CON', 'LRB', 'CKK'].includes(building.code)) expect(building.detailedExterior.url).not.toBe(previous.detailedExterior.url);
  else if(building.code==='CLM') expect(building.detailedExterior.sha256).not.toBe(previous.detailedExterior.sha256);
  else expect(building.detailedExterior ?? null, building.code).toEqual(previous.detailedExterior);
  }
});

test('refined MAR renders at desktop and phone sizes without WebGL errors', async ({ page }) => {
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('console', message => {
    if (message.type() === 'error') errors.push(message.text());
  });
  await page.goto('/#MAR');
  await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready', 'exterior-MAR', { timeout: 60000 });
  await page.waitForTimeout(400);
  await page.screenshot({ path: 'result/web/release25/MAR-desktop.png' });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.waitForTimeout(400);
  await page.screenshot({ path: 'result/web/release25/MAR-mobile.png' });
  expect(errors).toEqual([]);
});
