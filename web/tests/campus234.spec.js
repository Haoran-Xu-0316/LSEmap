import {test,expect} from '@playwright/test';
import {readFile,mkdir,writeFile} from 'node:fs/promises';
const read=async path=>JSON.parse(await readFile(path,'utf8'));
const output='result/blender/stage234/browser';
test.use({reducedMotion:'reduce'});

test('234 preserves geographic buildings and earlier rooms while publishing the sourced room',async()=>{
 const before=await read('result/blender/stage234/catalogue-before.json');
 const after=await read('dist/models/catalogue.json');
 const native=await read('result/blender/stage234/building-refinement.json');
 const plan=await read('result/blender/stage234/release-plan.json');
 expect(before.version).toBe('233');expect(after.version).toBe('234');
 expect(after.sourceModelSha256).toBe(native.sourceModelSha256);expect(after.buildings).toHaveLength(31);
 const changed=[];let priorRooms=0,interiors=0,exteriors=0;
 for(const old of before.buildings){
  const current=after.buildings.find(row=>row.code===old.code);
  for(const field of ['detailedExterior','detailedInterior'])if(old[field]){
   if(current[field].sha256!==old[field].sha256)changed.push(old.code+':'+field);
   if(field==='detailedInterior')interiors++;else exteriors++;
  }
  for(const room of old.interiorSpaces||[]){
   expect(current.interiorSpaces.find(row=>row.id===room.id)?.detailedInterior.sha256,room.id).toBe(room.detailedInterior.sha256);priorRooms++;
  }
 }
 expect(changed.sort()).toEqual(plan.expectedChangedBuildingAssets);
 expect(interiors).toBe(25);expect(exteriors).toBe(30);expect(priorRooms).toBe(34);
 expect(after.buildings.flatMap(row=>row.interiorSpaces||[])).toHaveLength(35);
 const gallery=await read('dist/gallery-manifest.json');expect(gallery.version).toBe('234');
 expect(gallery.images).toHaveLength(plan.expectedGalleryImages);
 expect(gallery.images.every(row=>row.sourceModelSha256===after.sourceModelSha256)).toBe(true);
 const room=after.buildings.find(row=>row.code==='CKK').interiorSpaces.find(row=>row.id==='ckk-110');
 expect(room.interiorView.position.every((v,i)=>v>=room.interiorBounds.min[i]&&v<=room.interiorBounds.max[i])).toBe(true);
 const road=await read('result/blender/street-ground234/audit.json');
 expect(road.archivedObjects).toHaveLength(1);expect(road.addedObjects).toHaveLength(1);
 await mkdir(output,{recursive:true});
 await writeFile(output+'/asset-scope.json',JSON.stringify({changed,priorRoomsPreserved:priorRooms,totalRoomSpaces:35,defaultInteriorsPreserved:interiors,detailedExteriorsPreserved:exteriors,galleryViews:gallery.images.length})+'\n');
});

for(const width of [1440,390])test(`234 sourced classroom loads at ${width}px`,async({page})=>{
 test.setTimeout(120000);await mkdir(output,{recursive:true});
 await page.setViewportSize({width,height:width===390?844:1000});
 const errors=[];page.on('pageerror',error=>errors.push(error.message));
 await page.goto('/#CKK');await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-CKK',{timeout:60000});
 await page.locator('#interior-view').click();await page.locator('#interior-space').selectOption('ckk-110');
 await expect(page.locator('canvas')).toHaveAttribute('data-interior-space','ckk-110');
 await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','interior-CKK:ckk-110',{timeout:60000});
 await page.screenshot({path:output+'/ckk110-'+width+'.png'});
 const plan=await read('result/blender/stage234/release-plan.json');
 const visibleCaptions=['CKK.1.10U形教室','CKK.1.10来源椅位、两窗湾与完整天花'];
 for(const [index,job] of plan.newRoomGalleryViews.entries()){
  await page.getByRole('button',{name:visibleCaptions[index],exact:true}).click();
  await expect(page.locator('#gallery-image')).toHaveAttribute('src',new RegExp('/images/'+job.name+'[.]webp[?]v=234-'));
  await page.getByRole('button',{name:'关闭图片',exact:true}).click();
 }
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
 expect(errors).toEqual([]);
});
