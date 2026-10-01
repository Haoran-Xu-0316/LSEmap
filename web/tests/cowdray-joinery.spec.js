import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';

test('saved Cowdray sashes preserve other buildings and attic windows',async()=>{
  const audit=JSON.parse(await readFile('result/blender/stage76/cowdray-joinery-audit.json'));
  expect(audit.savedMeasurements.otherBuildingsAndInteriorsUnchanged).toBeTruthy();
  expect(audit.savedMeasurements.groundAndDormerRailsUnchanged).toBeTruthy();
  expect(audit.savedMeasurements.sixRowWindows).toBe(72);
  expect(audit.savedMeasurements.newHorizontalRails).toBe(288);
});

test('overview and Cowdray detail share corrected slate and sash materials',async()=>{
  const catalogue=JSON.parse(await readFile('dist/models/catalogue.json'));
  const building=catalogue.buildings.find(b=>b.code==='COW');
  for(const url of ['/models/campus.glb',building.detailedExterior.url]){
    const bytes=await readFile('dist'+url);
    const doc=JSON.parse(bytes.subarray(20,20+bytes.readUInt32LE(12)));
    const node=doc.nodes.find(n=>n.extras?.buildingCode==='COW')??doc.nodes.find(n=>n.mesh!==undefined);
    const names=doc.meshes[node.mesh].primitives.map(p=>doc.materials[p.material].name);
    for(const key of ['slate','frame','trim','stone'])expect(names.some(n=>n.endsWith('COW_V76_'+key))).toBeTruthy();
  }
});

test('Cowdray exterior and entrance gallery load without fallback',async({page})=>{
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto('/#COW');
  await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-COW',{timeout:60000});
  await expect(page.locator('#fallback')).toBeHidden();
  await page.locator('.detail-gallery img[src*="cow-entrance"]').click();
  await expect(page.locator('#gallery-image')).toBeVisible();
  expect(await page.locator('#gallery-image').evaluate(i=>i.complete&&i.naturalWidth>0)).toBeTruthy();
  expect(errors).toEqual([]);
});
