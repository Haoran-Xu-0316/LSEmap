import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';
const read = async path => JSON.parse(await readFile(path,'utf8'));
const glb = async path => {
 const bytes = await readFile(path);
 return JSON.parse(bytes.toString('utf8',20,20+bytes.readUInt32LE(12)));
};

test('edition181 preserves unrelated assets and certifies consistent exterior glass surfaces',async()=>{
 const before = await read('result/blender/stage181/catalogue-before.json');
 const current = await read('dist/models/catalogue.json');
 const proof = await read('result/blender/stage181/building-refinement.json');
 const native = await read('result/blender/stage181/reopened-verification.json');
 expect(current.version).toBe('181');
 expect(current.sourceModelSha256).toBe(proof.sourceModelSha256);
 expect(native.savedSceneReopened && native.idempotent && native.allOriginalShapesAndUVsPreserved).toBe(true);
 for(const building of current.buildings){
  const old=before.buildings.find(item=>item.code===building.code);
  if(proof.changes[0].records.some(r=>r.code===building.code)) expect(building.detailedExterior.sha256).not.toBe(old.detailedExterior.sha256);
  else expect(building.detailedExterior,building.code).toEqual(old.detailedExterior);
  if(building.code!=='LRB') expect(building.detailedInterior,building.code).toEqual(old.detailedInterior);
  expect(building.interiorSpaces,building.code).toEqual(old.interiorSpaces);
 }
 expect(proof.changes).toHaveLength(1);
 expect(native.glassSurfacePolicyVerified).toBe(true);
 expect(native.reversedShells).toBe(3238);
 expect(native.closedShells).toBe(3863);
 for(const code of new Set(proof.changes[0].records.map(r=>r.code))){
  const building=current.buildings.find(item=>item.code===code);
  const document=await glb('dist'+building.detailedExterior.url);
  const used=new Set(document.meshes.flatMap(mesh=>mesh.primitives).map(p=>p.material));
  const revised=[...used].map(i=>document.materials[i]).filter(m=>m.name?.includes('GLASS181_'));
  expect(revised.length,code).toBeGreaterThan(0);
  for(const material of revised){
   expect(material.pbrMetallicRoughness.metallicFactor ?? 1,material.name).toBe(0);
   if(material.name.includes('GLASS181_shell_')) expect(material.extras?.webClosedGlazing,material.name).toBe(true);
  }
 }

});

for(const width of [1440,390]) for(const code of ['CKK','LRB','CBG','OLD']){
 test(`${code} edition181 loads at${width}px`,async({page})=>{
  const errors=[];page.on('pageerror',error=>errors.push(error.message));
  await page.setViewportSize({width,height:1000});await page.goto('/#'+code);
  await page.waitForFunction(code=>document.querySelector('canvas')?.dataset.detailReady==='exterior-'+code,code);
  expect(await page.locator('#fallback').isVisible()).toBe(false);
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  expect(errors).toEqual([]);
 });
}
