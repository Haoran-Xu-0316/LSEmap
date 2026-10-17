import {test,expect} from '@playwright/test';
import {readFile,mkdir} from 'node:fs/promises';
import {galleryRendererSignature} from '../tools/gallery_signature.mjs';
const read=async path=>JSON.parse(await readFile(path,'utf8'));
const output='result/blender/stage236/browser';
test.use({reducedMotion:'reduce'});

test('236 shares the repaired entrance and preserves all existing room and other building assets',async()=>{
 const before=await read('result/blender/stage236/catalogue-before.json');
 const after=await read('dist/models/catalogue.json');
 const native=await read('result/blender/stage236/native-verification.json');
 const record=await read('result/blender/stage236/building-refinement.json');
 expect(before.version).toBe('234');expect(after.version).toBe('236');
 expect(after.sourceModelSha256).toBe(record.sourceModelSha256);
 expect(native.originalObjectsVerified).toBe(8582);expect(native.originalMaterialNodesVerified).toBe(2327);
 expect(native.sourceRoomsVerified).toBe(35);expect(native.sourceRoomObjectsVerified).toBe(1485);
 expect(record.addedObjects).toHaveLength(2);expect(record.archivedObjects).toHaveLength(2);
 let rooms=0,interiors=0,exteriors=0;
 for(const old of before.buildings){
  const current=after.buildings.find(row=>row.code===old.code);
  if(old.detailedExterior){exteriors++;if(old.code==='OLD')expect(current.detailedExterior.sha256).not.toBe(old.detailedExterior.sha256);else expect(current.detailedExterior.sha256,old.code).toBe(old.detailedExterior.sha256);}
  if(old.detailedInterior){interiors++;expect(current.detailedInterior.sha256,old.code).toBe(old.detailedInterior.sha256);}
  for(const room of old.interiorSpaces||[]){rooms++;expect(current.interiorSpaces.find(row=>row.id===room.id).detailedInterior.sha256,room.id).toBe(room.detailedInterior.sha256);}
 }
 expect([exteriors,interiors,rooms]).toEqual([30,25,35]);
 const gallery=await read('dist/gallery-manifest.json');expect(gallery.images).toHaveLength(194);
 expect(gallery.rendererSha256).toBe(await galleryRendererSignature());
 expect(gallery.images.every(row=>row.sourceModelSha256===after.sourceModelSha256&&row.rendererSha256===gallery.rendererSha256)).toBe(true);
});

for(const width of [1440,390])test(`236 entrance and retained room load at ${width}px`,async({page})=>{
 test.setTimeout(120000);await mkdir(output,{recursive:true});await page.setViewportSize({width,height:width===390?844:1000});
 const errors=[];page.on('pageerror',error=>errors.push(error.message));
 await page.goto('/#KGS');await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-KGS',{timeout:60000});
 await page.getByRole('button',{name:'King’s Chambers穹顶与铅皮拼缝',exact:true}).click();
 await expect(page.locator('#gallery-image')).toHaveAttribute('src',/\/images\/kgs-cupola[.]webp[?]v=236-[a-f0-9]{12}/);
 await page.waitForFunction(()=>{const image=document.querySelector('#gallery-image');return image?.complete&&image.naturalWidth>0;});
 await page.getByRole('button',{name:'关闭图片',exact:true}).click();
 await page.goto('/#OLD');await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-OLD',{timeout:60000});
 await page.screenshot({path:output+'/old-'+width+'.png'});
 await page.goto('/#CKK');await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-CKK',{timeout:60000});
 await page.locator('#interior-view').click();await page.locator('#interior-space').selectOption('ckk-110');
 await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','interior-CKK:ckk-110',{timeout:60000});
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);expect(errors).toEqual([]);
});
