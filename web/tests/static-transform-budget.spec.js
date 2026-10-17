import { test, expect } from '@playwright/test';
import { createServer } from 'vite';
import { mkdir, writeFile } from 'node:fs/promises';

test('the full campus avoids repeated static transforms without changing pixels or picking', async ({ page }) => {
  test.setTimeout(150000);
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  const server = await createServer({ logLevel: 'error', server: { host: '127.0.0.1', port: 0 } });
  try {
    await server.listen();
    await page.route('**/__static-transforms', route => route.fulfill({ contentType: 'text/html', body:
      '<!doctype html><style>body{margin:0}#stage{width:960px;height:768px}#labels{display:none}</style><div id="stage"></div><div id="labels"></div>' }));
    await page.goto(`http://127.0.0.1:${server.httpServer.address().port}/__static-transforms`);
    const proof = await page.evaluate(async () => {
      const { CampusViewer } = await import('/src/viewer.js');
      const { prepareStaticModel } = await import('/src/surface-materials.js');
      const { THREE } = await import('/tests/interaction239-fixture.js');
      const catalogue = await (await fetch('/models/catalogue.json')).json();
      const viewer = new CampusViewer(document.querySelector('#stage'), document.querySelector('#labels'), catalogue.buildings, () => {}, () => {});
      window.viewer = viewer;
      // Explicitly load each exterior once, rather than timing background downloads.
      viewer.loadCampusExteriors = async () => {};
      await viewer.load();
      await viewer.environmentReady;
      for (const building of catalogue.buildings.filter(item => item.detailedExterior)) await viewer.loadExterior(building);
      cancelAnimationFrame(viewer.frame);
      viewer.transition = null;
      viewer.home(false);
      const roots = [viewer.campus, ...viewer.exteriors.values()];
      const staticNodes = [];
      for (const root of roots) root.traverse(object => staticNodes.push(object));
      const productionFlags = staticNodes.every(object => !object.matrixAutoUpdate) && !viewer.scene.matrixAutoUpdate;
      const measure = () => {
        const originalCompose = THREE.Matrix4.prototype.compose;
        const originalMultiply = THREE.Matrix4.prototype.multiplyMatrices;
        let compositions = 0, multiplications = 0;
        THREE.Matrix4.prototype.compose = function (...args) { compositions++; return originalCompose.apply(this, args); };
        THREE.Matrix4.prototype.multiplyMatrices = function (...args) { multiplications++; return originalMultiply.apply(this, args); };
        const times = [];
        try {
          viewer.scene.updateMatrixWorld();
          compositions = multiplications = 0;
          for (let index = 0; index < 40; index++) {
            const start = performance.now();
            viewer.scene.updateMatrixWorld();
            times.push(performance.now() - start);
          }
        } finally {
          THREE.Matrix4.prototype.compose = originalCompose;
          THREE.Matrix4.prototype.multiplyMatrices = originalMultiply;
        }
        return { compositionsPerFrame: compositions / 40, multiplicationsPerFrame: multiplications / 40,
          medianCpuMs: times.sort((a, b) => a - b)[20] };
      };
      const gl = viewer.renderer.getContext();
      const pixels = () => {
        viewer.renderPipeline.render({ moving: false, stabilize: false });
        gl.finish();
        const output = new Uint8Array(viewer.canvas.width * viewer.canvas.height * 4);
        gl.readPixels(0, 0, viewer.canvas.width, viewer.canvas.height, gl.RGBA, gl.UNSIGNED_BYTE, output);
        return output;
      };
      // Recreate the previous per-frame transform policy on the same loaded scene.
      for (const object of staticNodes) object.matrixAutoUpdate = true;
      viewer.scene.matrixAutoUpdate = true;
      const before = measure();
      pixels();
      const reference = pixels();
      for (const root of roots) prepareStaticModel(root);
      viewer.scene.matrixAutoUpdate = false;
      const after = measure();
      const actual = pixels();
      let maxPixelDifference = 0;
      for (let index = 0; index < actual.length; index++) maxPixelDifference = Math.max(maxPixelDifference, Math.abs(actual[index] - reference[index]));
      // Frozen local matrices must still follow a live parent and remain raycastable.
      const parent = new THREE.Group();
      const mesh = new THREE.Mesh(new THREE.BoxGeometry(2, 2, 2), new THREE.MeshBasicMaterial());
      mesh.position.set(3, 2, 1); parent.add(mesh); prepareStaticModel(parent);
      const liveParent = new THREE.Group(); liveParent.add(parent); viewer.scene.add(liveParent);
      liveParent.position.set(10, 0, 0); viewer.scene.updateMatrixWorld();
      const worldPosition = mesh.getWorldPosition(new THREE.Vector3()).toArray();
      const ray = new THREE.Raycaster(new THREE.Vector3(13, 2, 10), new THREE.Vector3(0, 0, -1));
      const firstHit = ray.intersectObject(parent, true).length > 0;
      mesh.visible = false;
      const hiddenToggles = !mesh.visible; mesh.visible = true;
      liveParent.position.x += 2; viewer.scene.updateMatrixWorld();
      const movedPosition = mesh.getWorldPosition(new THREE.Vector3()).toArray();
      liveParent.removeFromParent(); mesh.geometry.dispose(); mesh.material.dispose();
      return { productionFlags, exteriorCount: viewer.exteriors.size, staticNodeCount: staticNodes.length,
        before, after, maxPixelDifference, worldPosition, movedPosition, firstHit, hiddenToggles,
        scope: 'Local production campus and all 30 exteriors; matrix work and pixel parity, not a universal FPS guarantee' };
    });
    await mkdir('result/web/static-transform-budget', { recursive: true });
    await writeFile('result/web/static-transform-budget/measurement.json', JSON.stringify(proof, null, 2) + '\n');
    expect(proof.productionFlags).toBe(true);
    expect(proof.exteriorCount).toBe(30);
    expect(proof.staticNodeCount).toBeGreaterThan(100);
    expect(proof.after.compositionsPerFrame).toBeLessThan(proof.before.compositionsPerFrame * .05);
    expect(proof.after.multiplicationsPerFrame).toBeLessThan(proof.before.multiplicationsPerFrame * .05);
    expect(proof.maxPixelDifference).toBe(0);
    expect(proof.worldPosition).toEqual([13, 2, 1]);
    expect(proof.movedPosition).toEqual([15, 2, 1]);
    expect(proof.firstHit).toBe(true);
    expect(proof.hiddenToggles).toBe(true);
    expect(errors).toEqual([]);
  } finally {
    await page.evaluate(() => window.viewer?.dispose()).catch(() => {});
    await server.close();
  }
});
