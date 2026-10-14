import {test,expect} from '@playwright/test';
import {readFile,mkdir,writeFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
const read=async path=>JSON.parse(await readFile(path,'utf8'));

test('edition209 preserves unrelated assets and recovers original mapped ground',async()=>{
 const before=await read('result/blender/stage209/catalogue-before.json'),current=await read('web/public/models/catalogue.json'),saved=await read('result/blender/stage209/reopened-verification.json');
 expect(current.version).toBe('209');expect(saved.originalsVerified).toBe(7331);expect(saved.addedObjectsVerified).toBe(42);expect(saved.completeModelReopened).toBe(true);
 expect(createHash('sha256').update(await readFile('result/blender/LSE_campus_detailed_v209.blend')).digest('hex')).toBe(current.sourceModelSha256);
 for(const b of current.buildings){const previous=before.buildings.find(x=>x.code===b.code);
  expect(b.interiorSpaces??null,b.code+' independent rooms').toEqual(previous.interiorSpaces??null);
  if(['MAR','OLD','CKK'].includes(b.code))expect(b.detailedExterior.sha256,b.code).not.toBe(previous.detailedExterior.sha256);
  else expect(b.detailedExterior??null,b.code+' exterior').toEqual(previous.detailedExterior??null);
  if(b.code==='CKK')expect(b.detailedInterior.sha256).not.toBe(previous.detailedInterior.sha256);
  else expect(b.detailedInterior??null,b.code+' interior').toEqual(previous.detailedInterior??null);
 }
 const ground=await read('result/blender/pedestrian-surfaces209/coverage-verification.json');expect(ground.verified).toBe(true);expect(ground.recoveredMappedPathAreaM2).toBeGreaterThan(2000);expect(ground.savedPathRays).toBe(78);expect(ground.explicitAsphaltWays).toBe(50);expect(ground.savedDuplicateAreaM2).toBeLessThan(.02);
 const old=await read('result/blender/old-exterior209/verification.json'),mar=await read('result/blender/mar-exterior209/verification.json'),ckk=await read('result/blender/ckk-interior209/verification.json');
 expect(old.continuousMetricBond.continuous).toBe(56);expect(old.allGlassGeometryBackingAndOpticsUnchanged).toBe(true);expect(mar.transmissionAndOpacityUnchanged).toBe(true);expect(ckk.centralVoidPreserved).toBe(true);
 const gallery=await read('web/public/gallery-manifest.json');expect(gallery.images).toHaveLength(134);expect(gallery.images.find(i=>i.name==='ckk-sounding-board-interior').mode).toBe('interior');
});

test('edition209 exteriors and added atrium gallery render on desktop and mobile',async({page})=>{
 test.setTimeout(150000);const folder='result/blender/stage209/browser',errors=[];await mkdir(folder,{recursive:true});page.on('pageerror',error=>errors.push(error.message));
 for(const width of [1440,390]){
  await page.setViewportSize({width,height:1000});
  for(const code of ['MAR','OLD']){
   await page.goto('/#'+code);await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-'+code,{timeout:65000});await page.waitForTimeout(1000);await page.screenshot({path:folder+'/'+code+'-'+width+'.png'});await expect(page.locator('#fallback')).toBeHidden();
  }
  await page.goto('/#CKK');await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-CKK',{timeout:65000});await page.locator('#interior-view').click();await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','interior-CKK',{timeout:65000});await page.waitForTimeout(1000);await page.screenshot({path:folder+'/ckk-interior-'+width+'.png'});
  await page.getByRole('button',{name:'公共中庭木墙与双层廊桥',exact:true}).click();await expect(page.locator('#gallery-image')).toHaveAttribute('src',/ckk-sounding-board-interior/);await page.waitForFunction(()=>{const i=document.querySelector('#gallery-image');return i?.complete&&i.naturalWidth>0;});await page.screenshot({path:folder+'/ckk-gallery-'+width+'.png'});await page.getByRole('button',{name:'关闭图片',exact:true}).click();
  await page.locator('#overview').click();await page.waitForTimeout(1100);await expect(page.locator('#fallback')).toBeHidden();await page.screenshot({path:folder+'/overview-'+width+'.png'});
 }
 expect(errors).toEqual([]);await writeFile(folder+'/acceptance.json',JSON.stringify({widths:[1440,390],exteriors:['MAR','OLD'],ckkAtrium:true,newGallery:true,overview:true,errors},null,2)+'\n');
});
