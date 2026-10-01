import {test, expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';

async function readModel(url) {
  const bytes = await readFile('dist' + url);
  return JSON.parse(bytes.subarray(20, 20 + bytes.readUInt32LE(12)));
}
const sourceName = material => material.name.replace(/^WEB_(DETAIL_)?/, '');
const finish = material => ({
  color: material.pbrMetallicRoughness?.baseColorFactor ?? [1, 1, 1, 1],
  roughness: material.pbrMetallicRoughness?.roughnessFactor ?? 1,
  metallic: material.pbrMetallicRoughness?.metallicFactor ?? 1,
  alpha: material.alphaMode ?? 'OPAQUE',
  surface: material.extras?.surfaceDetail ?? null,
});

test('every shared campus exterior preserves detail colors and procedural finishes', async () => {
  const catalogue = JSON.parse(await readFile('dist/models/catalogue.json'));
  const campus = await readModel('/models/campus.glb');
  let buildings = 0, surfaces = 0, brickSurfaces = 0;
  for (const building of catalogue.buildings.filter(b => b.detailedExterior)) {
    const detail = await readModel(building.detailedExterior.url);
    const detailMaterials = new Map(detail.materials.map(m => [sourceName(m), m]));
    const node = campus.nodes.find(n => n.extras?.buildingCode === building.code);
    expect(node, building.code).toBeTruthy();
    for (const primitive of campus.meshes[node.mesh].primitives) {
      const material = campus.materials[primitive.material];
      const reference = detailMaterials.get(sourceName(material));
      expect(reference, building.code + ': ' + sourceName(material)).toBeTruthy();
      expect(finish(material), building.code + ': ' + sourceName(material)).toEqual(finish(reference));
      if (material.extras?.surfaceDetail?.kind === 'brick') {
        expect(primitive.attributes.TEXCOORD_0, building.code).toBeDefined();
        brickSurfaces++;
      }
      surfaces++;
    }
    buildings++;
  }
  expect(buildings).toBe(30);
  expect(surfaces).toBeGreaterThan(450);
  expect(brickSurfaces).toBeGreaterThan(10);
});

test('accessible entrance retains original geometry and other detailed models', async () => {
  const audit = JSON.parse(await readFile('result/blender/stage88/tower-entry-audit.json'));
  expect(audit.savedMeasurements.originalObjectsUnchanged).toBeTruthy();
  expect(audit.savedMeasurements.retainedGlazingAndFramesUnchanged).toBeTruthy();
  expect(audit.savedMeasurements.revolvingDoorGeometryUnchanged).toBeTruthy();
  expect(audit.savedMeasurements.clearWidthMetres).toBeCloseTo(.98, 4);
  expect(audit.savedMeasurements.controlCentreMetres).toBeCloseTo(.78, 5);
  const before = JSON.parse(await readFile('result/blender/stage88/catalogue-before.json'));
  const after = JSON.parse(await readFile('dist/models/catalogue.json'));
  for (const building of before.buildings) {
    const current = after.buildings.find(b => b.code === building.code);
    if (building.code !== 'PAN') expect(current.detailedExterior?.url).toBe(building.detailedExterior?.url);
    expect(current.detailedInterior?.url).toBe(building.detailedInterior?.url);
    expect(current.interiorSpaces).toEqual(building.interiorSpaces);
  }
  const pan = after.buildings.find(b => b.code === 'PAN');
  for (const url of ['/models/campus.glb', pan.detailedExterior.url]) {
    const doc = await readModel(url);
    const names = doc.materials.map(m => m.name);
    expect(names.some(n => n.includes('PAN_V88_dark_door_frame'))).toBeTruthy();
    expect(names.some(n => n.includes('PAN_V88_control_metal'))).toBeTruthy();
  }
});

test('shared entrance and OLD exterior load without the model fallback', async ({page}) => {
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  for (const code of ['PAN', 'FAW', 'OLD']) {
    await page.goto('/#' + code);
    await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready', 'exterior-' + code, {timeout:60000});
    await expect(page.locator('#fallback')).toBeHidden();
  }
  expect(errors).toEqual([]);
});
