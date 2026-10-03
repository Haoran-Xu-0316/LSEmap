import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';
const read=async path=>JSON.parse(await readFile(path,'utf8'));
test('edition137 integrates three independent street facades and preserves other assets',async()=>{
 const proof=await read('result/blender/stage137/saved-verification.json');
 const rebuilt=await read('result/blender/stage137/rebuild/rebuild-verification.json');
 const catalogue=await read('dist/models/catalogue.json');
 const before=await read('result/blender/stage137/catalogue-before.json');
 expect(catalogue.version).toBe('137');
 expect(catalogue.sourceModelSha256).toBe(proof.sourceModelSha256);
 expect(proof.retainedOriginalObjects).toBe(5567);
 expect(proof.ownedObjects).toHaveLength(30);
 expect(proof.components.map(c=>c.code)).toEqual(['CLM','61A','COL']);
 expect(proof.savedSceneReopened).toBe(true);
 expect(proof.originalGeometryRetained).toBe(true);
 expect(proof.unrelatedVisibilityPreserved).toBe(true);
 expect(rebuilt.exactFingerprintMatch).toBe(true);
 expect(rebuilt.savedSceneReopened).toBe(true);
 expect(rebuilt.objects).toBe(5597);
 for(const b of catalogue.buildings){
  const old=before.buildings.find(o=>o.code===b.code);
  expect(b.detailedInterior,b.code).toEqual(old.detailedInterior);
  expect(b.interiorSpaces,b.code).toEqual(old.interiorSpaces);
  if(['CLM','61A','COL'].includes(b.code))expect(b.detailedExterior.url).not.toBe(old.detailedExterior.url);
  else expect(b.detailedExterior,b.code).toEqual(old.detailedExterior);
 }
});
test('three revised street facades and retained interiors load on desktop and phone',async({page})=>{
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 for(const code of ['CLM','61A','COL'])for(const width of [1440,390]){
  await page.setViewportSize({width,height:1000});await page.goto('/#'+code);
  await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-'+code,{timeout:60000});
  await expect(page.locator('#fallback')).toBeHidden();
  await page.locator('#interior-view').click();
  await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','interior-'+code,{timeout:60000});
 }
 expect(errors).toEqual([]);
});
