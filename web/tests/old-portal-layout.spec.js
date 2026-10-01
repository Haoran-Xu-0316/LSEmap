import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';
test('saved OLD has both inner and outer windows with retained wing apertures and interiors',async()=>{
 const a=JSON.parse(await readFile('result/blender/stage79/old-portal-layout-audit.json'));
 expect(a.savedMeasurements.totalGroundWindows).toBe(4);
 expect(a.savedMeasurements.innerWindows).toBe(2);
 expect(a.savedMeasurements.outerWindows).toBe(2);
 expect(a.savedMeasurements.wingWindowHoles).toBe(48);
 expect(a.savedMeasurements.outerWindowGeometryRestoredExactly).toBeTruthy();
 expect(a.savedMeasurements.allOriginalGeometryUnchanged).toBeTruthy();
 expect(a.savedMeasurements.otherBuildingsAndInteriorsUnchanged).toBeTruthy();
 const before=JSON.parse(await readFile('result/blender/stage79/catalogue-before.json'));
 const after=JSON.parse(await readFile('dist/models/catalogue.json'));
 for(const old of before.buildings){
  const current=after.buildings.find(b=>b.code===old.code);
  if(old.code!=='OLD')expect(current.detailedExterior?.url).toBe(old.detailedExterior?.url);
  expect(current.detailedInterior?.url).toBe(old.detailedInterior?.url);
  expect(current.interiorSpaces).toEqual(old.interiorSpaces);
 }
});
test('overview and detail retain inner and outer window materials and coursed wing stone',async()=>{
 const c=JSON.parse(await readFile('dist/models/catalogue.json'));
 for(const url of ['/models/campus.glb',c.buildings.find(b=>b.code==='OLD').detailedExterior.url]){
  const bytes=await readFile('dist'+url);
  const doc=JSON.parse(bytes.subarray(20,20+bytes.readUInt32LE(12)));
  const node=doc.nodes.find(n=>n.extras?.buildingCode==='OLD')??doc.nodes.find(n=>n.mesh!==undefined);
  const names=doc.meshes[node.mesh].primitives.map(p=>doc.materials[p.material].name);
  for(const key of ['OLD_V78_glass','OLD_V78_blue','OLD_V79_Window_glazing','OLD_V79_Window_sash_frames','OLD_V79_V52_Houghton_blue',...Array.from({length:7},(_,i)=>'OLD_V79_ashlar_'+i)])
   expect(names.some(n=>n.endsWith(key)),key).toBeTruthy();
 }
});
test('OLD corrected exterior and entrance gallery load without errors',async({page})=>{
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('/#OLD');
 await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-OLD',{timeout:60000});
 await expect(page.locator('#fallback')).toBeHidden();
 await page.locator('.detail-gallery img[src*="old-houghton-entrance"]').click();
 await expect(page.locator('#gallery-image')).toBeVisible();
 expect(await page.locator('#gallery-image').evaluate(i=>i.complete&&i.naturalWidth>0)).toBeTruthy();
 expect(errors).toEqual([]);
});
