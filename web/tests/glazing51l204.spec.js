import {test,expect} from '@playwright/test';
import {readFile,mkdir,writeFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
const read=async path=>JSON.parse(await readFile(path,'utf8'));

test('51L restrained glazing keeps every original shape and unrelated building asset',async()=>{
 const before=await read('result/blender/stage204/catalogue-before.json');
 const current=await read('web/public/models/catalogue.json');
 const saved=await read('result/blender/stage204/reopened-verification.json');
 const paneProof=await read('result/blender/51l-exterior204/verification.json');
 expect(current.version).toBe('204');expect(saved.originalsVerified).toBe(7060);
 expect(saved.addedObjectsVerified).toBe(6);expect(saved.completeModelReopened).toBe(true);
 expect(paneProof.windowFirstSurfaceProbeCount).toBe(15);expect(paneProof.paneBackingProbeCount).toBe(101);
 expect(paneProof.replacementGeometryAndUvIdentical).toBe(true);expect(paneProof.outwardClosedShellsVerified).toBe(true);
 const native=await readFile('result/blender/LSE_campus_detailed_v204.blend');
 expect(createHash('sha256').update(native).digest('hex')).toBe(current.sourceModelSha256);
 for(const building of current.buildings){
  const previous=before.buildings.find(row=>row.code===building.code);
  for(const key of ['interiorAsset','detailedInterior','interiorSpaces'])expect(building[key]??null,building.code+key).toEqual(previous[key]??null);
  if(building.code==='51L')expect(building.detailedExterior.sha256).not.toBe(previous.detailedExterior.sha256);
  else expect(building.detailedExterior,building.code).toEqual(previous.detailedExterior);
 }
 const model=current.buildings.find(b=>b.code==='51L').detailedExterior;
 const bytes=await readFile('web/public'+model.url);const glb=JSON.parse(bytes.subarray(20,20+bytes.readUInt32LE(12)));
 const glass=glb.materials.filter(m=>m.name.includes('51L204_clear_'));expect(glass.length).toBeGreaterThan(0);
 for(const material of glass){expect(material.alphaMode).toBe('BLEND');expect(material.pbrMetallicRoughness.baseColorFactor[3]).toBeCloseTo(.72,5);expect(material.pbrMetallicRoughness.metallicFactor).toBe(0);}
});

test('51L glass facade renders on desktop and mobile and retains the same overview asset',async({page})=>{
 const errors=[];page.on('pageerror',error=>errors.push(error.message));
 await mkdir('result/blender/stage204/browser',{recursive:true});
 for(const width of [1440,390]){
  await page.setViewportSize({width,height:1000});await page.goto('/#51L');
  const canvas=page.locator('canvas');await expect(canvas).toHaveAttribute('data-detail-ready','exterior-51L',{timeout:65000});
  await page.screenshot({path:'result/blender/stage204/browser/51l-'+width+'.png'});
  await page.locator('#overview').click();await expect(canvas).toHaveAttribute('data-campus-details',/51L/);
 }
 expect(errors).toEqual([]);await writeFile('result/blender/stage204/browser/acceptance.json',JSON.stringify({widths:[1440,390],exterior51L:true,overviewIncludes51L:true,errors},null,2)+'\n');
});
