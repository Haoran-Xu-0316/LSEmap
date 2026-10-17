import { test, expect } from '@playwright/test';
import { readFile, writeFile } from 'node:fs/promises';
const output = 'result/blender/stage243';
const read = async path => JSON.parse(await readFile(path, 'utf8'));

test('243 preserves every detailed building, public interior and room asset', async () => {
  const before = await read(`${output}/catalogue-before.json`);
  const after = await read('dist/models/catalogue.json');
  const native = await read(`${output}/native-verification.json`);
  expect(after.version).toBe('243');
  expect(native.originalObjectsVerified).toBe(8619);
  expect(native.addedObjectsVerified).toBe(2);
  expect(native.protectedRooms).toBe(35);
  let exteriors = 0, interiors = 0, rooms = 0;
  for (const original of before.buildings) {
    const current = after.buildings.find(b => b.code === original.code);
    for (const key of ['detailedExterior', 'detailedInterior']) {
      if (!original[key]) continue;
      expect(current[key].sha256, `${original.code}:${key}`).toBe(original[key].sha256);
      if (key === 'detailedExterior') exteriors++; else interiors++;
    }
    for (const room of original.interiorSpaces ?? []) {
      rooms++;
      expect(current.interiorSpaces.find(r => r.id === room.id).detailedInterior.sha256, room.id).toBe(room.detailedInterior.sha256);
    }
  }
  expect([exteriors, interiors, rooms]).toEqual([30, 25, 35]);
  const oldRelease = await read(`${output}/release-before.json`), release = await read('dist/release.json');
  const fallbacks = Object.keys(oldRelease.assets).filter(path => /^\/models\/[a-z0-9]+-interior\.glb$/.test(path));
  for (const path of fallbacks) expect(release.assets[path].sha256, path).toBe(oldRelease.assets[path].sha256);
  expect(fallbacks).toHaveLength(25);
  await writeFile(`${output}/asset-scope.json`, JSON.stringify({ detailedExteriorsUnchanged:exteriors, publicInteriorsUnchanged:interiors, roomsUnchanged:rooms, fallbackInteriorsUnchanged:fallbacks.length }, null, 2)+'\n');
});

test('the production Draco campus contains the repaired street tops and support', async ({ page }) => {
  const release = await read('dist/release.json');
  const moduleUrl = Object.keys(release.assets).find(p => /^\/assets\/viewer-.*\.js$/.test(p));
  const html = `<style>body{margin:0}#stage{width:960px;height:768px}#labels{display:none}</style><div id="stage"></div><div id="labels"></div><script type="module">
  import {CampusViewer} from '${moduleUrl}';
  const catalogue=await(await fetch('/models/catalogue.json')).json();
  const viewer=new CampusViewer(document.querySelector('#stage'),document.querySelector('#labels'),catalogue.buildings,()=>{},()=>{throw Error('Context lost')},()=>{},catalogue.sourceModelSha256);
  window.viewer=viewer;await viewer.load();await viewer.environmentReady;
  const site=viewer.groups.get('SITE');site.updateMatrixWorld(true);
  const checks=[];
  for(const [x,y,expected] of [[-2.8433,-123.9301,.05],[-4.272,-128.2704,.05],[-3.1869,-120.6436,.018]]){
    viewer.raycaster.set(viewer.camera.position.clone().set(x,3,-y),viewer.camera.position.clone().set(0,-1,0));
    const hits=viewer.raycaster.intersectObject(site,true).filter(hit=>hit.point.y<.1);
    const top=hits[0]?.point.y;
    checks.push({nativeXY:[x,y],expected,top,topLayers:hits.filter(hit=>Math.abs(hit.point.y-top)<.0001).length});
  }
  viewer.camera.position.set(.3,6,142);viewer.controls.target.set(-1.5,1.6,107);viewer.controls.update();viewer.transition=null;viewer.needsRender=true;window.streetChecks=checks;
  </script>`;
  try {
    await page.route('**/__street243', route => route.fulfill({ contentType:'text/html', body:html }));
    await page.goto('/__street243');
    await page.waitForFunction(() => window.streetChecks, null, {timeout:60000});
    const checks = await page.evaluate(() => window.streetChecks);
    for (const row of checks) {
      expect(row.top, JSON.stringify(row.nativeXY)).toBeCloseTo(row.expected, 3);
      expect(row.topLayers, JSON.stringify(row.nativeXY)).toBe(1);
    }
    await writeFile(`${output}/production-street-contacts.json`, JSON.stringify({ actualProductionDracoModel:true, checks }, null, 2)+'\n');
    await page.screenshot({path:`${output}/production-street.png`});
  } finally { await page.evaluate(() => window.viewer?.dispose()).catch(() => {}); }
});
