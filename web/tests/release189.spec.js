import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';
const json=async path=>JSON.parse(await readFile(path,'utf8'));
const glb=async path=>{const b=await readFile(path);return JSON.parse(b.toString('utf8',20,20+b.readUInt32LE(12)));};
test('189 preserves every unrelated building and room resource',async()=>{
 const before=await json('result/blender/stage189/catalogue-before.json');
 const current=await json('dist/models/catalogue.json');
 const proof=await json('result/blender/stage189/building-refinement.json');
 const native=await json('result/blender/stage189/reopened-verification.json');
 expect(current.version).toBe('189');expect(current.sourceModelSha256).toBe(proof.sourceModelSha256);
 expect(native.savedSceneReopened&&native.baselineGeometryUVFontsAndBindingsPreserved&&native.unrelatedVisibilityAndCollectionsPreserved&&native.idempotent).toBe(true);
 expect(native.protectedArtworkSamples).toBeGreaterThan(18000);
 expect(proof.changes[0].addedObjects).toEqual(['OLD_NEXT_ARTWORK_front_glazing']);
 for(const b of current.buildings){
  const old=before.buildings.find(v=>v.code===b.code);
  if(b.code==='OLD'){
   expect(b.detailedExterior.sha256).not.toBe(old.detailedExterior.sha256);
   expect(b.detailedExterior.triangles).toBe(old.detailedExterior.triangles);
   expect(b.detailedExterior.bytes).toBeLessThan(old.detailedExterior.bytes*1.01);
  }else expect(b.detailedExterior,b.code).toEqual(old.detailedExterior);
  expect(b.detailedInterior,b.code).toEqual(old.detailedInterior);
  expect(b.interiorSpaces,b.code).toEqual(old.interiorSpaces);
 }
});
test('OLD protective glass has matching placement and optics in overview and detail',async()=>{
 const catalogue=await json('dist/models/catalogue.json');const old=catalogue.buildings.find(b=>b.code==='OLD');
 const docs=await Promise.all(['web/public/models/campus.glb','dist'+old.detailedExterior.url].map(glb));
 const values=docs.map(d=>{
  const index=d.materials.findIndex(m=>m.name.endsWith('OLD_ARTWORK_clear_protective_glass'));
  expect(index).toBeGreaterThanOrEqual(0);
  expect(d.materials.some(m=>m.name.includes('FinalSale_glazing'))).toBe(false);
  const mat=d.materials[index];expect(mat.alphaMode).toBe('BLEND');
  expect(mat.pbrMetallicRoughness.baseColorFactor[3]).toBeCloseTo(.22,5);
  expect(mat.pbrMetallicRoughness.metallicFactor??1).toBe(0);
  const p=d.meshes.flatMap(m=>m.primitives).filter(p=>p.material===index);
  expect(p).toHaveLength(1);
  return {position:d.accessors[p[0].attributes.POSITION],indices:d.accessors[p[0].indices].count,optics:mat.pbrMetallicRoughness};
 });
 expect(values[0].optics).toEqual(values[1].optics);expect(values[0].indices).toBe(values[1].indices);
 for(const bound of ['min','max'])for(let axis=0;axis<3;axis++)expect(values[0].position[bound][axis]).toBeCloseTo(values[1].position[bound][axis],4);
});
for(const width of [1440,390])for(const code of ['OLD','MAR','SAR','CBG']){
 test(`${code}189 loads at${width}px`,async({page})=>{
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.setViewportSize({width,height:1000});await page.goto('/#'+code);
  await page.waitForFunction(c=>document.querySelector('canvas')?.dataset.detailReady==='exterior-'+c,code);
  expect(await page.locator('#fallback').isVisible()).toBe(false);
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  expect(errors).toEqual([]);
 });
}
