import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';

test('Houghton correction preserves other buildings and keeps unresolved sculpture explicit',async()=>{
 const audit=JSON.parse(await readFile('result/blender/stage52/old-houghton-audit.json'));
 expect(audit.changedOtherObjects).toEqual([]);
 expect(audit.changedExistingObjects.every(name=>name.startsWith('OLD_'))).toBeTruthy();
 expect(audit.windowCount).toBe(14);expect(audit.windowColumns).toBe(3);
 expect(audit.stoneBlocks).toBeGreaterThan(300);
 expect(audit.removedCentralBarFaces).toBe(84);
 expect(audit.removedDoorFaces.OLD_Window_glazing).toBeGreaterThan(0);
 expect(audit.reliefFigureCount).toBe(5);
 expect(audit.limitations.join(' ')).toContain('not a sculpture scan');
});

test('overview and detail export the same new entrance masonry and window materials',async()=>{
 const catalogue=JSON.parse(await readFile('dist/models/catalogue.json'));
 const old=catalogue.buildings.find(b=>b.code==='OLD');
 for(const url of ['/models/campus.glb',old.detailedExterior.url]){
  const bytes=await readFile('dist'+url);
  const doc=JSON.parse(bytes.subarray(20,20+bytes.readUInt32LE(12)).toString());
  const node=doc.nodes.find(n=>n.extras?.buildingCode==='OLD')??doc.nodes.find(n=>n.mesh!==undefined);
  const names=doc.meshes[node.mesh].primitives.map(p=>doc.materials[p.material].name);
  for(const key of ['ashlar_0','ashlar_6','blue','iron','vent'])expect(names.some(n=>n.includes('OLD_V52_'+key))).toBeTruthy();
  expect((doc.images??[]).every(image=>image.name==='globe-map')).toBeTruthy();
 }
});

test('OLD close view is available from the current gallery without browser errors',async({page})=>{
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('/#OLD');
 await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-OLD',{timeout:60000});
 const image=page.locator('.detail-gallery img[src*="old-houghton-entrance"]');
 await expect(image).toBeVisible();await image.click();
 await expect(page.locator('#gallery-image')).toHaveAttribute('src',/old-houghton-entrance/);
 expect(errors).toEqual([]);
});
