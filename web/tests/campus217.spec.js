import {test, expect} from '@playwright/test';
import {readFile, mkdir, writeFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
const read = async path => JSON.parse(await readFile(path, 'utf8'));
const proof = 'result/blender/stage217/browser';
const glbDocument = async url => {
 const bytes = await readFile('web/public' + url);
 expect(bytes.toString('ascii',0,4)).toBe('glTF');
 return JSON.parse(bytes.toString('utf8',20,20+bytes.readUInt32LE(12)));
};

test('edition217 changes only the reviewed building assets and preserves all independent rooms', async () => {
 const before = await read('result/blender/stage217/catalogue-before.json');
 const after = await read('web/public/models/catalogue.json');
 const native = await read('result/blender/stage217/building-refinement.json');
 expect(after.version).toBe('217');expect(after.sourceModelSha256).toBe(native.sourceModelSha256);
 expect(after.buildings).toHaveLength(31);
 let roomCount=0;
 for(const old of before.buildings) {
  const current=after.buildings.find(item=>item.code===old.code);
  for(const field of ['detailedExterior','detailedInterior']) {
   if(!old[field])continue;
   const changed=field==='detailedExterior'?['COW','OLD','MAR'].includes(old.code):old.code==='MAR';
   if(changed)expect(current[field].sha256,old.code+field).not.toBe(old[field].sha256);
   else expect(current[field].sha256,old.code+field).toBe(old[field].sha256);
  }
  for(const room of old.interiorSpaces||[]) {
   expect(current.interiorSpaces.find(item=>item.id===room.id).detailedInterior.sha256,room.id).toBe(room.detailedInterior.sha256);roomCount++;
  }
 }
 expect(roomCount).toBe(18);
 const fallbacks=await read('result/blender/stage217/asset-hashes-before.json');
 expect(fallbacks).toHaveLength(25);
 for(const old of fallbacks){
  const hash=createHash('sha256').update(await readFile('web/public'+old.url)).digest('hex');
  if(old.code==='MAR')expect(hash,old.code+' fallback').not.toBe(old.sha256);
  else expect(hash,old.code+' fallback').toBe(old.sha256);
 }
 const cow=after.buildings.find(item=>item.code==='COW');
 expect(cow.detailedExterior.triangles).toBe(before.buildings.find(item=>item.code==='COW').detailedExterior.triangles);
 const old=after.buildings.find(item=>item.code==='OLD');
 expect(old.detailedExterior.triangles).toBe(before.buildings.find(item=>item.code==='OLD').detailedExterior.triangles);
 const cowGlb=await glbDocument(cow.detailedExterior.url);
 const brick=cowGlb.materials.find(material=>material.name==='WEB_DETAIL_COW217_HERITAGE09_brick');
 expect(brick?.extras.surfaceDetail.kind).toBe('brick');
 expect(brick.extras.surfaceDetail.brickWidth).toBeCloseTo(.225,6);
 expect(brick.extras.surfaceDetail.rowHeight).toBeCloseTo(.078,6);
 expect(brick.extras.surfaceDetail.mortarSize).toBeCloseTo(.004,6);
 expect(brick.extras.surfaceDetail.bump).toBeCloseTo(.0009,6);
 const oldGlb=await glbDocument(old.detailedExterior.url);
 const panes=oldGlb.materials.filter(material=>material.name.startsWith('WEB_DETAIL_OLDGLASS217_'));
 expect(panes).toHaveLength(3);
 for(const material of panes){expect(material.extras.webClosedGlazing).toBe(true);expect(material.pbrMetallicRoughness.baseColorFactor[3]).toBe(1);}
 const gallery=await read('web/public/gallery-manifest.json');
 expect(gallery.version).toBe('217');expect(gallery.images).toHaveLength(136);
 expect(gallery.images.every(image=>image.sourceModelSha256===after.sourceModelSha256)).toBe(true);
});

for(const width of [1440,390])test(`registered MAR exterior, public hall and independent room load at ${width}px`,async({page})=>{
 test.setTimeout(150000);await mkdir(proof,{recursive:true});
 await page.setViewportSize({width,height:width===390?844:1000});
 const errors=[];page.on('pageerror',error=>errors.push(error.message));
 await page.goto('/#MAR');await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-MAR',{timeout:90000});
 await page.waitForTimeout(1000);await page.screenshot({path:`${proof}/mar-exterior-${width}.png`});
 await page.locator('#interior-view').click();await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','interior-MAR',{timeout:60000});
 await page.waitForTimeout(1000);await page.screenshot({path:`${proof}/mar-hall-${width}.png`});
 await page.locator('#interior-space').selectOption('mar-104');
 await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','interior-MAR:mar-104',{timeout:60000});
 await expect(page.locator('#interior-sections')).toBeHidden();
 await page.locator('#interior-space').selectOption('default');
 await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','interior-MAR',{timeout:60000});
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
 await page.locator('#overview').click();await expect(page.locator('#fallback')).toBeHidden();
 await page.waitForTimeout(1000);await page.screenshot({path:`${proof}/campus-${width}.png`});
 expect(errors).toEqual([]);await writeFile(`${proof}/ui-${width}.json`,JSON.stringify({width,errors,marPublicAndRoomNavigation:true})+'\n');
});
