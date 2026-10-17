import { test, expect } from '@playwright/test';
import { readFile, writeFile, mkdir } from 'node:fs/promises';
import { galleryRendererSignature } from '../tools/gallery_signature.mjs';
const output = 'result/blender/stage242';
const read = async path => JSON.parse(await readFile(path, 'utf8'));

test('242 changes only SAW assets and retains every other building and room', async () => {
  const before = await read(`${output}/catalogue-before.json`), after = await read('dist/models/catalogue.json');
  const native = await read(`${output}/native-verification.json`), gallery = await read('dist/gallery-manifest.json');
  expect(after.version).toBe('242');
  expect(native.originalObjectsVerified).toBe(8607);
  expect(native.addedObjectsVerified).toBe(12);
  expect([native.protectedRooms, native.protectedRoomMembers]).toEqual([35, 1485]);
  let exteriors = 0, interiors = 0, rooms = 0;
  for (const previous of before.buildings) {
    const current = after.buildings.find(b => b.code === previous.code);
    for (const [key, count] of [['detailedExterior', 'exterior'], ['detailedInterior', 'interior']]) {
      if (!previous[key]) continue;
      if (count === 'exterior') exteriors++; else interiors++;
      if (previous.code === 'SAW') expect(current[key].sha256).not.toBe(previous[key].sha256);
      else expect(current[key].sha256, `${previous.code}:${key}`).toBe(previous[key].sha256);
    }
    for (const room of previous.interiorSpaces ?? []) {
      rooms++;
      expect(current.interiorSpaces.find(r => r.id === room.id).detailedInterior.sha256, room.id).toBe(room.detailedInterior.sha256);
    }
  }
  expect([exteriors, interiors, rooms]).toEqual([30, 25, 35]);
  const oldRelease=await read(`${output}/release-before.json`),newRelease=await read('dist/release.json');
  const fallback=[];
  for(const [path,asset]of Object.entries(oldRelease.assets)){
    if(/^\/models\/[a-z0-9]+-interior\.glb$/.test(path)&&path!=='/models/saw-interior.glb'){
      expect(newRelease.assets[path].sha256,path).toBe(asset.sha256);fallback.push(path);
    }
  }
  expect(fallback).toHaveLength(24);
  expect(gallery.images).toHaveLength(197);
  expect(gallery.rendererSha256).toBe(await galleryRendererSignature());
  expect(gallery.images.every(r => r.sceneSamples === 4 && r.sourceModelSha256 === after.sourceModelSha256)).toBe(true);
  await writeFile(`${output}/asset-scope.json`, JSON.stringify({ otherExteriorsUnchanged:29, otherPublicInteriorsUnchanged:24, allRoomsUnchanged:rooms, galleryImages:197 }, null, 2)+'\n');
});

for (const width of [1440, 390]) test(`242 new SAW stair views and exterior return work at ${width}px`, async ({ page }) => {
  const errors = []; page.on('pageerror', e => errors.push(e.message));
  await page.setViewportSize({ width, height: width === 390 ? 844 : 1000 });
  await page.goto('/#SAW');
  await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready', 'exterior-SAW', { timeout:60000 });
  await page.locator('#interior-view').click();
  await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready', 'interior-SAW', { timeout:60000 });
  for (const id of ['stair-3-4', 'stair-4-5', 'all']) {
    await page.locator('#interior-level').selectOption(id);
    await expect(page.locator('canvas')).toHaveAttribute('data-interior-section', id);
    if(id !== 'all') {
      await page.waitForTimeout(1000);
      await mkdir(`${output}/browser`,{recursive:true});
      await page.screenshot({path:`${output}/browser/saw-${id}-${width}.png`});
    }
  }
  await page.locator('#exterior-view').click();
  await expect(page.locator('canvas')).not.toHaveAttribute('data-interior-section');
  await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready', 'exterior-SAW');
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  expect(errors).toEqual([]);
});

test('SAW stair groups survive fallback-to-detail upgrade and reset for whole-building views', async ({ page }) => {
  test.setTimeout(150000);
  const catalogue = await read('dist/models/catalogue.json'), release = await read('dist/release.json');
  const building = catalogue.buildings.find(b => b.code === 'SAW');
  const moduleUrl = Object.keys(release.assets).find(p => /^\/assets\/viewer-.*\.js$/.test(p));
  let releaseDetail;
  const detailGate = new Promise(resolve => { releaseDetail = resolve; });
  await page.route(`**${building.detailedInterior.url}`, async route => { await detailGate; await route.continue(); });
  const html = `<style>body{margin:0}#stage{width:1200px;height:900px}#labels{display:none}</style><div id="stage"></div><div id="labels"></div><script type="module">
  import {CampusViewer} from '${moduleUrl}';
  const catalogue=await(await fetch('/models/catalogue.json')).json();const building=catalogue.buildings.find(b=>b.code==='SAW');
  const viewer=new CampusViewer(document.querySelector('#stage'),document.querySelector('#labels'),catalogue.buildings,()=>{},()=>{throw Error('Context lost')});
  window.viewer=viewer;window.building=building;await viewer.load();await viewer.environmentReady;viewer.select(building);await viewer.showInterior(building);window.ready=true;
  window.displayGroups=()=>{const root=viewer.activeDetail?.kind==='interior'?viewer.activeDetail.group:viewer.interiors.get('SAW:default');const groups={};root.traverse(o=>{if(o.userData.interiorDisplayGroup)groups[o.userData.interiorDisplayGroup]=o.visible;});return groups;};
  </script>`;
  try {
    await page.route('**/__saw242-groups', route => route.fulfill({ contentType:'text/html', body:html }));
    await page.goto('/__saw242-groups'); await page.waitForFunction(() => window.ready, null, { timeout:60000 });
    await page.evaluate(() => viewer.setInteriorSection(building, 'stair-3-4'));
    const expected = { public:true, floors:true, 'lower-stairs':false, 'stair-3-4':true, 'stair-4-5':false, 'stair-5-6':false };
    expect(await page.evaluate(() => displayGroups())).toEqual(expected);
    releaseDetail();
    await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready', 'interior-SAW', { timeout:60000 });
    expect(await page.evaluate(() => displayGroups())).toEqual(expected);
    await page.evaluate(() => viewer.setInteriorSection(building, 'stair-4-5'));
    expect(await page.evaluate(() => displayGroups())).toEqual({ ...expected, 'stair-3-4':false, 'stair-4-5':true });
    await page.evaluate(() => viewer.setInteriorSection(building, 'all'));
    expect(Object.values(await page.evaluate(() => displayGroups())).every(Boolean)).toBe(true);
    const framing=await page.evaluate(()=>{
      viewer.container.style.width='600px';viewer.resize();viewer.setInteriorSection(building,'stair-3-4');
      const view=building.interiorSections.find(s=>s.id==='stair-3-4').view;
      const nativeDistance=Math.hypot(...view.position.map((v,i)=>v-view.target[i]));
      const ratio=viewer.transition.position.distanceTo(viewer.transition.target)/nativeDistance;
      const authored=viewer.activeInterior.authoredView;viewer.setInteriorSection(building,'G');
      const floorFitCleared=!viewer.activeInterior.authoredView;viewer.container.style.width='1200px';viewer.resize();return{ratio,authored,floorFitCleared};
    });
    expect(framing.ratio).toBeCloseTo(1.25/(600/900),8);expect(framing.authored&&framing.floorFitCleared).toBe(true);
    await page.evaluate(() => viewer.setInteriorSection(building, 'stair-3-4'));
    await page.evaluate(() => viewer.select(building));
    expect(await page.locator('canvas').getAttribute('data-interior-section')).toBeNull();
    await page.evaluate(() => viewer.showInterior(building));
    await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready', 'interior-SAW');
    expect(Object.values(await page.evaluate(() => displayGroups())).every(Boolean)).toBe(true);
    await mkdir(`${output}/browser`, { recursive:true });
    await writeFile(`${output}/semantic-section-lifecycle.json`, JSON.stringify({ fallbackAndDetailMatch:true, sectionChangeRestoresWholeAssemblies:true, allAndReentryRestoreEveryGroup:true, displayGroups:Object.keys(expected) }, null, 2)+'\n');
  } finally { releaseDetail?.(); await page.evaluate(() => window.viewer?.dispose()).catch(() => {}); }
});

test('new SAW waists retain the same native geometry in overview, exterior and grouped interior', async ({ page }) => {
  test.setTimeout(150000);
  const release = await read('dist/release.json'), saved = await read('result/blender/saw-circulation242/reopened-surfaces.json');
  const expected = Object.fromEntries(saved.objects.filter(o => /Flight[34]_continuous_winding_waist/.test(o.name)).map(o => [o.name.includes('Flight3') ? 'stair-3-4' : 'stair-4-5', o.vertices.map(p => [p[0],p[2],-p[1]])]));
  const moduleUrl = Object.keys(release.assets).find(p => /^\/assets\/viewer-.*\.js$/.test(p));
  const html = `<div id="stage" style="width:400px;height:300px"></div><div id="labels"></div><script type="module">
  import {CampusViewer} from '${moduleUrl}';
  const catalogue=await(await fetch('/models/catalogue.json')).json(),building=catalogue.buildings.find(b=>b.code==='SAW');
  const viewer=new CampusViewer(document.querySelector('#stage'),document.querySelector('#labels'),catalogue.buildings,()=>{},()=>{throw Error('Context lost')});window.viewer=viewer;
  const collect=(root,displayGroup=null)=>{root.updateMatrixWorld(true);const positions=[];root.traverse(o=>{if(!o.isMesh)return;const materials=Array.isArray(o.material)?o.material:[o.material];if(!materials.some(m=>m.name.includes('SAW173_public_concrete')))return;let group=o;while(group&&!group.userData.interiorDisplayGroup)group=group.parent;if(displayGroup&&group?.userData.interiorDisplayGroup!==displayGroup)return;const p=o.geometry.attributes.position;for(let i=0;i<p.count;i++)positions.push(viewer.camera.position.clone().fromBufferAttribute(p,i).applyMatrix4(o.matrixWorld).toArray());});return positions;};
  const distance=(source,target)=>{const cell=.00025,grid=new Map();for(const p of target){const key=p.map(v=>Math.floor(v/cell)).join(',');if(!grid.has(key))grid.set(key,[]);grid.get(key).push(p);}let maximum=0;for(const p of source){const c=p.map(v=>Math.floor(v/cell));let nearest=Infinity;for(let x=-1;x<=1;x++)for(let y=-1;y<=1;y++)for(let z=-1;z<=1;z++)for(const q of grid.get([c[0]+x,c[1]+y,c[2]+z].join(','))||[])nearest=Math.min(nearest,Math.hypot(p[0]-q[0],p[1]-q[1],p[2]-q[2]));maximum=Math.max(maximum,nearest);}return maximum;};
  await viewer.load();const overview=collect(viewer.groups.get('SAW'));const exterior=collect(await viewer.loadExterior(building));const interior=(await viewer.loadAsset(building.detailedInterior.url)).scene;const expected=${JSON.stringify(expected)},proof=[];
  for(const [id,source]of Object.entries(expected)){const grouped=collect(interior,id);proof.push({id,nativeVertices:source.length,groupedVertices:grouped.length,nativeToOverview:distance(source,overview),nativeToExterior:distance(source,exterior),nativeToInterior:distance(source,grouped),interiorToNative:distance(grouped,source)});}window.parity=proof;viewer.dispose();
  </script>`;
  await page.route('**/__saw242-parity', route => route.fulfill({contentType:'text/html',body:html}));
  await page.goto('/__saw242-parity'); await page.waitForFunction(()=>window.parity,null,{timeout:90000});
  const proof=await page.evaluate(()=>window.parity);
  for(const row of proof){expect(row.groupedVertices).toBeGreaterThan(100);for(const key of ['nativeToOverview','nativeToExterior','nativeToInterior','interiorToNative'])expect(row[key],`${row.id}:${key}`).toBeLessThan(.0002);}
  await writeFile(`${output}/overview-detail-parity.json`,JSON.stringify({actualProductionGlbs:true,toleranceM:.0002,comparisons:proof},null,2)+'\n');
});
