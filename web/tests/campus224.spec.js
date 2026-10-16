import {test,expect} from '@playwright/test';
import {readFile,mkdir,writeFile} from 'node:fs/promises';
const read=async path=>JSON.parse(await readFile(path,'utf8'));
const proof='result/blender/stage224/browser';

test('RCS context refinement preserves all LSE exterior and interior assets',async()=>{
 const before=await read('result/blender/stage224/catalogue-before.json');
 const after=await read('web/public/models/catalogue.json');
 const native=await read('result/blender/stage224/building-refinement.json');
 expect(before.version).toBe('223');expect(after.version).toBe('224');
 expect(after.sourceModelSha256).toBe(native.sourceModelSha256);
 expect(after.buildings).toHaveLength(31);
 let exteriors=0,interiors=0,rooms=0;
 for(const old of before.buildings){
  const current=after.buildings.find(item=>item.code===old.code);
  for(const field of ['detailedExterior','detailedInterior']){
   if(!old[field])continue;
   expect(current[field].sha256,old.code+':'+field).toBe(old[field].sha256);
   if(field==='detailedExterior')exteriors++;else interiors++;
  }
  for(const room of old.interiorSpaces||[]){
   expect(current.interiorSpaces.find(item=>item.id===room.id).detailedInterior.sha256,room.id).toBe(room.detailedInterior.sha256);rooms++;
  }
 }
 expect(exteriors).toBe(30);expect(interiors).toBe(25);expect(rooms).toBe(21);
 const gallery=await read('web/public/gallery-manifest.json');
 expect(gallery.version).toBe('224');
 expect(gallery.images.every(image=>image.sourceModelSha256===after.sourceModelSha256)).toBe(true);
 const rcs=gallery.images.filter(image=>image.name.includes('rcs-'));
 expect(rcs.length).toBeGreaterThan(0);
 expect(rcs.every(image=>image.code==='CAMPUS'&&image.mode==='campus')).toBe(true);
 await mkdir(proof,{recursive:true});
 await writeFile(proof+'/asset-scope.json',JSON.stringify({exteriorsPreserved:exteriors,defaultInteriorsPreserved:interiors,priorRoomsPreserved:rooms,rcsViews:rcs.map(image=>image.name)})+'\n');
});

for(const width of [1440,390])test(`RCS neighbor gallery and MAR navigation work at ${width}px`,async({page})=>{
 test.setTimeout(150000);await mkdir(proof,{recursive:true});
 await page.setViewportSize({width,height:width===390?844:1000});
 const errors=[];page.on('pageerror',error=>errors.push(error.message));
 await page.goto('/#MAR');
 await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-MAR',{timeout:90000});
 const image=page.getByRole('button',{name:'周边RCS入口柱廊',exact:true});
 await expect(image).toBeVisible();await image.click();
 await expect(page.locator('#gallery-dialog')).toBeVisible();
 await expect(page.locator('#gallery-image')).toHaveAttribute('src',/rcs-/);
 await page.screenshot({path:`${proof}/rcs-gallery-${width}.png`});
 await page.getByRole('button',{name:'关闭图片',exact:true}).click();
 await page.locator('#interior-view').click();
 await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','interior-MAR',{timeout:60000});
 await page.locator('#interior-level').selectOption('2');
 await expect(page.locator('canvas')).toHaveAttribute('data-interior-section','2');
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
 expect(errors).toEqual([]);
});
