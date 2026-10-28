import {test, expect} from '@playwright/test';

async function hold(page, pattern) {
  let release;
  const gate = new Promise(resolve => {release = resolve;});
  await page.route(pattern, async route => {
    await gate;
    await route.abort().catch(() => {});
  });
  return release;
}

test('a stalled gallery manifest does not block the interactive campus', async ({page}) => {
  const release = await hold(page, '**/gallery-manifest.json');
  try {
    await page.goto('/', {waitUntil:'domcontentloaded'});
    await expect(page.locator('canvas')).toHaveAttribute('data-ready', 'true', {timeout:10000});
    await expect(page.locator('#fallback')).toBeHidden();
    await page.locator('#building-search').fill('OLD');
    await page.locator('#building-list button').filter({hasText:'Old Building'}).click();
    await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready', 'exterior-OLD');
  } finally {await page.goto('about:blank'); release();}
});

test('a transient catalogue service error recovers without a manual reload', async ({page}) => {
  let requests = 0;
  await page.route('**/models/catalogue.json', route => {
    requests++;
    return requests === 1 ? route.fulfill({status:503,body:'Temporary outage'}) : route.continue();
  });
  await page.goto('/');
  await expect(page.locator('canvas')).toHaveAttribute('data-ready', 'true', {timeout:10000});
  expect(requests).toBeGreaterThanOrEqual(2);
  await expect(page.locator('#fallback')).toBeHidden();
});

test('an unavailable catalogue leaves a bounded recoverable state', async ({page}) => {
  const release = await hold(page, '**/models/catalogue.json');
  try {
    await page.clock.install();
    await page.goto('/', {waitUntil:'domcontentloaded'});
    await page.clock.runFor(8500);
    await page.waitForTimeout(50);
    await page.clock.runFor(8500);
    await expect(page.locator('#fallback')).toBeVisible();
    await expect(page.locator('#retry')).toBeEnabled();
  } finally {await page.goto('about:blank'); release();}
});
