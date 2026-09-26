import { test, expect } from "@playwright/test";
import { readFile } from "node:fs/promises";
import { ModelCache } from "../src/model-cache.js";

const catalogue = JSON.parse(await readFile("web/public/models/catalogue.json", "utf8"));

test("all thirty exteriors and twenty-five interiors render without shader errors", async ({ page }) => {
  test.setTimeout(240000);
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("console", (message) => { if (message.type() === "error") errors.push(message.text()); });
  await page.goto("/#CBG");
  await expect(page.locator('canvas[data-ready="true"]')).toBeVisible({ timeout: 60000 });
  for (const building of catalogue.buildings.filter((b) => b.detailedExterior)) {
    await page.locator('#overview').click();
    await page.locator('#building-search').fill(building.code);
    await page.locator(`.building-row[data-code="${building.code}"]`).click();
    await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready', `exterior-${building.code}`, { timeout: 45000 });
    await expect(page.locator('#detail-quality-status')).toHaveText('外观细节已加载');
    await page.waitForTimeout(1100);
    if (['MAR', 'SAL', 'OLD', 'COW', 'PEA', 'KGS', '5LF', '61A', '49L', '50L'].includes(building.code))
      await page.screenshot({ path: `result/web/detail-upgrade/${building.code.toLowerCase()}-exterior.png` });
    if (building.detailedInterior) {
      await page.locator('#interior-view').click();
      await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready', `interior-${building.code}`, { timeout: 45000 });
      await expect(page.locator('#detail-quality-status')).toHaveText('内部细节已加载');
      await page.waitForTimeout(1100);
      if (['CKK', 'LRB'].includes(building.code))
        await page.screenshot({ path: `result/web/detail-upgrade/${building.code.toLowerCase()}-interior.png` });
    }
  }
  expect(errors).toEqual([]);
});

test("detail failure preserves base navigation and explicit retry recovers", async ({ page }) => {
  await page.route('**/models/details/**', route => route.abort());
  await page.goto('/#CBG');
  await expect(page.locator('#detail-quality-retry')).toBeVisible({ timeout: 60000 });
  await expect(page.locator('canvas[data-ready="true"]')).toBeVisible();
  await expect(page.locator('#fallback')).toBeHidden();
  await expect(page.locator('#detail-quality-status')).toContainText('基础模型');
  await page.unroute('**/models/details/**');
  await page.locator('#detail-quality-retry').click();
  await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready', 'exterior-CBG', { timeout: 45000 });
  await expect(page.locator('#detail-quality-retry')).toBeHidden();
});

test("switching to another building cannot reveal a late detail response", async ({ page }) => {
  let release;
  const gate = new Promise(resolve => { release = resolve; });
  await page.route('**/models/details/cbg-exterior-*', async route => { await gate; await route.continue(); });
  await page.goto('/#CBG');
  await expect(page.locator('#detail-quality-status')).toContainText('正在加载', { timeout: 60000 });
  await page.locator('#overview').click();
  await page.locator('#building-search').fill('COL');
  await page.locator('.building-row[data-code="COL"]').click();
  release();
  await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready', 'exterior-COL', { timeout: 45000 });
  await expect(page.locator('#detail-panel h2')).toHaveText('Columbia House');
  await expect(page.locator('.map-label:visible')).toHaveAttribute('data-code', 'COL');
});

test("detail cache coalesces downloads, cancels queued work and releases evicted models", async () => {
  const started = [], disposed = [];
  const resolvers = new Map();
  const cache = new ModelCache(url => {
    started.push(url);
    return new Promise(resolve => resolvers.set(url, () => resolve({ url })));
  }, () => {}, model => disposed.push(model.url), 2);
  const a = cache.request('a', 'a');
  const sameA = cache.request('a', 'a');
  expect(sameA).toBe(a);
  const stale = cache.request('b', 'b').catch(error => error.name);
  const c = cache.request('c', 'c');
  expect(await stale).toBe('AbortError');
  expect(started).toEqual(['a']);
  resolvers.get('a')(); await a;
  await expect.poll(() => started).toEqual(['a', 'c']);
  resolvers.get('c')(); await c;
  const d = cache.request('d', 'd');
  resolvers.get('d')(); await d;
  expect(disposed).toEqual(['a']);
  expect([...cache.models.keys()]).toEqual(['c', 'd']);
  cache.dispose();
  expect(disposed).toEqual(['a', 'c', 'd']);
});


test("detailed models remain usable on mobile and return to the campus", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/#SAL');
  await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready', 'exterior-SAL', { timeout: 60000 });
  await page.waitForTimeout(1100);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await expect(page.locator('#detail-quality-status')).toBeVisible();
  await page.screenshot({ path: 'result/web/detail-upgrade/sal-mobile.png' });
  await page.locator('#overview').click();
  await expect(page.locator('#detail-panel')).toBeHidden();
  await expect(page.locator('canvas')).not.toHaveAttribute('data-detail-ready');
});
