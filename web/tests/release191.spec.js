import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';
const json=async path=>JSON.parse(await readFile(path,'utf8'));
const glb=async path=>{const bytes=await readFile(path);return JSON.parse(bytes.toString('utf8',20,20+bytes.readUInt32LE(12)));};
const materials=['LRB_WINDOW191_sheet_GLASS181_shell_LRB_EXTERIOR172_LRB_V110_glass','LRB_WINDOW191_sheet_GLASS181_shell_LRB_EXTERIOR172_LRB_V110_roof_glass'];
function panes(document,suffix,count){
 const index=document.materials.findIndex(m=>m.name.endsWith(suffix));
 expect(index).toBeGreaterThanOrEqual(0);
 const primitive=document.meshes.flatMap(m=>m.primitives).filter(p=>p.material===index);
 expect(primitive).toHaveLength(1);
 expect(document.accessors[primitive[0].indices].count).toBe(count*6);
 expect(document.materials[index].alphaMode??'OPAQUE').toBe('OPAQUE');
 expect(document.materials[index].pbrMetallicRoughness.metallicFactor??1).toBe(0);
 return {bounds:document.accessors[primitive[0].attributes.POSITION],material:document.materials[index].pbrMetallicRoughness};
}
function same(left,right){
 expect(left.material).toEqual(right.material);
 for(const bound of ['min','max'])for(let axis=0;axis<3;axis++)expect(left.bounds[bound][axis]).toBeCloseTo(right.bounds[bound][axis],4);
}
test('191 changes only registered library glazing resources',async()=>{
 const before=await json('result/blender/stage191/catalogue-before.json');
 const current=await json('dist/models/catalogue.json');
 const proof=await json('result/blender/stage191/reopened-verification.json');
 expect(current.version).toBe('191');expect(current.sourceModelSha256).toBe(proof.sourceModelSha256);
 expect(proof.savedSceneReopened&&proof.originalGeometryUVFontsBindingsPreserved&&proof.collectionsPreserved&&proof.idempotent&&proof.paneFrontsAndCornerUVsPreserved&&proof.opticalInputsPreserved).toBe(true);
 for(const building of current.buildings){
  const old=before.buildings.find(v=>v.code===building.code);
  for(const field of ['detailedExterior','detailedInterior']){
   if(building.code==='LRB'){
    expect(building[field].sha256).not.toBe(old[field].sha256);
    expect(building[field].triangles-old[field].triangles).toBe(field==='detailedExterior'?-1030:-180);
    expect(building[field].bounds).toEqual(old[field].bounds);
   }else expect(building[field],building.code+field).toEqual(old[field]);
  }
  expect(building.interiorSpaces,building.code).toEqual(old.interiorSpaces);
 }
});
test('Portugal Street panes match between overview and exterior detail',async()=>{
 const catalogue=await json('dist/models/catalogue.json');const library=catalogue.buildings.find(b=>b.code==='LRB');
 const [campus,detail]=await Promise.all(['web/public/models/campus.glb','dist'+library.detailedExterior.url].map(glb));
 for(const [index,count] of [85,18].entries())same(panes(campus,materials[index],count),panes(detail,materials[index],count));
 expect(campus.materials.some(m=>m.name.includes('WEB_GLASS181_shell_LRB_EXTERIOR172_LRB_V110_glass'))).toBe(false);
});
test('retained interior cutaway shares the same roof panes',async()=>{
 const catalogue=await json('dist/models/catalogue.json');const library=catalogue.buildings.find(b=>b.code==='LRB');
 const [outside,inside]=await Promise.all([library.detailedExterior.url,library.detailedInterior.url].map(url=>glb('dist'+url)));
 same(panes(outside,materials[1],18),panes(inside,materials[1],18));
 expect(inside.materials.some(m=>m.name.endsWith(materials[0]))).toBe(false);
});
for(const width of [1440,390])for(const code of ['LRB','OLD'])test(`${code}191 loads at${width}px`,async({page})=>{
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.setViewportSize({width,height:1000});await page.goto('/#'+code);
 await page.waitForFunction(c=>document.querySelector('canvas')?.dataset.detailReady==='exterior-'+c,code);
 expect(await page.locator('#fallback').isVisible()).toBe(false);
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
 expect(errors).toEqual([]);
});
