import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';
test('saved MAR wings replace 245 apertures and protect other buildings and interiors',async()=>{
 const audit=JSON.parse(await readFile('result/blender/stage75/mar-academic-wings-audit.json'));
 expect(audit.savedMeasurements.otherBuildingsAndInteriorsUnchanged).toBeTruthy();
 expect(audit.savedMeasurements.newApertures).toBe(245);
 expect(audit.savedMeasurements.removedGlassPanels).toBe(245);
 expect(audit.savedMeasurements.replacedFacades).toBe(5);
});
test('campus and MAR close model share corrected academic-wing concrete, glass and bronze',async()=>{
 const catalogue=JSON.parse(await readFile('dist/models/catalogue.json'));
 const building=catalogue.buildings.find(b=>b.code==='MAR');
 for(const url of ['/models/campus.glb',building.detailedExterior.url]){
  const bytes=await readFile('dist'+url);
  const doc=JSON.parse(bytes.subarray(20,20+bytes.readUInt32LE(12)));
  const node=doc.nodes.find(n=>n.extras?.buildingCode==='MAR')??doc.nodes.find(n=>n.mesh!==undefined);
  const names=doc.meshes[node.mesh].primitives.map(p=>doc.materials[p.material].name);
  for(const key of ['concrete','glass','joinery'])expect(names.some(n=>n.endsWith('MAR_V75_'+key))).toBeTruthy();

 }
});

test('MAR exterior and refreshed gallery load in the browser',async({page})=>{
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('/#MAR');
 await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-MAR',{timeout:60000});
 await expect(page.locator('#fallback')).toBeHidden();
 await page.locator('.detail-gallery img[src*="mar-academic-wings"]').click();
 await expect(page.locator('#gallery-image')).toBeVisible();
 expect(await page.locator('#gallery-image').evaluate(i=>i.complete&&i.naturalWidth>0)).toBeTruthy();
 expect(errors).toEqual([]);
});
