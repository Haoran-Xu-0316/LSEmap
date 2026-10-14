import{test,expect}from'@playwright/test';
import{readFile,mkdir,writeFile}from'node:fs/promises';
import{createHash}from'node:crypto';
const read=async p=>JSON.parse(await readFile(p,'utf8'));

test('edition207 preserves room isolation and unrelated assets',async()=>{
 const before=await read('result/blender/stage207/catalogue-before.json'),current=await read('web/public/models/catalogue.json');
 const saved=await read('result/blender/stage207/reopened-verification.json'),scene=await read('result/blender/stage207/independent-scene-verification.json'),pea=await read('result/blender/pea-interior207/verification.json'),por=await read('result/blender/por-exterior207/verification.json');
 expect(current.version).toBe('207');expect(saved.originalsVerified).toBe(7257);expect(saved.addedObjectsVerified).toBe(33);expect(saved.completeModelReopened).toBe(true);
 expect(scene.noAuditoriumLeakIntoCampus).toBe(true);expect(scene.archivedObjectsHiddenInOwningLayers).toBe(true);expect(scene.newObjectsVisibleInOwningLayers).toBe(true);expect(scene.actualStageClearHeight).toBeCloseTo(5.9,5);
 expect(pea.seatSupportRays).toBe(846);expect(pea.seatSupportMisses).toEqual([]);expect(pea.stallsRows).toBe(22);expect(pea.circleSectionAnchors).toBe(8);expect(pea.prosceniumOpening).toEqual([13,5.9]);
 expect(por.originalGeometryUvMaterialBindingsUnchanged).toBe(true);expect(por.replacementUvPreserved).toBe(true);expect(por.exactAddedObjects).toHaveLength(3);
 const native=await readFile('result/blender/LSE_campus_detailed_v207.blend');expect(createHash('sha256').update(native).digest('hex')).toBe(current.sourceModelSha256);
 for(const b of current.buildings){const previous=before.buildings.find(x=>x.code===b.code);expect(b.interiorSpaces??null,b.code+'rooms').toEqual(previous.interiorSpaces??null);
  if(b.code==='PEA'){expect(b.detailedInterior.sha256).not.toBe(previous.detailedInterior.sha256);expect(b.interiorStudy.scope).toContain('846');}else expect(b.detailedInterior??null,b.code+'interior').toEqual(previous.detailedInterior??null);
  if(b.code==='POR')expect(b.detailedExterior.sha256).not.toBe(previous.detailedExterior.sha256);else expect(b.detailedExterior??null,b.code+'exterior').toEqual(previous.detailedExterior??null);
 }
});

test('PEA auditorium and POR entrance render on desktop and mobile',async({page})=>{
 const errors=[];page.on('pageerror',e=>errors.push(e.message));await mkdir('result/blender/stage207/browser',{recursive:true});
 for(const width of[1440,390]){
  await page.setViewportSize({width,height:1000});await page.goto('/#PEA');const canvas=page.locator('canvas');await expect(canvas).toHaveAttribute('data-detail-ready','exterior-PEA',{timeout:65000});await page.locator('#interior-view').click();await expect(canvas).toHaveAttribute('data-detail-ready','interior-PEA',{timeout:65000});await page.waitForTimeout(1300);await page.screenshot({path:'result/blender/stage207/browser/pea-'+width+'.png'});
  if(width===1440)for(const[caption,name]of[['Peacock Stalls与舞台口','pea-stalls-interior'],['Peacock楼座与池座','pea-circle-interior']]){
   await page.getByRole('button',{name:caption,exact:true}).click();await expect(page.locator('#gallery-image')).toHaveAttribute('src',new RegExp(name));await page.waitForFunction(()=>{const i=document.querySelector('#gallery-image');return i?.complete&&i.naturalWidth>0;});await page.screenshot({path:'result/blender/stage207/browser/'+name+'.png'});await page.getByRole('button',{name:'关闭图片',exact:true}).click();
  }
  await page.goto('/#POR');await expect(canvas).toHaveAttribute('data-detail-ready','exterior-POR',{timeout:65000});await page.locator('#detail-view').click();await page.waitForTimeout(1300);await page.screenshot({path:'result/blender/stage207/browser/por-'+width+'.png'});await expect(page.locator('#fallback')).toBeHidden();
 }
 expect(errors).toEqual([]);await writeFile('result/blender/stage207/browser/acceptance.json',JSON.stringify({widths:[1440,390],peaInterior:true,porEntrance:true,peaGalleryViews:2,errors},null,2)+'\n');
});
