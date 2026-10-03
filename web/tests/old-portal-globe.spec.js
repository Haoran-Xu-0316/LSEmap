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
test('OLD accepted components retain exact geometry across both scales',async()=>{
 const proof=await read('result/blender/stage134/saved-verification.json'),catalogue=await read('dist/models/catalogue.json');
 expect(catalogue.version).toBe('134');expect(catalogue.sourceModelSha256).toBe(proof.sourceModelSha256);
 expect(proof.savedSceneReopened).toBe(true);expect(proof.unrelatedVisibilityPreserved).toBe(true);expect(proof.retainedOriginalObjects).toBe(5559);expect(proof.ownedObjects.length).toBe(2);
 for(const code of ['OLD']){
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
 const before=await read('result/blender/stage134/catalogue-before.json');
 for(const b of catalogue.buildings){const old=before.buildings.find(o=>o.code===b.code);
  expect(b.detailedInterior,b.code).toEqual(old.detailedInterior);expect(b.interiorSpaces,b.code).toEqual(old.interiorSpaces);
  if(!['OLD'].includes(b.code))expect(b.detailedExterior,b.code).toEqual(old.detailedExterior);
 }
 const component=await read('result/blender/old_portal_overlap_next/verification.json');
 expect(component.savedComponentReopened).toBe(true);expect(component.originalGeometryPreserved).toBe(true);
 expect(component.reloadedProbes).toHaveLength(48);
 expect(component.stoneFirstWindowHitsBefore).toBe(16);expect(component.stoneFirstWindowHitsAfter).toBe(0);
 const audit=await read('result/blender/old_portal_overlap_next/audit.json');
 expect(audit.changedVertices).toBe(48);expect(audit.unchangedOuterVertices).toBe(48);
 const rebuild=await read('result/blender/stage134/rebuild/rebuild-verification.json');
 expect(rebuild.exactFingerprintMatch).toBe(true);expect(rebuild.objects).toBe(5561);
 const recovered=await read('result/blender/stage134/old-rebuild/verification.json');
 expect(recovered.savedComponentReopened).toBe(true);expect(recovered.reloadedProbes).toEqual(component.reloadedProbes);
});
test('India texture preserves labels and other countries in the exported campus',async()=>{
 const audit=await read('result/blender/globe_india_next/texture-verification.json');
 const proof=await read('result/blender/globe_india_next/verification.json');
 expect(proof.savedComponentReopened).toBe(true);expect(proof.candidateGeometryMatchesSource).toBe(true);
 expect(proof.meshUVTransformAndPolygonSlotsPreserved).toBe(true);expect(proof.radialFirstHits).toHaveLength(6);
 const recovered=await read('result/blender/stage134/globe-rebuild/verification.json');
 expect(recovered.originalGeometryPreserved).toBe(true);expect(recovered.radialFirstHits).toEqual(proof.radialFirstHits);
 expect(audit.changedPixels).toBeGreaterThan(1000);
 for(const field of ['outsideCountryUnchanged','nonFillPixelsUnchanged','allUnselectedPixelsUnchanged','AustraliaCorrectionPreserved'])expect(audit[field],field).toBe(true);
 const bytes=await readFile('dist/models/campus.glb');const len=bytes.readUInt32LE(12),glb=JSON.parse(bytes.subarray(20,20+len));
 expect(glb.images).toHaveLength(1);const view=glb.bufferViews[glb.images[0].bufferView];
 const start=28+len+(view.byteOffset??0);const hash=createHash('sha256').update(bytes.subarray(start,start+view.byteLength)).digest('hex');
 expect(hash).toBe(audit.candidateSha256);
 const catalogue=await read('dist/models/catalogue.json');expect(catalogue.generatedTextures[0].sha256).toBe(hash);
});
test('OLD exterior and retained interior load on desktop and phone',async({page})=>{
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 for(const width of [1440,390])for(const code of ['OLD']){
  await page.setViewportSize({width,height:1000});await page.goto('/#'+code);
  await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-'+code,{timeout:60000});
  await expect(page.locator('#fallback')).toBeHidden();await page.locator('#interior-view').click();
  await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','interior-'+code,{timeout:60000});
 }
 expect(errors).toEqual([]);
});
