import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';

test('5LF saved ground openings have shallow arched crowns and isolated geometry changes',async()=>{
 const audit=JSON.parse(await readFile('result/blender/stage55/five-lincolns-frontage-audit.json'));
 expect(audit.changedOtherObjects).toEqual([]);
 expect(audit.arches).toHaveLength(3);
 expect(audit.savedArchHeights.glass.length).toBeGreaterThan(10);
 expect(Math.max(...audit.savedArchHeights.glass)).toBe(3.5);
 expect(Math.min(...audit.savedArchHeights.glass)).toBe(3.25);
 expect(audit.removedRectangularFaces['5LF_D5_head_white']).toBeGreaterThan(0);
});

test('5LF overview and detail use the same new arch materials',async()=>{
 const catalogue=JSON.parse(await readFile('dist/models/catalogue.json'));const building=catalogue.buildings.find(b=>b.code==='5LF');
 for(const url of ['/models/campus.glb',building.detailedExterior.url]){
  const bytes=await readFile('dist'+url);const doc=JSON.parse(bytes.subarray(20,20+bytes.readUInt32LE(12)));
  const node=doc.nodes.find(n=>n.extras?.buildingCode==='5LF')??doc.nodes.find(n=>n.mesh!==undefined);
  const names=doc.meshes[node.mesh].primitives.map(p=>doc.materials[p.material].name);
  for(const key of ['plaster','frame','glass','door'])expect(names.some(name=>name.endsWith('5LF_V55_'+key))).toBeTruthy();
 }
});

test('5LF current exterior loads and opens its refreshed gallery',async({page})=>{
 const errors=[];page.on('pageerror',e=>errors.push(e.message));await page.goto('/#5LF');
 await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-5LF',{timeout:60000});
 await expect(page.locator('#fallback')).toBeHidden();await page.locator('.detail-photo').click();
 await expect(page.locator('#gallery-image')).toHaveAttribute('src',/5lf-exterior\.webp\?v=/);expect(errors).toEqual([]);
});
