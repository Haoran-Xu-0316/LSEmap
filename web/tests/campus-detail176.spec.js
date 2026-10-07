import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';
const read=async path=>JSON.parse(await readFile(path,'utf8'));
const glb=async path=>{const bytes=await readFile(path);return JSON.parse(bytes.toString('utf8',20,20+bytes.readUInt32LE(12)));};

test('edition176 changes KGS attic and shared street without replacing other exteriors or rooms',async()=>{
 const before=await read('result/blender/stage176/catalogue-before.json');
 const current=await read('dist/models/catalogue.json');
 const proof=await read('result/blender/stage176/building-refinement.json');
 const native=await read('result/blender/stage176/reopened-verification.json');
 expect(current.version).toBe('176');expect(current.buildings).toHaveLength(31);
 expect(current.sourceModelSha256).toBe(proof.sourceModelSha256);
 expect(native.savedSceneReopened).toBe(true);expect(native.idempotent).toBe(true);
 expect(native.allOriginalShapesAndUVsPreserved).toBe(true);
 for(const building of current.buildings){
  const old=before.buildings.find(b=>b.code===building.code);
  if(building.code==='KGS')expect(building.detailedExterior.sha256).not.toBe(old.detailedExterior.sha256);
  else expect(building.detailedExterior,building.code).toEqual(old.detailedExterior);
  expect(building.detailedInterior,building.code).toEqual(old.detailedInterior);
  for(const room of old.interiorSpaces||[])expect(building.interiorSpaces.find(r=>r.id===room.id),room.id).toEqual(room);
 }
 expect(proof.changes).toHaveLength(2);
 expect(proof.changes.reduce((n,c)=>n+c.addedObjects.length,0)).toBe(25);
 expect(proof.archivedObjects).toHaveLength(19);
 expect(native.atticWindowAxes).toBe(5);expect(native.atticPaneFacets).toBe(9);
 expect(native.streetMeshesSingleSiteMembership).toBe(true);
 const campus=await glb('web/public/models/campus.glb');
 for(const name of ['SITE176_PEA_cast_iron_black_paint','SITE176_Portugal_road_marking_ochre']){
  const index=campus.materials.findIndex(m=>m.name==='WEB_'+name);
  expect(index,name).toBeGreaterThanOrEqual(0);
  const primitives=campus.meshes.flatMap(m=>m.primitives).filter(p=>p.material===index);
  expect(primitives).toHaveLength(1);
  expect(campus.accessors[primitives[0].indices].count).toBeGreaterThan(0);
 }
 const gallery=await read('dist/gallery-manifest.json');
 const views=Array.isArray(gallery)?gallery:gallery.images;
 // The frontage photo is rendered from the campus because roads belong to the site.
 const job=(await read('web/tools/gallery-views.json')).find(j=>j.name==='pea-frontage');
 expect(job.code).toBe('CAMPUS');
 expect(views).toBeTruthy();
});
for(const width of [1440,390])for(const code of ['KGS','PEA']){
 test(`${code} edition176 loads at${width}px`,async({page})=>{
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.setViewportSize({width,height:1000});await page.goto('/#'+code);
  await page.waitForFunction(code=>document.querySelector('canvas')?.dataset.detailReady==='exterior-'+code,code);
  expect(await page.locator('#fallback').isVisible()).toBe(false);
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  expect(errors).toEqual([]);
 });
}
