import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';
const read = async path => JSON.parse(await readFile(path,'utf8'));
const glb = async path => {
 const bytes = await readFile(path);
 return JSON.parse(bytes.toString('utf8',20,20+bytes.readUInt32LE(12)));
};

test('edition187 restores MAR third podium window while preserving other models',async()=>{
 const before=await read('result/blender/stage187/catalogue-before.json');
 const current=await read('dist/models/catalogue.json');
 const proof=await read('result/blender/stage187/building-refinement.json');
 const native=await read('result/blender/stage187/reopened-verification.json');
 const podium=await read('result/blender/stage187/podium-verification.json');
 expect(current.version).toBe('187');
 expect(current.sourceModelSha256).toBe(proof.sourceModelSha256);
 expect(native.savedSceneReopened&&native.idempotent&&native.allOriginalFontsPreserved).toBe(true);
 expect(podium.savedSourceVerified&&podium.allOriginalShapesAndUVsPreserved).toBe(true);
 expect(podium.newPaneSightlines).toHaveLength(12);
 expect(podium.retainedWindowChecks).toBe(4);
 expect(podium.openLoggiaChecks).toBe(2);
 for(const building of current.buildings){
  const old=before.buildings.find(item=>item.code===building.code);
  if(building.code==='MAR') {
   expect(building.detailedExterior.sha256).not.toBe(old.detailedExterior.sha256);
   const document=await glb('dist'+building.detailedExterior.url);
   const glass=document.materials.find(material=>material.name.includes('MAR187_podium_window_glass'));
   expect(glass).toBeTruthy();
   expect(glass.pbrMetallicRoughness.baseColorFactor[3]).toBe(1);
   expect(glass.pbrMetallicRoughness.metallicFactor??1).toBe(0);
   expect(building.detailedExterior.triangles-old.detailedExterior.triangles).toBeLessThan(200);
  } else expect(building.detailedExterior,building.code).toEqual(old.detailedExterior);
  expect(building.detailedInterior,building.code).toEqual(old.detailedInterior);
  expect(building.interiorSpaces,building.code).toEqual(old.interiorSpaces);
 }
 expect(proof.changes[0].addedObjects).toHaveLength(3);
});

for(const width of [1440,390]) for(const code of ['MAR','SAR','OLD','CBG']){
 test(`${code} edition187 loads at${width}px`,async({page})=>{
  const errors=[];page.on('pageerror',error=>errors.push(error.message));
  await page.setViewportSize({width,height:1000});await page.goto('/#'+code);
  await page.waitForFunction(code=>document.querySelector('canvas')?.dataset.detailReady==='exterior-'+code,code);
  expect(await page.locator('#fallback').isVisible()).toBe(false);
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  expect(errors).toEqual([]);
 });
}
