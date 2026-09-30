import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';
test('saved PAR has pointed window heads, two cowls and four round chimney pots',async()=>{
 const a=JSON.parse(await readFile('result/blender/stage66/parish-exterior-audit.json'));
 expect(a.changedOtherObjects).toEqual([]);expect(a.savedMeasurements.roofCowls).toBe(2);
 expect(a.savedMeasurements.roundPots).toBe(4);expect(a.savedMeasurements.centralMullions).toBe(8);
 expect(a.savedMeasurements.lowerSashBars).toBe(4);expect(a.savedMeasurements.outwardEntranceGable).toBeTruthy();
 expect(a.savedMeasurements.upwardRoofFaces).toBeTruthy();
 for(const peak of a.savedMeasurements.pointedHeadPeaks)expect(peak).toBeGreaterThan(6.79);
});
test('PAR overview and close model share the corrected palette and roof furniture',async()=>{
 const c=JSON.parse(await readFile('dist/models/catalogue.json'));const b=c.buildings.find(b=>b.code==='PAR');
 for(const path of ['/models/campus.glb',b.detailedExterior.url]){
  const bytes=await readFile('dist'+path);const d=JSON.parse(bytes.subarray(20,20+bytes.readUInt32LE(12)));
  const node=d.nodes.find(n=>n.extras?.buildingCode==='PAR')??d.nodes.find(n=>n.mesh!==undefined);
  const names=d.meshes[node.mesh].primitives.map(p=>d.materials[p.material].name);
  for(const key of ['brick','tile','frame','lead','slate'])expect(names.some(n=>n.endsWith('PAR_V66_'+key))).toBeTruthy();
 }
});
test('PAR roof gallery opens with the live exterior',async({page})=>{
 const errors=[];page.on('pageerror',e=>errors.push(e.message));await page.goto('/#PAR');
 await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-PAR',{timeout:60000});
 await expect(page.locator('#fallback')).toBeHidden();await page.locator('.detail-gallery img[src*="par-roof"]').click();
 await expect(page.locator('#gallery-image')).toHaveAttribute('src',/par-roof\.webp\?v=/);expect(errors).toEqual([]);
});
