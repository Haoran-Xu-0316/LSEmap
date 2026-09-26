import { test, expect } from '@playwright/test';
import { readFile } from 'node:fs/promises';
import { detailFor } from '../src/content.js';
const catalogue = JSON.parse(await readFile('web/public/models/catalogue.json', 'utf8'));
const previous = JSON.parse(await readFile('web/tests/fixtures/edition19-models.json', 'utf8'));
const additions = ['5LF','49L','COL','COW','FAW','KGS','KSW','LAK','PAN','PAR','PEA','PEL','SAL','SAR','STC'];
const replacements = ['50L','51L','KSW','SAR'];

test('edition 24 preserves the previous room additions and exterior repairs', async () => {
  expect(catalogue.version).toBe('24');
  expect(catalogue.buildings.filter(building => building.interior)).toHaveLength(25);
  for (const building of catalogue.buildings) {
    const before = previous.buildings.find(item => item.code === building.code);
    if (before.detailedExterior) {
      if (replacements.includes(building.code) || building.code === "LRB") expect(building.detailedExterior.sha256).not.toBe(before.detailedExterior.sha256);
      else expect(building.detailedExterior.sha256).toBe(before.detailedExterior.sha256);
    }
    if (before.detailedInterior && building.code !== "LRB") expect(building.detailedInterior.sha256).toBe(before.detailedInterior.sha256);
    if (additions.includes(building.code)) {
      expect(building.interiorStudy.kind).toBe('room-sample');
      expect(building.interiorStudy.scope.length).toBeGreaterThan(20);
      expect(detailFor(building).images.map(([name]) => name)).toContain(`${building.code.toLowerCase()}-interior`);
      expect(detailFor(building).note).not.toMatch(/未建立内部[。；]/);
    }
  }
});

for (const width of [1440, 390]) {
  test(`interior directory finds every available room and explains empty results at ${width}px`, async ({ page }) => {
    await page.setViewportSize({width, height:width === 390 ? 844 : 1000});
    await page.goto('/');
    await expect(page.locator('canvas[data-ready="true"]')).toBeVisible({timeout:60000});
    if (width === 390) await page.locator('#index-toggle').click();
    await expect(page.locator('#interior-count')).toHaveText('25栋可查看局部内部');
    await page.locator('#interior-filter').click();
    await expect(page.locator('.building-row')).toHaveCount(25);
    await page.locator('#building-search').fill('LCH');
    await expect(page.locator('#empty-search')).toContainText('取消筛选');
    await page.locator('#interior-filter').click();
    await expect(page.locator('.building-row')).toHaveCount(1);
    await page.locator('#building-search').fill('KGS');
    await expect(page.locator('.interior-hint')).toContainText('KGS.1.02');
    await page.locator('.building-row').click();
    await expect(page.locator('#interior-view')).toBeEnabled();
    await page.locator('#interior-view').click();
    await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','interior-KGS',{timeout:60000});
    await expect(page.locator('.room-study-caption')).toContainText('KGS.1.02');
    await page.waitForTimeout(1100);
    await page.screenshot({path:`result/web/completion/kgs-${width}.png`});
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  });
}

test('every new interior opens and its gallery has the same model edition', async ({ page }) => {
  test.setTimeout(240000);
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('console', message => {if(message.type() === 'error') errors.push(message.text());});
  await page.goto('/');
  await expect(page.locator('canvas[data-ready="true"]')).toBeVisible({timeout:60000});
  for (const code of additions) {
    await page.locator('#overview').click();
    await page.locator('#building-search').fill(code);
    await page.locator(`.building-row[data-code="${code}"]`).click();
    await expect(page.locator('#interior-view')).toBeEnabled();
    await page.locator('#interior-view').click();
    await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready',`interior-${code}`,{timeout:60000});
    await page.waitForTimeout(1100);
    await page.screenshot({path:`result/web/completion/${code.toLowerCase()}-interior.png`});
    const building = catalogue.buildings.find(item => item.code === code);
    const images = detailFor(building).images;
    const index = images.findIndex(([name]) => name === `${code.toLowerCase()}-interior`);
    await page.locator('.detail-gallery button').nth(index).click();
    await expect(page.locator('#gallery-image')).toHaveAttribute('src',new RegExp(`/${code.toLowerCase()}-interior\\.webp\\?v=24-`));
    await expect.poll(() => page.locator('#gallery-image').evaluate(image => image.complete && image.naturalWidth >= 1000)).toBe(true);
    await page.keyboard.press('Escape');
  }
  expect(errors).toEqual([]);
});

for (const code of ['PEA', 'COW', '49L', '5LF', 'LAK', 'SAR']) {
  test(`${code} interior stays usable above the mobile detail sheet`, async ({ page }) => {
    await page.setViewportSize({width:390,height:844});
    await page.goto(`/#${code}`);
    await expect(page.locator('#interior-view')).toBeEnabled({timeout:60000});
    await page.locator('#interior-view').click();
    await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready',`interior-${code}`,{timeout:60000});
    await page.waitForTimeout(1100);
    await page.screenshot({path:`result/web/completion/${code.toLowerCase()}-mobile.png`});
    const caption = page.locator('.room-study-caption');
    expect(await caption.evaluate(node => getComputedStyle(node).gridColumn)).toBe('1 / -1');
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await page.locator('#overview').click();
    await expect(page.locator('#detail-panel')).toBeHidden();
  });
}

for (const code of replacements) {
  test(`${code} replacement facade has a working dedicated close-up`, async ({ page }) => {
    await page.goto(`/#${code}`);
    await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready',`exterior-${code}`,{timeout:60000});
    await page.locator('#detail-view').click();
    await expect(page.locator('#detail-view')).toHaveAttribute('aria-pressed','true');
    await page.waitForTimeout(1100);
    await page.screenshot({path:`result/web/completion/${code.toLowerCase()}-closeup.png`});
    const building = catalogue.buildings.find(item => item.code === code);
    const images = detailFor(building).images;
    await page.locator('.detail-gallery button').nth(images.findIndex(([name]) => name === building.closeupImage)).click();
    await expect(page.locator('#gallery-image')).toHaveAttribute('src',new RegExp(`/${building.closeupImage}\\.webp\\?v=24-`));
    await expect.poll(() => page.locator('#gallery-image').evaluate(image => image.complete && image.naturalWidth >= 1000)).toBe(true);
  });
}
