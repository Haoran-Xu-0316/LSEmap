import {test,expect} from '@playwright/test';
import {readFile,mkdir,writeFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
const read=async path=>JSON.parse(await readFile(path,'utf8'));

test('CBG registered envelope preserves unrelated buildings and isolated rooms',async()=>{
 const before=await read('result/blender/stage205/catalogue-before.json');
 const current=await read('web/public/models/catalogue.json');
 const saved=await read('result/blender/stage205/reopened-verification.json');
 const assembly=await read('result/blender/cbg-assembled205/audit.json');
 const podium=await read('result/blender/cbg-podium205/independent-verification.json');
 const stair=await read('result/blender/cbg-stair205/audit.json');
 expect(current.version).toBe('205');expect(saved.originalsVerified).toBe(7066);
 expect(saved.addedObjectsVerified).toBe(183);expect(saved.completeModelReopened).toBe(true);
 expect(assembly.verification.officeSurfaceProbes).toBe(172);
 expect(stair.savedGeometryChecks.treadSolidCount).toBe(28);
 expect(stair.verification.actualEndpointSupportPass).toBe(true);
 expect(stair.obstructions).toEqual([]);
 const native=await readFile('result/blender/LSE_campus_detailed_v205.blend');
 expect(createHash('sha256').update(native).digest('hex')).toBe(current.sourceModelSha256);
 for(const building of current.buildings){
  const previous=before.buildings.find(row=>row.code===building.code);
  expect(building.interiorSpaces??null,building.code+' rooms').toEqual(previous.interiorSpaces??null);
  if(building.code==='CBG'){
   expect(building.detailedExterior.sha256).not.toBe(previous.detailedExterior.sha256);
   expect(building.detailedInterior.sha256).not.toBe(previous.detailedInterior.sha256);
  }else for(const key of ['detailedExterior','detailedInterior','interiorView'])expect(building[key]??null,building.code+key).toEqual(previous[key]??null);
 }
 expect(podium.sameFacingDuplicatePolygonCount).toBe(0);
 expect(podium.actualSavedComponentReopened).toBe(true);
 expect(podium.actualSavedReviewReopened).toBe(true);
});

test('CBG exterior public circulation and four rooms render on desktop and mobile',async({page})=>{
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await mkdir('result/blender/stage205/browser',{recursive:true});
 for(const width of [1440,390]){
  await page.setViewportSize({width,height:1000});await page.goto('/#CBG');
  const canvas=page.locator('canvas');await expect(canvas).toHaveAttribute('data-detail-ready','exterior-CBG',{timeout:65000});
  await page.waitForTimeout(1300);await page.screenshot({path:'result/blender/stage205/browser/cbg-exterior-'+width+'.png'});
  await page.locator('#interior-view').click();await expect(canvas).toHaveAttribute('data-interior-space','default',{timeout:65000});
  await page.waitForTimeout(1300);await page.screenshot({path:'result/blender/stage205/browser/cbg-interior-'+width+'.png'});
  if(width===1440)for(const id of ['cbg-102','cbg-103','cbg-104','cbg-205']){
   await page.locator('#interior-space').selectOption(id);await expect(canvas).toHaveAttribute('data-interior-space',id,{timeout:65000});
  }
  await page.locator('#overview').click();await expect(canvas).toHaveAttribute('data-campus-details',/CBG/);
  await page.waitForTimeout(1300);await page.screenshot({path:'result/blender/stage205/browser/cbg-overview-'+width+'.png'});
 }
 expect(errors).toEqual([]);await writeFile('result/blender/stage205/browser/acceptance.json',JSON.stringify({widths:[1440,390],exterior:true,publicInterior:true,allFourRooms:true,overview:true,errors},null,2)+'\n');
});
