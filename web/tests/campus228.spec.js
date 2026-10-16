import {test,expect} from '@playwright/test';
import {readFile,mkdir,writeFile} from 'node:fs/promises';
const read=async path=>JSON.parse(await readFile(path,'utf8'));
const proof='result/blender/stage228/browser';
const newRooms=[{code:'CLM',id:'clm-g03',report:'clmg03-room228'},{code:'MAR',id:'mar-108',report:'mar108-room228'}];

test('228 adds two independent classrooms while preserving all prior model assets',async()=>{
 const before=await read('result/blender/stage228/catalogue-before.json');
 const after=await read('web/public/models/catalogue.json');
 const native=await read('result/blender/stage228/building-refinement.json');
 expect(before.version).toBe('227');expect(after.version).toBe('228');
 expect(after.sourceModelSha256).toBe(native.sourceModelSha256);expect(after.buildings).toHaveLength(31);
 const changed=[];let rooms=0,interiors=0,exteriors=0;
 for(const old of before.buildings){
  const current=after.buildings.find(item=>item.code===old.code);
  for(const field of ['detailedExterior','detailedInterior']){
   if(!old[field])continue;
   if(current[field].sha256!==old[field].sha256)changed.push(old.code+':'+field);
   if(field==='detailedInterior')interiors++;else exteriors++;
  }
  for(const room of old.interiorSpaces||[]){
   expect(current.interiorSpaces.find(item=>item.id===room.id).detailedInterior.sha256,room.id).toBe(room.detailedInterior.sha256);rooms++;
  }
 }
 expect(changed).toEqual([]);expect(interiors).toBe(25);expect(exteriors).toBe(30);expect(rooms).toBe(25);
 const spaces=after.buildings.flatMap(building=>building.interiorSpaces||[]);expect(spaces).toHaveLength(27);
 const gallery=await read('web/public/gallery-manifest.json');expect(gallery.version).toBe('228');
 expect(gallery.images.every(image=>image.sourceModelSha256===after.sourceModelSha256)).toBe(true);
 for(const room of newRooms){
  expect(spaces.find(space=>space.id===room.id).detailedInterior.sha256).toMatch(/^[a-f0-9]{64}$/);
  const views=gallery.images.filter(image=>image.spaceId===room.id);expect(views).toHaveLength(2);
  expect(views.every(view=>view.mode==='interior'&&view.detail==='interior-'+room.code+':'+room.id)).toBe(true);
 }
 await mkdir(proof,{recursive:true});
 await writeFile(proof+'/asset-scope.json',JSON.stringify({changed,defaultInteriorsPreserved:interiors,detailedExteriorsPreserved:exteriors,priorRoomsPreserved:rooms,totalRoomSpaces:spaces.length,newRooms:newRooms.map(room=>room.id),galleryViews:gallery.images.length})+'\n');
});

for(const width of [1440,390])test(`both classrooms and their galleries load at ${width}px`,async({page})=>{
 test.setTimeout(150000);await mkdir(proof,{recursive:true});
 await page.setViewportSize({width,height:width===390?844:1000});
 const errors=[];page.on('pageerror',error=>errors.push(error.message));
 for(const room of newRooms){
  await page.goto('/#'+room.code);
  await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-'+room.code,{timeout:60000});
  await page.locator('#interior-view').click();
  await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','interior-'+room.code,{timeout:60000});
  await page.locator('#interior-space').selectOption(room.id);
  await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','interior-'+room.code+':'+room.id,{timeout:60000});
  await page.screenshot({path:`${proof}/${room.id}-${width}.png`});
  const audit=await read('result/blender/'+room.report+'/audit.json');const view=audit.gallerySuggestions[1];
  await page.getByRole('button',{name:view.label,exact:true}).click();
  await expect(page.locator('#gallery-image')).toHaveAttribute('src',new RegExp('/images/'+view.name+'[.]webp[?]v=228-'));
  await page.getByRole('button',{name:'关闭图片',exact:true}).click();
 }
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);expect(errors).toEqual([]);
});
