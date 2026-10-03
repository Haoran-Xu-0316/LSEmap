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
test('CBG and OLD accepted components retain exact geometry across both scales',async()=>{
 const proof=await read('result/blender/stage128/saved-verification.json'),catalogue=await read('dist/models/catalogue.json');
 expect(catalogue.version).toBe('128');expect(catalogue.sourceModelSha256).toBe(proof.sourceModelSha256);
 expect(proof.savedSceneReopened).toBe(true);expect(proof.unrelatedVisibilityPreserved).toBe(true);expect(proof.retainedOriginalObjects).toBe(5522);expect(proof.ownedObjects.length).toBeGreaterThan(4);
 for(const code of ['CBG','OLD']){
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
 const before=await read('result/blender/stage128/catalogue-before.json');
 for(const b of catalogue.buildings){const old=before.buildings.find(o=>o.code===b.code);
  expect(b.detailedInterior,b.code).toEqual(old.detailedInterior);expect(b.interiorSpaces,b.code).toEqual(old.interiorSpaces);
  if(!['CBG','OLD'].includes(b.code))expect(b.detailedExterior,b.code).toEqual(old.detailedExterior);
 }
 const glazing=await read('result/blender/cbg_glazing_next/verification.json');
 expect(glazing.savedComponentReopened).toBe(true);
 expect(glazing.originalGeometryPreserved).toBe(true);
 expect(glazing.sourceLuminanceRetained).toBe(true);
 expect(glazing.sourceTransparencyRetained).toBe(true);
 const audit=await read('result/blender/cbg_glazing_next/audit.json');
 const light=c=>c[0]*.2126+c[1]*.7152+c[2]*.0722;
 expect(light(audit.newColorLinear)).toBeCloseTo(light(audit.oldColorLinear),7);
 expect(audit.webOpacity).toBe(.56);
 const old=await read('result/blender/old_glazing_next/verification.json');
 expect(old.savedComponentReopened).toBe(true);
 expect(old.originalGeometryPreserved).toBe(true);
 expect(old.visibleElevationNewBlueTransomFirstHits).toBe(2);
 expect(old.visibleElevationRetainedGlassFirstHits).toBe(4);

});
test('CBG and OLD exterior and retained interior load on desktop and phone',async({page})=>{
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 for(const width of [1440,390])for(const code of ['CBG','OLD']){
  await page.setViewportSize({width,height:1000});await page.goto('/#'+code);
  await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-'+code,{timeout:60000});
  await expect(page.locator('#fallback')).toBeHidden();await page.locator('#interior-view').click();
  await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','interior-'+code,{timeout:60000});
 }
 expect(errors).toEqual([]);
});
