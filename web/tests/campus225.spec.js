import {test,expect} from '@playwright/test';
import {readFile,mkdir,writeFile} from 'node:fs/promises';
const read=async path=>JSON.parse(await readFile(path,'utf8'));
const proof='result/blender/stage225/browser';

test('225 confines changes to Peacock exterior and the new KSW room',async()=>{
 const before=await read('result/blender/stage225/catalogue-before.json');
 const after=await read('web/public/models/catalogue.json');
 const native=await read('result/blender/stage225/building-refinement.json');
 expect(before.version).toBe('224');expect(after.version).toBe('225');
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
 expect(changed).toEqual(['PEA:detailedExterior']);expect(interiors).toBe(25);expect(rooms).toBe(21);
 const spaces=after.buildings.flatMap(building=>building.interiorSpaces||[]);expect(spaces).toHaveLength(22);
 const room=spaces.find(space=>space.id==='ksw-212');expect(room).toBeTruthy();expect(room.detailedInterior.sha256).toMatch(/^[a-f0-9]{64}$/);
 const gallery=await read('web/public/gallery-manifest.json');expect(gallery.version).toBe('225');
 expect(gallery.images.every(image=>image.sourceModelSha256===after.sourceModelSha256)).toBe(true);
 const views=gallery.images.filter(image=>image.spaceId==='ksw-212');expect(views).toHaveLength(2);expect(views.every(view=>view.mode==='interior'&&view.detail==='interior-KSW:ksw-212')).toBe(true);
 await mkdir(proof,{recursive:true});
 await writeFile(proof+'/asset-scope.json',JSON.stringify({changed,defaultInteriorsPreserved:interiors,priorRoomsPreserved:rooms,newRoom:room.id,totalRoomSpaces:spaces.length,galleryViews:gallery.images.length})+'\n');
});

for(const width of [1440,390])test(`Peacock frontage and KSW room load at ${width}px`,async({page})=>{
 test.setTimeout(150000);await mkdir(proof,{recursive:true});
 await page.setViewportSize({width,height:width===390?844:1000});
 const errors=[];page.on('pageerror',error=>errors.push(error.message));
 await page.goto('/#PEA');
 await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-PEA',{timeout:90000});
 await page.getByRole('button',{name:'Peacock三组双扇入口',exact:true}).click();
 await expect(page.locator('#gallery-image')).toHaveAttribute('src',/pea-paired-entrance/);
 await page.getByRole('button',{name:'关闭图片',exact:true}).click();
 await page.goto('/#KSW');
 await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-KSW',{timeout:60000});
 await page.locator('#interior-view').click();
 await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','interior-KSW',{timeout:60000});
 await page.locator('#interior-space').selectOption('ksw-212');
 await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','interior-KSW:ksw-212',{timeout:60000});
 await page.screenshot({path:`${proof}/ksw212-${width}.png`});
 await page.getByRole('button',{name:'KSW.2.12双屏教学墙',exact:true}).click();
 await expect(page.locator('#gallery-image')).toHaveAttribute('src',/ksw-212-teaching-wall-interior/);
 await page.getByRole('button',{name:'关闭图片',exact:true}).click();
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);expect(errors).toEqual([]);
});
