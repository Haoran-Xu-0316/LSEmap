import {test,expect} from '@playwright/test';
import {readFile,mkdir,writeFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
const read=async path=>JSON.parse(await readFile(path,'utf8'));
const proof='result/blender/stage222/browser';

test('edition222 bounds public-structure changes and preserves all existing rooms',async()=>{
 const before=await read('result/blender/stage222/catalogue-before.json');
 const after=await read('web/public/models/catalogue.json');
 const native=await read('result/blender/stage222/building-refinement.json');
 expect(before.version).toBe('221');expect(after.version).toBe('222');
 expect(after.sourceModelSha256).toBe(native.sourceModelSha256);expect(after.buildings).toHaveLength(31);
 const allowed=new Set(['61A:detailedExterior','61A:detailedInterior','SAL:detailedExterior','SAL:detailedInterior']);
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
 expect(changed.sort()).toEqual(['61A:detailedExterior','61A:detailedInterior','SAL:detailedExterior','SAL:detailedInterior']);
 expect(rooms).toBe(19);
 for(const item of await read('result/blender/stage222/asset-hashes-before.json')){
  if(['61A','SAL'].includes(item.code))continue;
  const hash=createHash('sha256').update(await readFile('web/public'+item.url)).digest('hex');
  expect(hash,item.code+' default interior').toBe(item.sha256);
 }
 for(const [code,id] of [['61A','61a-reception'],['SAL','sal-g01']]){
  const old=before.buildings.find(b=>b.code===code);
  const current=after.buildings.find(b=>b.code===code);
  expect(current.interiorSpaces.find(r=>r.id===id).detailedInterior.triangles).toBe(old.detailedInterior.triangles);
  expect(current.interiorStudy).toBeUndefined();
  expect(current.interiorSections).toHaveLength(2);
 }
 expect(after.buildings.flatMap(b=>b.interiorSpaces||[])).toHaveLength(21);
 const gallery=await read('web/public/gallery-manifest.json');
 expect(gallery.version).toBe('222');
 expect(gallery.images.every(image=>image.sourceModelSha256===after.sourceModelSha256)).toBe(true);
 for(const name of ['61a-floor4-interior','61a-floor6-interior','61a-reception-interior','sal-g01-interior','sal-interior'])
  expect(gallery.images.find(image=>image.name===name),name).toBeTruthy();
 await mkdir(proof,{recursive:true});
 await writeFile(`${proof}/asset-scope.json`,JSON.stringify({changed,priorRoomsPreserved:rooms,galleryViews:gallery.images.length})+'\n');
});

for(const width of [1440,390])test(`new public structures and preserved samples load at ${width}px`,async({page})=>{
 test.setTimeout(240000);await mkdir(proof,{recursive:true});
 await page.setViewportSize({width,height:width===390?844:1000});
 const errors=[];page.on('pageerror',error=>errors.push(error.message));
 for(const [code,level,space] of [['SAL','LG','sal-g01'],['61A','4','61a-reception']]){
  await page.goto('/#'+code);
  await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-'+code,{timeout:90000});
  await expect(page.getByRole('button',{name:code==='SAL'?'公共走廊与楼梯':'四、六层楼板与双中庭',exact:true})).toBeVisible();
  await page.locator('#interior-view').click();
  await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','interior-'+code,{timeout:60000});
  await page.locator('#interior-level').selectOption(level);
  await expect(page.locator('#interior-level')).toHaveValue(level);
  await page.waitForTimeout(1000);
  await page.screenshot({path:`${proof}/${code}-public-${width}.png`});
  await page.locator('#interior-space').selectOption(space);
  await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','interior-'+code+':'+space,{timeout:60000});
 }
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
 expect(errors).toEqual([]);
 await writeFile(`${proof}/ui-${width}.json`,JSON.stringify({width,errors,publicAndRetainedRoomNavigation:true})+'\n');
});
