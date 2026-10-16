import {test,expect} from '@playwright/test';
import {readFile,mkdir,writeFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
const read=async path=>JSON.parse(await readFile(path,'utf8'));
const proof='result/blender/stage223/browser';

test('edition223 bounds public-structure changes and preserves all existing rooms',async()=>{
 const before=await read('result/blender/stage223/catalogue-before.json');
 const after=await read('web/public/models/catalogue.json');
 const native=await read('result/blender/stage223/building-refinement.json');
 expect(before.version).toBe('222');expect(after.version).toBe('223');
 expect(after.sourceModelSha256).toBe(native.sourceModelSha256);expect(after.buildings).toHaveLength(31);
 const allowed=new Set(['CBG:detailedExterior','CBG:detailedInterior','MAR:detailedExterior','MAR:detailedInterior','SAW:detailedExterior','SAW:detailedInterior']);
 const changed=[];let rooms=0;
 for(const old of before.buildings){
  const current=after.buildings.find(item=>item.code===old.code);
  for(const field of ['detailedExterior','detailedInterior']){
   if(!old[field])continue;
   const key=old.code+':'+field;
   if(current[field].sha256!==old[field].sha256){
    expect(allowed.has(key),key).toBe(true);changed.push(key);
   }
  }
  for(const room of old.interiorSpaces||[]){
   expect(current.interiorSpaces.find(item=>item.id===room.id).detailedInterior.sha256,room.id).toBe(room.detailedInterior.sha256);rooms++;
  }
 }
 expect(changed.sort()).toEqual(['CBG:detailedExterior','CBG:detailedInterior','MAR:detailedExterior','MAR:detailedInterior','SAW:detailedExterior','SAW:detailedInterior']);
 expect(rooms).toBe(21);
 for(const item of await read('result/blender/stage223/asset-hashes-before.json')){
  if(['CBG','MAR','SAW'].includes(item.code))continue;
  const hash=createHash('sha256').update(await readFile('web/public'+item.url)).digest('hex');
  expect(hash,item.code+' default interior').toBe(item.sha256);
 }
 expect(after.buildings.flatMap(b=>b.interiorSpaces||[])).toHaveLength(21);
 const gallery=await read('web/public/gallery-manifest.json');
 expect(gallery.version).toBe('223');
 expect(gallery.images.every(image=>image.sourceModelSha256===after.sourceModelSha256)).toBe(true);
 for(const name of ['61a-floor4-interior','61a-floor6-interior','61a-reception-interior','sal-g01-interior','sal-interior'])
  expect(gallery.images.find(image=>image.name===name),name).toBeTruthy();
 await mkdir(proof,{recursive:true});
 await writeFile(`${proof}/asset-scope.json`,JSON.stringify({changed,priorRoomsPreserved:rooms,galleryViews:gallery.images.length})+'\n');
});

for(const width of [1440,390])test(`public structure levels and preserved rooms load at ${width}px`,async({page})=>{
 test.setTimeout(240000);await mkdir(proof,{recursive:true});
 await page.setViewportSize({width,height:width===390?844:1000});
 const catalogue=await read('web/public/models/catalogue.json');
 const errors=[];page.on('pageerror',error=>errors.push(error.message));
 for(const code of ['CBG','MAR','SAW']){
  const building=catalogue.buildings.find(item=>item.code===code);
  await page.goto('/#'+code);
  await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-'+code,{timeout:90000});
  await page.locator('#interior-view').click();
  await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','interior-'+code,{timeout:60000});
  expect(building.interiorSections?.length,code+' public level controls').toBeGreaterThan(0);
  for(const section of [building.interiorSections[0],building.interiorSections.at(-1)]){
   await page.locator('#interior-level').selectOption(section.id);
   await expect(page.locator('canvas')).toHaveAttribute('data-interior-section',section.id);
  }
  await page.waitForTimeout(1000);
  await page.screenshot({path:`${proof}/${code}-public-${width}.png`});
  await page.locator('#interior-level').selectOption('all');
  await expect(page.locator('canvas')).toHaveAttribute('data-interior-section','all');
  const space=building.interiorSpaces?.[0];
  if(space){
   await page.locator('#interior-space').selectOption(space.id);
   await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','interior-'+code+':'+space.id,{timeout:60000});
  }
 }
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
 expect(errors).toEqual([]);
 await writeFile(`${proof}/ui-${width}.json`,JSON.stringify({width,errors,publicAndRetainedRoomNavigation:true})+'\n');
});
