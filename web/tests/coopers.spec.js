import { test, expect } from '@playwright/test';
import { readFile } from 'node:fs/promises';

const catalogue = JSON.parse(await readFile('web/public/models/catalogue.json', 'utf8'));

for (const width of [1440, 390]) {
  test(`Coopers and the adjoining 50/50A building occupy separate locations at ${width}px`, async ({ page }) => {
    const restaurant = catalogue.buildings.find(building => building.code === '49L');
    const neighbour = catalogue.buildings.find(building => building.code === '50L');
    const centreSouth = building => (building.bounds.min[2] + building.bounds.max[2]) / 2;
    expect(centreSouth(neighbour) - centreSouth(restaurant)).toBeGreaterThan(5);
    await page.setViewportSize({ width, height: width === 390 ? 844 : 1000 });
    await page.goto('/#49L');
    for (const code of ['49L', '50L']) {
      if (code === '50L') {
        await page.locator('#overview').click();
        if (width === 390) await page.getByRole('button', { name: '建筑目录', exact: true }).click();
        await page.locator('#building-search').fill(code);
        await page.locator(`.building-row[data-code="${code}"]`).click();
      }
      await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready', `exterior-${code}`, { timeout: 60000 });
      await expect(page.locator('.model-state')).toHaveText('沿街立面研究');
      await expect(page.locator('#interior-view')).toHaveCount(0);
      await page.locator('.detail-note summary').click();
      await expect(page.locator('.detail-note')).toContainText('2022年规划总图');
      await page.waitForTimeout(1100);
      await page.screenshot({ path: `result/web/edition08/${code.toLowerCase()}-${width}.png` });
    }
  });
}

test('a catalogue record without a supported footprint remains accessible without a fake model', async ({ page }) => {
  const fixture = structuredClone(catalogue);
  const record = fixture.buildings.find(building => building.code === '49L');
  record.bounds = null;
  record.status = 'unlocated';
  delete record.detailedExterior;
  await page.route('**/models/catalogue.json', route => route.fulfill({ json: fixture }));
  await page.goto('/#49L');
  await expect(page.locator('canvas[data-ready="true"]')).toBeVisible({ timeout: 60000 });
  await expect(page.locator('.model-state')).toHaveText('独立轮廓待确认');
  await expect(page.locator('#exterior-view')).toHaveCount(0);
  await expect(page.locator('canvas')).not.toHaveAttribute('data-detail-ready');
});
