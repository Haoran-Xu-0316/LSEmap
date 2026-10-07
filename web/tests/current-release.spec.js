import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';
const read = async path => JSON.parse(await readFile(path,'utf8'));
const glb = async path => {
 const bytes = await readFile(path);
 return JSON.parse(bytes.toString('utf8',20,20+bytes.readUInt32LE(12)));
};

test('edition180 preserves unrelated assets and corrects registered CON/PAR glass',async()=>{
 const before = await read('result/blender/stage180/catalogue-before.json');
 const current = await read('dist/models/catalogue.json');
 const proof = await read('result/blender/stage180/building-refinement.json');
 const native = await read('result/blender/stage180/reopened-verification.json');
 expect(current.version).toBe('180');
 expect(current.sourceModelSha256).toBe(proof.sourceModelSha256);
 expect(native.savedSceneReopened && native.idempotent && native.allOriginalShapesAndUVsPreserved).toBe(true);
 for(const building of current.buildings){
  const old=before.buildings.find(item=>item.code===building.code);
  if(['CON','PAR'].includes(building.code)) expect(building.detailedExterior.sha256).not.toBe(old.detailedExterior.sha256);
  else expect(building.detailedExterior,building.code).toEqual(old.detailedExterior);
  expect(building.detailedInterior,building.code).toEqual(old.detailedInterior);
  expect(building.interiorSpaces,building.code).toEqual(old.interiorSpaces);
 }
 expect(proof.changes).toHaveLength(2);
 expect(native.conSinglePaneCount).toBe(8);
 expect(native.parPhotographedPaneCount).toBe(20);
 expect(native.parUnseenPaneCount).toBe(33);
 const con=current.buildings.find(item=>item.code==='CON');
 const document=await glb('dist'+con.detailedExterior.url);
 for(const [suffix,count,alpha] of [['registered_lower_frontage_glass_optical',30,.82],['fanlight_glass_optical',6,.82],['inner_door_glass_optical',12,.42]]){
  const index=document.materials.findIndex(item=>item.name?.endsWith('CON_EXTERIOR180_'+suffix));
  expect(index).toBeGreaterThanOrEqual(0);
  expect(document.materials[index].alphaMode).toBe('BLEND');
  expect(document.materials[index].pbrMetallicRoughness.baseColorFactor[3]).toBeCloseTo(alpha);
  expect(document.materials[index].pbrMetallicRoughness.metallicFactor ?? 1).toBe(0);
  const panes=document.meshes.flatMap(mesh=>mesh.primitives).filter(item=>item.material===index);
  expect(panes).toHaveLength(1);
  expect(document.accessors[panes[0].indices].count).toBe(count);
 }
 const par=current.buildings.find(item=>item.code==='PAR');
 const hall=await glb('dist'+par.detailedExterior.url);
 const index=hall.materials.findIndex(item=>item.name?.endsWith('PAR_NEXT_EXTERIOR180_dielectric_street_glass'));
 expect(index).toBeGreaterThanOrEqual(0);
 expect(hall.materials[index].pbrMetallicRoughness.metallicFactor ?? 1).toBe(0);
 expect(hall.materials[index].alphaMode ?? 'OPAQUE').toBe('OPAQUE');
 const glass=hall.meshes.flatMap(mesh=>mesh.primitives).filter(item=>item.material===index);
 expect(glass.reduce((sum,p)=>sum+hall.accessors[p.indices].count,0)).toBe(20*36);
});

for(const width of [1440,390]) for(const code of ['CON','PAR']){
 test(`${code} edition180 loads at${width}px`,async({page})=>{
  const errors=[];page.on('pageerror',error=>errors.push(error.message));
  await page.setViewportSize({width,height:1000});await page.goto('/#'+code);
  await page.waitForFunction(code=>document.querySelector('canvas')?.dataset.detailReady==='exterior-'+code,code);
  expect(await page.locator('#fallback').isVisible()).toBe(false);
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  expect(errors).toEqual([]);
 });
}
