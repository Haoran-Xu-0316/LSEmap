import { test, expect } from '@playwright/test';
import * as THREE from 'three';
import { createServer } from 'vite';
import { readFile, writeFile, mkdir } from 'node:fs/promises';
import { LocalSceneContext } from '../src/scene-context.js';

const output = 'result/web/scene-context263';
const bounds = new THREE.Box3(new THREE.Vector3(-2, 0, -2), new THREE.Vector3(2, 8, 2));

test('local crops interpolate ground attributes, retain whole trees, cancel stale work and own only copied geometry', async () => {
  const source = new THREE.Group();
  const ground = new THREE.Mesh(new THREE.PlaneGeometry(1000, 1000), new THREE.MeshStandardMaterial({ name: 'Road asphalt', side: THREE.DoubleSide }));
  ground.rotation.x = -Math.PI / 2; source.add(ground);
  const underground = new THREE.Mesh(new THREE.BoxGeometry(20, 2, 20), new THREE.MeshStandardMaterial({ name: 'underground service' }));
  underground.position.y = -2; source.add(underground);
  const pavilion = new THREE.Mesh(new THREE.BoxGeometry(4, 1, 4), new THREE.MeshStandardMaterial({ name: 'PARK233_estimated_roof_tiles' }));
  pavilion.position.y = 4; source.add(pavilion);
  const trunks = [], crowns = [];
  for (const x of [13.5, 16.5]) {
    const trunk = new THREE.Mesh(new THREE.CylinderGeometry(.15, .2, 3, 8), new THREE.MeshStandardMaterial({ name: 'Oak public interior' }));
    trunk.position.set(x, 1.5, 0); source.add(trunk); trunks.push(trunk);
    const crown = new THREE.Mesh(new THREE.SphereGeometry(2, 10, 8), new THREE.MeshStandardMaterial({ name: 'foliage' }));
    crown.position.set(x, 4, 0); source.add(crown); crowns.push(crown);
  }
  source.updateMatrixWorld(true);
  const context = new LocalSceneContext([source]);
  const stale = context.activate('stale', bounds);
  const selected = context.activate('selected', bounds);
  expect(await stale).toBeNull();
  const group = await selected;
  expect(context.activeGroup).toBe(group);
  expect(group.children.some(mesh => mesh.material === underground.material || mesh.material === pavilion.material)).toBe(false);
  const floor = group.children.find(mesh => mesh.material === ground.material);
  const box = floor.geometry.boundingBox;
  expect(box.min.x).toBeGreaterThanOrEqual(-14.00001); expect(box.max.x).toBeLessThanOrEqual(14.00001);
  expect(box.min.z).toBeGreaterThanOrEqual(-14.00001); expect(box.max.z).toBeLessThanOrEqual(14.00001);
  const ray = new THREE.Raycaster(new THREE.Vector3(7, 10, -9), new THREE.Vector3(0, -1, 0));
  const before = ray.intersectObject(ground)[0], after = ray.intersectObject(floor)[0];
  expect(after.point.distanceTo(before.point)).toBeLessThan(1e-5);
  expect(after.uv.distanceTo(before.uv)).toBeLessThan(1e-6);
  const normal = new THREE.Vector3().fromBufferAttribute(floor.geometry.attributes.normal, 0);
  expect(normal.distanceTo(new THREE.Vector3(0, 1, 0))).toBeLessThan(1e-6);
  const localCrown = group.children.find(mesh => mesh.material === crowns[0].material);
  expect(localCrown.geometry.index.count).toBe(crowns[0].geometry.index.count);
  expect(localCrown.geometry.boundingBox.max.x).toBeGreaterThan(14);
  expect(group.children.some(mesh => mesh.material === crowns[1].material)).toBe(false);
  let sourceGeometryDisposed = 0, sourceMaterialDisposed = 0, copiedGeometryDisposed = 0;
  source.traverse(object => { object.geometry?.addEventListener('dispose', () => sourceGeometryDisposed++); object.material?.addEventListener('dispose', () => sourceMaterialDisposed++); });
  floor.geometry.addEventListener('dispose', () => copiedGeometryDisposed++);
  for (const code of ['second', 'third', 'fourth']) await context.activate(code, bounds);
  expect(context.cache.size).toBe(3); expect(context.cache.has('selected')).toBe(false);
  expect(copiedGeometryDisposed).toBe(1);
  const pending = context.activate('cancel-on-dispose', bounds);
  context.dispose(); expect(await pending).toBeNull();
  expect(context.cache.size).toBe(0); expect(context.root.children).toHaveLength(0);
  expect(sourceGeometryDisposed).toBe(0); expect(sourceMaterialDisposed).toBe(0);
  source.traverse(object => { object.geometry?.dispose(); object.material?.dispose(); });
});

test('indexed furniture stays whole across UV and hard-normal seams without changing its attributes', async () => {
  const source = new THREE.Group();
  // BoxGeometry is indexed, but each face has its own vertices for UVs and normals.
  // The right face lies outside the crop while the complete object's centre is inside.
  const furniture = new THREE.Mesh(new THREE.BoxGeometry(4, 2, 2), new THREE.MeshStandardMaterial({ name: 'Street furniture' }));
  furniture.position.set(13.5, 1, 0); source.add(furniture); source.updateMatrixWorld(true);
  const context = new LocalSceneContext([source]);
  try {
    const group = await context.activate('indexed-seams', bounds);
    const copy = group.children.find(mesh => mesh.material === furniture.material);
    expect(copy.geometry.index.count).toBe(furniture.geometry.index.count);
    const triangleAttributes = geometry => Array.from(geometry.index.array, index => {
      const position = new THREE.Vector3().fromBufferAttribute(geometry.attributes.position, index);
      if (geometry === furniture.geometry) position.applyMatrix4(furniture.matrixWorld);
      return [...position.toArray(), ...Array.from({ length: 3 }, (_, c) => geometry.attributes.normal.getComponent(index, c)),
        ...Array.from({ length: 2 }, (_, c) => geometry.attributes.uv.getComponent(index, c))].map(n => n.toFixed(6)).join(',');
    }).sort();
    expect(triangleAttributes(copy.geometry)).toEqual(triangleAttributes(furniture.geometry));
    expect(copy.geometry.boundingBox.max.x).toBe(15.5);
  } finally { context.dispose(); furniture.geometry.dispose(); furniture.material.dispose(); }
});

test('SAW retains nearby public street context while camera response, overview, room views and surface zoom stay coherent', async ({ browser }) => {
  test.setTimeout(150000);
  await mkdir(output, { recursive: true });
  const server = await createServer({
    server: { host: '127.0.0.1', port: 0 }, logLevel: 'error',
    plugins: [{ name: 'scene-context263', enforce: 'pre',
      async load(id) { if (id.endsWith('/src/viewer.js?baseline263')) return readFile(`${output}/before-viewer.js`, 'utf8'); },
      configureServer(server) { server.middlewares.use('/__context263', (request, response) => {
        const suffix = request.url.includes('baseline') ? '?baseline263' : '';
        response.setHeader('Content-Type', 'text/html'); response.end(`<!doctype html><link rel="icon" href="data:,"><style>body{margin:0}#stage{width:1000px;height:800px}#labels{display:none}</style><div id="stage"></div><div id="labels"></div><script type="module">
          import * as THREE from '/@fs/${process.cwd()}/node_modules/three/build/three.module.js';
          import {CampusViewer} from '/src/viewer.js${suffix}';
          const c=await(await fetch('/models/catalogue.json')).json();
          const v=new CampusViewer(document.querySelector('#stage'),document.querySelector('#labels'),c.buildings,()=>{},()=>{throw Error('Context lost')},()=>{},c.sourceModelSha256);
          window.viewer=v;window.THREE=THREE;window.catalogue=c;v.loadCampusExteriors=async()=>{};await v.load();await v.environmentReady;
          await v.loadExterior(c.buildings.find(b=>b.code==='SAW'));cancelAnimationFrame(v.frame);v.controls.enableDamping=false;window.ready=true;
        </script>`);
      }); },
    }],
  });
  await server.listen();
  const records = {}, errors = [];
  try {
    for (const mode of ['baseline', 'candidate']) {
      const page = await browser.newPage({ viewport: { width: 1000, height: 800 } });
      page.on('pageerror', error => errors.push(error.message));
      page.on('console', message => { if (message.type() === 'error') errors.push(message.text()); });
      try {
        await page.goto(`http://127.0.0.1:${server.httpServer.address().port}/__context263?${mode}`);
        await page.waitForFunction(() => window.ready, null, { timeout: 90000 });
        records[mode] = await page.evaluate(async () => {
          const v = viewer, b = catalogue.buildings.find(b => b.code === 'SAW');
          const cameraBefore = v.camera.position.clone();
          const started = performance.now(); v.select(b); const synchronousSelectMs = performance.now() - started;
          v.frame = requestAnimationFrame(v.tick);
          await new Promise(requestAnimationFrame);
          const cameraRespondedBeforeContext = !v.camera.position.equals(cameraBefore) && !v.localContext?.activeGroup;
          await v.localContext?.ready;
          await v.upgradeModel(b, 'exterior'); cancelAnimationFrame(v.frame);
          if (v.transition) v.moveCamera(v.transition.position, v.transition.target, false);
          v.controls.update(); v.camera.updateMatrixWorld();
          for (let i = 0; i < 4; i++) v.renderPipeline.render({ moving: false, progressive: true, restart: i === 0 });
          const local = v.localContext?.activeGroup;
          const effective = object => { for (let p = object; p; p = p.parent) if (!p.visible) return false; return true; };
          const count = roots => { let meshes = 0, triangles = 0; for (const root of roots.filter(Boolean)) root.traverse(object => { if (object.isMesh && effective(object)) { meshes++; triangles += (object.geometry.index?.count ?? object.geometry.attributes.position.count) / 3; } }); return { meshes, triangles }; };
          const isolated = { local: local?.userData.streetContext ?? null, originals: ['SITE', 'LANDSCAPE', 'CONTEXT'].map(code => ({ code, visible: v.groups.get(code).visible })), public: count([local]), otherBuildings: [...v.groups].filter(([code, group]) => !['SAW', 'SITE', 'LANDSCAPE', 'CONTEXT'].includes(code) && group.visible).map(([code]) => code) };
          const ray = new THREE.Raycaster(new THREE.Vector3(-45.12255, 30, -9.88738), new THREE.Vector3(0, -1, 0));
          const originalTree = ray.intersectObject(v.groups.get('LANDSCAPE'), true)[0];
          const localTree = local ? ray.intersectObject(local, true)[0] : null;
          let surfaceZoom = null;
          if (local) for (const [x, z] of [[-39, -7], [-40, 0], [-42, 6], [-43, 14]]) {
            ray.set(new THREE.Vector3(x, 1, z), new THREE.Vector3(0, -1, 0));
            const ground = ray.intersectObject(local, true).find(hit => /yorkstone|paving|asphalt|slab/.test(hit.object.material.name));
            if (!ground) continue;
            const screen = ground.point.clone().project(v.camera), rect = v.canvas.getBoundingClientRect();
            const hit = v.surfaceAt({ clientX: rect.left + (screen.x + 1) * rect.width / 2, clientY: rect.top + (1 - screen.y) * rect.height / 2 });
            if (hit && /yorkstone|paving|asphalt|slab/.test(hit.object.material.name)) { surfaceZoom = { material: hit.object.material.name, difference: hit.point.distanceTo(ground.point) }; break; }
          }
          return { camera: { position: v.camera.position.toArray().map(n => Number(n.toFixed(8))), target: v.controls.target.toArray().map(n => Number(n.toFixed(8))), fov: v.camera.fov }, synchronousSelectMs, cameraRespondedBeforeContext, isolated, tree: { originalY: originalTree.point.y, localY: localTree?.point.y ?? null }, surfaceZoom, code: b.code, sourceModelSha256: catalogue.sourceModelSha256 };
        });
        await page.locator('canvas').screenshot({ path: `${output}/${mode}-saw.png` });
        await page.evaluate(() => { const v=viewer;v.camera.fov=48;v.updateCameraProjection();v.moveCamera(new THREE.Vector3(-39,3,3),new THREE.Vector3(-49,1.8,-10),false);v.camera.updateMatrixWorld();for(let i=0;i<4;i++)v.renderPipeline.render({moving:false,progressive:true,restart:i===0}); });
        await page.locator('canvas').screenshot({ path: `${output}/${mode}-street.png` });
        if (mode === 'candidate') records[mode].lifecycle = await page.evaluate(async () => {
          const v = viewer, b = catalogue.buildings.find(b => b.code === 'SAW'), cached = v.localContext.activeGroup;
          const selectedBounds = new THREE.Box3(new THREE.Vector3(...b.bounds.min), new THREE.Vector3(...b.bounds.max));
          const pending = v.localContext.activate('discarded', selectedBounds);
          await new Promise(requestAnimationFrame); await new Promise(requestAnimationFrame);
          const partial = v.localContext.pending?.job.group;
          let disposedCopies = 0, disposedMaterials = 0;
          const partialMeshes = partial?.children.length ?? 0;
          partial?.traverse(object => { object.geometry?.addEventListener('dispose', () => disposedCopies++); object.material?.addEventListener('dispose', () => disposedMaterials++); });
          v.toggleContext(true); const cancelled = await pending;
          const cancellation = { returnedNull: cancelled === null, partialMeshes, disposedCopies, disposedMaterials, cached: v.localContext.cache.has('discarded') };
          const full = { localVisible: v.localContext.root.visible, siteVisible: v.groups.get('SITE').visible, landscapeVisible: v.groups.get('LANDSCAPE').visible, contextVisible: v.groups.get('CONTEXT').visible };
          v.toggleContext(false); await v.localContext.ready; const reused = v.localContext.activeGroup === cached;
          await v.showInterior(b); await v.upgradeModel(b, 'interior');
          const interior = { localVisible: v.localContext.root.visible, campusVisible: v.campus.visible, mode: v.mode };
          v.select(b); await v.localContext.ready; await v.upgradeModel(b, 'exterior');
          const returned = v.localContext.activeGroup === cached;
          v.home(false); const overview = { localVisible: v.localContext.root.visible, siteVisible: v.groups.get('SITE').visible, landscapeVisible: v.groups.get('LANDSCAPE').visible };
          v.dispose(); return { cancellation, full, reused, interior, returned, overview, cacheDisposed: v.localContext.cache.size === 0 && v.localContext.root.children.length === 0 };
        });
      } finally { await page.evaluate(() => window.viewer?.disposed || window.viewer?.dispose()).catch(() => {}); await page.close(); }
    }
    await writeFile(`${output}/verification.json`, JSON.stringify({ records, errors }, null, 2) + '\n');
    expect(errors).toEqual([]);
    const p = records.candidate;
    expect(p.sourceModelSha256).toBe(records.baseline.sourceModelSha256);
    expect(p.camera).toEqual(records.baseline.camera);
    expect(records.baseline.tree.localY).toBeNull();
    expect(p.tree.localY).toBeCloseTo(p.tree.originalY, 5);
    expect(p.isolated.otherBuildings).toEqual([]);
    expect(p.isolated.originals.every(row => !row.visible)).toBe(true);
    expect(p.isolated.public.triangles).toBeLessThan(100000);
    expect(p.synchronousSelectMs).toBeLessThan(20);
    expect(p.cameraRespondedBeforeContext).toBe(true);
    expect(p.isolated.local.maxBlockMs).toBeLessThan(20);
    expect(p.isolated.local.yields).toBeGreaterThan(1);
    expect(p.surfaceZoom?.difference).toBeLessThan(.001);
    expect(p.lifecycle.cancellation.returnedNull).toBe(true);
    expect(p.lifecycle.cancellation.partialMeshes).toBeGreaterThan(0);
    expect(p.lifecycle.cancellation.disposedCopies).toBe(p.lifecycle.cancellation.partialMeshes);
    expect(p.lifecycle.cancellation.disposedMaterials).toBe(0);
    expect(p.lifecycle.cancellation.cached).toBe(false);
    expect(p.lifecycle.full).toEqual({ localVisible: false, siteVisible: true, landscapeVisible: true, contextVisible: true });
    expect(p.lifecycle.interior).toEqual({ localVisible: false, campusVisible: false, mode: 'interior' });
    expect(p.lifecycle.overview).toEqual({ localVisible: false, siteVisible: true, landscapeVisible: true });
    expect(p.lifecycle.reused && p.lifecycle.returned && p.lifecycle.cacheDisposed).toBe(true);
  } finally { await server.close(); }
});
