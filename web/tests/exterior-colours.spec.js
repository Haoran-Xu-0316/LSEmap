import { test, expect } from '@playwright/test';
import { readFile } from 'node:fs/promises';

function glbDocument(buffer) {
  return JSON.parse(buffer.subarray(20, 20 + buffer.readUInt32LE(12)).toString());
}

test('CBG red and orange are source materials in both campus and detailed models', async () => {
  const catalogue = JSON.parse(await readFile('dist/models/catalogue.json', 'utf8'));
  const building = catalogue.buildings.find(b => b.code === 'CBG');
  for (const path of ['/models/campus.glb', building.detailedExterior.url]) {
    const glb = glbDocument(await readFile(`dist${path}`));
    const red = glb.materials.find(m => m.name.includes('ochre_anodised_blade_palette26'));
    const orange = glb.materials.find(m => m.name.includes('orange_blade_returns_palette26'));
    expect(red, path).toBeTruthy();
    expect(orange, path).toBeTruthy();
    const [r, g, b] = red.pbrMetallicRoughness.baseColorFactor;
    expect(r).toBeGreaterThan(g * 5);
    expect(r).toBeGreaterThan(b * 5);
    const [or, og, ob] = orange.pbrMetallicRoughness.baseColorFactor;
    expect(og).toBeGreaterThan(g * 3);
    expect(or).toBeGreaterThan(og);
    expect(og).toBeGreaterThan(ob * 3);
    for (const material of [red, orange]) {
      const index = glb.materials.indexOf(material);
      expect(glb.meshes.some(mesh => mesh.primitives.some(p => p.material === index))).toBe(true);
    }
  }
});

for (const code of ['CBG', 'SAW']) test(`${code} colour review on desktop and phone`, async ({ page }) => {
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('console', message => { if (message.type() === 'error') errors.push(message.text()); });
  await page.goto(`/#${code}`);
  await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready', `exterior-${code}`, { timeout: 60000 });
  await page.waitForTimeout(350);
  await page.screenshot({ path: `result/web/release26/${code}-desktop.png` });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.waitForTimeout(450);
  await page.screenshot({ path: `result/web/release26/${code}-mobile.png` });
  await page.locator('#interior-view').click();
  await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready', `interior-${code}`, { timeout: 60000 });
  expect(errors).toEqual([]);
});
