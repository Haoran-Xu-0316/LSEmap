import {test, expect} from '@playwright/test';
import {readFile, writeFile} from 'node:fs/promises';

const folder = 'result/blender/lrb259';
const read = async path => JSON.parse(await readFile(path, 'utf8'));
const glbDocument = bytes => JSON.parse(bytes.subarray(20, 20 + bytes.readUInt32LE(12)).toString());
const sourceSha = 'b304b1fe4f519a6aafd3df15dcf9235ca25a99f3bd699e99a14beaab410c7e8e';
const glassMaterials = document => (document.materials ?? [])
  .filter(material => material.extras?.webSurfaceRole === 'glazing')
  .sort((a, b) => a.name.localeCompare(b.name));

// Real rays through the former blue strip in the accepted258 gallery camera.
// These previously hit LGcarpet at nativeZ−3.668 after a transparent shadow plane.
const galleryRays = [
  {pixel: [.3, .715], direction: [.380945362620097, -.5966293327618338, -.7063384953309648]},
  {pixel: [.4, .725], direction: [.4470622616454949, -.60836806203524, -.6557618739358834]},
  {pixel: [.5, .725], direction: [.5134443038053168, -.6105652789318928, -.6029800884379959]},
  {pixel: [.7, .725], direction: [.6338707266210653, -.6019160605170342, -.4857004818038961]},
].map(ray => ({...ray, origin: [-33.51981501499165, 98.16655566423654, 104.6018146627701]}));

async function prepareViewer(page) {
  const release = await read('dist/release.json');
  const viewerModule = Object.keys(release.assets).find(path => /^\/assets\/viewer-.*\.js$/.test(path));
  expect(viewerModule).toBeTruthy();
  const html = `<!doctype html><link rel="icon" href="data:,"><style>body{margin:0}#stage{width:1000px;height:800px}#labels{display:none}</style><div id="stage"></div><div id="labels"></div><script type="module">
    import {CampusViewer} from '${viewerModule}';
    const catalogue=await(await fetch('/models/catalogue.json')).json();
    if(catalogue.version!=='259'||catalogue.sourceModelSha256!=='${sourceSha}')throw Error('Wrong production model');
    const viewer=new CampusViewer(document.querySelector('#stage'),document.querySelector('#labels'),catalogue.buildings,()=>{},()=>{throw Error('Context lost')},()=>{},catalogue.sourceModelSha256);
    window.viewer=viewer;viewer.loadCampusExteriors=async()=>{};
    await viewer.load();await viewer.environmentReady;
    const lrb=catalogue.buildings.find(building=>building.code==='LRB');
    await viewer.loadExterior(lrb);
    await viewer.loadInterior(lrb,null,{interiorAsset:lrb.detailedInterior});
    await viewer.loadInterior(lrb,'fallback259',{interiorAsset:'/models/lrb-interior.glb'});
    window.ready=true;
  </script>`;
  await page.route('**/__library_basement259', route => route.fulfill({contentType: 'text/html', body: html}));
  await page.goto('/__library_basement259');
  await page.waitForFunction(() => window.ready, null, {timeout: 60000});
}

test('LRB production exteriors remove leaked LGcarpet while both public interiors retain it', async ({page}) => {
  const catalogue = await read('dist/models/catalogue.json');
  expect(catalogue.version).toBe('259');
  expect(catalogue.sourceModelSha256).toBe(sourceSha);
  const lrb = catalogue.buildings.find(building => building.code === 'LRB');
  const previous = glbDocument(await readFile('result/blender/stage259/lrb-detailedExterior.glb'));
  const latest = glbDocument(await readFile('dist' + lrb.detailedExterior.url));
  const oldGlass = glassMaterials(previous);
  expect(oldGlass.length).toBeGreaterThan(0);
  expect(glassMaterials(latest)).toEqual(oldGlass);
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  try {
    await prepareViewer(page);
    const result = await page.evaluate(galleryRays => {
      const viewer = window.viewer;
      const vector = array => viewer.controls.target.clone().fromArray(array);
      const finish = (mesh, index) => Array.isArray(mesh.material) ? mesh.material[index] : mesh.material;
      const blue = material => material?.name.endsWith('ATRIA_blue_carpet');
      const roots = [
        ['overview-exterior', viewer.groups.get('LRB'), false],
        ['detailed-exterior', viewer.exteriors.get('LRB'), false],
        ['default-interior', viewer.interiors.get('LRB:default'), true],
        ['fallback-interior', viewer.interiors.get('LRB:fallback259'), true],
      ];
      viewer.scene.updateMatrixWorld(true);
      const rows = [];
      for (const [mode, root, interior] of roots) {
        if (!root) throw Error('Missing exported root: ' + mode);
        const levels = new Set();
        const materials = new Set();
        let minimum = Infinity;
        let vertexReferences = 0;
        root.traverse(mesh => {
          if (!mesh.isMesh) return;
          const geometry = mesh.geometry;
          const positions = geometry.getAttribute('position');
          const index = geometry.getIndex();
          const groups = geometry.groups.length ? geometry.groups : [{start: 0, count: index?.count ?? positions.count, materialIndex: 0}];
          for (const group of groups) {
            const material = finish(mesh, group.materialIndex);
            if (!blue(material)) continue;
            materials.add(material.name);
            for (let offset = group.start; offset < group.start + group.count; offset++) {
              const point = viewer.controls.target.clone().fromBufferAttribute(positions, index ? index.getX(offset) : offset).applyMatrix4(mesh.matrixWorld);
              minimum = Math.min(minimum, point.y);
              levels.add(Math.round(point.y * 100000) / 100000);
              vertexReferences++;
            }
          }
        });
        const rays = galleryRays.map(probe => {
          viewer.raycaster.set(vector(probe.origin), vector(probe.direction));
          viewer.raycaster.near = 0;
          viewer.raycaster.far = Infinity;
          const hits = viewer.raycaster.intersectObject(root, true).map(hit => ({
            material: finish(hit.object, hit.face.materialIndex).name,
            distance: hit.distance, nativeZ: hit.point.y,
          }));
          return {...probe, hits, blueHits: hits.filter(hit => hit.material.endsWith('ATRIA_blue_carpet'))};
        });
        rows.push({mode, interior, minimumBlueZ: minimum, blueLevels: [...levels].sort((a, b) => a - b),
          blueMaterials: [...materials], blueVertexReferences: vertexReferences, rays});
      }
      return {rows};
    }, galleryRays);
    await writeFile(`${folder}/production-basement-diagnostic.json`, JSON.stringify({...result, errors}, null, 2) + '\n');
    expect(result.rows).toHaveLength(4);
    for (const row of result.rows) {
      expect(row.blueVertexReferences, row.mode).toBeGreaterThan(0);
      expect(row.blueLevels.some(level => Math.abs(level - .332) < .0001), row.mode).toBe(true);
      if (row.interior) {
        expect(row.minimumBlueZ, row.mode).toBeLessThan(-3.6);
        expect(row.blueLevels.some(level => Math.abs(level + 3.668) < .0001), row.mode).toBe(true);
        for (const ray of row.rays) expect(ray.blueHits.some(hit => Math.abs(hit.nativeZ + 3.668) < .0001), JSON.stringify({mode: row.mode, ray})).toBe(true);
      } else {
        expect(row.minimumBlueZ, row.mode).toBeGreaterThanOrEqual(-.00001);
        for (const ray of row.rays) expect(ray.blueHits.filter(hit => hit.nativeZ < -.00001), JSON.stringify({mode: row.mode, ray})).toEqual([]);
      }
    }
    expect(errors).toEqual([]);
    await writeFile(`${folder}/production-basement-verification.json`, JSON.stringify({
      passed: true, sourceModelSha256: sourceSha, modes: 4, raysPerMode: galleryRays.length,
      preservedOpticalMaterials: oldGlass.map(material => material.name), ...result, errors,
    }, null, 2) + '\n');
  } finally {
    await page.evaluate(() => window.viewer?.dispose()).catch(() => {});
  }
});
