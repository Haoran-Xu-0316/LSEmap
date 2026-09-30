import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';
test('saved Aldwych pavilion has eight roof faces and wrapping glazing',async()=>{
 const a=JSON.parse(await readFile('result/blender/stage63/aldwych-pavilion-audit.json'));
 expect(a.changedExistingGeometry).toEqual([]);expect(a.savedMeasurements.roofFaces).toBe(8);expect(a.savedMeasurements.upwardRoofFaces).toBe(8);expect(a.savedMeasurements.eave).toBeCloseTo(35.35,4);expect(a.savedMeasurements.peak).toBeCloseTo(37.7,4);expect(a.savedMeasurements.lowerWindows).toBe(8);expect(a.savedMeasurements.clerestoryFaces).toBe(8);
});
test('Aldwych overview and detailed roof share pavilion finishes',async()=>{
 const c=JSON.parse(await readFile('dist/models/catalogue.json'));const b=c.buildings.find(b=>b.code==='61A');
 for(const path of ['/models/campus.glb',b.detailedExterior.url]){
  const bytes=await readFile('dist'+path);const d=JSON.parse(bytes.subarray(20,20+bytes.readUInt32LE(12)));const node=d.nodes.find(n=>n.extras?.buildingCode==='61A')??d.nodes.find(n=>n.mesh!==undefined);const names=d.meshes[node.mesh].primitives.map(p=>d.materials[p.material].name);
  for(const k of ['stone','trim','glass','bronze','slate'])expect(names.some(n=>n.endsWith('61A_V63_'+k))).toBeTruthy();
 }
});
test('Aldwych roof close view opens with the live model',async({page})=>{
 const errors=[];page.on('pageerror',e=>errors.push(e.message));await page.goto('/#61A');await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-61A',{timeout:60000});await expect(page.locator('#fallback')).toBeHidden();await page.locator('.detail-gallery img[src*="61a-pavilion"]').click();await expect(page.locator('#gallery-image')).toHaveAttribute('src',/61a-pavilion\.webp\?v=/);expect(errors).toEqual([]);
});
