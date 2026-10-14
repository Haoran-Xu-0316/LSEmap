import{test,expect}from'@playwright/test';
import{readFile,mkdir,writeFile}from'node:fs/promises';
import{createHash}from'node:crypto';
const read=async path=>JSON.parse(await readFile(path,'utf8'));

test('edition208 preserves unrelated buildings and all independent room assets',async()=>{
 const before=await read('result/blender/stage208/catalogue-before.json'),current=await read('web/public/models/catalogue.json'),saved=await read('result/blender/stage208/reopened-verification.json');
 expect(current.version).toBe('208');expect(saved.originalsVerified).toBe(7290);expect(saved.addedObjectsVerified).toBe(41);expect(saved.completeModelReopened).toBe(true);
 expect(createHash('sha256').update(await readFile('result/blender/LSE_campus_detailed_v208.blend')).digest('hex')).toBe(current.sourceModelSha256);
 for(const b of current.buildings){const previous=before.buildings.find(x=>x.code===b.code);expect(b.interiorSpaces??null,b.code+'rooms').toEqual(previous.interiorSpaces??null);
  if(['61A','CON','OCS'].includes(b.code))expect(b.detailedExterior.sha256,b.code).not.toBe(previous.detailedExterior.sha256);else expect(b.detailedExterior??null,b.code+'exterior').toEqual(previous.detailedExterior??null);
  if(b.code==='LRB')expect(b.detailedInterior.sha256).not.toBe(previous.detailedInterior.sha256);else expect(b.detailedInterior??null,b.code+'interior').toEqual(previous.detailedInterior??null);
 }
 expect(current.buildings.find(b=>b.code==='61A').status).toBe('provisional');
 const ocs=await read('result/blender/ocs-exterior208/verification.json'),con=await read('result/blender/con-exterior208/verification.json'),library=await read('result/blender/lrb-interior208/verification.json');
 expect(ocs.savedComponentReopened).toBe(true);expect(ocs.replacementSurfacePreserved).toBe(true);expect(ocs.glassGeometryOpticsAndInteriorUnchanged).toBe(true);
 const aldwych=await read('result/blender/61a-exterior208/verification.json');expect(aldwych.backedTransparentPanes).toBe(10);expect(aldwych.retainedOpaqueProxyPanes).toBe(243);expect(aldwych.backingRayCount).toBe(1265);
 expect(con.savedComponentReopened).toBe(true);expect(library.supportRaysVerified).toBe(75);expect(library.noGStudyFurnitureIntersections).toBe(true);expect(library.noAtriumOpeningIntrusion).toBe(true);
 const gallery=await read('web/public/gallery-manifest.json');const view=gallery.images.find(i=>i.name==='lrb-services-interior');expect(view.sectionId).toBe('G');expect(view.mode).toBe('interior');
});

test('corrected exteriors and library G section render on desktop and mobile',async({page})=>{
 test.setTimeout(150000);const folder='result/blender/stage208/browser',errors=[];await mkdir(folder,{recursive:true});page.on('pageerror',error=>errors.push(error.message));
 for(const width of[1440,390]){
  await page.setViewportSize({width,height:1000});
  for(const code of['61A','CON','OCS']){
   await page.goto('/#'+code);await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-'+code,{timeout:65000});await page.waitForTimeout(1000);await page.screenshot({path:folder+'/'+code+'-'+width+'.png'});await expect(page.locator('#fallback')).toBeHidden();
  }
  await page.goto('/#LRB');await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-LRB',{timeout:65000});await page.locator('#interior-view').click();await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','interior-LRB',{timeout:65000});
  await page.locator('#interior-level').selectOption('G');await expect(page.locator('canvas')).toHaveAttribute('data-interior-section','G');await page.waitForTimeout(1100);await page.screenshot({path:folder+'/lrb-G-'+width+'.png'});
  await page.getByRole('button',{name:'图书馆G层公共服务区',exact:true}).click();await expect(page.locator('#gallery-image')).toHaveAttribute('src',/lrb-services-interior/);await page.waitForFunction(()=>{const i=document.querySelector('#gallery-image');return i?.complete&&i.naturalWidth>0;});await page.screenshot({path:folder+'/lrb-services-gallery-'+width+'.png'});await page.getByRole('button',{name:'关闭图片',exact:true}).click();
 }
 expect(errors).toEqual([]);await writeFile(folder+'/acceptance.json',JSON.stringify({widths:[1440,390],exteriors:['61A','CON','OCS'],libraryGSection:true,currentServiceGallery:true,errors},null,2)+'\n');
});
