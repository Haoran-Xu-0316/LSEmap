import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';

test('saved OLD reveal is recessed and the replacement composition retains five figures and two baskets',async()=>{
 const audit=JSON.parse(await readFile('result/blender/stage56/old-entry-relief-audit.json'));
 expect(audit.changedOtherObjects).toEqual([]);
 expect(audit.hiddenPreviousObjects).toContain('OLD_Rusticated_arch_voussoirs');
 expect(audit.hiddenPreviousObjects).toContain('OLD_V52_Houghton_stone');
 expect(audit.hiddenPreviousObjects).toContain('OLD_Photographic_relief_panel');
 expect(audit.savedRevealDepthRange[0]).toBeLessThan(-.62);
 expect(audit.savedRevealDepthRange[1]).toBeGreaterThan(.21);
 expect(audit.figureCount).toBe(5);expect(audit.basketCount).toBe(2);
 expect(audit.figures.map(f=>f.pose)).toEqual(['walking','basket','reaching','raised','basket']);
 expect(audit.limitations.join(' ')).toContain('not a scan');
});

test('overview and detail share the new OLD relief without exporting the reference photograph',async()=>{
 const catalogue=JSON.parse(await readFile('dist/models/catalogue.json'));const old=catalogue.buildings.find(b=>b.code==='OLD');
 for(const url of ['/models/campus.glb',old.detailedExterior.url]){
  const bytes=await readFile('dist'+url);const doc=JSON.parse(bytes.subarray(20,20+bytes.readUInt32LE(12)));
  const node=doc.nodes.find(n=>n.extras?.buildingCode==='OLD')??doc.nodes.find(n=>n.mesh!==undefined);
  const names=doc.meshes[node.mesh].primitives.map(p=>doc.materials[p.material].name);
  for(const key of ['stone','reveal','shelf','basket','book','rim','backing','joint'])expect(names.some(n=>n.endsWith('OLD_V56_'+key))).toBeTruthy();
  expect(names.some(n=>n.includes('OLD_V53_blue'))).toBeTruthy();
  expect((doc.images??[]).every(image=>image.name==='globe-map')).toBeTruthy();
 }
});

test('current OLD entry gallery and 3D exterior load without errors',async({page})=>{
 const errors=[];page.on('pageerror',e=>errors.push(e.message));await page.goto('/#OLD');
 await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-OLD',{timeout:60000});
 await expect(page.locator('#fallback')).toBeHidden();await page.locator('.detail-gallery img[src*="old-houghton-entrance"]').click();
 await expect(page.locator('#gallery-image')).toHaveAttribute('src',/old-houghton-entrance\.webp\?v=/);expect(errors).toEqual([]);
});
