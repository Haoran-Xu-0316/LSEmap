import { test, expect } from '@playwright/test';
import { createServer } from 'vite';
import { createHash } from 'node:crypto';
import { readFile, mkdir, writeFile } from 'node:fs/promises';

const proofDirectory = 'result/blender/stage241';
const read = async path => JSON.parse(await readFile(path, 'utf8'));

// Render the isolated candidate through the production lighting/material pipeline.
// This private page never enters the public build.
test('CLM241 candidate inscription follows the stone without changing its finish', async ({ page }) => {
  const html = `<!doctype html><style>body{margin:0}#stage{width:1200px;height:900px}#labels{display:none}</style>
  <div id="stage"></div><div id="labels"></div><script type="module">
  import {THREE} from '/tests/interaction239-fixture.js';
  import {CampusViewer} from '/src/viewer.js';
  import {loadOutdoorEnvironment} from '/src/outdoor-environment.js';
  import {loadGroundTextures} from '/src/ground-textures.js';
  import {prepareDetailedModel} from '/src/surface-materials.js';
  const catalogue=await(await fetch('/models/catalogue.json')).json();
  const building=catalogue.buildings.find(b=>b.code==='CLM');
  const viewer=new CampusViewer(document.querySelector('#stage'),document.querySelector('#labels'),[],()=>{},()=>{throw Error('Context lost')});
  cancelAnimationFrame(viewer.frame);viewer.transition=null;await Promise.all([loadOutdoorEnvironment(viewer),loadGroundTextures(viewer)]);
  viewer.camera.fov=35;viewer.updateCameraProjection();
  viewer.camera.position.set(112.5,9.1,166);viewer.controls.target.set(114.02,8.47,154.14);viewer.controls.update();
  viewer.fitSunShadow(new THREE.Box3(new THREE.Vector3(...building.bounds.min),new THREE.Vector3(...building.bounds.max)));let active=null;
  window.captureCandidate=async name=>{
    if(active){viewer.scene.remove(active);}
    const gltf=await viewer.loader.loadAsync('/__candidate/'+name+'.glb');active=gltf.scene;
    prepareDetailedModel(active,viewer.environmentTarget.texture,viewer.groundTextures);viewer.applyEnvironmentRotation(active);viewer.scene.add(active);active.visible=true;
    viewer.camera.updateMatrixWorld();viewer.renderer.shadowMap.needsUpdate=true;
    viewer.renderPipeline.resetHistory();viewer.renderPipeline.render({moving:false,stabilize:false});
    return viewer.canvas.toDataURL('image/png').split(',')[1];
  };
  window.ready=true;window.disposeCandidate=()=>viewer.dispose();
  </script>`;
  const server = await createServer({
    logLevel: 'error', server: { host: '127.0.0.1', port: 0 },
    plugins: [{ name: 'clm241-review', configureServer(server) {
      server.middlewares.use('/__review241', (_, response) => {
        response.setHeader('Content-Type', 'text/html'); response.end(html);
      });
      server.middlewares.use('/__candidate', async (request, response) => {
        const name = request.url === '/before.glb' ? 'before' : request.url === '/after.glb' ? 'after' : null;
        if (!name) { response.statusCode = 404; response.end(); return; }
        response.setHeader('Content-Type', 'model/gltf-binary');
        response.end(await readFile(`result/blender/clm-inscription241/${name}.glb`));
      });
    } }],
  });
  try {
    await server.listen();
    const errors = []; page.on('pageerror', error => errors.push(error.message));
    await page.setViewportSize({ width: 1200, height: 900 });
    await page.goto(`http://127.0.0.1:${server.httpServer.address().port}/__review241`);
    await page.waitForFunction(() => window.ready);
    await mkdir(`${proofDirectory}/browser`, { recursive: true });
    const captures = [];
    for (const name of ['before', 'after']) {
      const image = await page.evaluate(name => window.captureCandidate(name), name);
      const bytes = Buffer.from(image, 'base64'); captures.push(createHash('sha256').update(bytes).digest('hex'));
      expect(bytes.length).toBeGreaterThan(10000);
      await writeFile(`${proofDirectory}/browser/clm-${name}.png`, bytes);
    }
    expect(captures[0]).not.toBe(captures[1]);
    expect(errors).toEqual([]);
    await page.evaluate(() => window.disposeCandidate());
  } finally { await server.close(); }
});

test('CLM241 release preserves every other exterior, interior and room', async () => {
  const before = await read(`${proofDirectory}/catalogue-before.json`);
  const current = await read('dist/models/catalogue.json');
  const native = await read(`${proofDirectory}/native-verification.json`);
  expect(current.version).toBe('241');
  expect(native.originalObjectsVerified).toBe(8606);
  expect(native.protectedRooms).toBe(35);
  expect(native.protectedRoomMembers).toBe(1485);
  expect(native.contact.minimumClearance).toBeGreaterThan(.0008);
  expect(native.contact.maximumClearance).toBeLessThan(.01305);
  let exteriors = 0, interiors = 0, rooms = 0;
  for (const old of before.buildings) {
    const building = current.buildings.find(row => row.code === old.code);
    if (old.detailedExterior) {
      exteriors++;
      if (old.code === 'CLM') {
        expect(building.detailedExterior.sha256).not.toBe(old.detailedExterior.sha256);
        expect(building.detailedExterior.bytes - old.detailedExterior.bytes).toBeLessThan(25000);
        expect(building.detailedExterior.bounds).toEqual(old.detailedExterior.bounds);
      } else expect(building.detailedExterior.sha256, old.code).toBe(old.detailedExterior.sha256);
    }
    if (old.detailedInterior) {
      interiors++;
      expect(building.detailedInterior.sha256, old.code).toBe(old.detailedInterior.sha256);
    }
    for (const room of old.interiorSpaces || []) {
      rooms++;
      expect(building.interiorSpaces.find(row => row.id === room.id).detailedInterior.sha256, room.id).toBe(room.detailedInterior.sha256);
    }
  }
  expect([exteriors, interiors, rooms]).toEqual([30, 25, 35]);
  const gallery = await read('dist/gallery-manifest.json');
  expect(gallery.images).toHaveLength(195);
  expect(gallery.images.every(image => image.sourceModelSha256 === current.sourceModelSha256 && image.sceneSamples === 4)).toBe(true);
});

for (const width of [1440, 390]) {
  test(`CLM241 exterior and retained room load at ${width}px`, async ({ page }) => {
    test.setTimeout(120000);
    await page.setViewportSize({ width, height: width === 390 ? 844 : 1000 });
    await page.emulateMedia({ reducedMotion: 'reduce' });
    const errors = []; page.on('pageerror', error => errors.push(error.message));
    await page.goto('/#CLM');
    await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready', 'exterior-CLM', { timeout: 60000 });
    await page.locator('#detail-view').click();
    await expect(page.locator('#view-mode')).toHaveText('校名题字');
    await page.screenshot({ path: `${proofDirectory}/browser/clm-${width}.png` });
    await page.locator('#interior-view').click();
    await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready', 'interior-CLM', { timeout: 60000 });
    await expect(page.locator('#fallback')).toBeHidden();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    expect(errors).toEqual([]);
  });
}

test('CLM241 overview and selected exterior retain identical inscription geometry', async ({ page }) => {
  test.setTimeout(120000);
  const release = await read('dist/release.json');
  const audit = await read('result/blender/clm-inscription241/audit.json');
  const viewerModule = Object.keys(release.assets).find(path => /^\/assets\/viewer-.*\.js$/.test(path));
  const html = `<!doctype html><style>body{margin:0}#stage{width:1200px;height:900px}#labels{display:none}</style>
  <div id="stage"></div><div id="labels"></div><script type="module">
  import {CampusViewer} from '${viewerModule}';
  const catalogue=await(await fetch('/models/catalogue.json')).json();
  const viewer=new CampusViewer(document.querySelector('#stage'),document.querySelector('#labels'),catalogue.buildings,()=>{},()=>{throw Error('Context lost')},()=>{},catalogue.sourceModelSha256);
  const collect=group=>{
    viewer.scene.updateMatrixWorld(true);const points=[];let triangles=0;
    group.traverse(object=>{
      if(!object.geometry || Array.isArray(object.material) || !object.material.name.includes('sign_letters'))return;
      const geometry=object.geometry,position=geometry.attributes.position,index=geometry.index,count=index?index.count:position.count;
      for(let i=0;i<count;i+=3){
        const triangle=[];
        for(let k=0;k<3;k++)triangle.push(viewer.camera.position.clone().fromBufferAttribute(position,index?index.getX(i+k):i+k).applyMatrix4(object.matrixWorld).toArray());
        if(triangle.every(point=>point[0]>110&&point[0]<118&&point[1]>8.37&&point[1]<8.57&&point[2]>151&&point[2]<155.5)){points.push(...triangle);triangles++;}
      }
    });return {points,triangles};
  };
  await viewer.load();await viewer.environmentReady;
  const overview=collect(viewer.groups.get('CLM'));
  const building=catalogue.buildings.find(row=>row.code==='CLM');viewer.select(building);await viewer.upgradeModel(building,'exterior');
  const selected=collect(viewer.activeDetail.group);viewer.dispose();window.parity={overview,selected};
  </script>`;
  await page.route('**/__clm241-parity', route => route.fulfill({ contentType: 'text/html', body: html }));
  await page.goto('/__clm241-parity');
  await page.waitForFunction(() => window.parity, null, { timeout: 60000 });
  const result = await page.evaluate(() => window.parity);
  expect(result.overview.triangles).toBe(audit.triangles);
  expect(result.selected.triangles).toBe(result.overview.triangles);
  const maximumDistance = (from, to) => {
    const cells = new Map(), cache = new Map(), cellSize = .0001;
    const key = point => point.map(value => Math.floor(value / cellSize));
    for (const point of to) {
      const cell = key(point).join(',');
      if (!cells.has(cell)) cells.set(cell, []);
      cells.get(cell).push(point);
    }
    let maximum = 0;
    for (const point of from) {
      const exact = point.join(',');
      if (cache.has(exact)) { maximum = Math.max(maximum, cache.get(exact)); continue; }
      const [x, y, z] = key(point); let nearest = Infinity;
      for (let a = -1; a <= 1; a++) for (let b = -1; b <= 1; b++) for (let c = -1; c <= 1; c++) {
        for (const other of cells.get([x + a, y + b, z + c].join(',')) || []) {
          nearest = Math.min(nearest, Math.hypot(...point.map((value, i) => value - other[i])));
        }
      }
      cache.set(exact, nearest); maximum = Math.max(maximum, nearest);
    }
    return maximum;
  };
  const error = Math.max(maximumDistance(result.overview.points, result.selected.points), maximumDistance(result.selected.points, result.overview.points));
  expect(error).toBeLessThan(.0001);
  await writeFile(`${proofDirectory}/overview-detail-parity.json`, JSON.stringify({
    actualProductionGlbs: true, triangles: result.overview.triangles,
    maximumWorldPositionDifferenceM: error, comparison: 'Bidirectional nearest positions independent of Draco ordering',
  }, null, 2) + '\n');
});
