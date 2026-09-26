import { test, expect } from '@playwright/test';
import { readFile } from 'node:fs/promises';

const catalogue = JSON.parse(await readFile('web/public/models/catalogue.json', 'utf8'));
const facades = catalogue.buildings.filter(building => building.status === 'facade');

test('all fifteen street studies have their own gallery and honest scope', async ({ page }) => {
  test.setTimeout(120000);
  expect(facades).toHaveLength(15);
  await page.goto('/#COW');
  await expect(page.locator('canvas[data-ready="true"]')).toBeVisible({ timeout: 60000 });
  for (const building of facades) {
    await page.locator('#overview').click();
    await page.locator('#building-search').fill(building.code);
    await page.locator(`.building-row[data-code="${building.code}"]`).click();
    await expect(page.locator('.model-state')).toHaveText('沿街立面研究');
    await expect(page.locator('#interior-view')).toHaveCount(building.interior ? 1 : 0);
    await page.locator('.detail-photo').click();
    const image = page.locator('#gallery-image');
    await expect(image).toHaveAttribute('src', new RegExp('^' + `/images/${building.code.toLowerCase()}-exterior.webp`.replace('.webp', '\\.webp') + '\\?v=[0-9]+-[a-f0-9]{12}$'));
    await expect.poll(() => image.evaluate(img => img.complete && img.naturalWidth >= 800)).toBe(true);
    await page.keyboard.press('Escape');
    await page.locator('.detail-note summary').click();
    await expect(page.locator('.detail-note')).toContainText('仍为估计');
  }
});
