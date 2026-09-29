import { test, expect } from '@playwright/test';
import { readFile } from 'node:fs/promises';

const gallery = JSON.parse(await readFile('web/public/gallery-manifest.json', 'utf8'));

test('a release change cannot reuse the previous fixed-name campus or interior URL', async ({ page }) => {
  const requested = [];
  let revision = gallery.modelAssetsSha256;
  await page.route('**/gallery-manifest.json', route => route.fulfill({
    json: { ...gallery, modelAssetsSha256: revision },
  }));
  await page.route('**/models/*.glb*', route => {
    const url = new URL(route.request().url());
    if (url.pathname.includes('/details/')) return route.continue();
    requested.push(url.pathname + url.search);
    // A cached old fixed-name URL would fail this release-mismatch regression.
    return url.searchParams.get('v') === revision ? route.continue() : route.abort();
  });
  await page.goto('/#5LF');
  await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready', 'exterior-5LF', { timeout: 60000 });
  revision = 'next-exported-assets';
  await page.goto('/#MAR');
  await page.reload();
  await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready', 'exterior-MAR', { timeout: 60000 });
  await page.locator('#interior-view').click();
  await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready', 'interior-MAR', { timeout: 60000 });
  expect(requested).toContain(`/models/campus.glb?v=${gallery.modelAssetsSha256}`);
  expect(requested).toContain('/models/campus.glb?v=next-exported-assets');
  expect(requested).toContain('/models/mar-interior.glb?v=next-exported-assets');
});
