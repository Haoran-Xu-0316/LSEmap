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
