import {test, expect} from '@playwright/test';
import {readFile, writeFile} from 'node:fs/promises';

const folder = 'result/blender/stage257';
const read = async path => JSON.parse(await readFile(path, 'utf8'));
const glbDocument = bytes => JSON.parse(
  bytes.subarray(20, 20 + bytes.readUInt32LE(12)).toString());

// The three exterior changes must not replace room assets or re-tune glazing.
test('edition257 preserves unrelated architecture, rooms and glass finishes', async () => {
  const before = await read(`${folder}/catalogue-before.json`);
  const after = await read('dist/models/catalogue.json');
  const protection = await read(`${folder}/complete-protection.json`);
  expect(after.version).toBe('257');
  expect(after.sourceModelSha256).toBe(protection.sourceModelSha256);
  expect(protection.completeModelReopened).toBe(true);
  expect(protection.originalObjectsProtected).toBe(8691);
  expect(protection.originalMaterialGraphsProtected).toBe(2349);
  expect(protection.roomStudiesProtected).toBe(35);
  expect(protection.roomMembershipUnchanged).toBe(true);
  expect(protection.campusRoomMembershipUnchanged).toBe(true);

  const counts = {exteriors: 0, interiors: 0, rooms: 0, fallbacks: 0};
  for (const old of before.buildings) {
    const current = after.buildings.find(building => building.code === old.code);
    if (old.detailedExterior) {
      if (['PEL', 'OCS', 'LCH'].includes(old.code)) {
        expect(current.detailedExterior.sha256).not.toBe(old.detailedExterior.sha256);
        const previous = glbDocument(await readFile(`${folder}/${old.code.toLowerCase()}-before.glb`));
        const latest = glbDocument(await readFile('dist' + current.detailedExterior.url));
        const glass = document => document.materials
          .filter(material => material.extras?.webSurfaceRole === 'glazing')
          .sort((a, b) => a.name.localeCompare(b.name));
        expect(glass(previous).length).toBeGreaterThan(0);
        expect(glass(latest)).toEqual(glass(previous));
      } else {
        expect(current.detailedExterior.sha256, old.code).toBe(old.detailedExterior.sha256);
        counts.exteriors++;
      }
    }
    if (old.detailedInterior) {
      expect(current.detailedInterior.sha256, old.code).toBe(old.detailedInterior.sha256);
      counts.interiors++;
    }
    for (const room of old.interiorSpaces ?? []) {
      expect(current.interiorSpaces.find(item => item.id === room.id).detailedInterior.sha256, room.id)
        .toBe(room.detailedInterior.sha256);
      counts.rooms++;
    }
  }
  const previousRelease = await read(`${folder}/release-before.json`);
  const release = await read('dist/release.json');
  for (const path of Object.keys(previousRelease.assets)
    .filter(path => /^\/models\/[a-z0-9]+-interior\.glb$/.test(path))) {
    expect(release.assets[path].sha256, path).toBe(previousRelease.assets[path].sha256);
    counts.fallbacks++;
  }
  expect(counts).toEqual({exteriors: 27, interiors: 25, rooms: 35, fallbacks: 25});
  const previousGallery = await read(`${folder}/gallery-before.json`);
  const gallery = await read('dist/gallery-manifest.json');
  expect(gallery.images).toHaveLength(206);
  const changed = gallery.images.filter(image => image.sha256 !==
    previousGallery.images.find(previous => previous.name === image.name)?.sha256);
  expect(changed.every(image => image.mode !== 'interior')).toBe(true);
  await writeFile(`${folder}/asset-scope.json`, JSON.stringify({
    unchanged: counts, changedExteriors: ['PEL', 'OCS', 'LCH'],
    changedImages: changed.map(image => ({name: image.name, code: image.code, mode: image.mode})),
  }, null, 2) + '\n');
});


test('overview and selected facades retain corrected entrance and sash geometry', async ({page}) => {
  const release = await read('dist/release.json');
  const viewerModule = Object.keys(release.assets).find(path => /^\/assets\/viewer-.*\.js$/.test(path));
  const pel = await read('result/blender/pel257/audit.json');
  const ocs = await read('result/blender/ocs257/audit.json');
  const lch = await read('result/blender/lch257/audit.json');
  const probes = [
    ...pel.faceProbes.map((probe, index) => ({code: 'PEL', index, origin: probe.origin,
      direction: probe.direction, distance: probe.expectedDistanceMetres,
      material: probe.expectedMaterial})),
    ...ocs.windows.flatMap(window => window.bars.map((bar, index) => ({
      code: 'OCS', index: `${window.pane}:${index}`, origin: bar.worldProbeOrigin,
      direction: bar.worldOutwardNormal.map(value => -value), distance: .025,
      material: Object.values(ocs.replacementMaterialBindings)[0][0],
    }))),
    ...[...lch.glyphs, ...lch.numbers.samples].map(glyph => ({code: 'LCH', index: glyph.index,
      origin: glyph.worldProbeOrigin,
      direction: glyph.worldOutwardNormal.map(value => -value), distance: .025,
      material: Object.values(lch.replacementMaterialBindings)[0][0],
    })),
  ];
  expect(probes.filter(probe => probe.code === 'PEL')).toHaveLength(2);
  expect(probes.filter(probe => probe.code === 'OCS')).toHaveLength(9);
  expect(probes.filter(probe => probe.code === 'LCH').length).toBeGreaterThanOrEqual(16);
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  const html = `<!doctype html><link rel="icon" href="data:,"><style>body{margin:0}#stage{width:1000px;height:800px}#labels{display:none}</style><div id="stage"></div><div id="labels"></div><script type="module">
    import {CampusViewer} from '${viewerModule}';
    const catalogue=await(await fetch('/models/catalogue.json')).json();
    const viewer=new CampusViewer(document.querySelector('#stage'),document.querySelector('#labels'),catalogue.buildings,()=>{},()=>{throw Error('Context lost')},()=>{},catalogue.sourceModelSha256);
    window.viewer=viewer;viewer.loadCampusExteriors=async()=>{};
    await viewer.load();await viewer.environmentReady;
    for(const code of ['PEL','OCS','LCH'])await viewer.loadExterior(catalogue.buildings.find(building=>building.code===code));
    window.ready=true;
  </script>`;
  try {
    await page.route('**/__campus257', route => route.fulfill({contentType: 'text/html', body: html}));
    await page.goto('/__campus257');
    await page.waitForFunction(() => window.ready, null, {timeout: 60000});
    const rows = await page.evaluate(probes => {
      const viewer = window.viewer;
      const web = point => viewer.controls.target.clone().set(point[0], point[2], -point[1]);
      viewer.scene.updateMatrixWorld(true);
      const rows = [];
      for (const probe of probes) {
        for (const [level, root] of [['overview', viewer.groups.get(probe.code)], ['detail', viewer.exteriors.get(probe.code)]]) {
          viewer.raycaster.set(web(probe.origin), web(probe.direction));
          viewer.raycaster.far = probe.distance + .02;
          const hits = viewer.raycaster.intersectObject(root, true).map(hit => {
            const materials = hit.object.material;
            const material = Array.isArray(materials) ? materials[hit.face.materialIndex] : materials;
            return {material: material.name, distance: hit.distance};
          });
          rows.push({...probe, level, hits});
        }
      }
      return rows;
    }, probes);
    await writeFile(`${folder}/production-facades-diagnostic.json`, JSON.stringify({rows, errors}, null, 2) + '\n');
    expect(rows).toHaveLength(2 * probes.length);
    for (const row of rows) {
      expect(row.hits.length, JSON.stringify(row)).toBeGreaterThan(0);
      expect(row.hits[0].material, JSON.stringify(row)).toBe(
        (row.level === 'detail' ? 'WEB_DETAIL_' : 'WEB_') + row.material);
      expect(row.hits[0].distance, JSON.stringify(row)).toBeCloseTo(row.distance, 3);
    }
    expect(errors).toEqual([]);
    await writeFile(`${folder}/production-facades-verification.json`, JSON.stringify({passed: true, probes: probes.length, rows, errors}, null, 2) + '\n');
  } finally {
    await page.evaluate(() => window.viewer?.dispose()).catch(() => {});
  }
});
