import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
const read=async path=>JSON.parse(await readFile(path,'utf8'));
function geometryDigest(glb,bytes,primitive){
 const extension=primitive.extensions?.KHR_draco_mesh_compression;
 if(!extension)throw Error('Expected production Draco geometry');
 const view=glb.bufferViews[extension.bufferView],start=28+bytes.readUInt32LE(12)+(view.byteOffset??0);
 const meta=index=>{const a=glb.accessors[index];return {count:a.count,type:a.type,componentType:a.componentType,min:a.min,max:a.max};};
 return {sha256:createHash('sha256').update(bytes.subarray(start,start+view.byteLength)).digest('hex'),decoderAttributes:extension.attributes,indices:meta(primitive.indices),attributes:Object.fromEntries(Object.entries(primitive.attributes).map(([k,v])=>[k,meta(v)]))};
}
test('CON accepted components retain exact geometry across both scales',async()=>{
 const proof=await read('result/blender/stage133/saved-verification.json'),catalogue=await read('dist/models/catalogue.json');
 expect(catalogue.version).toBe('133');expect(catalogue.sourceModelSha256).toBe(proof.sourceModelSha256);
 expect(proof.savedSceneReopened).toBe(true);expect(proof.unrelatedVisibilityPreserved).toBe(true);expect(proof.retainedOriginalObjects).toBe(5552);expect(proof.ownedObjects.length).toBe(7);
 for(const code of ['CON']){
  const building=catalogue.buildings.find(b=>b.code===code),summaries=[],accepted=new Set(proof.ownedMaterialNames[code]);
  for(const url of ['/models/campus.glb',building.detailedExterior.url]){
   const bytes=await readFile('dist'+url),glb=JSON.parse(bytes.subarray(20,20+bytes.readUInt32LE(12))),primitives=[];
   for(const mesh of glb.meshes)for(const p of mesh.primitives){
    const m=glb.materials[p.material];if(!accepted.has(m.name.replace(/^WEB_(DETAIL_)?/,'')))continue;
    primitives.push({material:m.name.replace('WEB_DETAIL_','WEB_'),geometry:geometryDigest(glb,bytes,p),pbr:m.pbrMetallicRoughness,finish:m.extras?.surfaceDetail});
   }
   expect(primitives.length).toBeGreaterThan(0);summaries.push(primitives);
  }
  expect(summaries[0],code).toEqual(summaries[1]);
 }
 const before=await read('result/blender/stage133/catalogue-before.json');
 for(const b of catalogue.buildings){const old=before.buildings.find(o=>o.code===b.code);
  expect(b.detailedInterior,b.code).toEqual(old.detailedInterior);expect(b.interiorSpaces,b.code).toEqual(old.interiorSpaces);
  if(!['CON'].includes(b.code))expect(b.detailedExterior,b.code).toEqual(old.detailedExterior);
 }
 const component=await read('result/blender/con_portal_window_next/verification.json');
 expect(component.savedComponentReopened).toBe(true);expect(component.originalGeometryPreserved).toBe(true);
 expect(component.reloadedProbes).toHaveLength(12);
 expect(component.reloadedProbes.slice(0,4).every(p=>p.firstObject==='CON_NEXT_PORTAL_WINDOW_recessed_glass')).toBe(true);
 expect(component.reloadedProbes.slice(4,8).every(p=>p.firstObject==='CON_NEXT_PORTAL_WINDOW_stone_spandrels')).toBe(true);
 const audit=await read('result/blender/con_portal_window_next/audit.json');
 expect(audit.windowRegistration.newHeight).toBeLessThan(audit.windowRegistration.oldHeight);
 expect(audit.windowRegistration.newTransomFraction).toBeCloseTo(audit.references[0].pixelRegistration.transomFractionFromSillApprox,2);
 expect(audit.afterProbes.slice(8).map(p=>p.firstObject.replace('CON_NEXT_PORTAL_WINDOW_','CON_D4_'))).toEqual(audit.beforeProbes.slice(8).map(p=>p.firstObject));
 const rebuild=await read('result/blender/stage133/rebuild/rebuild-verification.json');
 expect(rebuild.exactFingerprintMatch).toBe(true);expect(rebuild.objects).toBe(5559);
 const fallback=await read('result/blender/stage133/con-rebuild/verification.json');
 expect(fallback.savedComponentReopened).toBe(true);expect(fallback.originalGeometryPreserved).toBe(true);
 expect(fallback.reloadedProbes).toEqual(component.reloadedProbes);




});
test('CON exterior and retained interior load on desktop and phone',async({page})=>{
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 for(const width of [1440,390])for(const code of ['CON']){
  await page.setViewportSize({width,height:1000});await page.goto('/#'+code);
  await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-'+code,{timeout:60000});
  await expect(page.locator('#fallback')).toBeHidden();await page.locator('#interior-view').click();
  await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','interior-'+code+':con-methodology',{timeout:60000});
 }
 expect(errors).toEqual([]);
});
