import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';
const read = async path => JSON.parse(await readFile(path,'utf8'));
const glb = async path => {
 const bytes = await readFile(path);
 return JSON.parse(bytes.toString('utf8',20,20+bytes.readUInt32LE(12)));
};

test('edition186 reveals SAR street blinds without changing unrelated models',async()=>{
 const before=await read('result/blender/stage186/catalogue-before.json');
 const current=await read('dist/models/catalogue.json');
 const proof=await read('result/blender/stage186/building-refinement.json');
 const native=await read('result/blender/stage186/reopened-verification.json');
 const glazing=await read('result/blender/stage186/glazing-verification.json');
 expect(current.version).toBe('186');
 expect(current.sourceModelSha256).toBe(proof.sourceModelSha256);
 expect(native.savedSceneReopened&&native.idempotent&&native.allOriginalFontsPreserved).toBe(true);
 expect(glazing.sourceModelSha256).toBe(current.sourceModelSha256);
 expect(glazing.treatedWindows).toBe(4);
 expect(glazing.blindSlats).toBe(80);
 expect(glazing.twoLayerSightlines).toHaveLength(48);
 expect(glazing.originalGlassGeometryAndUVsPreserved&&glazing.otherPaneFinishesPreserved).toBe(true);
 for(const building of current.buildings){
  const old=before.buildings.find(item=>item.code===building.code);
  if(building.code==='SAR') {
   expect(building.detailedExterior.sha256).not.toBe(old.detailedExterior.sha256);
   const document=await glb('dist'+building.detailedExterior.url);
   const glass=document.materials.find(material=>material.name.includes('SAR186_clear_street_glass'));
   expect(glass).toBeTruthy();
   expect(glass.alphaMode).toBe('BLEND');
   expect(glass.pbrMetallicRoughness.baseColorFactor[3]).toBeCloseTo(.38,5);
   expect(glass.pbrMetallicRoughness.metallicFactor??1).toBe(0);
   expect(glass.extras.webClosedGlazing).toBe(true);
   expect(document.materials.some(material=>material.name.includes('SAR186_pale_blind_fabric'))).toBe(true);
   expect(building.detailedExterior.triangles-old.detailedExterior.triangles).toBeLessThan(2000);
  } else expect(building.detailedExterior,building.code).toEqual(old.detailedExterior);
  expect(building.detailedInterior,building.code).toEqual(old.detailedInterior);
  expect(building.interiorSpaces,building.code).toEqual(old.interiorSpaces);
 }
 expect(proof.changes[0].selectedPanes).toHaveLength(4);
});

for(const width of [1440,390]) for(const code of ['SAR','OLD','CBG','PEL']){
 test(`${code} edition186 loads at${width}px`,async({page})=>{
  const errors=[];page.on('pageerror',error=>errors.push(error.message));
  await page.setViewportSize({width,height:1000});await page.goto('/#'+code);
  await page.waitForFunction(code=>document.querySelector('canvas')?.dataset.detailReady==='exterior-'+code,code);
  expect(await page.locator('#fallback').isVisible()).toBe(false);
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  expect(errors).toEqual([]);
 });
}
