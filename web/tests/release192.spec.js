import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';
const json=async path=>JSON.parse(await readFile(path,'utf8'));
const glb=async path=>{const b=await readFile(path);return JSON.parse(b.toString('utf8',20,20+b.readUInt32LE(12)));};
test('192 preserves buildings, rooms and entrance geometry',async()=>{
 const before=await json('result/blender/stage192/catalogue-before.json');const current=await json('dist/models/catalogue.json');const proof=await json('result/blender/stage192/reopened-verification.json');
 expect(current.version).toBe('192');expect(current.sourceModelSha256).toBe(proof.sourceModelSha256);
 expect(proof.savedSceneReopened&&proof.originalGeometryUVFontsBindingsPreserved&&proof.collectionsPreserved&&proof.idempotent&&proof.entranceGeometryAndUVPreserved&&proof.unrelatedOpticalInputsPreserved).toBe(true);
 for(const b of current.buildings){const old=before.buildings.find(v=>v.code===b.code);
  if(b.code==='OLD'){expect(b.detailedExterior.sha256).not.toBe(old.detailedExterior.sha256);expect(b.detailedExterior.triangles).toBe(old.detailedExterior.triangles);expect(b.detailedExterior.bounds).toEqual(old.detailedExterior.bounds);}
  else expect(b.detailedExterior,b.code).toEqual(old.detailedExterior);
  expect(b.detailedInterior,b.code).toEqual(old.detailedInterior);expect(b.interiorSpaces,b.code).toEqual(old.interiorSpaces);
 }
});
test('neutral entrance glass has identical optics and bounds in both views',async()=>{
 const c=await json('dist/models/catalogue.json');const old=c.buildings.find(b=>b.code==='OLD');
 const documents=await Promise.all(['web/public/models/campus.glb','dist'+old.detailedExterior.url].map(glb));
 const panes=documents.map(d=>{
  const index=d.materials.findIndex(m=>m.name.endsWith('OLD_ENTRANCE192_clear_glass'));expect(index).toBeGreaterThanOrEqual(0);
  const material=d.materials[index];expect(material.alphaMode).toBe('BLEND');
  for(const [axis,value] of [.15,.18,.18,.28].entries())expect(material.pbrMetallicRoughness.baseColorFactor[axis]).toBeCloseTo(value,6);
  expect(material.pbrMetallicRoughness.metallicFactor).toBe(0);expect(material.pbrMetallicRoughness.roughnessFactor).toBeCloseTo(.17,6);
  const primitives=d.meshes.flatMap(m=>m.primitives).filter(p=>p.material===index);expect(primitives).toHaveLength(1);
  expect(d.accessors[primitives[0].indices].count).toBe(48);
  expect(primitives[0].attributes.TEXCOORD_0).toBeDefined();
  expect(d.accessors[primitives[0].attributes.TEXCOORD_0].count).toBe(32);
  return {material:material.pbrMetallicRoughness,position:d.accessors[primitives[0].attributes.POSITION]};
 });
 expect(panes[0].material).toEqual(panes[1].material);
 for(const bound of ['min','max'])for(let axis=0;axis<3;axis++)expect(panes[0].position[bound][axis]).toBeCloseTo(panes[1].position[bound][axis],4);
});
for(const width of [1440,390])for(const code of ['OLD','LRB'])test(`${code}192 loads at${width}px`,async({page})=>{
 const errors=[];page.on('pageerror',e=>errors.push(e.message));await page.setViewportSize({width,height:1000});await page.goto('/#'+code);
 await page.waitForFunction(c=>document.querySelector('canvas')?.dataset.detailReady==='exterior-'+c,code);
 expect(await page.locator('#fallback').isVisible()).toBe(false);expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);expect(errors).toEqual([]);
});
