import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
const json=async path=>JSON.parse(await readFile(path,'utf8'));
const glb=async path=>{const b=await readFile(path);const end=20+b.readUInt32LE(12);return {document:JSON.parse(b.toString('utf8',20,end)),binarySha256:createHash('sha256').update(b.subarray(end)).digest('hex')};};
test('193 preserves unrelated exteriors, interiors and whole native geometry',async()=>{
 const before=await json('result/blender/stage193/catalogue-before.json');const current=await json('dist/models/catalogue.json');const proof=await json('result/blender/stage193/reopened-verification.json');
 expect(current.version).toBe('193');expect(current.sourceModelSha256).toBe(proof.sourceModelSha256);
 for(const field of ['savedSceneReopened','allShapesUVFontsPreserved','collectionsVisibilityPreserved','allOriginalMaterialInputsPreserved','unrelatedBindingsPreserved','onlyPaintMetallicAndRoughnessChanged','idempotent'])expect(proof[field],field).toBe(true);
 expect(proof.paintObjects).toBe(20);expect(proof.paintMaterials).toBe(12);
 for(const b of current.buildings){const old=before.buildings.find(v=>v.code===b.code);
  if(b.code==='OLD'){expect(b.detailedExterior.sha256).not.toBe(old.detailedExterior.sha256);expect(b.detailedExterior.triangles).toBe(old.detailedExterior.triangles);expect(b.detailedExterior.bounds).toEqual(old.detailedExterior.bounds);}
  else expect(b.detailedExterior,b.code).toEqual(old.detailedExterior);
  expect(b.detailedInterior,b.code).toEqual(old.detailedInterior);expect(b.interiorSpaces,b.code).toEqual(old.interiorSpaces);
 }
});
for(const mode of ['overview','detail'])test(`paint-only export preserves ${mode} binary geometry, palette and other optics`,async()=>{
 const before=(await json('result/blender/stage193/asset-geometry-before.json'))[mode];
 const catalogue=await json('dist/models/catalogue.json');const old=catalogue.buildings.find(b=>b.code==='OLD');
 const current=await glb(mode==='overview'?'web/public/models/campus.glb':'dist'+old.detailedExterior.url);
 expect(current.binarySha256).toBe(before.binarySha256);
 let paintCount=0;
 const normalized=structuredClone(current.document);
 for(let i=0;i<normalized.materials.length;i++){
  const material=normalized.materials[i];const original=before.document.materials[i];
  if(material.name.includes('OLD_PAINT193_')){
   paintCount++;expect(material.name.replace('OLD_PAINT193_','')).toBe(original.name);
   expect(material.pbrMetallicRoughness.baseColorFactor).toEqual(original.pbrMetallicRoughness.baseColorFactor);
   expect(material.pbrMetallicRoughness.metallicFactor).toBe(0);expect(material.pbrMetallicRoughness.roughnessFactor).toBeCloseTo(.46,6);
   material.name=original.name;material.pbrMetallicRoughness.metallicFactor=original.pbrMetallicRoughness.metallicFactor;
   material.pbrMetallicRoughness.roughnessFactor=original.pbrMetallicRoughness.roughnessFactor;
  }
 }
 expect(paintCount).toBe(12);expect(normalized).toEqual(before.document);
});
for(const width of [1440,390])for(const code of ['OLD','MAR'])test(`${code}193 loads at${width}px`,async({page})=>{
 const errors=[];page.on('pageerror',e=>errors.push(e.message));await page.setViewportSize({width,height:1000});await page.goto('/#'+code);
 await page.waitForFunction(c=>document.querySelector('canvas')?.dataset.detailReady==='exterior-'+c,code);
 expect(await page.locator('#fallback').isVisible()).toBe(false);expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);expect(errors).toEqual([]);
});
