import { test, expect } from '@playwright/test';
import { readFile, writeFile } from 'node:fs/promises';
const output = 'result/blender/stage246';
const read = async path => JSON.parse(await readFile(path, 'utf8'));

test('246 changes only the CON exterior while preserving rooms and all other exteriors', async () => {
  const before = await read(`${output}/catalogue-before.json`);
  const after = await read('dist/models/catalogue.json');
  const native = await read(`${output}/native-verification.json`);
  expect(after.version).toBe('246');
  expect(native.originalObjectsVerified).toBe(8621);
  expect(native.addedObjectsVerified).toBe(13);
  expect(native.protectedRooms).toBe(35);
  let exteriors = 0, interiors = 0, rooms = 0;
  for (const original of before.buildings) {
    const current = after.buildings.find(b => b.code === original.code);
    if (original.detailedExterior) {
      if (original.code === 'CON') expect(current.detailedExterior.sha256).not.toBe(original.detailedExterior.sha256);
      else { expect(current.detailedExterior.sha256, original.code).toBe(original.detailedExterior.sha256); exteriors++; }
    }
    if (original.detailedInterior) { expect(current.detailedInterior.sha256, original.code).toBe(original.detailedInterior.sha256); interiors++; }
    for (const room of original.interiorSpaces ?? []) {
      rooms++;
      expect(current.interiorSpaces.find(r => r.id === room.id).detailedInterior.sha256, room.id).toBe(room.detailedInterior.sha256);
    }
  }
  expect([exteriors, interiors, rooms]).toEqual([29, 25, 35]);
  const oldRelease = await read(`${output}/release-before.json`), release = await read('dist/release.json');
  const fallbacks = Object.keys(oldRelease.assets).filter(path => /^\/models\/[a-z0-9]+-interior\.glb$/.test(path));
  for (const path of fallbacks) expect(release.assets[path].sha256, path).toBe(oldRelease.assets[path].sha256);
  expect(fallbacks).toHaveLength(25);
  await writeFile(`${output}/asset-scope.json`, JSON.stringify({ detailedExteriorsUnchanged:exteriors, publicInteriorsUnchanged:interiors, roomsUnchanged:rooms, fallbackInteriorsUnchanged:fallbacks.length, changedExterior:'CON' }, null, 2)+'\n');
});

test('production overview and detailed CON both distinguish80 transparent windows and9 opaque source modules', async ({ page }) => {
  const release = await read('dist/release.json');
  const moduleUrl = Object.keys(release.assets).find(p => /^\/assets\/viewer-.*\.js$/.test(p));
  const registration = await read('result/blender/con-registration244/registration-plan.json');
  const source = await read(registration.sourcePlan);
  const html = `<style>body{margin:0}#stage{width:960px;height:768px}#labels{display:none}</style><div id="stage"></div><div id="labels"></div><script type="module">
  import {CampusViewer} from '${moduleUrl}';
  const catalogue=await(await fetch('/models/catalogue.json')).json();
  const viewer=new CampusViewer(document.querySelector('#stage'),document.querySelector('#labels'),catalogue.buildings,()=>{},()=>{throw Error('Context lost')},()=>{},catalogue.sourceModelSha256);
  window.viewer=viewer; viewer.loadCampusExteriors=async()=>{};
  await viewer.load(); await viewer.environmentReady;
  const con=catalogue.buildings.find(b=>b.code==='CON');
  const detail=await viewer.loadExterior(con);
  window.productionRoots=[viewer.groups.get('CON'),detail];window.productionReady=true;
  </script>`;
  try {
    await page.route('**/__con244', route => route.fulfill({ contentType:'text/html', body:html }));
    await page.goto('/__con244');
    await page.waitForFunction(() => window.productionReady, null, {timeout:60000});
    const proof = await page.evaluate(({registration,source}) => {
      const checks=[];
      for(let rootIndex=0;rootIndex<productionRoots.length;rootIndex++){
        const root=productionRoots[rootIndex];root.updateMatrixWorld(true);
        let checked=0; const finishes=[];
        for(const opening of source.openings){
          const [x0,y0,x1,y1]=opening.sourceBounds;
          const x=x0+(x1-x0)*.37, y=y0+(y1-y0)*.61;
          const station=(x-source.sourceOrigin[0])*source.metresPerPoint*registration.horizontalFit;
          const index=Number(station>registration.segmentLengthsM[0]);
          const along=station-(index?registration.segmentLengthsM[0]:0);
          const a=registration.frontage[index],b=registration.frontage[index+1],len=registration.segmentLengthsM[index];
          const tx=(b[0]-a[0])/len,ty=(b[1]-a[1])/len,nx=-ty,ny=tx;
          const px=a[0]+tx*along,py=a[1]+ty*along;
          let z=(source.sourceOrigin[1]-y)*source.metresPerPoint;
          if(opening.role==='door'){
            const bottom=(source.sourceOrigin[1]-y1)*source.metresPerPoint,head=(source.sourceOrigin[1]-y0)*source.metresPerPoint;
            z=head-(head-z)*(head-registration.doorThresholdM)/(head-bottom);
          }
          const origin=viewer.camera.position.clone().set(px-nx,z,-(py-ny));
          const direction=viewer.camera.position.clone().set(nx,0,-ny);
          viewer.raycaster.set(origin,direction);
          const hits=viewer.raycaster.intersectObject(root,true);
          const oldLayers=hits.filter(hit=>{
            const m=Array.isArray(hit.object.material)?hit.object.material[hit.face.materialIndex]:hit.object.material;
            return hit.distance<1.59 && m.userData.webSurfaceRole==='glazing' && !m.name.includes('CON244_');
          });
          if(oldLayers.length)throw Error('Old glazing overlaps new source module: '+opening.id);
          const hit=hits.find(hit=>{
            const m=Array.isArray(hit.object.material)?hit.object.material[hit.face.materialIndex]:hit.object.material;
            return m.name.includes(opening.role==='window'?'CON244_backed_window_glass':'CON244_unverified_ground_infill');
          });
          if(!hit)throw Error('Missing outward pane: '+rootIndex+':'+opening.id);
          if(Math.abs(hit.distance-1.14)>.004)throw Error('Wrong pane depth: '+opening.id+':'+hit.distance);
          const m=Array.isArray(hit.object.material)?hit.object.material[hit.face.materialIndex]:hit.object.material;
          finishes.push({role:opening.role,opacity:m.opacity,transparent:m.transparent,side:m.side,metalness:m.metalness});checked++;
        }
        checks.push({view:rootIndex?'detailed':'overview',checked,finishes});
      }
      const con=viewer.buildings.find(b=>b.code==='CON');viewer.select(con);viewer.transition=null;
      viewer.moveCamera(viewer.camera.position.clone().set(52,18,111),viewer.controls.target.clone().set(-7,16.5,111),false);
      viewer.needsRender=true;
      return {actualProductionDracoModels:true,checks};
    },{registration,source});
    for(const row of proof.checks){
      expect(row.checked).toBe(89);
      for(const material of row.finishes){
        expect(material.opacity).toBeCloseTo(material.role==='window'?.44:1);expect(material.transparent).toBe(material.role==='window');
        expect(material.side).toBe(2);expect(material.metalness).toBe(0);
      }
    }
    await writeFile(`${output}/production-con-panes.json`,JSON.stringify(proof,null,2)+'\n');
    await page.locator('canvas').screenshot({path:`${output}/production-con.png`});
  } finally { await page.evaluate(() => window.viewer?.dispose()).catch(() => {}); }
});
