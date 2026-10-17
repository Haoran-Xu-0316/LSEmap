import { test, expect } from '@playwright/test';
import { createServer } from 'vite';
import { mkdir, writeFile } from 'node:fs/promises';

// Exercise the real campus and all detailed facades, including transparent panes.
test('building selection retains the nearest surface with a bounded triangle budget', async ({ page }) => {
  test.setTimeout(150000);
  const server = await createServer({ logLevel: 'error', server: { host: '127.0.0.1', port: 0 } });
  try {
    await server.listen();
    await page.route('**/__picking', route => route.fulfill({ contentType: 'text/html', body:
      '<!doctype html><style>body{margin:0}#stage{width:960px;height:768px}#labels{display:none}</style><div id="stage"></div><div id="labels"></div>' }));
    await page.goto(`http://127.0.0.1:${server.httpServer.address().port}/__picking`);
    const proof = await page.evaluate(async () => {
      const { THREE } = await import('/tests/interaction239-fixture.js');
      const { CampusViewer } = await import('/src/viewer.js');
      const catalogue = await (await fetch('/models/catalogue.json')).json();
      const viewer = new CampusViewer(document.querySelector('#stage'), document.querySelector('#labels'), catalogue.buildings, () => {}, () => {});
      window.viewer = viewer;
      viewer.loadCampusExteriors = async () => {};
      await viewer.load(); await viewer.environmentReady;
      await Promise.all(catalogue.buildings.filter(b => b.detailedExterior).map(b => viewer.loadExterior(b)));
      cancelAnimationFrame(viewer.frame); viewer.transition = null; viewer.home(false);
      viewer.scene.updateMatrixWorld(true); viewer.camera.updateMatrixWorld(true);
      const roots = [...viewer.pickable, ...viewer.exteriors.values()].filter(root => root.visible);
      let triangles = 0, meshChecks = 0;
      const originalRaycast = THREE.Mesh.prototype.raycast;
      THREE.Mesh.prototype.raycast = function(...args) { meshChecks++; return originalRaycast.apply(this, args); };
      const original = THREE.Mesh.prototype._computeIntersections;
      THREE.Mesh.prototype._computeIntersections = function(...args) {
        triangles += (this.geometry.index?.count ?? this.geometry.attributes.position.count) / 3;
        return original.apply(this, args);
      };
      const measure = fn => {
        triangles = 0; meshChecks = 0; const start = performance.now(); const hit = fn();
        return { ms: performance.now() - start, triangles, meshChecks, uuid: hit?.object.uuid ?? null, distance: hit?.distance ?? null };
      };
      const pick = (await import('/src/building-picking.js')).createBuildingPicker();
      const raycaster = new THREE.Raycaster(), records = [];
      const samples = [];
      for (const y of [-.65, -.3, 0, .3, .65]) for (const x of [-.7, -.35, 0, .35, .7]) samples.push(new THREE.Vector2(x,y));
      for (const root of roots) {
        const center = new THREE.Box3().setFromObject(root).getCenter(new THREE.Vector3()).project(viewer.camera);
        samples.push(new THREE.Vector2(center.x, center.y));
      }
      for (const {x,y} of samples) {
        raycaster.setFromCamera(new THREE.Vector2(x, y), viewer.camera);
        const before = measure(() => raycaster.intersectObjects(roots, true)[0]);
        const after = measure(() => pick(raycaster, roots));
        records.push({ x, y, before, after });
      }
      THREE.Mesh.prototype._computeIntersections = original;
      THREE.Mesh.prototype.raycast = originalRaycast;
      return { roots: roots.length, records, scope: 'Current full campus with 30 detailed exteriors; local Chromium CPU picking, not device-independent FPS' };
    });
    await mkdir('result/web/building-picking', { recursive: true });
    await writeFile('result/web/building-picking/measurement.json', JSON.stringify(proof, null, 2) + '\n');
    const hits = proof.records.filter(r => r.before.uuid);
    expect(hits.length).toBeGreaterThan(3);
    for (const record of proof.records) {
      expect(record.after.uuid).toBe(record.before.uuid);
      if (record.before.distance !== null) expect(record.after.distance).toBeCloseTo(record.before.distance, 6);
    }
    const total = key => proof.records.reduce((sum, row) => sum + row[key].meshChecks, 0);
    expect(total('after')).toBeLessThan(total('before') * .1);
    const triangles = key => proof.records.reduce((sum, row) => sum + row[key].triangles, 0);
    expect(triangles('after')).toBeLessThan(triangles('before') * .8);
  } finally {
    await page.evaluate(() => window.viewer?.dispose()).catch(() => {});
    await server.close();
  }
});

test('picking handles inside rays, parent motion, distance limits and tied surfaces', async ({ page }) => {
  const server = await createServer({ logLevel: 'error', server: { host: '127.0.0.1', port: 0 } });
  try {
    await server.listen();
    await page.route('**/__picking-edges', route => route.fulfill({ contentType: 'text/html', body: '<!doctype html>' }));
    await page.goto(`http://127.0.0.1:${server.httpServer.address().port}/__picking-edges`);
    const result = await page.evaluate(async () => {
      const { THREE } = await import('/tests/interaction239-fixture.js');
      const { createBuildingPicker } = await import('/src/building-picking.js');
      const pick = createBuildingPicker(), parent = new THREE.Group(), roots = [];
      const material = new THREE.MeshBasicMaterial({ side: THREE.DoubleSide, transparent: true, opacity: .4 });
      for (const z of [-4, -8, -4]) {
        const root = new THREE.Group();
        root.add(new THREE.Mesh(new THREE.BoxGeometry(2, 2, 2), material));
        root.position.z = z; parent.add(root); roots.push(root);
      }
      const ray = new THREE.Raycaster(new THREE.Vector3(), new THREE.Vector3(0, 0, -1));
      const checks = [];
      const compare = name => {
        parent.updateMatrixWorld(true);
        const before = ray.intersectObjects(roots, true)[0], after = pick(ray, roots);
        checks.push({ name, same: before?.object === after?.object && before?.distance === after?.distance });
      };
      compare('overlap uses original traversal order');
      ray.near = 4; compare('near plane skips the first surface');
      ray.far = 4.5; compare('far plane rejects all surfaces');
      ray.near = 0; ray.far = Infinity; ray.ray.origin.z = -4; compare('ray starts inside a building');
      parent.position.x = 10; compare('moving parent invalidates cached bounds');
      ray.ray.origin.x = 10; compare('selection follows the moved building');
      ray.layers.set(2); compare('raycaster layers remain effective');
      return checks;
    });
    expect(result.every(check => check.same)).toBe(true);
  } finally { await server.close(); }
});
