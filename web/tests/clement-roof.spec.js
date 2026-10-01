import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';
test('saved CLM roof has five dormers and four chimneys with protected lower facade',async()=>{
 const audit=JSON.parse(await readFile('result/blender/stage73/clement-roof-audit.json'));
 expect(audit.savedMeasurements.dormerCount).toBe(5);
 expect(audit.savedMeasurements.chimneyCount).toBe(4);
 expect(audit.savedMeasurements.lowerFacadeUnchanged).toBeTruthy();
 expect(audit.savedMeasurements.upwardFacingCaps).toBe(120);
});

test('campus and CLM close model share corrected slate, attic glazing and roof metalwork',async()=>{
 const catalogue=JSON.parse(await readFile('dist/models/catalogue.json'));
 const building=catalogue.buildings.find(b=>b.code==='CLM');
 for(const url of ['/models/campus.glb',building.detailedExterior.url]){
  const bytes=await readFile('dist'+url);
  const doc=JSON.parse(bytes.subarray(20,20+bytes.readUInt32LE(12)));
  const node=doc.nodes.find(n=>n.extras?.buildingCode==='CLM')??doc.nodes.find(n=>n.mesh!==undefined);
  const names=doc.meshes[node.mesh].primitives.map(p=>doc.materials[p.material].name);
  for(const key of ['slate','asphalt','glass','metal','paint'])expect(names.some(n=>n.endsWith('CLM_V73_'+key))).toBeTruthy();

 }
});

test('CLM exterior and refreshed gallery load in the browser',async({page})=>{
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('/#CLM');
 await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-CLM',{timeout:60000});
 await expect(page.locator('#fallback')).toBeHidden();
 await page.locator('.detail-gallery img[src*="clm-exterior"]').click();
 await expect(page.locator('#gallery-image')).toBeVisible();
 expect(await page.locator('#gallery-image').evaluate(i=>i.complete&&i.naturalWidth>0)).toBeTruthy();
 expect(errors).toEqual([]);
});
