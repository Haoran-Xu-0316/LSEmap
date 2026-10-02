import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';

test('MAR view refinement retains every model and all other catalogue fields',async()=>{
 const before=JSON.parse(await readFile('result/blender/stage105/catalogue-before.json'));
 const after=JSON.parse(await readFile('dist/models/catalogue.json'));
 const audit=JSON.parse(await readFile('result/blender/stage105/mar-front-view-audit.json'));
 expect(after.version).toBe('105');
 expect(after.sourceModelSha256).toBe(audit.nativeSourceUnchanged);
 expect(Object.keys(audit.modelHashes)).toHaveLength(86);
 for(const [url,hash]of Object.entries(audit.modelHashes))expect(createHash('sha256').update(await readFile('dist'+url)).digest('hex'),url).toBe(hash);
 const mar=after.buildings.find(b=>b.code==='MAR');
 expect(mar.exteriorDirection).toEqual(audit.direction);
 expect(mar.exteriorDirection[1]).toBeLessThan(.03);
 mar.exteriorDirection=before.buildings.find(b=>b.code==='MAR').exteriorDirection;
 after.version=before.version;
 expect(after).toEqual(before);
});

test('MAR gallery presents the facade from a lower viewpoint',async()=>{
 const gallery=JSON.parse(await readFile('dist/gallery-manifest.json'));
 const mar=gallery.images.find(i=>i.name==='mar-exterior');
 expect(mar.view.position[1]).toBeGreaterThan(15);
 expect(mar.view.position[1]).toBeLessThan(30);
 expect(mar.view.target[1]).toBeCloseTo(21.4,4);
 expect(mar.detail).toBe('exterior-MAR');
});

test('mobile MAR facade opens with the aligned gallery',async({page})=>{
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.setViewportSize({width:390,height:844});
 await page.goto('/#MAR');
 await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-MAR',{timeout:60000});
 await expect(page.locator('#fallback')).toBeHidden();
 await page.locator('.detail-gallery img[src*="mar-exterior"]').click();
 await expect(page.locator('#gallery-image')).toBeVisible();
 expect(await page.locator('#gallery-image').evaluate(i=>i.complete&&i.naturalWidth>0)).toBeTruthy();
 expect(errors).toEqual([]);
});
