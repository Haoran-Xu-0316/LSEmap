import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';

test('saved OLD relief replaces the earlier sculpture without changing existing meshes',async()=>{
 const audit=JSON.parse(await readFile('result/blender/stage71/old-relief-drapery-audit.json'));
 expect(audit.savedMeasurements.changedOriginalObjects).toEqual([]);
 expect(audit.savedMeasurements.archDoorsAndClareRetained).toBeTruthy();
 expect(audit.figureCount).toBe(5);expect(audit.basketCount).toBe(2);
});

test('campus and close OLD models share the new relief and exclude the obsolete sculpture',async()=>{
 const catalogue=JSON.parse(await readFile('dist/models/catalogue.json'));
 const old=catalogue.buildings.find(b=>b.code==='OLD');
 for(const url of ['/models/campus.glb',old.detailedExterior.url]){
  const bytes=await readFile('dist'+url);
  const doc=JSON.parse(bytes.subarray(20,20+bytes.readUInt32LE(12)));
  const node=doc.nodes.find(n=>n.extras?.buildingCode==='OLD')??doc.nodes.find(n=>n.mesh!==undefined);
  const names=doc.meshes[node.mesh].primitives.map(p=>doc.materials[p.material].name);
  for(const key of ['stone','book','basket','shelf'])expect(names.some(n=>n.endsWith('OLD_V71_'+key))).toBeTruthy();
  expect(names.some(n=>n.endsWith('OLD_V56_stone'))).toBeFalsy();
 }
});

test('OLD sculpture gallery opens from the live detail panel',async({page})=>{
 await page.goto('/#OLD');
 await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-OLD',{timeout:60000});
 await expect(page.locator('#fallback')).toBeHidden();
 await page.locator('.detail-gallery img[src*="old-relief"]').click();
 await expect(page.locator('#gallery-image')).toBeVisible();
 expect(await page.locator('#gallery-image').evaluate(i=>i.complete&&i.naturalWidth>0)).toBeTruthy();
});
