import { test, expect } from "@playwright/test";
import * as THREE from "three";

for (const code of ["COL", "CON"])
for (const viewport of [{ width: 1440, height: 1000 }, { width: 390, height: 844 }]) {
  test(`${code} isolated labels and entrance presets work at ${viewport.width}px`, async ({ page }) => {
    await page.setViewportSize(viewport);
    await page.goto(`/#${code}`);
    await expect(page.locator('canvas[data-ready="true"]')).toBeVisible({ timeout: 60000 });
    await expect(page.locator('.map-label:visible')).toHaveCount(1);
    await expect(page.locator('.map-label:visible')).toHaveAttribute('data-code', code);
    await page.locator('#detail-view').click();
    await expect(page.locator('#detail-view')).toHaveAttribute('aria-pressed', 'true');
    await expect(page.locator('#view-mode')).toHaveText('入口细节');
    await expect(page.locator('#context-toggle')).toBeDisabled();
    await expect(page.locator('.map-label:visible')).toHaveCount(0);
    await page.waitForTimeout(1100);
    await page.screenshot({ path: `result/web/entrance-${code.toLowerCase()}-${viewport.width}.png` });
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await page.locator('#exterior-view').click();
    await expect(page.locator('#view-mode')).toHaveText('建筑外观');
    await expect(page.locator('#detail-view')).toHaveAttribute('aria-pressed', 'false');
    await expect(page.locator('.map-label:visible')).toHaveCount(1);
    await page.locator('#context-toggle').click();
    await expect(page.locator('#context-toggle')).toHaveAttribute('aria-pressed', 'true');
    await page.locator('#overview').click();
    await expect.poll(() => page.locator('.map-label:visible').count()).toBeGreaterThan(1);
  });
}

test('hidden buildings cannot intercept a click on the visible model', async () => {
  globalThis.matchMedia = () => ({ matches: false });
  const { CampusViewer } = await import('../src/viewer.js');
  const camera = new THREE.PerspectiveCamera(50, 1, 0.1, 100);
  const makeBuilding = (code, z, visible) => {
    const mesh = new THREE.Mesh(new THREE.PlaneGeometry(2, 2), new THREE.MeshBasicMaterial());
    mesh.position.z = z;
    mesh.userData.buildingCode = code;
    mesh.visible = visible;
    mesh.updateMatrixWorld();
    return mesh;
  };
  const hidden = makeBuilding('HIDDEN', -2, false);
  const visible = makeBuilding('VISIBLE', -4, true);
  let selected;
  const viewer = {
    ready: true, mode: 'campus',
    pointerStart: { id: 1, x: 50, y: 50, time: performance.now() },
    canvas: { getBoundingClientRect: () => ({ left: 0, top: 0, width: 100, height: 100 }) },
    pointer: new THREE.Vector2(), raycaster: new THREE.Raycaster(), camera,
    pickable: [hidden, visible], onPick: (code) => { selected = code; },
  };
  CampusViewer.prototype.pick.call(viewer, { button: 0, pointerId: 1, clientX: 50, clientY: 50 });
  expect(selected).toBe('VISIBLE');
  for (const mesh of [hidden, visible]) { mesh.geometry.dispose(); mesh.material.dispose(); }
});
