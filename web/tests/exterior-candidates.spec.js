import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';

const catalogue=async()=>JSON.parse(await readFile('dist/models/catalogue.json'));
test('MAR and CLM corrections retain other exteriors and every interior',async()=>{
 const proof=JSON.parse(await readFile('result/blender/stage114/saved-verification.json'));
 expect(proof.originalGeometryRetained).toBeTruthy();
 expect(proof.retainedObjects).toBe(5225);
 expect(proof.marFins).toBe(38);expect(proof.marHammerheads).toBe(38);
 expect(proof.clmTallWindows).toBe(7);expect(proof.clearClmWindowProbes).toBe(63);
 expect(proof.groundCoverageProbes).toBe(96);expect(proof.ringClearanceMetres).toBeGreaterThan(.0019);
 const before=JSON.parse(await readFile('result/blender/stage114/catalogue-before.json'));
 const after=await catalogue();expect(after.version).toBe('114');
 expect(after.sourceModelSha256).toBe(proof.sourceModelSha256);
 for(const b of before.buildings){
  const current=after.buildings.find(x=>x.code===b.code);
  if(['MAR','CLM'].includes(b.code))expect(current.detailedExterior.url).not.toBe(b.detailedExterior.url);
  else expect(current.detailedExterior).toEqual(b.detailedExterior);
  expect(current.detailedInterior).toEqual(b.detailedInterior);
  expect(current.interiorSpaces).toEqual(b.interiorSpaces);
 }
});

test('MAR thin upper screen has the same geometry and finish in overview and detail',async()=>{
 const data=await catalogue();const mar=data.buildings.find(b=>b.code==='MAR');const result=[];
 for(const url of ['/models/campus.glb',mar.detailedExterior.url]){
  const bytes=await readFile('dist'+url);const doc=JSON.parse(bytes.subarray(20,20+bytes.readUInt32LE(12)));
  const primitives=[];
  for(const mesh of doc.meshes)for(const p of mesh.primitives){
   const material=doc.materials[p.material];if(!material.name.includes('MAR_NEXT_upper_fins_precast'))continue;
   const a=doc.accessors[p.attributes.POSITION];
   primitives.push({indices:doc.accessors[p.indices].count,min:a.min,max:a.max,pbr:material.pbrMetallicRoughness});
  }
  expect(primitives).toHaveLength(1);expect(primitives[0].indices).toBe(38*2*36);result.push(primitives);
 }
 expect(result[0]).toEqual(result[1]);
});

for(const code of ['MAR','CLM','SAW'])test(`${code} corrections and galleries load on desktop and mobile`,async({page})=>{
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 for(const width of [1440,390]){
  await page.setViewportSize({width,height:1000});await page.goto('/#'+code);
  await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-'+code,{timeout:60000});
  await expect(page.locator('#fallback')).toBeHidden();
  expect(await page.locator('.brand-mark').evaluate(i=>i.complete&&i.naturalWidth>0)).toBeTruthy();
  const image=code==='SAW'?'saw-globe':code.toLowerCase()+'-exterior';
  await page.locator(`.detail-gallery img[src*="${image}"]`).click();
  await expect(page.locator('#gallery-image')).toBeVisible();
  await expect.poll(()=>page.locator('#gallery-image').evaluate(i=>i.complete&&i.naturalWidth>0)).toBeTruthy();
  await page.locator('#gallery-dialog [data-close]').click();
 }
 expect(errors).toEqual([]);
});
