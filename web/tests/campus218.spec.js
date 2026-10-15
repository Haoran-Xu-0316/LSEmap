import {test,expect} from '@playwright/test';
import {readFile,mkdir,writeFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
const read=async path=>JSON.parse(await readFile(path,'utf8'));
const proof='result/blender/stage218/browser';

test('edition218 changes reviewed OLD exterior and preserves other buildings and every room',async()=>{
 const before=await read('result/blender/stage218/catalogue-before.json');
 const after=await read('web/public/models/catalogue.json');
 const native=await read('result/blender/stage218/building-refinement.json');
 expect(after.version).toBe('218');expect(after.sourceModelSha256).toBe(native.sourceModelSha256);
 expect(after.buildings).toHaveLength(31);
 const changed=[];let roomCount=0;
 for(const old of before.buildings){
  const current=after.buildings.find(item=>item.code===old.code);
  for(const field of ['detailedExterior','detailedInterior']){
   if(!old[field])continue;
   if(current[field].sha256!==old[field].sha256)changed.push(old.code+':'+field);
   if(old.code!=='OLD')expect(current[field].sha256,old.code+field).toBe(old[field].sha256);
  }
  for(const room of old.interiorSpaces||[]){
   expect(current.interiorSpaces.find(item=>item.id===room.id).detailedInterior.sha256,room.id).toBe(room.detailedInterior.sha256);roomCount++;
  }
 }
 expect(changed).toContain('OLD:detailedExterior');expect(roomCount).toBe(18);
 const old=after.buildings.find(item=>item.code==='OLD');
 const prior=before.buildings.find(item=>item.code==='OLD');
 expect(old.detailedExterior.triangles).toBeLessThan(prior.detailedExterior.triangles-400000);
 const fallbacks=await read('result/blender/stage218/asset-hashes-before.json');
 expect(fallbacks).toHaveLength(25);
 for(const item of fallbacks){
  const hash=createHash('sha256').update(await readFile('web/public'+item.url)).digest('hex');
  if(item.code!=='OLD')expect(hash,item.code+' fallback').toBe(item.sha256);
 }
 const gallery=await read('web/public/gallery-manifest.json');
 expect(gallery.version).toBe('218');expect(gallery.images).toHaveLength(136);
 expect(gallery.images.every(image=>image.sourceModelSha256===after.sourceModelSha256)).toBe(true);
 await mkdir(proof,{recursive:true});
 await writeFile(`${proof}/asset-scope.json`,JSON.stringify({changed,independentRoomsPreserved:roomCount})+'\n');
});

for(const width of [1440,390])test(`OLD exterior and retained public corridor load at ${width}px`,async({page})=>{
 test.setTimeout(150000);await mkdir(proof,{recursive:true});
 await page.setViewportSize({width,height:width===390?844:1000});
 const errors=[];page.on('pageerror',error=>errors.push(error.message));
 await page.goto('/#OLD');
 await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-OLD',{timeout:90000});
 await page.waitForTimeout(1000);await page.screenshot({path:`${proof}/old-exterior-${width}.png`});
 await page.locator('#interior-view').click();
 await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','interior-OLD',{timeout:60000});
 await page.waitForTimeout(1000);await page.screenshot({path:`${proof}/old-public-${width}.png`});
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
 await page.locator('#overview').click();await expect(page.locator('#fallback')).toBeHidden();
 await page.waitForTimeout(1000);await page.screenshot({path:`${proof}/campus-${width}.png`});
 expect(errors).toEqual([]);
 await writeFile(`${proof}/ui-${width}.json`,JSON.stringify({width,errors,oldExteriorAndPublicNavigation:true})+'\n');
});
