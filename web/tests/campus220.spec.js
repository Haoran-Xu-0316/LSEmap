import {test,expect} from '@playwright/test';
import {readFile,mkdir,writeFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
const read=async path=>JSON.parse(await readFile(path,'utf8'));
const proof='result/blender/stage220/browser';

test('edition220 preserves published rooms and limits exterior edits to CKK and KSW',async()=>{
 const before=await read('result/blender/stage220/catalogue-before.json');
 const after=await read('web/public/models/catalogue.json');
 const native=await read('result/blender/stage220/building-refinement.json');
 expect(before.version).toBe('218');expect(after.version).toBe('220');
 expect(after.sourceModelSha256).toBe(native.sourceModelSha256);expect(after.buildings).toHaveLength(31);
 const changed=[];let priorRooms=0;let totalRooms=0;
 for(const old of before.buildings){
  const current=after.buildings.find(item=>item.code===old.code);
  for(const field of ['detailedExterior','detailedInterior']){
   if(!old[field])continue;
   if(current[field].sha256!==old[field].sha256)changed.push(old.code+':'+field);
   if(field==='detailedExterior'&&['CKK','KSW'].includes(old.code)){
    expect(current[field].triangles).toBe(old[field].triangles);
   }else expect(current[field].sha256,old.code+field).toBe(old[field].sha256);
  }
  for(const room of old.interiorSpaces||[]){
   expect(current.interiorSpaces.find(item=>item.id===room.id).detailedInterior.sha256,room.id).toBe(room.detailedInterior.sha256);priorRooms++;
  }
  totalRooms+=(current.interiorSpaces||[]).length;
 }
 expect(changed.sort()).toEqual(['CKK:detailedExterior','KSW:detailedExterior']);
 expect(priorRooms).toBe(18);expect(totalRooms).toBe(19);
 for(const item of await read('result/blender/stage220/asset-hashes-before.json')){
  const hash=createHash('sha256').update(await readFile('web/public'+item.url)).digest('hex');
  expect(hash,item.code+' default interior').toBe(item.sha256);
 }
 const clm=after.buildings.find(item=>item.code==='CLM');
 const theatre=clm.interiorSpaces.find(item=>item.id==='clm-hongkong');
 expect(theatre.label).toContain('Hong Kong Theatre');
 expect(theatre.detailedInterior.triangles).toBeGreaterThan(1000);
 expect(theatre.detailedInterior.triangles).toBeLessThan(250000);
 expect(theatre.detailedInterior.bytes).toBeLessThan(4*1024*1024);
 const gallery=await read('web/public/gallery-manifest.json');
 expect(gallery.version).toBe('220');expect(gallery.images).toHaveLength(137);
 expect(gallery.images.every(image=>image.sourceModelSha256===after.sourceModelSha256)).toBe(true);
 expect(gallery.images.find(image=>image.name===theatre.gallery)).toBeTruthy();
 await mkdir(proof,{recursive:true});
 await writeFile(`${proof}/asset-scope.json`,JSON.stringify({changed,priorRoomsPreserved:priorRooms,totalRooms,newRoom:theatre.id})+'\n');
});

for(const width of [1440,390])test(`refined exteriors and the Hong Kong Theatre load at ${width}px`,async({page})=>{
 test.setTimeout(180000);await mkdir(proof,{recursive:true});
 await page.setViewportSize({width,height:width===390?844:1000});
 const errors=[];page.on('pageerror',error=>errors.push(error.message));
 for(const code of ['KSW','CKK']){
  await page.goto('/#'+code);
  await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-'+code,{timeout:90000});
  await page.waitForTimeout(600);await page.screenshot({path:`${proof}/${code.toLowerCase()}-${width}.png`});
 }
 await page.goto('/#CLM');
 await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-CLM',{timeout:90000});
 await page.locator('#interior-view').click();
 await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','interior-CLM',{timeout:60000});
 await page.locator('#interior-space').selectOption('clm-hongkong');
 await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','interior-CLM:clm-hongkong',{timeout:60000});
 await expect(page.locator('#interior-sections')).toBeHidden();
 await expect(page.locator('#interior-space-scope')).toBeHidden();
 const sourceNote=page.locator('details.detail-note');
 await sourceNote.locator('summary').click();
 await expect(page.locator('#interior-space-scope')).toBeVisible();
 await expect(page.locator('#interior-space-scope')).toContainText('260');
 await sourceNote.locator('summary').click();
 await page.waitForTimeout(600);await page.screenshot({path:`${proof}/clm-hongkong-${width}.png`});
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
 await page.locator('#interior-space').selectOption('clm-502');
 await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','interior-CLM:clm-502',{timeout:60000});
 expect(errors).toEqual([]);
 await writeFile(`${proof}/ui-${width}.json`,JSON.stringify({width,errors,newAndRetainedRoomNavigation:true})+'\n');
});
