import {test,expect} from '@playwright/test';
import {readFile,mkdir,writeFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
const read=async path=>JSON.parse(await readFile(path,'utf8'));
const proof='result/blender/stage221/browser';

test('edition221 bounds public-structure changes and preserves all existing rooms',async()=>{
 const before=await read('result/blender/stage221/catalogue-before.json');
 const after=await read('web/public/models/catalogue.json');
 const native=await read('result/blender/stage221/building-refinement.json');
 expect(before.version).toBe('220');expect(after.version).toBe('221');
 expect(after.sourceModelSha256).toBe(native.sourceModelSha256);expect(after.buildings).toHaveLength(31);
 const allowed=new Set(['SAL:detailedExterior','LRB:detailedExterior','LRB:detailedInterior']);
 const changed=[];let rooms=0;
 for(const old of before.buildings){
  const current=after.buildings.find(item=>item.code===old.code);
  for(const field of ['detailedExterior','detailedInterior']){
   if(!old[field])continue;
   const key=old.code+':'+field;
   if(current[field].sha256!==old[field].sha256){
    expect(allowed.has(key),key).toBe(true);changed.push(key);
   }
  }
  for(const room of old.interiorSpaces||[]){
   expect(current.interiorSpaces.find(item=>item.id===room.id).detailedInterior.sha256,room.id).toBe(room.detailedInterior.sha256);rooms++;
  }
 }
 expect(changed.sort()).toEqual(['LRB:detailedExterior','LRB:detailedInterior','SAL:detailedExterior']);
 expect(rooms).toBe(19);
 for(const item of await read('result/blender/stage221/asset-hashes-before.json')){
  if(item.code==='LRB')continue;
  const hash=createHash('sha256').update(await readFile('web/public'+item.url)).digest('hex');
  expect(hash,item.code+' default interior').toBe(item.sha256);
 }
 const gallery=await read('web/public/gallery-manifest.json');
 expect(gallery.version).toBe('221');
 expect(gallery.images.every(image=>image.sourceModelSha256===after.sourceModelSha256)).toBe(true);
 expect(gallery.images.find(image=>image.name==='sal-public-entrance')).toBeTruthy();
 expect(gallery.images.find(image=>image.name==='sal-entrance-exterior')).toBeTruthy();
 expect(gallery.images.find(image=>image.name==='lrb-ramp-gallery-interior').sectionId).toBe('1');
 await mkdir(proof,{recursive:true});
 await writeFile(`${proof}/asset-scope.json`,JSON.stringify({changed,priorRoomsPreserved:rooms,galleryViews:gallery.images.length})+'\n');
});

for(const width of [1440,390])test(`public entries, library levels and retained rooms load at ${width}px`,async({page})=>{
 test.setTimeout(240000);await mkdir(proof,{recursive:true});
 await page.setViewportSize({width,height:width===390?844:1000});
 const errors=[];page.on('pageerror',error=>errors.push(error.message));
 await page.goto('/#SAL');
 await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-SAL',{timeout:90000});
 await expect(page.getByRole('button',{name:'玻璃入口亭与公共接待',exact:true})).toBeVisible();
 await page.getByRole('button',{name:'玻璃入口亭与公共接待',exact:true}).click();
 await expect(page.locator('#gallery-dialog')).toBeVisible();
 await page.screenshot({path:`${proof}/sal-entry-${width}.png`});
 await page.keyboard.press('Escape');
 await page.goto('/#LRB');
 await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-LRB',{timeout:90000});
 await page.locator('#interior-view').click();
 await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','interior-LRB',{timeout:60000});
 const floors=page.locator('#interior-level');
 await floors.selectOption('1');
 await expect(floors).toHaveValue('1');
 await page.waitForTimeout(700);
 await page.screenshot({path:`${proof}/lrb-level1-${width}.png`});
 await floors.selectOption('all');
 await expect(floors).toHaveValue('all');
 await page.goto('/#CLM');
 await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-CLM',{timeout:90000});
 await page.locator('#interior-view').click();
 await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','interior-CLM',{timeout:60000});
 await page.locator('#interior-space').selectOption('clm-hongkong');
 await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','interior-CLM:clm-hongkong',{timeout:60000});
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
 expect(errors).toEqual([]);
 await writeFile(`${proof}/ui-${width}.json`,JSON.stringify({width,errors,publicAndRetainedRoomNavigation:true})+'\n');
});
