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
test('OLD and SAW accepted components retain exact geometry across both scales',async()=>{
 const proof=await read('result/blender/stage125/saved-verification.json'),catalogue=await read('dist/models/catalogue.json');
 expect(catalogue.version).toBe('125');expect(catalogue.sourceModelSha256).toBe(proof.sourceModelSha256);
 expect(proof.savedSceneReopened).toBe(true);expect(proof.unrelatedVisibilityPreserved).toBe(true);expect(proof.retainedOriginalObjects).toBe(5494);expect(proof.ownedObjects).toHaveLength(4);
 for(const code of ['OLD','SAW']){
  const building=catalogue.buildings.find(b=>b.code===code),summaries=[];
  for(const url of ['/models/campus.glb',building.detailedExterior.url]){
   const bytes=await readFile('dist'+url),glb=JSON.parse(bytes.subarray(20,20+bytes.readUInt32LE(12))),primitives=[];
   for(const mesh of glb.meshes)for(const p of mesh.primitives){
    const m=glb.materials[p.material];if(!m.name.includes(code+'_NEXT_'))continue;
    primitives.push({material:m.name.replace('WEB_DETAIL_','WEB_'),geometry:geometryDigest(glb,bytes,p),pbr:m.pbrMetallicRoughness,finish:m.extras?.surfaceDetail});
   }
   expect(primitives.length).toBeGreaterThan(0);summaries.push(primitives);
  }
  expect(summaries[0],code).toEqual(summaries[1]);
 }
 const before=await read('result/blender/stage125/catalogue-before.json');
 for(const b of catalogue.buildings){const old=before.buildings.find(o=>o.code===b.code);
  expect(b.detailedInterior,b.code).toEqual(old.detailedInterior);expect(b.interiorSpaces,b.code).toEqual(old.interiorSpaces);
  if(!['OLD','SAW'].includes(b.code))expect(b.detailedExterior,b.code).toEqual(old.detailedExterior);
 }
 const old=await read('result/blender/old_mansard_next/verification.json'),saw=await read('result/blender/saw_exterior_next/verification.json');
 expect(old.correctedPhotographedWindows).toBe(10);expect(old.newInnerMembers).toBe(65);expect(old.glassFirstSurfaceProbes).toBe(20);
 expect(saw.visibleElevationUnsupportedCanopyProbes).toBe(10);expect(saw.visibleElevationNormalGlassProbes).toBe(9);expect(saw.verticalGlassFirstHits).toBe(9);expect(saw.verticalLipFirstHits).toBe(0);
 const canopy=await read('result/blender/saw_exterior_next/audit.json');expect(canopy.visibleElevationSheetNormalProbes).toHaveLength(9);expect(canopy.visibleElevationSheetNormalProbes.every(p=>p.firstSurface==='SAW_NEXT_central_canopy_glass')).toBe(true);
});
test('OLD and SAW exterior and retained interior load on desktop and phone',async({page})=>{
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 for(const width of [1440,390])for(const code of ['OLD','SAW']){
  await page.setViewportSize({width,height:1000});await page.goto('/#'+code);
  await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-'+code,{timeout:60000});
  await expect(page.locator('#fallback')).toBeHidden();await page.locator('#interior-view').click();
  await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','interior-'+code,{timeout:60000});
 }
 expect(errors).toEqual([]);
});
