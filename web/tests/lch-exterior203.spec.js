import {test,expect} from '@playwright/test';
import {readFile,mkdir,writeFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
const read=async path=>JSON.parse(await readFile(path,'utf8'));

test('LCH window correction preserves the complete campus and unrelated exterior/interior assets',async()=>{
 const before=await read('result/blender/stage203/catalogue-before.json');
 const current=await read('web/public/models/catalogue.json');
 const saved=await read('result/blender/stage203/reopened-verification.json');
 const proof=await read('result/blender/lch-exterior203/verification.json');
 expect(current.version).toBe('203');expect(saved.originalsVerified).toBe(7045);
 expect(saved.addedObjectsVerified).toBe(15);expect(saved.completeModelReopened).toBe(true);
 expect(proof.apertureProbes).toHaveLength(16);
 expect(proof.apertureProbes.every(row=>row.firstObject==='LCH203_sash_glass'&&row.nearOpaqueBacking===null)).toBe(true);
 const native=await readFile('result/blender/LSE_campus_detailed_v203.blend');
 expect(createHash('sha256').update(native).digest('hex')).toBe(current.sourceModelSha256);
 for(const building of current.buildings){
  const previous=before.buildings.find(row=>row.code===building.code);
  expect(building.interiorAsset??null,building.code).toEqual(previous.interiorAsset??null);
  expect(building.detailedInterior??null,building.code).toEqual(previous.detailedInterior??null);
  expect(building.interiorSpaces??null,building.code).toEqual(previous.interiorSpaces??null);
  if(building.code==='LCH')expect(building.detailedExterior.sha256).not.toBe(previous.detailedExterior.sha256);
  else expect(building.detailedExterior,building.code).toEqual(previous.detailedExterior);
 }
});

test('published LCH exterior remains interactive on desktop and mobile and joins the overview',async({page})=>{
 const errors=[];page.on('pageerror',error=>errors.push(error.message));
 await mkdir('result/blender/stage203/browser',{recursive:true});
 for(const width of [1440,390]){
  await page.setViewportSize({width,height:1000});await page.goto('/#LCH');
  const canvas=page.locator('canvas');await expect(canvas).toHaveAttribute('data-detail-ready','exterior-LCH',{timeout:65000});
  await page.screenshot({path:'result/blender/stage203/browser/lch-'+width+'.png'});
  await page.locator('#overview').click();await expect(canvas).toHaveAttribute('data-campus-details',/LCH/);
 }
 expect(errors).toEqual([]);await writeFile('result/blender/stage203/browser/acceptance.json',JSON.stringify({widths:[1440,390],exteriorLCH:true,overviewIncludesLCH:true,errors},null,2)+'\n');
});
