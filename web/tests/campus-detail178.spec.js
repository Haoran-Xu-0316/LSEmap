import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';
const read = async path => JSON.parse(await readFile(path,'utf8'));
const glb = async path => {
 const bytes = await readFile(path);
 return JSON.parse(bytes.toString('utf8',20,20+bytes.readUInt32LE(12)));
};

test('edition178 changes only OLD posts and LRB café glazing',async()=>{
 const before = await read('result/blender/stage178/catalogue-before.json');
 const current = await read('dist/models/catalogue.json');
 const proof = await read('result/blender/stage178/building-refinement.json');
 const native = await read('result/blender/stage178/reopened-verification.json');
 expect(current.version).toBe('178');
 expect(current.sourceModelSha256).toBe(proof.sourceModelSha256);
 expect(native.savedSceneReopened && native.idempotent && native.allOriginalShapesAndUVsPreserved).toBe(true);
 for(const building of current.buildings){
  const old = before.buildings.find(item=>item.code===building.code);
  if(['OLD','LRB'].includes(building.code)) expect(building.detailedExterior.sha256).not.toBe(old.detailedExterior.sha256);
  else expect(building.detailedExterior,building.code).toEqual(old.detailedExterior);
  expect(building.detailedInterior,building.code).toEqual(old.detailedInterior);
  expect(building.interiorSpaces,building.code).toEqual(old.interiorSpaces);
 }
 expect(proof.changes).toHaveLength(2);
 const library = current.buildings.find(item=>item.code==='LRB');
 const document = await glb('dist'+library.detailedExterior.url);
 const index = document.materials.findIndex(item=>item.name==='WEB_DETAIL_LRB_NEXT_LRB_NEXT_PLAZA155_glass');
 expect(index).toBeGreaterThanOrEqual(0);
 expect(document.materials[index].alphaMode).toBe('BLEND');
 expect(document.materials[index].pbrMetallicRoughness.baseColorFactor[3]).toBeCloseTo(.30);
 const primitives = document.meshes.flatMap(mesh=>mesh.primitives).filter(item=>item.material===index);
 expect(primitives).toHaveLength(1);
 expect(document.accessors[primitives[0].indices].count).toBe(66*6);
 const oldBuilding = current.buildings.find(item=>item.code==='OLD');
 const oldDocument = await glb('dist'+oldBuilding.detailedExterior.url);
 const coating = oldDocument.materials.find(item=>item.name?.endsWith('OLD178_Houghton_black_post_coating'));
 expect(coating).toBeDefined();
 expect(coating.pbrMetallicRoughness.baseColorFactor.slice(0,3).every(value=>value<.02)).toBe(true);
});

for(const width of [1440,390]) for(const code of ['OLD','LRB']){
 test(`${code} edition178 loads at${width}px`,async({page})=>{
  const errors=[];page.on('pageerror',error=>errors.push(error.message));
  await page.setViewportSize({width,height:1000});await page.goto('/#'+code);
  await page.waitForFunction(code=>document.querySelector('canvas')?.dataset.detailReady==='exterior-'+code,code);
  expect(await page.locator('#fallback').isVisible()).toBe(false);
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  expect(errors).toEqual([]);
 });
}
