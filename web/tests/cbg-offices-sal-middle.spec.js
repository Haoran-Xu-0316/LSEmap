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
test('CBG and SAL accepted components retain exact geometry across both scales',async()=>{
 const proof=await read('result/blender/stage130/saved-verification.json'),catalogue=await read('dist/models/catalogue.json');
 expect(catalogue.version).toBe('130');expect(catalogue.sourceModelSha256).toBe(proof.sourceModelSha256);
 expect(proof.savedSceneReopened).toBe(true);expect(proof.unrelatedVisibilityPreserved).toBe(true);expect(proof.retainedOriginalObjects).toBe(5531);expect(proof.ownedObjects.length).toBe(18);
 for(const code of ['CBG','SAL']){
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
 const before=await read('result/blender/stage130/catalogue-before.json');
 for(const b of catalogue.buildings){const old=before.buildings.find(o=>o.code===b.code);
  expect(b.detailedInterior,b.code).toEqual(old.detailedInterior);expect(b.interiorSpaces,b.code).toEqual(old.interiorSpaces);
  if(!['CBG','SAL'].includes(b.code))expect(b.detailedExterior,b.code).toEqual(old.detailedExterior);
 }
 const office=await read('result/blender/cbg_office_next/verification.json');
 expect(office.savedComponentReopened).toBe(true);expect(office.originalGeometryPreserved).toBe(true);
 expect(office.moduleCount).toBe(98);expect(office.visibleSurfaceChecks).toBe(294);expect(office.stairStripsRetained).toBe(10);
 const audit=await read('result/blender/cbg_office_next/audit.json');
 expect(audit.registration.glazedNominalWidth).toBe(2);expect(audit.registration.solidNominalWidth).toBe(1);
 for(const module of audit.officeModules){
  expect(module.x1-module.x0).toBe(3);expect(module.solidStart-module.x0).toBe(2);
  const centre=audit.registration.stairClearCentres[module.floor];
  expect(module.x1<=centre-7.8-.1||module.x0>=centre+7.8+.1).toBe(true);
 }
 const sal=await read('result/blender/sal_middle_next/verification.json');
 expect(sal.savedComponentReopened).toBe(true);expect(sal.originalGeometryPreserved).toBe(true);
 expect(sal.firstSurfaceChecks.length).toBe(54);
 expect(sal.firstSurfaceChecks.filter(row=>row.edge===2).length).toBe(42);
 expect(sal.firstSurfaceChecks.filter(row=>row.edge===0).length).toBe(12);


});
test('CBG and SAL exterior and retained interior load on desktop and phone',async({page})=>{
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 for(const width of [1440,390])for(const code of ['CBG','SAL']){
  await page.setViewportSize({width,height:1000});await page.goto('/#'+code);
  await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-'+code,{timeout:60000});
  await expect(page.locator('#fallback')).toBeHidden();await page.locator('#interior-view').click();
  await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','interior-'+code,{timeout:60000});
 }
 expect(errors).toEqual([]);
});
