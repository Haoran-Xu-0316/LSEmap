import { test, expect } from '@playwright/test';
import { readFile } from 'node:fs/promises';

test('heritage finish and UV revisions preserve unrelated interiors and unrelated exterior', async () => {
  const baseline = JSON.parse(await readFile('web/tests/fixtures/edition26-models.json', 'utf8'));
  const catalogue = JSON.parse(await readFile('dist/models/catalogue.json', 'utf8'));
  for (const building of catalogue.buildings) {
    for (const key of (building.code === 'LRB' ? ['interiorSpaces'] : ['detailedInterior', 'interiorSpaces']))
      expect(building[key] ?? null, `${building.code}: ${key}`).toEqual(baseline[building.code][key]);
    if (['OLD', 'SAL', 'KGS', 'KSW', 'CON', 'LRB', 'CKK'].includes(building.code))
      expect(building.detailedExterior.sha256).not.toBe(baseline[building.code].detailedExterior.sha256);
  else if(building.code==='CLM') expect(building.detailedExterior.sha256).not.toBe(baseline[building.code].detailedExterior.sha256);
  else expect(building.detailedExterior ?? null, building.code).toEqual(baseline[building.code].detailedExterior);
  }
});

for (const code of ['OLD', 'SAL', 'KGS']) test(`${code} source finish renders on desktop and phone`, async ({ page }) => {
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
  await page.goto(`/#${code}`);
  await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready', `exterior-${code}`, { timeout: 60000 });
  await page.waitForTimeout(350);
  await page.screenshot({ path: `result/web/release27/${code}-desktop.png` });
  if (code === 'KGS') {
    await page.locator('#detail-view').click();
    await page.waitForTimeout(1000);
    await page.screenshot({ path: 'result/web/release27/KGS-entrance.png' });
  }
  await page.setViewportSize({ width: 390, height: 844 });
  await page.waitForTimeout(400);
  await page.screenshot({ path: `result/web/release27/${code}-mobile.png` });
  expect(errors).toEqual([]);
});
