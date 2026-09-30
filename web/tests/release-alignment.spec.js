import { test, expect } from '@playwright/test';
import { readFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { detailFor } from '../src/content.js';
test('release manifest identifies every model and gallery in edition 51', async () => {
  const release = JSON.parse(await readFile('dist/release.json','utf8'));
  const catalogue = JSON.parse(await readFile('dist/models/catalogue.json','utf8'));
  expect(release.version).toBe('51');
  expect(release.sourceModelSha256).toBe(catalogue.sourceModelSha256);
  for (const building of catalogue.buildings) {
    const detail = detailFor(building);
    for (const [name] of detail.images) expect(release.assets[`/images/${name}.webp`]).toBeTruthy();
  }
  for (const [path, asset] of Object.entries(release.assets)) {
    const data = await readFile(`dist${path}`);
    expect(data.length).toBe(asset.bytes);
    expect(createHash('sha256').update(data).digest('hex')).toBe(asset.sha256);
  }
});
test('gallery images use a revisioned URL to bypass the previous release cache', async ({ page }) => {
  const errors=[];
  page.on('pageerror', error => errors.push(error.message));
  await page.goto('/#MAR');
  await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready', 'exterior-MAR', { timeout: 60000 });
  await expect(page.locator('.detail-photo img')).toHaveAttribute('src', /\/images\/mar-exterior\.webp\?v=51-[a-f0-9]{12}$/);
  await page.locator('.detail-photo').click();
  await expect(page.locator('#gallery-image')).toHaveAttribute('src', /\?v=51-[a-f0-9]{12}$/);
  await page.keyboard.press('Escape');
  await page.locator('#detail-view').click();
  await expect(page.locator('#view-mode')).toHaveText('入口细节');
  await page.locator('#interior-view').click();
  await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready', 'interior-MAR', { timeout: 60000 });
  expect(errors).toEqual([]);
});

test('mixed model and gallery releases cannot enter the live scene', async ({ page }) => {
  const gallery = JSON.parse(await readFile('dist/gallery-manifest.json', 'utf8'));
  await page.route('**/gallery-manifest.json', route => route.fulfill({
    json: { ...gallery, sourceModelSha256: 'f'.repeat(64) },
  }));
  await page.goto('/#CBG');
  await expect(page.locator('#fallback')).toBeVisible();
  await expect(page.locator('canvas')).toHaveCount(0);
});
