import {test, expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';

test('OLD finish changes preserve all geometry and other building references', async () => {
  const audit = JSON.parse(await readFile('result/blender/stage86/old-limestone-audit.json'));
  expect(audit.savedMeasurements.allGeometryUnchanged).toBeTruthy();
  expect(audit.savedMeasurements.onlyDeclaredMaterialSlotsChanged).toBeTruthy();
  expect(audit.savedMeasurements.photoTextures).toBe(0);
  const before = JSON.parse(await readFile('result/blender/stage86/catalogue-before.json'));
  const after = JSON.parse(await readFile('dist/models/catalogue.json'));
  for (const building of before.buildings) {
    const current = after.buildings.find(b => b.code === building.code);
    if (building.code !== 'OLD') expect(current.detailedExterior?.url).toBe(building.detailedExterior?.url);
    expect(current.detailedInterior?.url).toBe(building.detailedInterior?.url);
    expect(current.interiorSpaces).toEqual(building.interiorSpaces);
  }
});

test('campus and OLD detail carry identical limestone finish parameters', async () => {
  const catalogue = JSON.parse(await readFile('dist/models/catalogue.json'));
  const old = catalogue.buildings.find(b => b.code === 'OLD');
  const sets = [];
  for (const url of ['/models/campus.glb', old.detailedExterior.url]) {
    const bytes = await readFile('dist' + url);
    const doc = JSON.parse(bytes.subarray(20, 20 + bytes.readUInt32LE(12)));
    const node = doc.nodes.find(n => n.extras?.buildingCode === 'OLD') ?? doc.nodes.find(n => n.mesh !== undefined);
    const materials = doc.meshes[node.mesh].primitives.map(p => doc.materials[p.material]);
    const limestone = materials.filter(m => m.name.includes('OLD_V86_limestone_'));
    expect(limestone.length).toBeGreaterThan(20);
    const normalized = limestone.map(m => ({
      name: m.name.split('OLD_V86_limestone_')[1],
      detail: m.extras.surfaceDetail,
      color: m.pbrMetallicRoughness.baseColorFactor,
      roughness: m.pbrMetallicRoughness.roughnessFactor,
    })).sort((a,b) => a.name.localeCompare(b.name));
    for (const material of normalized) {
      expect(material.detail.kind).toBe('noise');
      expect(material.detail.scale).toBe(2);
      expect(material.detail.bump).toBeCloseTo(.0003, 7);
      expect(material.roughness).toBeCloseTo(.87, 5);
    }
    sets.push(normalized);
    expect(materials.some(m => m.name.includes('OLD_V84_FinalSale_figures'))).toBeTruthy();
    expect(materials.some(m => m.name.includes('OLD_V85_four_column_blue'))).toBeTruthy();
  }
  // The established overview omits V16/V17 sub-centimetre finish meshes.
  // Compare all shared stone surfaces, and explicitly bound those two exceptions.
  const detailOnly = sets[1].filter(m => !sets[0].some(s => s.name === m.name));
  expect(detailOnly.map(m => m.name).sort()).toEqual(['V16_OLD_finish', 'V17_OLD_finish']);
  expect(sets[0]).toEqual(sets[1].filter(m => !detailOnly.includes(m)));
});

test('OLD shaded exterior and entrance gallery load successfully', async ({page}) => {
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  await page.goto('/#OLD');
  await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready', 'exterior-OLD', {timeout:60000});
  await expect(page.locator('#fallback')).toBeHidden();
  await page.locator('.detail-gallery img[src*="old-houghton-entrance"]').click();
  await expect(page.locator('#gallery-image')).toBeVisible();
  expect(await page.locator('#gallery-image').evaluate(i => i.complete && i.naturalWidth > 0)).toBeTruthy();
  expect(errors).toEqual([]);
});
