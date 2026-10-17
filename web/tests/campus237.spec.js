import {test,expect} from '@playwright/test';
import {readFile,mkdir} from 'node:fs/promises';
import {galleryRendererSignature} from '../tools/gallery_signature.mjs';
const read=async p=>JSON.parse(await readFile(p,'utf8'));
const output='result/blender/stage237/browser';
test('237 shares the reviewed campus and keeps every existing interior',async()=>{
 const before=await read('result/blender/stage237/catalogue-before.json'),after=await read('dist/models/catalogue.json');
 const native=await read('result/blender/stage237/native-verification.json');
 expect(after.version).toBe('237');expect(native.originalObjectsVerified).toBe(8584);expect(native.originalMaterialNodesVerified).toBe(2327);expect(native.originalMeshNormalsVerified).toBeGreaterThan(7000);
 expect([native.sourceRoomsVerified,native.sourceRoomObjectsVerified]).toEqual([35,1485]);
 let rooms=0,interiors=0;
 for(const old of before.buildings){const current=after.buildings.find(b=>b.code===old.code);
  if(old.detailedExterior){if(['OLD','SAW','KGS'].includes(old.code))expect(current.detailedExterior.sha256).not.toBe(old.detailedExterior.sha256);else expect(current.detailedExterior.sha256,old.code).toBe(old.detailedExterior.sha256);}
  if(old.detailedInterior){interiors++;expect(current.detailedInterior.sha256,old.code).toBe(old.detailedInterior.sha256);}
  for(const room of old.interiorSpaces||[]){rooms++;expect(current.interiorSpaces.find(r=>r.id===room.id).detailedInterior.sha256,room.id).toBe(room.detailedInterior.sha256);}
 }
 expect([rooms,interiors]).toEqual([35,25]);
 const old=after.buildings.find(b=>b.code==='OLD').detailedExterior,saw=after.buildings.find(b=>b.code==='SAW').detailedExterior;
 expect(old.triangles).toBe(872344);expect(old.bytes).toBeLessThan(12e6);expect(saw.triangles).toBeLessThan(800000);expect(saw.bytes).toBeLessThan(9e6);
 const gallery=await read('dist/gallery-manifest.json');expect(gallery.images).toHaveLength(194);expect(gallery.rendererSha256).toBe(await galleryRendererSignature());expect(gallery.images.every(r=>r.sourceModelSha256===after.sourceModelSha256)).toBe(true);
});
for(const width of [1440,890,701,390])test(`237 map controls stay clear at ${width}px`,async({page})=>{
 test.setTimeout(120000);await mkdir(output,{recursive:true});await page.setViewportSize({width,height:width===390?844:1000});const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('/');await expect(page.locator('canvas')).toHaveAttribute('data-ready','true',{timeout:60000});
 const stage=await page.locator('#stage').boundingBox(),canvas=await page.locator('canvas').boundingBox();
 if(width>700){expect(stage.x).toBe(0);expect(stage.y).toBe(0);expect(stage.width).toBe(width);const sidebar=await page.locator('#sidebar').boundingBox(),toolbar=await page.locator('.map-toolbar').boundingBox();expect(toolbar.x).toBeGreaterThan(sidebar.x+sidebar.width);expect(toolbar.x+toolbar.width).toBeLessThanOrEqual(width);await page.locator('#index-toggle').click();expect((await page.locator('canvas').boundingBox()).width).toBe(canvas.width);await page.locator('#index-toggle').click();}
 await page.goto('/#SAW');await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-SAW',{timeout:60000});
 if(width===1440){const bearing=await page.locator('#north svg').getAttribute('style');await page.mouse.move(1100,500);await page.mouse.down();await page.mouse.move(1240,540,{steps:12});await page.mouse.up();await expect.poll(()=>page.locator('#north svg').getAttribute('style')).not.toBe(bearing);}
 await page.locator('#zoom-in').click();await page.locator('#zoom-out').click();await page.locator('#north').click();
 await expect(page.locator('#fallback')).toBeHidden();expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);await page.screenshot({path:output+'/ui-'+width+'.png'});
 if(width===1440){await page.goto('/#KGS');await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-KGS',{timeout:60000});await page.goto('/#CKK');await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-CKK',{timeout:60000});await page.locator('#interior-view').click();await page.locator('#interior-space').selectOption('ckk-110');await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','interior-CKK:ckk-110',{timeout:60000});}
 expect(errors).toEqual([]);
});
test('reduced motion keeps the map usable',async({page})=>{await page.emulateMedia({reducedMotion:'reduce'});await page.goto('/#OLD');await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-OLD',{timeout:60000});expect(await page.locator('#detail-panel').evaluate(e=>getComputedStyle(e).animationName)).toBe('none');});
