import {test,expect} from '@playwright/test';
import {readFile,writeFile} from 'node:fs/promises';
const folder='result/blender/stage249';
const read=async path=>JSON.parse(await readFile(path,'utf8'));

test('249 preserves all rooms and unrelated architecture while updating OLD portal',async()=>{
  const before=await read(`${folder}/catalogue-before.json`),after=await read('dist/models/catalogue.json');
  const native=await read(`${folder}/building-refinement.json`),component=await read('result/blender/old-exterior249/verification.json');
  expect(after.version).toBe('249');expect(native.addedObjects).toEqual(['OLD249_two_horizontal_portal_grille_rails']);expect(native.archivedObjects).toEqual([]);expect(native.changedObjects).toEqual([]);
  expect(component.originalObjectsUnchanged).toBe(8636);expect(component.originalMaterialGraphsUnchanged).toBe(2341);expect(component.protectedRooms).toBe(35);expect(component.closedManifoldSolids).toBe(2);
  let exteriors=0,interiors=0,rooms=0;const changed=[];
  for(const old of before.buildings){const current=after.buildings.find(b=>b.code===old.code);
    if(old.detailedExterior){if(old.code==='OLD'){expect(current.detailedExterior.sha256).not.toBe(old.detailedExterior.sha256);changed.push('OLD exterior');}else{expect(current.detailedExterior.sha256,old.code).toBe(old.detailedExterior.sha256);exteriors++;}}
    if(old.detailedInterior){if(current.detailedInterior.sha256!==old.detailedInterior.sha256){expect(old.code).toBe('OLD');changed.push('OLD public interior');}else interiors++;}
    for(const room of old.interiorSpaces??[]){expect(current.interiorSpaces.find(r=>r.id===room.id).detailedInterior.sha256,room.id).toBe(room.detailedInterior.sha256);rooms++;}
  }
  expect(exteriors).toBe(29);expect(rooms).toBe(35);expect(interiors).toBeGreaterThanOrEqual(24);
  const previous=await read(`${folder}/release-before.json`),current=await read('dist/release.json');let fallbacks=0;
  for(const path of Object.keys(previous.assets).filter(p=>/^\/models\/[a-z0-9]+-interior\.glb$/.test(p))){if(previous.assets[path].sha256!==current.assets[path].sha256){expect(path).toBe('/models/old-interior.glb');changed.push('OLD interior fallback');}else fallbacks++;}
  expect(fallbacks).toBeGreaterThanOrEqual(24);
  const gallery=await read('dist/gallery-manifest.json');expect(gallery.images).toHaveLength(201);expect(gallery.images.some(i=>i.name==='old-portal-grille')).toBe(true);
  await writeFile(`${folder}/asset-scope.json`,JSON.stringify({unchangedExteriors:exteriors,unchangedDefaultInteriors:interiors,unchangedRooms:rooms,unchangedFallbacks:fallbacks,changed,privateCOLNotIntegrated:true},null,2)+'\n');
});

test('production OLD contains both grille rails with clear gaps and unchanged door panes',async({page})=>{
  const release=await read('dist/release.json'),module=Object.keys(release.assets).find(p=>/^\/assets\/viewer-.*\.js$/.test(p));const shape=await read('result/blender/old-exterior249/shape-plan.json');
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  const html=`<style>body{margin:0}#stage{width:1000px;height:800px}#labels{display:none}</style><div id="stage"></div><div id="labels"></div><script type="module">import{CampusViewer}from'${module}';const catalogue=await(await fetch('/models/catalogue.json')).json();const v=new CampusViewer(document.querySelector('#stage'),document.querySelector('#labels'),catalogue.buildings,()=>{},()=>{throw Error('Context lost')},()=>{},catalogue.sourceModelSha256);window.viewer=v;v.loadCampusExteriors=async()=>{};await v.load();await v.environmentReady;const old=catalogue.buildings.find(b=>b.code==='OLD');v.select(old);await v.upgradeModel(old,'exterior');v.transition=null;window.ready=true;</script>`;
  try{await page.route('**/__portal249',route=>route.fulfill({contentType:'text/html',body:html}));await page.goto('/__portal249');await page.waitForFunction(()=>window.ready,null,{timeout:60000});
    const proof=await page.evaluate(async shape=>{const v=window.viewer,group=v.exteriors.get('OLD');v.scene.updateMatrixWorld(true);const right=[.47449132800102234,.8802601099014282],normal=[.8802601099014282,-.47449132800102234];
      const point=(station,depth,height)=>v.controls.target.clone().set(right[0]*station+normal[0]*depth,height,-right[1]*station-normal[1]*depth);
      const direction=v.controls.target.clone().set(-normal[0],0,normal[1]);const hits=[],gaps=[];
      const first=(station,height)=>{v.raycaster.set(point(station,shape.estimatedRailNormalRange[1]+1,height),direction);return v.raycaster.intersectObject(group,true)[0];};
      for(const fraction of [.12,.32,.68,.88]){const station=shape.nativeClearWidth[0]+(shape.nativeClearWidth[1]-shape.nativeClearWidth[0])*fraction;
        for(const height of shape.railCentreZ){const hit=first(station,height);if(!hit)throw Error('Missing grille rail');hits.push({distance:hit.distance,material:(Array.isArray(hit.object.material)?hit.object.material[hit.face.materialIndex]:hit.object.material).name});}
        const hit=first(station,(shape.railCentreZ[0]+shape.railCentreZ[1])/2);gaps.push(hit?.distance??Infinity);
      }
      const jobs=await(await fetch('/gallery-manifest.json')).json();const view=jobs.images.find(i=>i.name==='old-portal-grille').view;v.camera.fov=view.fov;v.updateCameraProjection();v.moveCamera(v.camera.position.clone().fromArray(view.position),v.controls.target.clone().fromArray(view.target),false);v.renderPipeline.render({moving:false,stabilize:false});v.renderer.getContext().finish();return{hits,gaps};},shape);
    expect(proof.hits).toHaveLength(8);for(const hit of proof.hits){expect(Math.abs(hit.distance-1)).toBeLessThan(.003);expect(hit.material).not.toMatch(/glass|glaz/i);}for(const gap of proof.gaps)expect(gap).toBeGreaterThan(1.1);
    expect(errors).toEqual([]);await writeFile(`${folder}/production-portal.json`,JSON.stringify(proof,null,2)+'\n');await page.locator('canvas').screenshot({path:`${folder}/production-portal.png`});
  }finally{await page.evaluate(()=>window.viewer?.dispose()).catch(()=>{});}
});
