import { test, expect } from '@playwright/test';
import { readFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';

const readJson = async path => JSON.parse(await readFile(path, 'utf8'));
const sha256 = bytes => createHash('sha256').update(bytes).digest('hex');
const buildingByCode = (catalogue, code) => catalogue.buildings.find(building => building.code === code);
const extraSpaces = catalogue => catalogue.buildings.flatMap(building =>
  (building.interiorSpaces ?? []).map(space => ({ code: building.code, ...space })));

test('edition158 changes only OLD classroom and MAR104 while adding CBG103', async () => {
  const before = await readJson('result/blender/stage158/catalogue-before.json');
  const catalogue = await readJson('web/public/models/catalogue.json');
  const production = await readJson('dist/models/catalogue.json');
  expect(String(catalogue.version)).toBe('158');
  expect(production).toEqual(catalogue);
  expect(catalogue.buildings.map(building => building.code)).toEqual(before.buildings.map(building => building.code));
  expect(catalogue.generatedTextures).toEqual(before.generatedTextures);
  expect(extraSpaces(catalogue)).toHaveLength(9);
  const previousIds = extraSpaces(before).map(space => `${space.code}:${space.id}`);
  const addedIds = extraSpaces(catalogue).map(space => `${space.code}:${space.id}`).filter(id => !previousIds.includes(id));
  expect(addedIds).toEqual(['CBG:cbg-103']);

  for (const building of catalogue.buildings) {
    const previous = buildingByCode(before, building.code);
    // The OLD classroom is the default OLD_PUBLIC_INTERIOR_study export.
    // Its SSC room is an additional space and must remain byte-identical.
    expect(building.detailedExterior, `${building.code} exterior`).toEqual(previous.detailedExterior);
    if (building.code === 'OLD') {
      expect(building.interiorStudy?.label).toBe('OLD.4.10阶梯教室');
      expect(building.detailedInterior?.sha256).not.toBe(previous.detailedInterior?.sha256);
    } else {
      for (const key of ['detailedInterior', 'interiorView', 'interiorBounds', 'interiorStudy']) {
        expect(building[key], `${building.code} default ${key}`).toEqual(previous[key]);
      }
    }
    for (const previousSpace of previous.interiorSpaces ?? []) {
      const space = building.interiorSpaces?.find(item => item.id === previousSpace.id);
      expect(space, `${building.code}:${previousSpace.id} retained`).toBeTruthy();
      if (building.code === 'MAR' && space.id === 'mar-104') {
        expect(space.detailedInterior?.sha256).not.toBe(previousSpace.detailedInterior?.sha256);
      } else {
        expect(space, `${building.code}:${space.id} unchanged`).toEqual(previousSpace);
      }
    }
    for (const asset of [building.detailedInterior, ...(building.interiorSpaces ?? []).map(space => space.detailedInterior)].filter(Boolean)) {
      expect(asset.url).toMatch(/^\/models\/details\/.+\.glb$/);
      expect(asset.sha256).toMatch(/^[a-f0-9]{64}$/);
      expect(sha256(await readFile('dist' + asset.url)), asset.url).toBe(asset.sha256);
    }
  }
  const cbg = buildingByCode(catalogue, 'CBG');
  const room = cbg.interiorSpaces.find(space => space.id === 'cbg-103');
  expect(room.label).toContain('CBG.1.03');
  expect(room.interiorAsset).toBe(room.detailedInterior.url);
  expect(room.detailedInterior.sha256).not.toBe(cbg.detailedInterior.sha256);
  expect(room.detailedInterior.sha256).not.toBe(cbg.interiorSpaces.find(space => space.id === 'cbg-102').detailedInterior.sha256);
});

for (const width of [1440, 390]) {
  test(`CBG103 switches independently between classrooms, atrium and exterior at ${width}px`, async ({ page }) => {
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    page.on('response', response => {
      if (response.status() >= 400) errors.push(`${response.status()} ${response.url()}`);
    });
    await page.setViewportSize({ width, height: width === 390 ? 844 : 1000 });
    await page.goto('/#CBG');
    const canvas = page.locator('canvas');
    await expect(canvas).toHaveAttribute('data-detail-ready', 'exterior-CBG', { timeout: 60000 });
    await expect(page.locator('#fallback')).toBeHidden();
    await expect(page.locator('#interior-view')).toBeEnabled();
    await page.locator('#interior-view').click();
    await expect(canvas).toHaveAttribute('data-detail-ready', 'interior-CBG', { timeout: 60000 });
    await expect(canvas).toHaveAttribute('data-interior-space', 'default');
    const selector = page.locator('#interior-space');
    await expect(selector.locator('option[value="cbg-103"]')).toHaveCount(1);

    for (const id of ['cbg-102', 'cbg-103', 'default']) {
      await expect(selector).toBeEnabled();
      await selector.selectOption(id);
      const detailKey = id === 'default' ? 'interior-CBG' : `interior-CBG:${id}`;
      await expect(canvas).toHaveAttribute('data-detail-ready', detailKey, { timeout: 60000 });
      await expect(canvas).toHaveAttribute('data-interior-space', id);
      await expect(selector).toHaveValue(id);
      await expect(page.locator('#fallback')).toBeHidden();
      await expect(page.locator('#interior-view')).not.toHaveAttribute('data-failed', 'true');
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), id + ' overflow').toBe(true);
    }
    await page.locator('#exterior-view').click();
    await expect(canvas).toHaveAttribute('data-detail-ready', 'exterior-CBG', { timeout: 60000 });
    await expect(page.locator('#interior-spaces')).toBeHidden();
    await expect(page.locator('#fallback')).toBeHidden();
    expect(errors).toEqual([]);
  });
}
