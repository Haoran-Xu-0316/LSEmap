import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';
test('saved OLD entablature preserves main windows and interiors while correcting attic sashes',async()=>{
 const a=JSON.parse(await readFile('result/blender/stage77/old-entablature-audit.json'));
 expect(a.savedMeasurements.changedOriginalGeometry).toEqual(['OLD_Window_sash_bars']);
 expect(a.savedMeasurements.mainWindowsUnchanged).toBeTruthy();
 expect(a.savedMeasurements.mansardWindows).toBe(10);
 expect(a.savedMeasurements.otherBuildingsAndInteriorsUnchanged).toBeTruthy();
 expect(a.savedMeasurements.roundels).toBe(15);
 expect(a.savedMeasurements.profiledConsoles).toBe(6);
 expect(a.savedMeasurements.archedScreens).toBe(4);
 expect(a.savedMeasurements.upperVents).toBe(5);
});
test('overview and OLD detail contain the same entablature and opened mansard materials',async()=>{
 const c=JSON.parse(await readFile('dist/models/catalogue.json'));
 const building=c.buildings.find(b=>b.code==='OLD');
 for(const url of ['/models/campus.glb',building.detailedExterior.url]){
  const bytes=await readFile('dist'+url);
  const doc=JSON.parse(bytes.subarray(20,20+bytes.readUInt32LE(12)));
  const node=doc.nodes.find(n=>n.extras?.buildingCode==='OLD')??doc.nodes.find(n=>n.mesh!==undefined);
  const primitives=doc.meshes[node.mesh].primitives;
  const names=primitives.map(p=>doc.materials[p.material].name);
  for(const key of ['stone','blue','recess','mansard_brick'])expect(names.some(n=>n.endsWith('OLD_V77_'+key))).toBeTruthy();
 }
});
test('OLD exterior and entablature gallery load without errors',async({page})=>{
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('/#OLD');
 await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-OLD',{timeout:60000});
 await expect(page.locator('#fallback')).toBeHidden();
 await page.locator('.detail-gallery img[src*="old-entablature"]').click();
 await expect(page.locator('#gallery-image')).toBeVisible();
 expect(await page.locator('#gallery-image').evaluate(i=>i.complete&&i.naturalWidth>0)).toBeTruthy();
 expect(errors).toEqual([]);
});
