import {test, expect} from '@playwright/test';
import {readFile, writeFile} from 'node:fs/promises';

const folder = 'result/blender/stage256';
const read = async path => JSON.parse(await readFile(path, 'utf8'));
const glbDocument = bytes => JSON.parse(
  bytes.subarray(20, 20 + bytes.readUInt32LE(12)).toString());

// The two exterior changes must not replace room assets or re-tune glazing.
test('edition256 preserves unrelated architecture, rooms and glass finishes', async () => {
  const before = await read(`${folder}/catalogue-before.json`);
  const after = await read('dist/models/catalogue.json');
  const protection = await read(`${folder}/complete-protection.json`);
  expect(after.version).toBe('256');
  expect(after.sourceModelSha256).toBe(protection.sourceModelSha256);
  expect(protection.seatedNumbersRetainOriginalFontIdentities).toBe(true);
  expect(protection.completeModelReopened).toBe(true);
  expect(protection.originalObjectsProtected).toBe(8685);
  expect(protection.originalMaterialGraphsProtected).toBe(2348);
  expect(protection.roomStudiesProtected).toBe(35);
  expect(protection.roomMembershipUnchanged).toBe(true);
  expect(protection.campusRoomMembershipUnchanged).toBe(true);

  const counts = {exteriors: 0, interiors: 0, rooms: 0, fallbacks: 0};
  for (const old of before.buildings) {
    const current = after.buildings.find(building => building.code === old.code);
    if (old.detailedExterior) {
      if (['PAN', 'KGS'].includes(old.code)) {
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
  expect(counts).toEqual({exteriors: 28, interiors: 25, rooms: 35, fallbacks: 25});
  const previousGallery = await read(`${folder}/gallery-before.json`);
  const gallery = await read('dist/gallery-manifest.json');
  expect(gallery.images).toHaveLength(206);
  const changed = gallery.images.filter(image => image.sha256 !==
    previousGallery.images.find(previous => previous.name === image.name)?.sha256);
  await writeFile(`${folder}/asset-scope.json`, JSON.stringify({
    unchanged: counts, changedExteriors: ['KGS', 'PAN'],
    changedImages: changed.map(image => ({name: image.name, code: image.code, mode: image.mode})),
  }, null, 2) + '\n');
});

test('overview and selected models retain seated KGS lettering and real PAN apertures', async ({page}) => {
  const release = await read('dist/release.json');
  const viewerModule = Object.keys(release.assets).find(path => /^\/assets\/viewer-.*\.js$/.test(path));
  const kgs = await read('result/blender/kgs256/audit.json');
  const pan = await read('result/blender/pan256/audit.json');
  const forecourt = await read('result/blender/forecourt256/audit.json');
  const frame = (await read('result/blender/forecourt256/inspection.json')).frame;
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  const html = `<!doctype html><link rel="icon" href="data:,"><style>body{margin:0}#stage{width:1000px;height:800px}#labels{display:none}</style><div id="stage"></div><div id="labels"></div><script type="module">
    import {CampusViewer} from '${viewerModule}';
    const catalogue=await(await fetch('/models/catalogue.json')).json();
    const viewer=new CampusViewer(document.querySelector('#stage'),document.querySelector('#labels'),catalogue.buildings,()=>{},()=>{throw Error('Context lost')},()=>{},catalogue.sourceModelSha256);
    window.viewer=viewer;viewer.loadCampusExteriors=async()=>{};
    await viewer.load();await viewer.environmentReady;
    for(const code of ['KGS','PAN'])await viewer.loadExterior(catalogue.buildings.find(building=>building.code===code));
    window.ready=true;
  </script>`;
  try {
    await page.route('**/__campus256', route => route.fulfill({contentType: 'text/html', body: html}));
    await page.goto('/__campus256');
    await page.waitForFunction(() => window.ready, null, {timeout: 60000});
    const rows = await page.evaluate(({kgs, pan, forecourt, frame}) => {
      const viewer = window.viewer;
      const web = point => viewer.controls.target.clone().set(point[0], point[2], -point[1]);
      viewer.scene.updateMatrixWorld(true);
      function hits(root, origin, direction, limit) {
        viewer.raycaster.set(web(origin), web(direction));
        viewer.raycaster.far = limit;
        return viewer.raycaster.intersectObject(root, true).map(hit => {
          const materials = hit.object.material;
          const material = Array.isArray(materials) ? materials[hit.face.materialIndex] : materials;
          return {material: material.name, distance: hit.distance};
        });
      }
      const proof = [];
      for (const [level, root] of [['overview', viewer.groups.get('KGS')], ['detail', viewer.exteriors.get('KGS')]]) {
        for (const glyph of [...kgs.glyphs, ...kgs.numbers.samples]) {
          proof.push({code: 'KGS', level, index: glyph.index,
            hits: hits(root, glyph.worldProbeOrigin, glyph.worldOutwardNormal.map(value => -value), .05)});
        }
      }
      for (const [level, root] of [['overview', viewer.groups.get('PAN')], ['detail', viewer.exteriors.get('PAN')]]) {
        for (const probe of pan.apertureGeometry.representatives) {
          for (const [kind, origin] of [['hole', probe.holeRayOrigin], ['metal', probe.metalRayOrigin]]) {
            proof.push({code: 'PAN', level, index: probe.cellIndex, kind,
              hits: hits(root, origin, probe.direction, probe.rayLimitMetres)
                .filter(hit => /PAN_D3_silver/.test(hit.material))});
          }
        }
      }
      const furniture = forecourt.units.map((unit, index) => {
        const rectangle = unit.rectangles[1] ?? unit.outer;
        return {
          index,
          x: unit.rectangles[1] ? (rectangle[0] + rectangle[1]) / 2 : rectangle[1] - .02,
          depth: (rectangle[2] + rectangle[3]) / 2,
          top: unit.base + (unit.rectangles[1] ? unit.seatHeight : unit.planterHeight),
        };
      });
      for (const [level, root] of [['overview', viewer.groups.get('PAN')], ['detail', viewer.exteriors.get('PAN')]]) {
        for (const point of furniture) {
          const origin = frame.origin.map((value, index) => value +
            frame.right[index] * point.x + frame.outward[index] * point.depth);
          origin[2] = 2;
          proof.push({code: 'PAN_FORECOURT', level, index: point.index,
            expectedDistance: 2 - point.top, hits: hits(root, origin, [0, 0, -1], 2.5)});
        }
      }
      return proof;
    }, {kgs, pan, forecourt, frame});
    await writeFile(`${folder}/production-facades-diagnostic.json`, JSON.stringify({rows, errors}, null, 2) + '\n');
    expect(rows).toHaveLength(2 * (kgs.glyphs.length + kgs.numbers.samples.length) +
      4 * pan.apertureGeometry.representatives.length + 2 * forecourt.units.length);
    for (const row of rows) {
      if (row.code === 'PAN' && row.kind === 'hole') expect(row.hits, JSON.stringify(row)).toHaveLength(0);
      else if (row.code === 'PAN_FORECOURT') {
        expect(row.hits.length, JSON.stringify(row)).toBeGreaterThan(0);
        expect(row.hits[0].material).toMatch(/PAN_FORECOURT256_estimated_grey_stone/);
        expect(row.hits[0].distance).toBeCloseTo(row.expectedDistance, 3);
      } else {
        expect(row.hits.length, JSON.stringify(row)).toBeGreaterThan(0);
        expect(row.hits[0].material).toMatch(row.code === 'KGS' ? /HERITAGE09_gold/ : /PAN_D3_silver/);
        expect(row.hits[0].distance).toBeCloseTo(row.code === 'KGS' ? .025 : .03, 3);
      }
    }
    expect(errors).toEqual([]);
    await writeFile(`${folder}/production-facades.json`, JSON.stringify({passed: true, rows, errors}, null, 2) + '\n');
  } finally {
    await page.evaluate(() => window.viewer?.dispose()).catch(() => {});
  }
});
