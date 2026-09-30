import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';

test('Clare Market refinement affects only OLD facade components',async()=>{
 const audit=JSON.parse(await readFile('result/blender/stage49/old-clare-audit.json'));
 expect(audit.edgeIndex).toBe(7);
 expect(audit.edgeLength).toBeGreaterThan(17);
 expect(audit.measuredStepRanges).toHaveLength(4);
 for(const [bottom,top] of audit.measuredStepRanges){expect(bottom).toBeCloseTo(.05,5);expect(top).toBeGreaterThan(bottom);}
 expect(audit.changedExistingObjects.length).toBeGreaterThan(0);
 expect(audit.changedExistingObjects.every(n=>n.startsWith('OLD_'))).toBeTruthy();
 expect(Object.keys(audit.removedLocalFaces).sort()).toEqual(audit.changedExistingObjects.sort());
 expect(audit.limitations.join(' ')).toContain('figurative carving remains unresolved');
});

test('OLD overview and on-demand detail both contain the blue portal and red-white sculpture',async()=>{
 const catalogue=JSON.parse(await readFile('dist/models/catalogue.json'));
 const old=catalogue.buildings.find(b=>b.code==='OLD');
 for(const path of ['/models/campus.glb',old.detailedExterior.url]){
  const bytes=await readFile('dist'+path);
  const doc=JSON.parse(bytes.subarray(20,20+bytes.readUInt32LE(12)).toString());
  const node=doc.nodes.find(n=>n.extras?.buildingCode==='OLD')??doc.nodes.find(n=>n.mesh!==undefined);
  const names=doc.meshes[node.mesh].primitives.map(p=>doc.materials[p.material].name);
  for(const key of ['blue','red','white','stone','metal'])expect(names.some(n=>n.includes('OLD_V53_'+key))).toBeTruthy();
  const blue=doc.materials.find(m=>m.name.includes('OLD_V53_blue')).pbrMetallicRoughness.baseColorFactor;
  expect(blue[2]).toBeGreaterThan(blue[1]);expect(blue[1]).toBeGreaterThan(blue[0]);
 }
});

test('OLD gallery exposes the refined Clare Market facade',async({page})=>{
 await page.goto('/#OLD');
 await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-OLD',{timeout:60000});
 const image=page.locator('.detail-gallery img[src*="old-clare-market"]');
 await expect(image).toHaveAttribute('src',new RegExp('v='+JSON.parse(await readFile('dist/models/catalogue.json')).version+'-'));
 await image.click();
 await expect(page.locator('#gallery-image')).toHaveAttribute('src',/old-clare-market/);
});
