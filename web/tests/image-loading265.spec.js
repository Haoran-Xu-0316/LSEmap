import {test,expect} from '@playwright/test';
import {mkdir,readFile,writeFile} from 'node:fs/promises';
const catalogue=JSON.parse(await readFile('dist/models/catalogue.json'));
const releaseIdentity=JSON.parse(await readFile('dist/release.json'));
const folder='result/web/release'+catalogue.version+'/image-loading';

const campusImage=request=>new URL(request.url()).pathname==='/images/campus.webp';
async function record(name,data){await mkdir(folder,{recursive:true});await writeFile(`${folder}/${name}.json`,JSON.stringify(data,null,2)+'\n');}

test('hidden fallback and gallery images do not compete with the initial model transfer',async({page})=>{
 const images=[];page.on('request',request=>{if(campusImage(request))images.push(request.url());});
 let release;const gate=new Promise(resolve=>{release=resolve;});
 await page.route('**/models/campus-parts.json*',async route=>{await gate;await route.abort().catch(()=>{});});
 try{
  await page.goto('/');
  await expect(page.locator('html')).toHaveAttribute('data-model-revision',/[a-f0-9]{64}/);
  await expect(page.locator('#loading')).toBeVisible();
  await page.waitForTimeout(350);
  await record('initial-requests',{images});
  expect(images).toEqual([]);
  expect(await page.locator('#gallery-image').getAttribute('src')).toBeNull();
 }finally{await page.goto('about:blank');release();}
});

test('model failure loads one current fallback image and the building gallery remains usable',async({page})=>{
 const images=[];page.on('request',request=>{if(campusImage(request))images.push(request.url());});
 await page.route('**/models/campus-parts.json*',route=>route.fulfill({status:503,body:'Unavailable'}));
 await page.goto('/#OLD');await expect(page.locator('#fallback')).toBeVisible();
 await expect.poll(()=>page.locator('#fallback img').evaluate(img=>img.complete&&img.naturalWidth>0)).toBe(true);
 expect(images).toHaveLength(1);
 expect(new URL(images[0]).searchParams.get('v')).toBe(catalogue.version+'-'+releaseIdentity.assets['/images/campus.webp'].sha256.slice(0,12));
 await page.locator('.detail-photo').click();await expect(page.locator('#gallery-dialog')).toBeVisible();
 await expect.poll(()=>page.locator('#gallery-image').evaluate(img=>img.complete&&img.naturalWidth>0)).toBe(true);
 expect(await page.locator('#gallery-image').getAttribute('src')).toMatch(/old-exterior\.webp\?v=/);
 await record('fallback-and-gallery',{images,gallery:await page.locator('#gallery-image').getAttribute('src')});
});

test('an unavailable catalogue still has a usable unversioned fallback image',async({page})=>{
 await page.route('**/models/catalogue.json',route=>route.fulfill({status:503,body:'Unavailable'}));
 await page.goto('/');await expect(page.locator('#fallback')).toBeVisible();
 await expect.poll(()=>page.locator('#fallback img').evaluate(img=>img.complete&&img.naturalWidth>0)).toBe(true);
 expect(await page.locator('#fallback img').getAttribute('src')).toBe('/images/campus.webp');
 await record('catalogue-fallback',{src:await page.locator('#fallback img').getAttribute('src')});
});
