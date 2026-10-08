import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';
const read = async path => JSON.parse(await readFile(path,'utf8'));
const glb = async path => {
 const bytes = await readFile(path);
 return JSON.parse(bytes.toString('utf8',20,20+bytes.readUInt32LE(12)));
};

test('edition188 aligns MAR recess and preserves unrelated models',async()=>{
 const before=await read('result/blender/stage188/catalogue-before.json');
 const current=await read('dist/models/catalogue.json');
 const proof=await read('result/blender/stage188/building-refinement.json');
 const native=await read('result/blender/stage188/reopened-verification.json');
 const north=await read('result/blender/stage188/north-verification.json');
 expect(north.clearFrontSamples).toBe(245);
 expect(north.frontWindowSightlines).toBe(75);
 expect(north.floorCoverageSamples).toBe(49248);
 expect(north.roofFootprintSamples).toBe(1995);
 expect(north.clearCourtyardRoofSamples).toBe(445);
 const podium=await read('result/blender/stage188/podium-verification.json');
 expect(current.version).toBe('188');
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
   expect(document.materials.some(m=>m.name.includes('MAR188_middle_retained_dielectric_glass'))).toBe(true);
   expect(document.materials.some(m=>m.name.includes('MAR188_retained_dielectric_glass'))).toBe(true);
   expect(building.detailedExterior.triangles).toBeLessThan(old.detailedExterior.triangles*1.15);
  } else expect(building.detailedExterior,building.code).toEqual(old.detailedExterior);
  if(building.code!=='MAR') expect(building.detailedInterior,building.code).toEqual(old.detailedInterior);
  expect(building.interiorSpaces,building.code).toEqual(old.interiorSpaces);
 }
 expect(proof.changes[0].addedObjects).toHaveLength(44);
});

for(const width of [1440,390]) for(const code of ['MAR','SAR','OLD','CBG']){
 test(`${code} edition188 loads at${width}px`,async({page})=>{
  const errors=[];page.on('pageerror',error=>errors.push(error.message));
  await page.setViewportSize({width,height:1000});await page.goto('/#'+code);
  await page.waitForFunction(code=>document.querySelector('canvas')?.dataset.detailReady==='exterior-'+code,code);
  expect(await page.locator('#fallback').isVisible()).toBe(false);
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  expect(errors).toEqual([]);
 });
}

test('MAR188 glazing shares geometry, UV presence and optics across overview and detail',async()=>{
 const catalogue=await read('dist/models/catalogue.json');
 const mar=catalogue.buildings.find(b=>b.code==='MAR');
 const documents=await Promise.all(['/models/campus.glb',mar.detailedExterior.url].map(url=>glb('dist'+url)));
 for(const suffix of ['MAR188_retained_dielectric_glass','MAR188_middle_retained_dielectric_glass']){
  const snapshots=documents.map(document=>{
   const materialIndex=document.materials.findIndex(m=>m.name.endsWith(suffix));
   expect(materialIndex).toBeGreaterThanOrEqual(0);
   const primitives=document.meshes.flatMap(m=>m.primitives).filter(p=>p.material===materialIndex);
   expect(primitives).toHaveLength(1);
   const primitive=primitives[0];
   expect(primitive.attributes.TEXCOORD_0).toBeDefined();
   const position=document.accessors[primitive.attributes.POSITION];
   return {position,indices:document.accessors[primitive.indices].count,
    optics:document.materials[materialIndex].pbrMetallicRoughness,
    alpha:document.materials[materialIndex].alphaMode};
  });
  expect(snapshots[0].indices).toBe(snapshots[1].indices);
  expect(snapshots[0].position.count).toBe(snapshots[1].position.count);
  expect(snapshots[0].optics).toEqual(snapshots[1].optics);
  expect(snapshots[0].alpha).toBe(snapshots[1].alpha);
  for(const bound of ['min','max']) for(let axis=0;axis<3;axis++)
   expect(snapshots[0].position[bound][axis]).toBeCloseTo(snapshots[1].position[bound][axis],3);
 }
});
