import { test, expect } from '@playwright/test';
import { readFile } from 'node:fs/promises';
const manifest = JSON.parse(await readFile('dist/release.json','utf8'));
test('an obsolete open tab refreshes once while preserving the selected building', async ({ page }) => {
  let navigations = 0;
  page.on('framenavigated', frame => { if (frame === page.mainFrame()) navigations++; });
  await page.route('**/release.json', route => route.fulfill({json:{...manifest,entryScript:'/assets/index-next-release.js'}}));
  await page.goto('/#KGS');
  await expect.poll(() => navigations).toBe(2);
  await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-KGS',{timeout:60000});
  await page.waitForTimeout(1500);
  expect(navigations).toBe(2);
  expect(new URL(page.url()).hash).toBe('#KGS');
});
test('the current release stays open without an unnecessary reload', async ({ page }) => {
  let navigations=0;
  page.on('framenavigated',frame=>{if(frame===page.mainFrame())navigations++;});
  await page.goto('/#MAR');
  await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-MAR',{timeout:60000});
  expect(navigations).toBe(1);
});
test('an unavailable release manifest does not block the current model', async ({ page }) => {
  await page.route('**/release.json',route=>route.fulfill({status:503,body:'Temporarily unavailable'}));
  await page.goto('/#POR');
  await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-POR',{timeout:60000});
});

test('a model-only release refreshes even when the application bundle is unchanged', async ({ page }) => {
  let navigations = 0;
  page.on('framenavigated', frame => { if (frame === page.mainFrame()) navigations++; });
  await page.route('**/release.json', async route => {
    await page.locator('canvas[data-ready="true"]').waitFor();
    await route.fulfill({json:{...manifest,sourceModelSha256:'a'.repeat(64)}});
  });
  await page.goto('/#MAR');
  await expect.poll(() => navigations, {timeout:60000}).toBe(2);
  await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-MAR',{timeout:60000});
  expect(new URL(page.url()).hash).toBe('#MAR');
});

test('re-exported assets refresh an open tab even when native source and bundle are unchanged', async ({ page }) => {
  const manifest = JSON.parse(await readFile('dist/release.json', 'utf8'));
  let changed = false;
  await page.route('**/release.json', route => route.fulfill({ json: changed
    ? { ...manifest, modelAssetsSha256: 'b'.repeat(64) } : manifest }));
  await page.goto('/#CBG');
  await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready', 'exterior-CBG', { timeout: 60000 });
  changed = true;
  await page.waitForTimeout(5100);
  const navigation = page.waitForEvent('framenavigated', frame => frame === page.mainFrame());
  await page.evaluate(() => window.dispatchEvent(new Event('focus')));
  await navigation;
  expect(new URL(page.url()).hash).toBe('#CBG');
});
