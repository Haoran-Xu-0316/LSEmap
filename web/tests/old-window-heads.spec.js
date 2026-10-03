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
test('OLD corrected window head geometry is identical in overview and detail',async()=>{
 const proof=await read('result/blender/stage136/saved-verification.json'),catalogue=await read('dist/models/catalogue.json');
 expect(catalogue.version).toBe('136');expect(catalogue.sourceModelSha256).toBe(proof.sourceModelSha256);
 expect(proof.retainedOriginalObjects).toBe(5566);expect(proof.ownedObjects).toEqual(['OLD_NEXT_CLARE_sealed_window_head_stone']);
 expect(proof.savedSceneReopened).toBe(true);expect(proof.originalGeometryRetained).toBe(true);expect(proof.unrelatedVisibilityPreserved).toBe(true);
 const building=catalogue.buildings.find(b=>b.code==='OLD'),accepted=new Set(proof.ownedMaterialNames.OLD),summaries=[];
 for(const url of ['/models/campus.glb',building.detailedExterior.url]){
  const bytes=await readFile('dist'+url),glb=JSON.parse(bytes.subarray(20,20+bytes.readUInt32LE(12))),primitives=[];
  for(const mesh of glb.meshes)for(const p of mesh.primitives){
   const m=glb.materials[p.material];if(!accepted.has(m.name.replace(/^WEB_(DETAIL_)?/,'')))continue;
   primitives.push({material:m.name.replace('WEB_DETAIL_','WEB_'),geometry:geometryDigest(glb,bytes,p),pbr:m.pbrMetallicRoughness,finish:m.extras?.surfaceDetail});
  }
  expect(primitives.length).toBeGreaterThan(0);summaries.push(primitives);
 }
 expect(summaries[0]).toEqual(summaries[1]);
 const before=await read('result/blender/stage136/catalogue-before.json');
 for(const b of catalogue.buildings){const old=before.buildings.find(o=>o.code===b.code);
  expect(b.detailedInterior,b.code).toEqual(old.detailedInterior);expect(b.interiorSpaces,b.code).toEqual(old.interiorSpaces);
  if(b.code!=='OLD')expect(b.detailedExterior,b.code).toEqual(old.detailedExterior);
 }
 const audit=await read('result/blender/old_facade_next/audit.json'),verification=await read('result/blender/old_facade_next/verification.json');
 expect(audit.changes).toHaveLength(1);expect(audit.changes[0].changedVertices).toBe(20);expect(audit.changes[0].unchangedVertices).toBe(1068);
 expect(audit.beforeProbes.slice(0,10).every(p=>p.firstObject===null)).toBe(true);
 expect(audit.afterProbes.slice(0,10).every(p=>p.firstObject===proof.ownedObjects[0])).toBe(true);
 expect(audit.afterProbes.slice(10).map(p=>({...p,firstObject:p.firstObject?.replace(proof.ownedObjects[0],audit.archivedObjects[0])}))).toEqual(audit.beforeProbes.slice(10));
 expect(verification.savedComponentReopened).toBe(true);expect(verification.ownedTopologyUVMaterialSlotsMatchOriginal).toBe(true);expect(verification.reloadedProbes).toEqual(audit.afterProbes);
 const rebuild=await read('result/blender/stage136/rebuild/rebuild-verification.json');expect(rebuild.exactFingerprintMatch).toBe(true);expect(rebuild.objects).toBe(5567);
 const recovered=await read('result/blender/stage136/component-rebuild/verification.json');expect(recovered.reloadedProbes).toEqual(verification.reloadedProbes);expect(recovered.originalObjectCount).toBe(5566);
});
test('Pending library and street hypotheses do not archive objects',async()=>{
 for(const folder of ['lrb_facade_next','houghton_access_next']){
  const audit=await read('result/blender/'+folder+'/audit.json');expect(audit.ownedObjects).toEqual([]);expect(audit.archivedObjects).toEqual([]);
 }
});
test('OLD exterior and retained interior load on desktop and phone',async({page})=>{
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 for(const width of [1440,390]){
  await page.setViewportSize({width,height:1000});await page.goto('/#OLD');
  await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-OLD',{timeout:60000});await expect(page.locator('#fallback')).toBeHidden();
  await page.locator('#interior-view').click();await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','interior-OLD',{timeout:60000});
 }
 expect(errors).toEqual([]);
});
