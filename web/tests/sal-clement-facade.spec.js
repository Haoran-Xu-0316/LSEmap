import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';

test('saved SAL has three upper window bands and eighteen oblique oriel side panes',async()=>{
 const audit=JSON.parse(await readFile('result/blender/stage70/sal-clement-facade-audit.json'));
 expect(audit.savedMeasurements.mainWindowLevels).toEqual([2.85,7.3,11.65,15.85]);
 expect(audit.savedMeasurements.obliqueSidePanes).toBe(18);
 expect(audit.savedMeasurements.clementCapitalScrolls).toBe(8);
 expect(audit.savedMeasurements.outsideSalExistingObjectsUnchanged).toBeTruthy();
});

test('overview and detail share the revised SAL sash and CLM capital finishes',async()=>{
 const catalogue=JSON.parse(await readFile('dist/models/catalogue.json'));
 for(const [code,material] of [['SAL','SAL_V70_blue_painted_sash'],['CLM','CLM_D3_Portland_stone']]){
  const record=catalogue.buildings.find(b=>b.code===code);
  for(const url of ['/models/campus.glb',record.detailedExterior.url]){
   const bytes=await readFile('dist'+url);
   const doc=JSON.parse(bytes.subarray(20,20+bytes.readUInt32LE(12)));
   const node=doc.nodes.find(n=>n.extras?.buildingCode===code)??doc.nodes.find(n=>n.mesh!==undefined);
   const names=doc.meshes[node.mesh].primitives.map(p=>doc.materials[p.material].name);
   expect(names.some(n=>n.includes(material))).toBeTruthy();
  }
 }
});

test('SAL and CLM updated models and close galleries load without errors',async({page})=>{
 const errors=[];page.on('pageerror',error=>errors.push(error.message));
 for(const [code,image] of [['SAL','sal-oriels'],['CLM','clm-capitals']]){
  await page.goto('/#'+code);
  await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-'+code,{timeout:60000});
  await expect(page.locator('#fallback')).toBeHidden();
  await page.locator('.detail-gallery img[src*="'+image+'"]').click();
  await expect(page.locator('#gallery-image')).toHaveAttribute('src',new RegExp(image+'\\.webp\\?v='));
  await page.keyboard.press('Escape');
 }
 expect(errors).toEqual([]);
});
