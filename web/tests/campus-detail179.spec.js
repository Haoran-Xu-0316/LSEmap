import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';
const read = async path => JSON.parse(await readFile(path,'utf8'));
const glb = async path => {
 const bytes = await readFile(path);
 return JSON.parse(bytes.toString('utf8',20,20+bytes.readUInt32LE(12)));
};

test('edition179 preserves unrelated assets and fixes SHF panes',async()=>{
 const before = await read('result/blender/stage179/catalogue-before.json');
 const current = await read('dist/models/catalogue.json');
 const proof = await read('result/blender/stage179/building-refinement.json');
 const native = await read('result/blender/stage179/reopened-verification.json');
 expect(current.version).toBe('179');
 expect(current.sourceModelSha256).toBe(proof.sourceModelSha256);
 expect(native.savedSceneReopened && native.idempotent && native.allOriginalShapesAndUVsPreserved).toBe(true);
 for(const building of current.buildings){
  const old=before.buildings.find(item=>item.code===building.code);
  if(building.code==='SHF') expect(building.detailedExterior.sha256).not.toBe(old.detailedExterior.sha256);
  else expect(building.detailedExterior,building.code).toEqual(old.detailedExterior);
  expect(building.detailedInterior,building.code).toEqual(old.detailedInterior);
  expect(building.interiorSpaces,building.code).toEqual(old.interiorSpaces);
 }
 expect(proof.changes).toHaveLength(2);
 const shf=current.buildings.find(item=>item.code==='SHF');
 const document=await glb('dist'+shf.detailedExterior.url);
 const index=document.materials.findIndex(item=>item.name?.endsWith('SHF_NEXT_EXTERIOR179_photographed_glass'));
 expect(index).toBeGreaterThanOrEqual(0);
 expect(document.materials[index].alphaMode).toBe('BLEND');
 expect(document.materials[index].pbrMetallicRoughness.baseColorFactor[3]).toBeCloseTo(.84);
 const panes=document.meshes.flatMap(mesh=>mesh.primitives).filter(item=>item.material===index);
 expect(panes).toHaveLength(1);
 expect(document.accessors[panes[0].indices].count).toBe(18);
 const trees=proof.changes[1].records;
 expect(trees.map(r=>r.modifiedMasses)).toEqual([12,6]);
 expect(trees[1].verticesAfter).toBe(trees[1].verticesBefore);
});

for(const width of [1440,390]) for(const code of ['SHF','OLD']){
 test(`${code} edition179 loads at${width}px`,async({page})=>{
  const errors=[];page.on('pageerror',error=>errors.push(error.message));
  await page.setViewportSize({width,height:1000});await page.goto('/#'+code);
  await page.waitForFunction(code=>document.querySelector('canvas')?.dataset.detailReady==='exterior-'+code,code);
  expect(await page.locator('#fallback').isVisible()).toBe(false);
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  expect(errors).toEqual([]);
 });
}
