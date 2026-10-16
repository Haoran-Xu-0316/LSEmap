import {test,expect} from '@playwright/test';
import {readFile,mkdir,writeFile} from 'node:fs/promises';
const read=async path=>JSON.parse(await readFile(path,'utf8'));
const proof='result/blender/stage226/browser';

test('226 adds PAN.2.01 while preserving every existing exterior and interior',async()=>{
 const before=await read('result/blender/stage226/catalogue-before.json');
 const after=await read('web/public/models/catalogue.json');
 const native=await read('result/blender/stage226/building-refinement.json');
 expect(before.version).toBe('225');expect(after.version).toBe('226');
 expect(after.sourceModelSha256).toBe(native.sourceModelSha256);expect(after.buildings).toHaveLength(31);
 const changed=[];let rooms=0,interiors=0;
 for(const old of before.buildings){
  const current=after.buildings.find(item=>item.code===old.code);
  for(const field of ['detailedExterior','detailedInterior']){
   if(!old[field])continue;
   if(current[field].sha256!==old[field].sha256)changed.push(old.code+':'+field);
   if(field==='detailedInterior')interiors++;
  }
  for(const room of old.interiorSpaces||[]){
   expect(current.interiorSpaces.find(item=>item.id===room.id).detailedInterior.sha256,room.id).toBe(room.detailedInterior.sha256);rooms++;
  }
 }
 expect(changed).toEqual([]);expect(interiors).toBe(25);expect(rooms).toBe(22);
 const spaces=after.buildings.flatMap(building=>building.interiorSpaces||[]);expect(spaces).toHaveLength(23);
 const room=spaces.find(space=>space.id==='pan-201');expect(room).toBeTruthy();expect(room.detailedInterior.sha256).toMatch(/^[a-f0-9]{64}$/);
 const gallery=await read('web/public/gallery-manifest.json');expect(gallery.version).toBe('226');
 expect(gallery.images.every(image=>image.sourceModelSha256===after.sourceModelSha256)).toBe(true);
 const views=gallery.images.filter(image=>image.spaceId==='pan-201');expect(views).toHaveLength(2);expect(views.every(view=>view.mode==='interior'&&view.detail==='interior-PAN:pan-201')).toBe(true);
 await mkdir(proof,{recursive:true});
 await writeFile(proof+'/asset-scope.json',JSON.stringify({changed,defaultInteriorsPreserved:interiors,priorRoomsPreserved:rooms,newRoom:room.id,totalRoomSpaces:spaces.length,galleryViews:gallery.images.length})+'\n');
});

for(const width of [1440,390])test(`Campus exterior and PAN room load at ${width}px`,async({page})=>{
 test.setTimeout(150000);await mkdir(proof,{recursive:true});
 await page.setViewportSize({width,height:width===390?844:1000});
 const errors=[];page.on('pageerror',error=>errors.push(error.message));
 await page.goto('/#PAN');
 await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-PAN',{timeout:60000});
 await page.locator('#interior-view').click();
 await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','interior-PAN',{timeout:60000});
 await page.locator('#interior-space').selectOption('pan-201');
 await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','interior-PAN:pan-201',{timeout:60000});
 await page.screenshot({path:`${proof}/pan201-${width}.png`});
 await page.getByRole('button',{name:'PAN.2.01教学墙与协作座位',exact:true}).click();
 await expect(page.locator('#gallery-image')).toHaveAttribute('src',/pan-201-teaching-wall-interior/);
 await page.getByRole('button',{name:'关闭图片',exact:true}).click();
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);expect(errors).toEqual([]);
});
