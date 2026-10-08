import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';
const json=async p=>JSON.parse(await readFile(p,'utf8'));
const glb=async p=>{const b=await readFile(p);return JSON.parse(b.toString('utf8',20,20+b.readUInt32LE(12)));};
test('190 preserves unrelated buildings and rooms',async()=>{
 const before=await json('result/blender/stage190/catalogue-before.json');
 const current=await json('dist/models/catalogue.json');
 const proof=await json('result/blender/stage190/reopened-verification.json');
 expect(current.version).toBe('190');expect(current.sourceModelSha256).toBe(proof.sourceModelSha256);
 expect(proof.savedSceneReopened&&proof.originalGeometryUVFontsBindingsPreserved&&proof.collectionsPreserved&&proof.idempotent).toBe(true);
 for(const b of current.buildings){
  const old=before.buildings.find(v=>v.code===b.code);
  if(b.code==='SAW'){
   expect(b.detailedExterior.sha256).not.toBe(old.detailedExterior.sha256);
   expect(b.detailedExterior.triangles-old.detailedExterior.triangles).toBe(149384);
   expect(b.detailedExterior.bytes).toBeLessThan(old.detailedExterior.bytes*1.13);
  }else expect(b.detailedExterior,b.code).toEqual(old.detailedExterior);
  expect(b.detailedInterior,b.code).toEqual(old.detailedInterior);
  expect(b.interiorSpaces,b.code).toEqual(old.interiorSpaces);
 }
});
test('SAW mortar has matching bounds and material in overview and detail',async()=>{
 const c=await json('dist/models/catalogue.json');const saw=c.buildings.find(b=>b.code==='SAW');
 const docs=await Promise.all(['web/public/models/campus.glb','dist'+saw.detailedExterior.url].map(glb));
 const values=docs.map(d=>{
  const index=d.materials.findIndex(m=>m.name.endsWith('SAW_SCREEN_bedding_mortar'));expect(index).toBeGreaterThanOrEqual(0);
  const p=d.meshes.flatMap(m=>m.primitives).filter(p=>p.material===index);expect(p).toHaveLength(1);
  expect(d.accessors[p[0].indices].count/3).toBe(149384);
  return {position:d.accessors[p[0].attributes.POSITION],optics:d.materials[index].pbrMetallicRoughness};
 });
 expect(values[0].optics).toEqual(values[1].optics);
 for(const bound of ['min','max'])for(let a=0;a<3;a++)expect(values[0].position[bound][a]).toBeCloseTo(values[1].position[bound][a],4);
});
for(const width of [1440,390])for(const code of ['SAW','OLD'])test(`${code}190 loads at${width}px`,async({page})=>{
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.setViewportSize({width,height:1000});await page.goto('/#'+code);
 await page.waitForFunction(c=>document.querySelector('canvas')?.dataset.detailReady==='exterior-'+c,code);
 expect(await page.locator('#fallback').isVisible()).toBe(false);
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);expect(errors).toEqual([]);
});
