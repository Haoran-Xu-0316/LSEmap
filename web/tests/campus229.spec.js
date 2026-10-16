import {test,expect} from '@playwright/test';
import {readFile,mkdir,writeFile} from 'node:fs/promises';
import * as THREE from 'three';
import {isGlazingMaterial,refineMaterialFinish} from '../src/surface-materials.js';
const read=async path=>JSON.parse(await readFile(path,'utf8'));
const proof='result/blender/stage229/browser';
const newRooms=[{code:'FAW',id:'faw-102',report:'faw102-room229'},{code:'SAL',id:'sal-b01',report:'salb01-room229'}];

test('229 refines SAL glazing and street fixtures while preserving all prior rooms',async()=>{
 const before=await read('result/blender/stage229/catalogue-before.json');
 const after=await read('web/public/models/catalogue.json');
 const native=await read('result/blender/stage229/building-refinement.json');
 expect(before.version).toBe('228');expect(after.version).toBe('229');
 expect(after.sourceModelSha256).toBe(native.sourceModelSha256);expect(after.buildings).toHaveLength(31);
 const changed=[];let rooms=0,interiors=0,exteriors=0;
 for(const old of before.buildings){
  const current=after.buildings.find(item=>item.code===old.code);
  for(const field of ['detailedExterior','detailedInterior']){
   if(!old[field])continue;
   if(current[field].sha256!==old[field].sha256)changed.push(old.code+':'+field);
   if(field==='detailedInterior')interiors++;else exteriors++;
  }
  for(const room of old.interiorSpaces||[]){
   expect(current.interiorSpaces.find(item=>item.id===room.id).detailedInterior.sha256,room.id).toBe(room.detailedInterior.sha256);rooms++;
  }
 }
 expect(changed).toEqual(['SAL:detailedExterior']);expect(interiors).toBe(25);expect(exteriors).toBe(30);expect(rooms).toBe(27);
 const spaces=after.buildings.flatMap(building=>building.interiorSpaces||[]);expect(spaces).toHaveLength(29);
 const gallery=await read('web/public/gallery-manifest.json');expect(gallery.version).toBe('229');
 expect(gallery.images.every(image=>image.sourceModelSha256===after.sourceModelSha256)).toBe(true);
 for(const room of newRooms){
  expect(spaces.find(space=>space.id===room.id).detailedInterior.sha256).toMatch(/^[a-f0-9]{64}$/);
  const views=gallery.images.filter(image=>image.spaceId===room.id);expect(views).toHaveLength(2);
  expect(views.every(view=>view.mode==='interior'&&view.detail==='interior-'+room.code+':'+room.id)).toBe(true);
 }
 await mkdir(proof,{recursive:true});
 await writeFile(proof+'/asset-scope.json',JSON.stringify({changed,defaultInteriorsPreserved:interiors,detailedExteriorsPreserved:exteriors-1,detailedExteriorsTotal:exteriors,priorRoomsPreserved:rooms,totalRoomSpaces:spaces.length,newRooms:newRooms.map(room=>room.id),galleryViews:gallery.images.length})+'\n');
});

for(const width of [1440,390])test(`both classrooms and their galleries load at ${width}px`,async({page})=>{
 test.setTimeout(150000);await mkdir(proof,{recursive:true});
 await page.setViewportSize({width,height:width===390?844:1000});
 const errors=[];page.on('pageerror',error=>errors.push(error.message));
 for(const room of newRooms){
  await page.goto('/#'+room.code);
  await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-'+room.code,{timeout:60000});
  const exterior=new RegExp('/images/'+room.code.toLowerCase()+'-exterior[.]webp[?]v=229-');
  await expect(page.locator('.detail-photo img')).toHaveAttribute('src',exterior);
  await page.locator('.detail-photo').click();
  await expect(page.locator('#gallery-image')).toHaveAttribute('src',exterior);
  await page.getByRole('button',{name:'关闭图片',exact:true}).click();
  await page.locator('#interior-view').click();
  await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','interior-'+room.code,{timeout:60000});
  await page.locator('#interior-space').selectOption(room.id);
  await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','interior-'+room.code+':'+room.id,{timeout:60000});
  await page.screenshot({path:`${proof}/${room.id}-${width}.png`});
  const audit=await read('result/blender/'+room.report+'/audit.json');const view=audit.gallerySuggestions[1];
  await page.getByRole('button',{name:view.label,exact:true}).click();
  await expect(page.locator('#gallery-image')).toHaveAttribute('src',new RegExp('/images/'+view.name+'[.]webp[?]v=229-'));
  await page.getByRole('button',{name:'关闭图片',exact:true}).click();
 }
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);expect(errors).toEqual([]);
});

// Check the exported optical contract rather than only the authoring report.
test('SAL tint revision preserves exported optics and opaque stone',async()=>{
 const audit=await read('result/blender/facade-material229/audit.json');
 const prior=await read('result/blender/stage229/sal-exterior-materials-before.json');
 const catalogue=await read('web/public/models/catalogue.json');
 const sal=catalogue.buildings.find(building=>building.code==='SAL');
 const bytes=await readFile('web/public'+sal.detailedExterior.url);
 const doc=JSON.parse(bytes.subarray(20,20+bytes.readUInt32LE(12)));
 const find=(materials,name)=>{
  const matches=materials.filter(material=>material.name.replace(/^WEB_(DETAIL_)?/,'')===name);
  expect(matches,name).toHaveLength(1);return matches[0];
 };
 const optical=material=>({
  pbr:Object.fromEntries(Object.entries(material.pbrMetallicRoughness||{}).filter(([key])=>key!=='baseColorFactor')),
  alpha:material.pbrMetallicRoughness?.baseColorFactor?.[3]??1,
  alphaMode:material.alphaMode??'OPAQUE',alphaCutoff:material.alphaCutoff??.5,
  doubleSided:material.doubleSided??false,extensions:material.extensions??{},
  role:material.extras?.webSurfaceRole,closed:material.extras?.webClosedGlazing,
 });
 const exported=[],unused=[];
 for(const change of audit.materials){
  // Blender retains archival material slots. glTF correctly omits slots without faces.
  const oldName='WEB_DETAIL_'+change.source,newName='WEB_DETAIL_'+change.replacement;
  if(!prior.materials.some(material=>material.name===oldName)){
   expect(doc.materials.some(material=>material.name===newName),change.source).toBe(false);
   unused.push(change.source);continue;
  }
  const old=find(prior.materials,change.source),current=find(doc.materials,change.replacement);
  exported.push(change.source);
  expect(optical(current),change.source).toEqual(optical(old));
  const actual=current.pbrMetallicRoughness.baseColorFactor.slice(0,3);
  actual.forEach((value,index)=>expect(value).toBeCloseTo(change.after.baseColor[index],6));
  const luminance=([r,g,b])=>r*.2126+g*.7152+b*.0722;
  expect(luminance(actual)).toBeCloseTo(luminance(old.pbrMetallicRoughness.baseColorFactor),6);
  const material=new THREE.MeshStandardMaterial({color:new THREE.Color(...actual),
   roughness:current.pbrMetallicRoughness.roughnessFactor,
   transparent:current.alphaMode==='BLEND',opacity:current.pbrMetallicRoughness.baseColorFactor[3]});
  material.name=current.name;material.userData=current.extras||{};
  expect(isGlazingMaterial(material),current.name).toBe(true);
  const environment=new THREE.Texture(),opacity=material.opacity;
  refineMaterialFinish(material,environment);
  expect(material.envMap).toBe(environment);expect(material.opacity).toBe(opacity);
  expect(luminance(material.color.toArray())).toBeCloseTo(luminance(actual),6);
  material.dispose();environment.dispose();
 }
 expect(exported).toHaveLength(4);expect(unused).toHaveLength(2);
 await writeFile(proof+'/sal-optics.json',JSON.stringify({sourceModelSha256:catalogue.sourceModelSha256,
  exportedOpticsPreserved:exported,unusedArchivalSlotsAbsentFromBothExports:unused,
  runtimeGlazingClassificationAndEnvironmentPreserved:true})+'\n');
 for(const material of prior.materials.filter(item=>!audit.materials.some(change=>item.name.replace(/^WEB_(DETAIL_)?/,'')===change.source))){
  const current=doc.materials.find(item=>item.name===material.name);
  expect(current,material.name).toEqual(material);
 }
});
