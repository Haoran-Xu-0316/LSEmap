import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
const read = async path => JSON.parse(await readFile(path,'utf8'));

test('edition159 limits changes to documented CKK rainwater, SAW stairs and LRB rail finishes',async()=>{
 const before=await read('result/blender/stage159/catalogue-before.json');
 const current=await read('dist/models/catalogue.json');
 const proof=await read('result/blender/stage159/building-refinement.json');
 expect(current.version).toBe('159');
 expect(current.sourceModelSha256).toBe(proof.sourceModelSha256);
 expect(proof.allUnrelatedMeshesPreserved).toBe(true);
 expect(proof.changes.flatMap(r=>r.changedObjects??[]).sort()).toEqual(['LRB_gallery_circular_handrail','LRB_landing_handrail.001','LRB_spiral_continuous_handrail','SAW_spiral_anti_slip_nosings']);
 expect(current.buildings).toHaveLength(31);
 expect(current.buildings.flatMap(b=>b.interiorSpaces??[])).toHaveLength(9);
 for(const building of current.buildings){
  const old=before.buildings.find(b=>b.code===building.code);
  if(['CKK','SAW','LRB'].includes(building.code))expect(building.detailedExterior.sha256).not.toBe(old.detailedExterior.sha256);
  else expect(building.detailedExterior).toEqual(old.detailedExterior);
  if(['SAW','LRB'].includes(building.code))expect(building.detailedInterior.sha256).not.toBe(old.detailedInterior.sha256);
  else expect(building.detailedInterior).toEqual(old.detailedInterior);
  expect(building.interiorSpaces).toEqual(old.interiorSpaces);
  for(const detail of [building.detailedExterior,building.detailedInterior,...(building.interiorSpaces??[]).map(s=>s.detailedInterior)].filter(Boolean)){
   const bytes=await readFile('dist'+detail.url);
   expect(createHash('sha256').update(bytes).digest('hex')).toBe(detail.sha256);
  }
 }
});

for(const width of [1440,390])test(`CKK facade and SAW stair remain navigable at ${width}px`,async({page})=>{
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.setViewportSize({width,height:width===390?844:1000});
 for(const code of ['CKK','SAW','LRB']){
  await page.goto('/#'+code);const canvas=page.locator('canvas');
  await expect(canvas).toHaveAttribute('data-detail-ready','exterior-'+code,{timeout:60000});
  await expect(page.locator('#fallback')).toBeHidden();
  await page.locator('#interior-view').click();
  await expect(canvas).toHaveAttribute('data-detail-ready','interior-'+code,{timeout:60000});
  await expect(page.locator('#fallback')).toBeHidden();
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  await page.locator('#exterior-view').click();
  await expect(canvas).toHaveAttribute('data-detail-ready','exterior-'+code,{timeout:60000});
 }
 expect(errors).toEqual([]);
});
