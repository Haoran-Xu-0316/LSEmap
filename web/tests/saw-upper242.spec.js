import { test, expect } from '@playwright/test';
import { createServer } from 'vite';
import { readFile, writeFile, mkdir } from 'node:fs/promises';
import { createHash } from 'node:crypto';

const output = 'result/blender/stage242/browser';
const read = async path => JSON.parse(await readFile(path, 'utf8'));

test('SAW242 candidate winders render through the production material pipeline', async ({ page }) => {
  const html = `<!doctype html><style>body{margin:0}#stage{width:1200px;height:900px}#labels{display:none}</style>
  <div id="stage"></div><div id="labels"></div><script type="module">
  import {THREE} from '/tests/interaction239-fixture.js';
  import {CampusViewer} from '/src/viewer.js';
  import {prepareDetailedModel} from '/src/surface-materials.js';
  import {loadOutdoorEnvironment} from '/src/outdoor-environment.js';
  import {loadGroundTextures} from '/src/ground-textures.js';
  const viewer=new CampusViewer(document.querySelector('#stage'),document.querySelector('#labels'),[],()=>{},()=>{throw Error('Context lost')});
  cancelAnimationFrame(viewer.frame);viewer.transition=null;
  await Promise.all([loadOutdoorEnvironment(viewer),loadGroundTextures(viewer)]);
  viewer.camera.fov=45;viewer.updateCameraProjection();viewer.camera.position.set(-82,24,3);viewer.controls.target.set(-70,14.6,-6.4);viewer.controls.update();
  let active=null;
  window.captureCandidate=async name=>{
    if(active)viewer.scene.remove(active);
    active=(await viewer.loader.loadAsync('/__saw242/'+name+'-structure.glb')).scene;
    prepareDetailedModel(active,viewer.environmentTarget.texture,viewer.groundTextures);viewer.applyEnvironmentRotation(active);active.visible=true;viewer.scene.add(active);
    viewer.fitSunShadow(new THREE.Box3().setFromObject(active));viewer.camera.updateMatrixWorld();viewer.renderer.shadowMap.needsUpdate=true;
    viewer.renderPipeline.resetHistory();viewer.renderPipeline.render({moving:false,stabilize:false});
    return viewer.canvas.toDataURL('image/png').split(',')[1];
  };window.ready=true;window.disposeCandidate=()=>viewer.dispose();
  </script>`;
  const server = await createServer({
    logLevel: 'error', server: { host: '127.0.0.1', port: 0 },
    plugins: [{ name: 'saw242-review', configureServer(server) {
      server.middlewares.use('/__saw242-review', (_, response) => {
        response.setHeader('Content-Type', 'text/html'); response.end(html);
      });
      server.middlewares.use('/__saw242', async (request, response) => {
        const name = request.url === '/before-structure.glb' ? 'before' : request.url === '/after-structure.glb' ? 'after' : null;
        if (!name) { response.statusCode = 404; response.end(); return; }
        response.setHeader('Content-Type', 'model/gltf-binary');
        response.end(await readFile(`result/blender/saw-circulation242/${name}-structure.glb`));
      });
    } }],
  });
  try {
    await server.listen(); await page.setViewportSize({ width: 1200, height: 900 });
    const errors = []; page.on('pageerror', error => errors.push(error.message));
    await page.goto(`http://127.0.0.1:${server.httpServer.address().port}/__saw242-review`);
    await page.waitForFunction(() => window.ready);
    await mkdir(output, { recursive: true });
    const hashes = [];
    for (const name of ['before', 'after']) {
      const data = await page.evaluate(name => window.captureCandidate(name), name);
      const bytes = Buffer.from(data, 'base64'); expect(bytes.length).toBeGreaterThan(10000);
      hashes.push(createHash('sha256').update(bytes).digest('hex'));
      await writeFile(`${output}/saw-${name}.png`, bytes);
    }
    expect(hashes[0]).not.toBe(hashes[1]); expect(errors).toEqual([]);
    await page.evaluate(() => window.disposeCandidate());
  } finally { await server.close(); }
});

test('SAW242 public-assembly camera studies use actual section clipping', async ({ page }) => {
  const jobs = [
    { name: '3-low-west', min: 10.9, max: 15.2, position: [-76.2, 13, -4.5], target: [-71.8, 12.5, -6.5], fov: 70 },
    { name: '3-low-curve', min: 10.9, max: 15.2, position: [-74.8, 12.9, -2.5], target: [-71.5, 12.5, -6.5], fov: 70 },
    { name: '3-low-front', min: 10.9, max: 15.2, position: [-72.5, 12.8, -1.5], target: [-71.2, 12.5, -6.6], fov: 65 },
    { name: '4-curve', min: 13.9, max: 19.1, position: [-72.5, 17.2, -3.8], target: [-70.8, 16, -6.6], fov: 70 },
    { name: '4-wide', min: 13.9, max: 19.1, position: [-73.2, 17, -3], target: [-70.8, 16, -6.6], fov: 65 },
    { name: '4-low', min: 13.9, max: 19.1, position: [-74, 16.3, -2.5], target: [-70.8, 16, -6.6], fov: 65 },
  ];
  const html = `<!doctype html><style>body{margin:0}#stage{width:1200px;height:900px}#labels{display:none}</style>
  <div id="stage"></div><div id="labels"></div><script type="module">
  import {THREE} from '/tests/interaction239-fixture.js';
  import {CampusViewer} from '/src/viewer.js';
  import {prepareDetailedModel} from '/src/surface-materials.js';
  import {loadOutdoorEnvironment} from '/src/outdoor-environment.js';
  import {loadGroundTextures} from '/src/ground-textures.js';
  import {applyInteriorLighting} from '/src/interior-lighting.js';
  const viewer=new CampusViewer(document.querySelector('#stage'),document.querySelector('#labels'),[],()=>{},()=>{throw Error('Context lost')});
  cancelAnimationFrame(viewer.frame);viewer.transition=null;viewer.mode='interior';
  await Promise.all([loadOutdoorEnvironment(viewer),loadGroundTextures(viewer)]);
  const group=(await viewer.loader.loadAsync('/__saw242-public.glb')).scene;
  prepareDetailedModel(group,viewer.environmentTarget.texture,viewer.groundTextures);viewer.applyEnvironmentRotation(group);group.visible=true;viewer.scene.add(group);
  viewer.interiors.set('SAW:default',group);
  const bounds=new THREE.Box3().setFromObject(group);viewer.fitSunShadow(bounds);applyInteriorLighting(viewer,true,bounds);viewer.renderer.shadowMap.enabled=false;
  window.captureSection=job=>{
    viewer.applyInteriorDisplayGroups(['public','floors',job.name.startsWith('3-')?'stair-3-4':'stair-4-5']);
    viewer.renderer.clippingPlanes=[new THREE.Plane(new THREE.Vector3(0,1,0),-job.min),new THREE.Plane(new THREE.Vector3(0,-1,0),job.max)];
    viewer.camera.fov=job.fov;viewer.updateCameraProjection();viewer.moveCamera(new THREE.Vector3(...job.position),new THREE.Vector3(...job.target),false);
    viewer.transition=null;viewer.controls.update();viewer.camera.updateMatrixWorld();viewer.renderPipeline.resetHistory();viewer.renderPipeline.render({moving:false,stabilize:false});
    return viewer.canvas.toDataURL('image/png').split(',')[1];
  };window.ready=true;window.disposeCandidate=()=>viewer.dispose();
  </script>`;
  const server = await createServer({
    logLevel: 'error', server: { host: '127.0.0.1', port: 0 },
    plugins: [{ name: 'saw242-public-review', configureServer(server) {
      server.middlewares.use('/__saw242-public.glb', async (_, response) => {
        response.setHeader('Content-Type', 'model/gltf-binary');
        response.end(await readFile('result/blender/saw-circulation242/after-public.glb'));
      });
      server.middlewares.use('/__saw242-public-review', (_, response) => {
        response.setHeader('Content-Type', 'text/html'); response.end(html);
      });
    } }],
  });
  try {
    await server.listen(); await page.setViewportSize({ width: 1200, height: 900 });
    const errors = []; page.on('pageerror', error => errors.push(error.message));
    await page.goto(`http://127.0.0.1:${server.httpServer.address().port}/__saw242-public-review`);
    await page.waitForFunction(() => window.ready);
    await mkdir(output, { recursive: true });
    for (const job of jobs) {
      const data = await page.evaluate(job => window.captureSection(job), job);
      const bytes = Buffer.from(data, 'base64'); expect(bytes.length).toBeGreaterThan(10000);
      await writeFile(`${output}/saw-section-${job.name}.png`, bytes);
    }
    expect(errors).toEqual([]); await page.evaluate(() => window.disposeCandidate());
  } finally { await server.close(); }
});
