import { test, expect } from '@playwright/test';
import * as THREE from 'three';
import { readFile } from 'node:fs/promises';
const catalogue = JSON.parse(await readFile('web/public/models/catalogue.json', 'utf8'));

test('mobile entrance framing keeps every supplied camera above ground and restores full-view projection', async () => {
  globalThis.matchMedia = () => ({ matches: false });
  const { CampusViewer } = await import('../src/viewer.js');
  for (const building of catalogue.buildings.filter(b => b.detailView)) {
    const camera = new THREE.PerspectiveCamera(46, 390 / 789, .1, 3000);
    const viewer = {
      ready: true, camera, container: { clientWidth: 390, clientHeight: 789 },
      controls: {}, select() {},
      updateCameraProjection() { CampusViewer.prototype.updateCameraProjection.call(this); },
      moveCamera(position, target) {
        camera.position.copy(position); camera.lookAt(target); camera.updateMatrixWorld();
        this.target = target.clone();
      },
    };
    CampusViewer.prototype.showDetail.call(viewer, building);
    expect(camera.position.y, building.code).toBeGreaterThan(.5);
    const projected = viewer.target.clone().project(camera);
    expect(projected.x, building.code).toBeCloseTo(0, 5);
    expect(projected.y, building.code).toBeCloseTo(.44, 5);
    viewer.mode = 'campus'; viewer.updateCameraProjection();
    expect(viewer.target.clone().project(camera).y, building.code).toBeCloseTo(0, 5);
    viewer.mode = 'detail'; viewer.updateCameraProjection();
    viewer.container.clientWidth = 1440; viewer.updateCameraProjection();
    expect(camera.view.enabled, building.code).toBe(false);
  }
});
