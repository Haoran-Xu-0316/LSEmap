import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';
test('saved Aldwych piers span all three middle storeys',async()=>{
 const a=JSON.parse(await readFile('result/blender/stage64/aldwych-belts-audit.json'));expect(a.changedExistingGeometry).toHaveLength(5);expect(a.savedMeasurements.continuousPilasters).toBe(24);expect(a.savedMeasurements.pilasterHeights.every(h=>Math.abs(h-10.8)<.0001)).toBeTruthy();expect(a.savedMeasurements.metalSpandrels).toBe(96);expect(a.savedMeasurements.retainedPavilionFaces).toBe(8);expect(a.savedMeasurements.verifiedClippedJoints).toBe(a.clippedJointSegments.length);expect(a.savedMeasurements.verifiedClippedJoints).toBeGreaterThan(300);
});
test('Aldwych metal spandrels are shared by the overview and detailed exterior',async()=>{
 const c=JSON.parse(await readFile('dist/models/catalogue.json'));const b=c.buildings.find(b=>b.code==='61A');
 for(const path of ['/models/campus.glb',b.detailedExterior.url]){
  const bytes=await readFile('dist'+path);const d=JSON.parse(bytes.subarray(20,20+bytes.readUInt32LE(12)));const node=d.nodes.find(n=>n.extras?.buildingCode==='61A')??d.nodes.find(n=>n.mesh!==undefined);const names=d.meshes[node.mesh].primitives.map(p=>d.materials[p.material].name);expect(names.some(n=>n.endsWith('61A_V64_spandrel'))).toBeTruthy();expect(names.some(n=>n.endsWith('61A_V63_slate'))).toBeTruthy();
 }
});
test('Aldwych window-belt close view opens with the exterior',async({page})=>{
 const errors=[];page.on('pageerror',e=>errors.push(e.message));await page.goto('/#61A');await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-61A',{timeout:60000});await expect(page.locator('#fallback')).toBeHidden();await page.locator('.detail-gallery img[src*="61a-belts"]').click();await expect(page.locator('#gallery-image')).toHaveAttribute('src',/61a-belts\.webp\?v=/);expect(errors).toEqual([]);
});
