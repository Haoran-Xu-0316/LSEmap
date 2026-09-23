import { test, expect } from '@playwright/test';
import { readFile } from 'node:fs/promises';

test('overview retains every detailed exterior across selection and interiors', async ({ page }) => {
  test.setTimeout(180000);
  const catalogue = JSON.parse(await readFile('dist/models/catalogue.json', 'utf8'));
  const codes = catalogue.buildings.filter(b => b.detailedExterior).map(b => b.code).sort();
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.goto('/');
  const canvas = page.locator('canvas');
  await expect(canvas).toHaveAttribute('data-campus-details', codes.join(','), { timeout: 120000 });
  await page.screenshot({ path: 'result/web/campus-details-overview.png' });
  await expect(page.locator('.map-label[data-code="MAR"]')).toBeVisible();
  await page.locator('.building-row[data-code="MAR"]').click();
  await expect(canvas).toHaveAttribute('data-detail-ready', 'exterior-MAR');
  await expect(canvas).toHaveAttribute('data-campus-details', 'MAR');
  await page.locator('#interior-view').click();
  await expect(canvas).toHaveAttribute('data-detail-ready', 'interior-MAR', { timeout: 60000 });
  await expect(canvas).toHaveAttribute('data-campus-details', '');
  await page.locator('#overview').click();
  await expect(canvas).toHaveAttribute('data-campus-details', codes.join(','));
  await expect(canvas).not.toHaveAttribute('data-detail-ready');
  expect(errors).toEqual([]);
});
