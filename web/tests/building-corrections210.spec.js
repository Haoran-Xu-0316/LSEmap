import {test,expect} from '@playwright/test';
import {readFile,mkdir,writeFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
const read=async path=>JSON.parse(await readFile(path,'utf8'));

test('edition210 preserves previous rooms and unrelated exteriors',async()=>{
 const before=await read('result/blender/stage210/catalogue-before.json'),current=await read('web/public/models/catalogue.json'),saved=await read('result/blender/stage210/reopened-verification.json'),native=await read('result/blender/stage210/room-and-roof-verification.json');
 expect(current.version).toBe('210');expect(saved.originalsVerified).toBe(7373);expect(saved.addedObjectsVerified).toBe(39);expect(saved.completeModelReopened).toBe(true);
 expect(createHash('sha256').update(await readFile('result/blender/LSE_campus_detailed_v210.blend')).digest('hex')).toBe(current.sourceModelSha256);
 let previousRooms=0;
 for(const b of current.buildings){const old=before.buildings.find(x=>x.code===b.code);
  for(const space of old.interiorSpaces??[]){expect(b.interiorSpaces.find(s=>s.id===space.id)).toEqual(space);previousRooms++;}
  if(b.code==='LRB')expect(b.detailedExterior.sha256).not.toBe(old.detailedExterior.sha256);
  else expect(b.detailedExterior??null,b.code+' exterior').toEqual(old.detailedExterior??null);
  if(b.code!=='LRB')expect(b.detailedInterior??null,b.code+' default interior').toEqual(old.detailedInterior??null);
 }
 expect(previousRooms).toBe(17);expect(current.buildings.reduce((n,b)=>n+(b.interiorSpaces?.length??0),0)).toBe(18);
 const room=current.buildings.find(b=>b.code==='CON').interiorSpaces.find(s=>s.id==='con-705');expect(room.label).toBe('CON.7.05会议室');expect(room.scope).toContain('不代表2026年现状');expect(room.detailedInterior.bytes).toBeLessThan(500000);
 expect(native.newRoomOnlyInItsOwnScene).toBe(true);expect(native.actualSeatCount).toBe(18);expect(native.floorSupportRays).toBe(18);expect(native.doorWallAperturesVerified).toBe(4);expect(native.originalMaterialsVerified).toBe(1901);
 const roof=await read('result/blender/lrb-exterior210/audit.json');expect(roof.supportChecks.supported).toBe(558);expect(roof.roofReview.preservedOtherRoofEdges).toBe(true);expect(roof.roofReview.retainedLightwell).toBe(true);
 const gallery=await read('web/public/gallery-manifest.json');expect(gallery.images).toHaveLength(135);expect(gallery.images.find(i=>i.name==='con-705-interior').spaceId).toBe('con-705');
});

test('library roof and independent CON committee room work on desktop and mobile',async({page})=>{
 test.setTimeout(150000);const out='result/blender/stage210/browser',errors=[];await mkdir(out,{recursive:true});page.on('pageerror',e=>errors.push(e.message));
 for(const width of [1440,390]){
  await page.setViewportSize({width,height:1000});await page.goto('/#LRB');await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-LRB',{timeout:65000});await page.waitForTimeout(1000);await page.screenshot({path:out+'/lrb-'+width+'.png'});await expect(page.locator('#fallback')).toBeHidden();
  await page.goto('/#CON');await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-CON',{timeout:65000});await page.locator('#interior-view').click();await page.locator('#interior-space').selectOption('con-705');await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','interior-CON:con-705',{timeout:65000});await expect(page.locator('#interior-space')).toHaveValue('con-705');await page.waitForTimeout(1000);await page.screenshot({path:out+'/con-705-'+width+'.png'});
  await page.getByRole('button',{name:'CON.7.05会议室',exact:true}).click();await expect(page.locator('#gallery-image')).toHaveAttribute('src',/con-705-interior/);await page.waitForFunction(()=>{const i=document.querySelector('#gallery-image');return i?.complete&&i.naturalWidth>0;});await page.screenshot({path:out+'/con-705-gallery-'+width+'.png'});await page.getByRole('button',{name:'关闭图片',exact:true}).click();
  await page.locator('#interior-space').selectOption('default');await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','interior-CON',{timeout:65000});await page.locator('#exterior-view').click();await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-CON');await page.locator('#overview').click();await page.waitForTimeout(1100);await expect(page.locator('#fallback')).toBeHidden();
 }
 expect(errors).toEqual([]);await writeFile(out+'/acceptance.json',JSON.stringify({widths:[1440,390],libraryExterior:true,con705:true,roomGallery:true,defaultInteriorReturn:true,overview:true,errors},null,2)+'\n');
});
