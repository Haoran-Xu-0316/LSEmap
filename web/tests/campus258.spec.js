import {test, expect} from '@playwright/test';
import {readFile, writeFile} from 'node:fs/promises';

const folder = 'result/blender/stage258';
const read = async path => JSON.parse(await readFile(path, 'utf8'));
const glbDocument = bytes => JSON.parse(
  bytes.subarray(20, 20 + bytes.readUInt32LE(12)).toString());
const exteriorCodes = ['MAR', 'LRB'];
const glassMaterials = document => (document.materials ?? [])
  .filter(material => material.extras?.webSurfaceRole === 'glazing')
  .sort((a, b) => a.name.localeCompare(b.name));

// Added LRB panes may introduce a previously unused material into a GLB. Every
// retained glass finish keeps complete parameters. Rebuilt single-sheet windows
// may replace the two old closed-shell material variants with their accepted
// optically identical sheet counterparts; native graphs remain protected.
function expectPreservedGlass(previous, latest, code, lrb) {
  const oldGlass = glassMaterials(previous);
  const newGlass = glassMaterials(latest);
  expect(oldGlass.length, code).toBeGreaterThan(0);
  const sheetLineage = code === 'LRB' ? {
    WEB_DETAIL_LRB233_limited_transmission_1: 'WEB_DETAIL_LRB233_limited_transmission_0',
    WEB_DETAIL_LRB233_limited_transmission_3: 'WEB_DETAIL_LRB233_limited_transmission_2',
  } : {};
  let retiredShells = 0;
  for (const material of oldGlass) {
    const retained = newGlass.find(current => current.name === material.name);
    if (retained) expect(retained, material.name).toEqual(material);
    else {
      const counterpart = newGlass.find(current => current.name === sheetLineage[material.name]);
      expect(counterpart, material.name).toBeTruthy();
      // Geometry changes from a closed shell to one optical sheet. Its side
      // policy may change, while every optical parameter must remain exact.
      for (const key of ['pbrMetallicRoughness', 'alphaMode', 'alphaCutoff', 'extensions', 'emissiveFactor']) {
        expect(counterpart[key], material.name + ':' + key).toEqual(material[key]);
      }
      retiredShells++;
    }
  }
  const added = newGlass.filter(material => !oldGlass.some(old => old.name === material.name));
  if (code !== 'LRB') expect(added, code).toEqual([]);
  else {
    const allowed = new Set(lrb.glassTriangleProbes.map(probe => `WEB_DETAIL_${probe.expectedMaterial}`));
    for (const material of added) expect(allowed.has(material.name), material.name).toBe(true);
  }
  expect(newGlass).toHaveLength(oldGlass.length + added.length - retiredShells);
  return added.map(material => material.name);
}

test('edition258 confines changes to MAR and LRB while preserving all35 room studies', async () => {
  const before = await read(`${folder}/catalogue-before.json`);
  const after = await read('dist/models/catalogue.json');
  const protection = await read(`${folder}/complete-protection.json`);
  const lrb = await read('result/blender/lrb258/audit.json');
  expect(after.version).toBe('258');
  expect(after.sourceModelSha256).toBe(protection.sourceModelSha256);
  expect(protection.completeModelReopened).toBe(true);
  expect(protection.originalObjectsProtected).toBe(8695);
  expect(protection.originalMaterialGraphsProtected).toBe(2349);
  expect(protection.roomStudiesProtected).toBe(35);
  expect(protection.roomMembershipUnchanged).toBe(true);
  expect(protection.campusRoomMembershipUnchanged).toBe(true);
  expect(after.buildings.map(building => building.code)).toEqual(before.buildings.map(building => building.code));

  const counts = {exteriors: 0, interiors: 0, rooms: 0, fallbacks: 0};
  const changedPublicInteriors = [];
  const addedGlass = [];
  for (const old of before.buildings) {
    const current = after.buildings.find(building => building.code === old.code);
    if (old.detailedExterior) {
      if (exteriorCodes.includes(old.code)) {
        expect(current.detailedExterior.sha256, old.code).not.toBe(old.detailedExterior.sha256);
        const previous = glbDocument(await readFile(`${folder}/${old.code.toLowerCase()}-detailedExterior.glb`));
        const latest = glbDocument(await readFile('dist' + current.detailedExterior.url));
        addedGlass.push({code: old.code, asset: 'exterior', names: expectPreservedGlass(previous, latest, old.code, lrb)});
      } else {
        expect(current.detailedExterior.sha256, old.code).toBe(old.detailedExterior.sha256);
        counts.exteriors++;
      }
    }
    if (old.detailedInterior) {
      if (exteriorCodes.includes(old.code)) {
        if (old.code === 'MAR') expect(current.detailedInterior.sha256).not.toBe(old.detailedInterior.sha256);
        if (current.detailedInterior.sha256 !== old.detailedInterior.sha256) changedPublicInteriors.push(old.code);
        const previous = glbDocument(await readFile(`${folder}/${old.code.toLowerCase()}-detailedInterior.glb`));
        const latest = glbDocument(await readFile('dist' + current.detailedInterior.url));
        addedGlass.push({code: old.code, asset: 'public-interior', names: expectPreservedGlass(previous, latest, old.code, lrb)});
      } else {
        expect(current.detailedInterior.sha256, old.code).toBe(old.detailedInterior.sha256);
        counts.interiors++;
      }
    }
    expect((current.interiorSpaces ?? []).map(room => room.id)).toEqual((old.interiorSpaces ?? []).map(room => room.id));
    for (const room of old.interiorSpaces ?? []) {
      expect(current.interiorSpaces.find(item => item.id === room.id).detailedInterior.sha256, room.id)
        .toBe(room.detailedInterior.sha256);
      counts.rooms++;
    }
  }
  const previousRelease = await read(`${folder}/release-before.json`);
  const release = await read('dist/release.json');
  const changedFallbacks = [];
  for (const path of Object.keys(previousRelease.assets)
    .filter(path => /^\/models\/[a-z0-9]+-interior\.glb$/.test(path))) {
    if (path === '/models/mar-interior.glb') {
      expect(release.assets[path].sha256, path).not.toBe(previousRelease.assets[path].sha256);
      changedFallbacks.push(path);
    } else if (path === '/models/lrb-interior.glb') {
      if (release.assets[path].sha256 !== previousRelease.assets[path].sha256) changedFallbacks.push(path);
    } else {
      expect(release.assets[path].sha256, path).toBe(previousRelease.assets[path].sha256);
      counts.fallbacks++;
    }
  }
  expect(counts).toEqual({exteriors: 28, interiors: 23, rooms: 35, fallbacks: 23});
  const previousGallery = await read(`${folder}/gallery-before.json`);
  const gallery = await read('dist/gallery-manifest.json');
  for (const image of previousGallery.images) expect(gallery.images.some(current => current.name === image.name), image.name).toBe(true);
  const changed = gallery.images.filter(image => image.sha256 !==
    previousGallery.images.find(previous => previous.name === image.name)?.sha256);
  // Campus/exterior images may show a neighbouring corrected building; unrelated
  // independent interior views have no reason to change.
  expect(changed.every(image => image.mode !== 'interior' || exteriorCodes.includes(image.code))).toBe(true);
  await writeFile(`${folder}/asset-scope.json`, JSON.stringify({
    passed: true, unchanged: counts, changedExteriors: exteriorCodes,
    changedPublicInteriors, changedFallbacks, addedGlass,
    changedImages: changed.map(image => ({name: image.name, code: image.code, mode: image.mode})),
  }, null, 2) + '\n');
});

async function prepareViewer(page) {
  const release = await read('dist/release.json');
  const viewerModule = Object.keys(release.assets).find(path => /^\/assets\/viewer-.*\.js$/.test(path));
  expect(viewerModule).toBeTruthy();
  const html = `<!doctype html><link rel="icon" href="data:,"><style>body{margin:0}#stage{width:1000px;height:800px}#labels{display:none}</style><div id="stage"></div><div id="labels"></div><script type="module">
    import {CampusViewer} from '${viewerModule}';
    const catalogue=await(await fetch('/models/catalogue.json')).json();
    const viewer=new CampusViewer(document.querySelector('#stage'),document.querySelector('#labels'),catalogue.buildings,()=>{},()=>{throw Error('Context lost')},()=>{},catalogue.sourceModelSha256);
    window.viewer=viewer;viewer.loadCampusExteriors=async()=>{};
    await viewer.load();await viewer.environmentReady;
    for(const code of ['MAR','LRB'])await viewer.loadExterior(catalogue.buildings.find(building=>building.code===code));
    const mar=catalogue.buildings.find(building=>building.code==='MAR');
    await viewer.loadInterior(mar,null,{interiorAsset:mar.detailedInterior});
    await viewer.loadInterior(mar,'fallback258',{interiorAsset:'/models/mar-interior.glb'});
    window.ready=true;
  </script>`;
  await page.route('**/__campus258', route => route.fulfill({contentType: 'text/html', body: html}));
  await page.goto('/__campus258');
  await page.waitForFunction(() => window.ready, null, {timeout: 60000});
}

test('actual overview and detailed GLBs retain MAR finishes and LRB window geometry', async ({page}) => {
  const mar = await read('result/blender/mar-finish258/audit.json');
  const lrb = await read('result/blender/lrb258/audit.json');
  const probes = [
    ...mar.records.flatMap(record => record.worldFaceProbes.map(probe => ({
      code: 'MAR', index: `${record.added}:${probe.index}`, origin: probe.worldProbeOrigin,
      direction: probe.worldOutwardNormal.map(value => -value), distance: .035,
      material: mar.replacementMaterialBindings[record.added][0],
    }))),
    ...lrb.glassTriangleProbes.flatMap(probe => [
      {code: 'LRB', index: `${probe.window}:surface`, origin: probe.origin,
        direction: probe.normal.map(value => -value), distance: probe.expectedDistance,
        material: probe.expectedMaterial},
      // A ray starting one metre outside the same real triangle also detects
      // retained proxy faces hiding a correctly placed new pane.
      {code: 'LRB', index: `${probe.window}:approach`,
        origin: probe.point.map((value, axis) => value + probe.normal[axis]),
        direction: probe.normal.map(value => -value), distance: 1,
        material: probe.expectedMaterial},
    ]),
  ];
  expect(probes.filter(probe => probe.code === 'MAR')).toHaveLength(9);
  expect(probes.filter(probe => probe.code === 'LRB').length).toBeGreaterThan(0);
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  try {
    await prepareViewer(page);
    const rows = await page.evaluate(probes => {
      const viewer = window.viewer;
      const web = point => viewer.controls.target.clone().set(point[0], point[2], -point[1]);
      viewer.scene.updateMatrixWorld(true);
      const rows = [];
      for (const probe of probes) {
        for (const [level, root] of [['overview', viewer.groups.get(probe.code)], ['detail', viewer.exteriors.get(probe.code)]]) {
          viewer.raycaster.set(web(probe.origin), web(probe.direction));
          viewer.raycaster.near = 0;
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

test('actual exported MAR deck has two correctly facing surfaces and three open lift shafts', async ({page}) => {
  const mar = await read('result/blender/mar258/audit.json');
  const section = mar.sectionProof;
  const [bottom, top] = mar.actualVolumeContactProof.candidateActualZRange;
  expect(section.liftHoles).toBe(3);
  expect(section.closedManifoldEveryEdgeTwoFaces).toBe(true);
  expect(section.independentBoundaryLoops).toBe(4);
  expect(top - bottom).toBeCloseTo(section.actualThicknessMetres, 6);
  expect(mar.actualVolumeContactProof.glassFramesAndOtherNeighborsWithoutVolumeIntrusion).toBe(true);
  const surfaces = section.topAndBottomSurfaceSamples.flatMap((point, index) => [
    {kind: 'top', index, origin: [point[0], point[1], top + .025], direction: [0, 0, -1], distance: .025, normalZ: 1},
    {kind: 'bottom', index, origin: [point[0], point[1], bottom - .025], direction: [0, 0, 1], distance: .025, normalZ: -1},
  ]);
  const holes = section.openLiftShaftRays.map((probe, index) => ({
    kind: 'hole', index, hole: probe.hole, origin: [...probe.xy, top + .025],
    direction: [0, 0, -1], distance: top - bottom + .05,
  }));
  expect(surfaces).toHaveLength(48);
  expect(new Set(holes.map(probe => probe.hole)).size).toBe(3);
  expect(holes).toHaveLength(60);
  const material = mar.replacementMaterialBindings[mar.addedObjects[0]][0];
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  try {
    await prepareViewer(page);
    const rows = await page.evaluate(({surfaces, holes, material}) => {
      const viewer = window.viewer;
      const web = point => viewer.controls.target.clone().set(point[0], point[2], -point[1]);
      viewer.scene.updateMatrixWorld(true);
      const roots = [
        ['overview', viewer.groups.get('MAR'), 'WEB_'],
        ['detail', viewer.exteriors.get('MAR'), 'WEB_DETAIL_'],
        ['public-interior', viewer.interiors.get('MAR:default'), 'WEB_DETAIL_'],
        ['fallback', viewer.interiors.get('MAR:fallback258'), 'WEB_'],
      ];
      const rows = [];
      for (const [level, root, prefix] of roots) {
        if (!root) throw new Error(`Missing actual exported MAR root: ${level}`);
        for (const probe of [...surfaces, ...holes]) {
          viewer.raycaster.set(web(probe.origin), web(probe.direction));
          viewer.raycaster.near = 0;
          viewer.raycaster.far = probe.kind === 'hole' ? probe.distance : probe.distance + .01;
          const hits = viewer.raycaster.intersectObject(root, true).map(hit => {
            const materials = hit.object.material;
            const finish = Array.isArray(materials) ? materials[hit.face.materialIndex] : materials;
            return {material: finish.name, distance: hit.distance,
              normalZ: hit.face.normal.clone().transformDirection(hit.object.matrixWorld).y};
          });
          // Building exports merge original objects by material. Limit hole
          // inspection to the deck finish and its exact thickness interval;
          // unrelated glass or lower storeys do not close this deck opening.
          const deckHits = hits.filter(hit => hit.material === prefix + material);
          rows.push({...probe, level, expectedMaterial: prefix + material, hits, deckHits});
        }
      }
      return rows;
    }, {surfaces, holes, material});
    await writeFile(`${folder}/production-deck-diagnostic.json`, JSON.stringify({rows, errors}, null, 2) + '\n');
    expect(rows).toHaveLength(4 * (surfaces.length + holes.length));
    for (const row of rows) {
      if (row.kind === 'hole') expect(row.deckHits, JSON.stringify(row)).toEqual([]);
      else {
        expect(row.hits.length, JSON.stringify(row)).toBeGreaterThan(0);
        expect(row.hits[0].material, JSON.stringify(row)).toBe(row.expectedMaterial);
        expect(row.hits[0].distance, JSON.stringify(row)).toBeCloseTo(row.distance, 3);
        expect(row.hits[0].normalZ * row.normalZ, JSON.stringify(row)).toBeGreaterThan(.999);
      }
    }
    expect(errors).toEqual([]);
    await writeFile(`${folder}/production-deck-verification.json`, JSON.stringify({
      passed: true, levels: 4, surfaceProbes: surfaces.length, shaftProbes: holes.length,
      shaftCount: 3, actualThicknessMetres: top - bottom,
      retainedPeripheralConcreteContacts: mar.actualVolumeContactProof.retainedPeripheralConcreteContacts,
      rows, errors,
    }, null, 2) + '\n');
  } finally {
    await page.evaluate(() => window.viewer?.dispose()).catch(() => {});
  }
});
