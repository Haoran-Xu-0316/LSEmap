import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';
const read = async path => JSON.parse(await readFile(path,'utf8'));
const glb = async path => {
 const bytes = await readFile(path);
 return JSON.parse(bytes.toString('utf8',20,20+bytes.readUInt32LE(12)));
};

test('edition185 registers OLD lettering while retaining unrelated models',async()=>{
 const before=await read('result/blender/stage185/catalogue-before.json');
 const current=await read('dist/models/catalogue.json');
 const proof=await read('result/blender/stage185/building-refinement.json');
 const native=await read('result/blender/stage185/reopened-verification.json');
 const lettering=await read('result/blender/stage185/lettering-verification.json');
 expect(current.version).toBe('185');
 expect(current.sourceModelSha256).toBe(proof.sourceModelSha256);
 expect(native.savedSceneReopened&&native.idempotent&&native.allOriginalFontsPreserved).toBe(true);
 expect(lettering.sourceModelSha256).toBe(current.sourceModelSha256);
 expect(lettering.registeredLabels).toBe(3);
 expect(lettering.stoneContactProbes).toBe(27);
 expect(lettering.frontVisibilityProbes).toBe(27);
 for(const contact of lettering.contacts){
  expect(contact.stoneContactProbes).toHaveLength(9);
  for(const probe of contact.stoneContactProbes) expect(probe.distance).toBeLessThan(.06);
 }
 for(const building of current.buildings){
  const old=before.buildings.find(item=>item.code===building.code);
  if(building.code==='OLD') {
   expect(building.detailedExterior.sha256).not.toBe(old.detailedExterior.sha256);
   expect((await glb('dist'+building.detailedExterior.url)).meshes.length).toBeGreaterThan(0);
  } else expect(building.detailedExterior,building.code).toEqual(old.detailedExterior);
  expect(building.detailedInterior,building.code).toEqual(old.detailedInterior);
  expect(building.interiorSpaces,building.code).toEqual(old.interiorSpaces);
 }
 expect(proof.changes[0].records).toHaveLength(3);
 expect(proof.changes[0].addedObjects).toHaveLength(3);
 for(const record of proof.changes[0].records){
  expect(record.registrationMaximumError).toBeLessThan(.00002);
  expect(record.backVertexContactCount).toBeGreaterThan(9);
 }
});

for(const width of [1440,390]) for(const code of ['SAL','OLD','CBG','CKK']){
 test(`${code} edition185 loads at${width}px`,async({page})=>{
  const errors=[];page.on('pageerror',error=>errors.push(error.message));
  await page.setViewportSize({width,height:1000});await page.goto('/#'+code);
  await page.waitForFunction(code=>document.querySelector('canvas')?.dataset.detailReady==='exterior-'+code,code);
  expect(await page.locator('#fallback').isVisible()).toBe(false);
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  expect(errors).toEqual([]);
 });
}
