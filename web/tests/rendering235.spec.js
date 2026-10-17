import {test,expect} from '@playwright/test';
import {readFile,mkdir} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {galleryRendererSignature,galleryModelSignature} from '../tools/gallery_signature.mjs';
const read=async path=>JSON.parse(await readFile(path,'utf8'));
const sha=bytes=>createHash('sha256').update(bytes).digest('hex');

test('presentation update preserves all accepted native and browser model bytes',async()=>{
 const baseline=await read('result/blender/stage235/baseline.json');
 expect(sha(await readFile(baseline.native.path))).toBe(baseline.native.sha256);
 for(const [path,digest] of Object.entries(baseline.models))expect(sha(await readFile(path)),path).toBe(digest);
 const before=await read('result/blender/stage235/release-before.json');
 const release=await read('dist/release.json');
 expect(release.version).toBe(before.version);
 expect(release.sourceModelSha256).toBe(before.sourceModelSha256);
 expect(release.modelAssetsSha256).toBe(before.modelAssetsSha256);
 expect(release.rendererSha256).not.toBe(before.rendererSha256);
 expect(release.rendererSha256).toBe(await galleryRendererSignature());
 expect(release.modelAssetsSha256).toBe(await galleryModelSignature('dist'));
 const gallery=await read('dist/gallery-manifest.json');expect(gallery.images).toHaveLength(193);
 expect(gallery.images.every(image=>image.rendererSha256===release.rendererSha256&&image.modelAssetsSha256===release.modelAssetsSha256)).toBe(true);
});

for(const width of [1440,390])test(`updated outdoor and room renderer works at ${width}px`,async({page})=>{
 test.setTimeout(120000);await mkdir('result/blender/stage235/browser',{recursive:true});
 await page.setViewportSize({width,height:width===390?844:1000});
 const errors=[];page.on('pageerror',error=>errors.push(error.message));
 await page.goto('/#CKK');
 await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-CKK',{timeout:60000});
 await page.locator('#interior-view').click();await page.locator('#interior-space').selectOption('ckk-110');
 await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','interior-CKK:ckk-110',{timeout:60000});
 await page.screenshot({path:`result/blender/stage235/browser/ckk110-${width}.png`});
 await page.getByRole('button',{name:'CKK.1.10U形教室',exact:true}).click();
 const gallery=await read('dist/gallery-manifest.json');
 const image=gallery.images.find(row=>row.name==='ckk-110-teaching-interior');
 await expect(page.locator('#gallery-image')).toHaveAttribute('src',new RegExp('/images/ckk-110-teaching-interior[.]webp[?]v=234-'+image.sha256.slice(0,12)));
 await page.getByRole('button',{name:'关闭图片',exact:true}).click();
 await page.goto('/');await expect(page.locator('#fallback')).toBeHidden();
 await expect(page.locator('canvas')).toBeVisible();
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
 expect(errors).toEqual([]);
});
