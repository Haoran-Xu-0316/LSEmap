import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';

test('SAL curved tower release preserves retained facade and interior assets',async()=>{
 const audit=JSON.parse(await readFile('result/blender/stage101/sal-tower-audit.json'));
 for(const key of ['originalObjectsUnchanged','twoRoofEndpointsRetained','bellCurvatureVerified','eightArchedPanes','closedPositiveVolumeMeshes'])expect(audit.savedMeasurements[key],key).toBeTruthy();
 expect(audit.towers).toHaveLength(2);
 const before=JSON.parse(await readFile('result/blender/stage101/catalogue-before.json'));
 const after=JSON.parse(await readFile('dist/models/catalogue.json'));
 expect(after.version).toBe('101');
 for(const b of before.buildings){
  const current=after.buildings.find(x=>x.code===b.code);
  if(b.code==='SAL')expect(current.detailedExterior.url).not.toBe(b.detailedExterior.url);
  else expect(current.detailedExterior?.url).toBe(b.detailedExterior?.url);
  expect(current.detailedInterior?.url).toBe(b.detailedInterior?.url);
  expect(current.interiorSpaces).toEqual(b.interiorSpaces);
 }
});
test('SAL tower close view loads with the exterior',async({page})=>{
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('/#SAL');
 await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-SAL',{timeout:60000});
 await expect(page.locator('#fallback')).toBeHidden();
 await page.locator('.detail-gallery img[src*="sal-tower-roofs"]').click();
 await expect(page.locator('#gallery-image')).toBeVisible();
 expect(await page.locator('#gallery-image').evaluate(i=>i.complete&&i.naturalWidth>0)).toBeTruthy();
 expect(errors).toEqual([]);
});
