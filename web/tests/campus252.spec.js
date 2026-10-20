import {test, expect} from '@playwright/test';
import {readFile, writeFile} from 'node:fs/promises';

const folder = 'result/blender/stage252';
const read = async path => JSON.parse(await readFile(path, 'utf8'));

test('252 changes COL finishes while preserving every other building and room asset', async () => {
  const before = await read(`${folder}/catalogue-before.json`);
  const after = await read('dist/models/catalogue.json');
  const saved = await read(`${folder}/complete-protection.json`);
  const native = await read(`${folder}/building-refinement.json`);
  expect(after.version).toBe('252');
  expect(saved.completeModelReopened).toBe(true);
  expect(saved.originalObjectsProtected).toBe(8669);
  expect(saved.originalMaterialGraphsProtected).toBe(2346);
  expect(saved.protectedRooms).toBe(35);
  expect(saved.protectedRoomMembers).toBe(1485);
  expect(native.changedObjects).toEqual([]);
  expect(native.addedObjects).toHaveLength(5);
  const counts = {exteriors: 0, interiors: 0, rooms: 0, fallbacks: 0};
  for (const old of before.buildings) {
    const current = after.buildings.find(building => building.code === old.code);
    if (old.detailedExterior) {
      if (old.code === 'COL') expect(current.detailedExterior.sha256).not.toBe(old.detailedExterior.sha256);
      else { expect(current.detailedExterior.sha256, old.code).toBe(old.detailedExterior.sha256); counts.exteriors++; }
    }
    if (old.detailedInterior) {
      expect(current.detailedInterior.sha256, old.code).toBe(old.detailedInterior.sha256);
      counts.interiors++;
    }
    for (const room of old.interiorSpaces ?? []) {
      expect(current.interiorSpaces.find(item => item.id === room.id).detailedInterior.sha256, room.id).toBe(room.detailedInterior.sha256);
      counts.rooms++;
    }
  }
  const previous = await read(`${folder}/release-before.json`);
  const release = await read('dist/release.json');
  for (const path of Object.keys(previous.assets).filter(path => /^\/models\/[a-z0-9]+-interior\.glb$/.test(path))) {
    expect(release.assets[path].sha256, path).toBe(previous.assets[path].sha256);
    counts.fallbacks++;
  }
  expect(counts).toEqual({exteriors: 29, interiors: 25, rooms: 35, fallbacks: 25});
  const gallery = await read('dist/gallery-manifest.json');
  expect(gallery.images).toHaveLength(204);
  await writeFile(`${folder}/asset-scope.json`, JSON.stringify({unchanged: counts, changed: ['COL exterior finish']}, null, 2) + '\n');
});

test('COL exported overview and close-up keep source apertures, backing and uniform photo-guided stone', async ({page}) => {
  const release = await read('dist/release.json');
  const module = Object.keys(release.assets).find(path => /^\/assets\/viewer-.*\.js$/.test(path));
  const source = await read('result/blender/col-component244/geometry-plan.json');
  const plan = await read('result/blender/col-roof251/geometry-plan.json');
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  const html = `<style>body{margin:0}#stage{width:1000px;height:800px}#labels{display:none}</style><div id="stage"></div><div id="labels"></div><script type="module">
    import {CampusViewer} from '${module}';
    const catalogue = await (await fetch('/models/catalogue.json')).json();
    const viewer = new CampusViewer(document.querySelector('#stage'),document.querySelector('#labels'),catalogue.buildings,()=>{},()=>{throw Error('Context lost')},()=>{},catalogue.sourceModelSha256);
    window.viewer = viewer; viewer.loadCampusExteriors = async()=>{};
    await viewer.load(); await viewer.environmentReady;
    const building = catalogue.buildings.find(building=>building.code==='COL');
    viewer.select(building); await viewer.upgradeModel(building,'exterior');
    viewer.transition = null; window.ready = true;
  </script>`;
  try {
    await page.route('**/__campus252', route => route.fulfill({contentType: 'text/html', body: html}));
    await page.goto('/__campus252');
    await page.waitForFunction(() => window.ready, null, {timeout: 60000});
    const result = await page.evaluate(({source, plan}) => {
      const v = window.viewer, reg = plan.registration;
      const vector = (x,y,z) => v.controls.target.clone().set(x,y,z);
      const [ox,oy] = source.sourceOrigin, scale = source.metresPerPoint;
      const [north] = reg.frontageNorthToSouth, [ax,ay] = reg.axis, [ix,iy] = reg.inwardNormal;
      const direction = vector(ix,0,-iy);
      const nameOf = hit => {
        const list = hit.object.material;
        return (Array.isArray(list) ? list[hit.face.materialIndex] : list).name.replace(/^WEB_(?:DETAIL_)?/,'');
      };
      v.scene.updateMatrixWorld(true); v.raycaster.far = 51;
      const assets = [];
      for (const root of [v.groups.get('COL'), v.exteriors.get('COL')]) {
        const failures = []; let rays = 0, backings = 0, stoneVertices = 0, colourError = 0;
        for (const opening of source.openings) {
          const [x0,y0,x1,y1] = opening.sourceBounds;
          for (const fraction of [.2,.5,.8]) {
            const u = (x0+(x1-x0)*fraction-ox)*scale;
            let z = (oy-y0-(y1-y0)*fraction)*scale;
            if (opening.role === 'entrance-material-unverified') {
              const low = Math.max((oy-y1)*scale,source.groundRiseNorthM*(1-u/source.sourceWidthM)), head = (oy-y0)*scale;
              z = head-(head-z)*(head-reg.flatStreetThresholdM)/(head-low);
            }
            const origin = vector(north[0]+ax*u*reg.horizontalFit-ix*50,z,-(north[1]+ay*u*reg.horizontalFit-iy*50));
            v.raycaster.set(origin,direction);
            const hits = v.raycaster.intersectObject(root,true), first = hits[0];
            const backing = hits.find(hit => nameOf(hit).includes('closed_recess_backing'));
            const acceptedMaterial = first && /^(COL249_(estimated_(window_glass|dark_joinery)|unverified_ground_infill)|COL195_FINISH_STREET_D4_dark_bronze_frames)$/.test(nameOf(first));
            if (!acceptedMaterial || first.distance < 49.98 || first.distance > 50.17) failures.push({opening: opening.id, fraction, type: 'first surface', material: first && nameOf(first)});
            if (!backing || Math.abs(backing.distance-50.6) > .005) failures.push({opening: opening.id, fraction, type: 'backing'});
            else backings++;
            rays++;
          }
        }
        root.traverse(mesh => {
          if (!mesh.isMesh) return;
          const materials = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
          const groups = mesh.geometry.groups.length ? mesh.geometry.groups : [{start:0,count:mesh.geometry.index?.count ?? mesh.geometry.attributes.position.count,materialIndex:0}];
          for (const group of groups) {
            const material = materials[group.materialIndex];
            if (!material.name.includes('COL252_photo_guided_uniform_stone')) continue;
            if (material.map) failures.push({type:'unsupported macro-colour map'});
            const expected = [.643538515065255,.6400501983663978,.5887113874163865];
            const actual = material.color.toArray();
            colourError = Math.max(colourError,...actual.map((value,index)=>Math.abs(value-expected[index])));
            if (Math.abs(material.roughness-.86) > .00001 || material.metalness !== 0) failures.push({type:'stone PBR mismatch'});
            stoneVertices += group.count;
          }
        });
        assets.push({rays,backings,failures,stoneVertices,colourError});
      }
      v.raycaster.far = Infinity;
      return {assets, order: ['campus','exterior']};
    }, {source, plan});
    for (const asset of result.assets) {
      expect(asset.failures).toEqual([]);
      expect(asset.rays).toBe(216); expect(asset.backings).toBe(216);
      expect(asset.stoneVertices).toBeGreaterThan(1000);
      expect(asset.colourError).toBeLessThan(.00001);
    }
    expect(errors).toEqual([]);
    await writeFile(`${folder}/production-finish.json`, JSON.stringify({...result,errors}, null, 2) + '\n');
  } finally { await page.evaluate(() => window.viewer?.dispose()).catch(()=>{}); }
});
