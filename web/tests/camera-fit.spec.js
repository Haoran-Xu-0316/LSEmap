import { test, expect } from "@playwright/test";
import * as THREE from "three";

// Exercise fitting without a renderer: the output must contain every projected corner.
test("street and exactly vertical camera directions fit the entire building", async () => {
  globalThis.matchMedia = () => ({ matches: false });
  const { CampusViewer } = await import("../src/viewer.js");
  const bounds = { min: [2.9, 0, 98.3], max: [23.4, 29, 128.2] };
  for (const direction of [
    new THREE.Vector3(0, 1, 0),
    new THREE.Vector3(-0.6, 0.55, 0.7).normalize(),
  ]) {
    const camera = new THREE.PerspectiveCamera(38, 1.2, 0.1, 3000);
    const viewer = {
      camera,
      container: { clientWidth: 1200 },
      activeCode: "COL",
      moveCamera(position, target) {
        camera.position.copy(position);
        camera.lookAt(target);
        camera.updateMatrixWorld();
      },
    };
    CampusViewer.prototype.fit.call(viewer, bounds, false, direction);
    for (const x of [bounds.min[0], bounds.max[0]])
      for (const y of [bounds.min[1], bounds.max[1]])
        for (const z of [bounds.min[2], bounds.max[2]]) {
          const projected = new THREE.Vector3(x, y, z).project(camera);
          expect(Math.abs(projected.x)).toBeLessThan(0.9);
          expect(Math.abs(projected.y)).toBeLessThan(0.9);
          expect(projected.z).toBeLessThan(1);
        }
  }
});
