import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';
const read=async path=>JSON.parse(await readFile(path,'utf8'));
test('edition138 integrates the corrected MAR envelope and preserves other assets',async()=>{
 const proof=await read('result/blender/stage138/saved-verification.json');
 const rebuilt=await read('result/blender/stage138/rebuild/rebuild-verification.json');
 const catalogue=await read('dist/models/catalogue.json');
 const before=await read('result/blender/stage138/catalogue-before.json');
 expect(catalogue.version).toBe('138');
 expect(catalogue.sourceModelSha256).toBe(proof.sourceModelSha256);
 expect(proof.retainedOriginalObjects).toBe(5597);
 expect(proof.ownedObjects).toHaveLength(3);
 expect(proof.components.map(c=>c.code)).toEqual(['MAR']);
 expect(proof.savedSceneReopened).toBe(true);
 expect(proof.originalGeometryRetained).toBe(true);
 expect(proof.unrelatedVisibilityPreserved).toBe(true);
 expect(rebuilt.exactFingerprintMatch).toBe(true);
 expect(rebuilt.savedSceneReopened).toBe(true);
 expect(rebuilt.objects).toBe(5600);
 for(const b of catalogue.buildings){
  const old=before.buildings.find(o=>o.code===b.code);
  expect(b.detailedInterior,b.code).toEqual(old.detailedInterior);
  expect(b.interiorSpaces,b.code).toEqual(old.interiorSpaces);
  if(b.code==='MAR')expect(b.detailedExterior.url).not.toBe(old.detailedExterior.url);
  else expect(b.detailedExterior,b.code).toEqual(old.detailedExterior);
 }
});
test('MAR and daylight revised OLD CBG load on desktop and phone',async({page})=>{
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 for(const code of ['MAR','OLD','CBG'])for(const width of [1440,390]){
  await page.setViewportSize({width,height:1000});await page.goto('/#'+code);
  await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-'+code,{timeout:60000});
  await expect(page.locator('#fallback')).toBeHidden();
  await page.locator('#interior-view').click();
  await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','interior-'+code,{timeout:60000});
 }
 expect(errors).toEqual([]);
});
