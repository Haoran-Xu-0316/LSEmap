import {test,expect} from '@playwright/test';
import {readFile,writeFile} from 'node:fs/promises';
const folder='result/blender/stage250';
const read=async path=>JSON.parse(await readFile(path,'utf8'));

test('250 keeps unrelated buildings and every room while updating OLD approach and MAR slab',async()=>{
 const before=await read(`${folder}/catalogue-before.json`),after=await read('dist/models/catalogue.json');
 const native=await read(`${folder}/building-refinement.json`),saved=await read(`${folder}/reopened-verification.json`);
 expect(after.version).toBe('250');expect(saved.completeModelReopened).toBe(true);expect(saved.originalsVerified).toBe(8637);
 expect(native.addedObjects.sort()).toEqual(['MAR250_third_floor_with_source_lift_shafts','OLD250_long_chamfer_external_four_steps']);
 expect(native.archivedObjects.sort()).toEqual(['MAR_MAR_floor_way/1376078546_17.5','OLD_NEXT_ACCESS_external_four_steps']);expect(native.changedObjects).toEqual([]);
 const counts={exteriors:0,interiors:0,rooms:0,fallbacks:0},changed=[];
 for(const old of before.buildings){const current=after.buildings.find(b=>b.code===old.code);
  if(old.detailedExterior){if(['OLD','MAR'].includes(old.code)){expect(current.detailedExterior.sha256).not.toBe(old.detailedExterior.sha256);changed.push(old.code+' exterior');}else{expect(current.detailedExterior.sha256,old.code).toBe(old.detailedExterior.sha256);counts.exteriors++;}}
  if(old.detailedInterior){if(old.code==='MAR'){expect(current.detailedInterior.sha256).not.toBe(old.detailedInterior.sha256);changed.push('MAR public interior');}else{expect(current.detailedInterior.sha256,old.code).toBe(old.detailedInterior.sha256);counts.interiors++;}}
  for(const room of old.interiorSpaces??[]){expect(current.interiorSpaces.find(r=>r.id===room.id).detailedInterior.sha256,room.id).toBe(room.detailedInterior.sha256);counts.rooms++;}
 }
 const previous=await read(`${folder}/release-before.json`),release=await read('dist/release.json');
 for(const path of Object.keys(previous.assets).filter(p=>/^\/models\/[a-z0-9]+-interior\.glb$/.test(p))){if(path==='/models/mar-interior.glb'){expect(release.assets[path].sha256).not.toBe(previous.assets[path].sha256);changed.push('MAR fallback interior');}else{expect(release.assets[path].sha256,path).toBe(previous.assets[path].sha256);counts.fallbacks++;}}
 expect(counts).toEqual({exteriors:28,interiors:24,rooms:35,fallbacks:24});
 expect(after.buildings.find(b=>b.code==='MAR').interiorBounds.max[1]).toBeCloseTo(17.5,4);
 const gallery=await read('dist/gallery-manifest.json');expect(gallery.images).toHaveLength(203);
 expect(gallery.images.find(i=>i.name==='mar-third-lift-openings-interior').sectionId).toBe('3');expect(gallery.images.some(i=>i.name==='old-approach')).toBe(true);
 await writeFile(`${folder}/asset-scope.json`,JSON.stringify({unchanged:counts,changed,COLRemainsUnchanged:true},null,2)+'\n');
});

test('production Draco assets retain MAR shaft voids and OLD tread support',async({page})=>{
 const release=await read('dist/release.json'),module=Object.keys(release.assets).find(p=>/^\/assets\/viewer-.*\.js$/.test(p));
 const probes=await read('result/blender/mar-third250/ray-probes.json'),old=await read('result/blender/old-approach250/saved-verification.json');
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 const html=`<style>body{margin:0}#stage{width:1000px;height:800px}#labels{display:none}</style><div id="stage"></div><div id="labels"></div><script type="module">import{CampusViewer}from'${module}';const catalogue=await(await fetch('/models/catalogue.json')).json();const v=new CampusViewer(document.querySelector('#stage'),document.querySelector('#labels'),catalogue.buildings,()=>{},()=>{throw Error('Context lost')},()=>{},catalogue.sourceModelSha256);window.viewer=v;window.catalogue=catalogue;v.loadCampusExteriors=async()=>{};await v.load();await v.environmentReady;const mar=catalogue.buildings.find(b=>b.code==='MAR');v.select(mar);await v.loadExterior(mar);await v.showInterior(mar);await v.upgradeModel(mar,'interior');v.setInteriorSection(mar,'3');v.transition=null;window.ready=true;</script>`;
 try{
  await page.route('**/__campus250',route=>route.fulfill({contentType:'text/html',body:html}));await page.goto('/__campus250');await page.waitForFunction(()=>window.ready,null,{timeout:60000});
  const marProof=await page.evaluate(probes=>{
   const v=viewer,down=v.controls.target.clone().set(0,-1,0);v.scene.updateMatrixWorld(true);v.raycaster.far=.12;
   const roots=[v.groups.get('MAR'),v.exteriors.get('MAR'),v.interiors.get('MAR:default'),v.activeDetail.group];const results=[];
   for(const root of roots){
    const hits=point=>{v.raycaster.set(v.controls.target.clone().set(point[0],17.55,-point[1]),down);return v.raycaster.intersectObject(root,true);};
    const filledVoids=probes.voids.filter(p=>hits(p.point).length).length;
    const missingBearings=probes.bearings.filter(p=>!hits(p.point).length).length;
    const missingStrips=probes.access.filter(p=>!hits(p).length).length;
    results.push({filledVoids,missingBearings,missingStrips});
   }
   v.raycaster.far=Infinity;return{assets:results,assetOrder:['campus','exterior','fallback interior','detailed interior'],voidRaysPerAsset:probes.voids.length,bearingRaysPerAsset:probes.bearings.length,section:v.canvas.dataset.interiorSection,mode:v.mode};
  },probes);
  for(const r of marProof.assets)expect(r).toEqual({filledVoids:0,missingBearings:0,missingStrips:0});expect(marProof.section).toBe('3');
  await page.evaluate(async()=>{const b=catalogue.buildings.find(b=>b.code==='OLD');viewer.select(b);await viewer.upgradeModel(b,'exterior');viewer.transition=null;});
  const oldProof=await page.evaluate(samples=>{
   const v=viewer,group=v.exteriors.get('OLD'),down=v.controls.target.clone().set(0,-1,0);v.scene.updateMatrixWorld(true);const errors=[];
   for(const sample of samples){v.raycaster.set(v.controls.target.clone().set(sample.point[0],sample.point[2]+.1,-sample.point[1]),down);
    const hits=v.raycaster.intersectObject(group,true);const hit=hits.find(h=>{const m=Array.isArray(h.object.material)?h.object.material[h.face.materialIndex]:h.object.material;return m.name.includes('ACCESS_stone');});
    if(!hit||Math.abs(hit.point.y-sample.newSupportZ)>.005)errors.push({sample,actual:hit?.point.y??null});
   }
   return{samples:samples.length,errors};
  },old.footSupportSamples);
  expect(oldProof.errors).toEqual([]);expect(errors).toEqual([]);
  await writeFile(`${folder}/production-geometry.json`,JSON.stringify({mar:marProof,old:oldProof,errors},null,2)+'\n');
 }finally{await page.evaluate(()=>window.viewer?.dispose()).catch(()=>{});}
});
