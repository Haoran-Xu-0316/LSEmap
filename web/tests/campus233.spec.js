import {test,expect} from '@playwright/test';
import {readFile,mkdir,writeFile} from 'node:fs/promises';
const read=async path=>JSON.parse(await readFile(path,'utf8'));
const output='result/blender/stage233/browser';
const model=async url=>{const bytes=await readFile('dist'+url);return JSON.parse(bytes.subarray(20,20+bytes.readUInt32LE(12)));};
test.use({reducedMotion:'reduce'});

test('233 preserves earlier rooms and publishes the approved exterior and circulation changes',async()=>{
 const before=await read('result/blender/stage233/catalogue-before.json');
 const after=await read('dist/models/catalogue.json');
 const native=await read('result/blender/stage233/building-refinement.json');
 const plan=await read('result/blender/stage233/release-plan.json');
 expect(before.version).toBe('232');expect(after.version).toBe('233');
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
 expect(after.buildings.flatMap(row=>row.interiorSpaces||[])).toHaveLength(34);
 const gallery=await read('dist/gallery-manifest.json');expect(gallery.version).toBe('233');
 expect(gallery.images).toHaveLength(plan.expectedGalleryImages);
 expect(gallery.images.every(row=>row.sourceModelSha256===after.sourceModelSha256)).toBe(true);
 // Check actual exported optical identity, not only a source report.
 const library=after.buildings.find(row=>row.code==='LRB');
 const doc=await model(library.detailedExterior.url);
 const glass=doc.materials.filter(row=>row.name.includes('LRB233_'));
 expect(glass).toHaveLength(4);
 expect(glass.filter(row=>row.name.includes('entry_dielectric'))).toHaveLength(1);
 for(const material of glass){
  expect(material.alphaMode).toBe('BLEND');expect(material.extras.webSurfaceRole).toBe('glazing');
  expect(material.pbrMetallicRoughness.metallicFactor).toBe(0);
  expect(material.pbrMetallicRoughness.baseColorFactor[3]).toBeCloseTo(material.name.includes('entry_dielectric')?.30:.76,5);
 }
 const stair=await read('result/blender/saw-circulation233/saved-route-triangle-proof.json');
 expect(stair.savedActualMeshVerified).toBe(true);expect(stair.conflictCount).toBe(0);
 expect(stair.remainingLiftConflictCount).toBe(plan.remainingSawLowerLiftConflicts);
 await mkdir(output,{recursive:true});
 await writeFile(output+'/asset-scope.json',JSON.stringify({changed,priorRoomsPreserved:priorRooms,totalRoomSpaces:34,defaultInteriorsPreserved:interiors-changed.filter(row=>row.endsWith(':detailedInterior')).length,detailedExteriorsPreserved:exteriors-changed.filter(row=>row.endsWith(':detailedExterior')).length,detailedExteriorsTotal:exteriors,galleryViews:gallery.images.length})+'\n');
});

for(const width of [1440,390])test(`233 library park and public stairs load at ${width}px`,async({page})=>{
 test.setTimeout(150000);await mkdir(output,{recursive:true});
 await page.setViewportSize({width,height:width===390?844:1000});
 const errors=[];page.on('pageerror',error=>errors.push(error.message));
 const openGallery=async(name,image)=>{
  await page.getByRole('button',{name,exact:true}).click();
  await expect(page.locator('#gallery-image')).toHaveAttribute('src',new RegExp('/images/'+image+'[.]webp[?]v=233-'));
  await page.getByRole('button',{name:'关闭图片',exact:true}).click();
 };
 await page.goto('/#LRB');await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-LRB',{timeout:60000});
 await openGallery('Watkins广场入口与台阶','lrb-watkins-entrance');
 await page.goto('/#OLD');await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-OLD',{timeout:60000});
 await openGallery('Houghton Street檐口与阁楼窗','old-entablature');
 await page.goto('/#MAR');await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-MAR',{timeout:60000});
 await openGallery('Lincoln’s Inn Fields公共建筑','LIF-park-public');
 await openGallery('公园八角亭','LIF-bandstand');
 await page.goto('/#SAW');await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-SAW',{timeout:60000});
 await page.locator('#interior-view').click();await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','interior-SAW',{timeout:60000});
 const plan=await read('result/blender/stage233/release-plan.json');
 for(const section of plan.expectedSectionViews){
  await page.locator('#interior-level').selectOption(section.id);
  await expect(page.locator('canvas')).toHaveAttribute('data-interior-section',section.id);
  await page.screenshot({path:output+'/'+section.id+'-'+width+'.png'});
  await openGallery(section.label,section.gallery);
 }
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
 expect(errors).toEqual([]);
});
