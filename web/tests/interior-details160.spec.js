import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
const read = async path => JSON.parse(await readFile(path,'utf8'));

test('edition160 limits changes to documented COL, CON and SAL room details',async()=>{
 const before=await read('result/blender/stage160/catalogue-before.json');
 const current=await read('dist/models/catalogue.json');
 const proof=await read('result/blender/stage160/building-refinement.json');
 expect(current.version).toBe('160');
 expect(current.sourceModelSha256).toBe(proof.sourceModelSha256);
 expect(proof.allUnrelatedMeshesPreserved).toBe(true);
 expect(proof.changes.flatMap(r=>r.changedObjects??[])).toEqual(expect.arrayContaining(['COL_V20_INTA_chair_back_oak','SAL_V20_INTA_projector_body_white']));
 const previousRelease=await read('result/blender/stage160/release-before.json');
 const currentRelease=await read('dist/release.json');
 expect(currentRelease.campusTransport).toEqual(previousRelease.campusTransport);
 expect(current.buildings).toHaveLength(31);
 expect(current.buildings.flatMap(b=>b.interiorSpaces??[])).toHaveLength(9);
 for(const building of current.buildings){
  const old=before.buildings.find(b=>b.code===building.code);
  expect(building.detailedExterior).toEqual(old.detailedExterior);
  if(['COL','CON','SAL'].includes(building.code))expect(building.detailedInterior.sha256).not.toBe(old.detailedInterior.sha256);
  else expect(building.detailedInterior).toEqual(old.detailedInterior);
  expect(building.interiorSpaces).toEqual(old.interiorSpaces);
  for(const detail of [building.detailedExterior,building.detailedInterior,...(building.interiorSpaces??[]).map(s=>s.detailedInterior)].filter(Boolean)){
   const bytes=await readFile('dist'+detail.url);
   expect(createHash('sha256').update(bytes).digest('hex')).toBe(detail.sha256);
  }
 }
});

for(const width of [1440,390])test(`COL, CON and SAL interiors remain navigable at ${width}px`,async({page})=>{
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.setViewportSize({width,height:width===390?844:1000});
 for(const code of ['COL','CON','SAL']){
  await page.goto('/#'+code);const canvas=page.locator('canvas');
  await expect(canvas).toHaveAttribute('data-detail-ready','exterior-'+code,{timeout:60000});
  await expect(page.locator('#fallback')).toBeHidden();
  await page.locator('#interior-view').click();
  if(code==='CON')await page.locator('#interior-space').selectOption('default');
  await expect(canvas).toHaveAttribute('data-detail-ready','interior-'+code,{timeout:60000});
  await expect(page.locator('#fallback')).toBeHidden();
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  await page.locator('#exterior-view').click();
  await expect(canvas).toHaveAttribute('data-detail-ready','exterior-'+code,{timeout:60000});
 }
 expect(errors).toEqual([]);
});
