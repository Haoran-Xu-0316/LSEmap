import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';

test('saved LRB roof regions are connected and retain the circular lightwell',async()=>{
 const audit=JSON.parse(await readFile('result/blender/stage60/library-mansard-audit.json'));
 expect(audit.changedOtherObjects).toEqual([]);expect(audit.changedExisting).toHaveLength(4);
 const measured=audit.savedMeasurements;expect(measured.deckHeight).toBeCloseTo(measured.domeBase,4);
 expect(measured.perimeterUpwardFaces).toBe(audit.roofTriangleCount);expect(measured.inwardLightwellLining).toBeTruthy();
 expect(measured.preservedVoidPoints).toBeGreaterThan(100);expect(measured.verifiedDormers).toBe(audit.dormers.length);
 const areas=audit.roofRegionAreas;expect(areas.bandArea+areas.deckArea+areas.holeArea).toBeCloseTo(areas.outerArea,5);
 expect(audit.dormerRoofFaces).toBe(2*audit.dormers.length);expect(audit.removedVerticalGridBars).toBe(5);
 expect(measured.gridFamilies).toBe(3);expect(measured.verifiedGridLines).toBeGreaterThan(10);
});

test('LRB overview, exterior and interior share the new perimeter roof materials',async()=>{
 const catalogue=JSON.parse(await readFile('dist/models/catalogue.json'));const b=catalogue.buildings.find(b=>b.code==='LRB');
 for(const [url,code]of [['/models/campus.glb','LRB'],[b.detailedExterior.url,'LRB'],[b.detailedInterior.url,'LRB_INTERIOR']]){
  const bytes=await readFile('dist'+url);const doc=JSON.parse(bytes.subarray(20,20+bytes.readUInt32LE(12)));
  const node=doc.nodes.find(n=>n.extras?.buildingCode===code)??doc.nodes.find(n=>n.mesh!==undefined);
  const names=doc.meshes[node.mesh].primitives.map(p=>doc.materials[p.material].name);
  for(const key of ['slate','stone','frame','glass','lining','roof_deck_lead','aperture_steel'])expect(names.some(name=>name.endsWith('LRB_V60_'+key))).toBeTruthy();
 }
});

test('LRB roof gallery and connected interior load without browser errors',async({page})=>{
 const errors=[];page.on('pageerror',e=>errors.push(e.message));await page.goto('/#LRB');
 await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-LRB',{timeout:60000});
 await expect(page.locator('#fallback')).toBeHidden();await page.locator('.detail-gallery img[src*="lrb-roof"]').click();
 await expect(page.locator('#gallery-image')).toHaveAttribute('src',/lrb-roof\.webp\?v=/);
 await page.keyboard.press('Escape');await page.locator('#interior-view').click();
 await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','interior-LRB',{timeout:60000});expect(errors).toEqual([]);
});
