import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';
const read=async path=>JSON.parse(await readFile(path,'utf8'));

test('Carey frontage comes from the saved native scene; unrelated building assets are retained',async()=>{
 const before=await read('result/blender/stage117/catalogue-before.json');
 const after=await read('dist/models/catalogue.json');
 const proof=await read('result/blender/stage117/saved-verification.json');
 expect(after.version).toBe('117');expect(after.sourceModelSha256).toBe(proof.sourceModelSha256);
 expect(proof.originalGeometryRetained).toBe(true);expect(proof.originalPortugalStreetPreserved).toBe(true);
 expect(proof.clearApertures).toBe(74);expect(proof.archCount).toBe(5);expect(proof.tangentContinuity).toBe(true);
 for(const b of before.buildings){
  const next=after.buildings.find(x=>x.code===b.code);
  if(b.code!=='LRB'){
   expect(next.detailedExterior,b.code).toEqual(b.detailedExterior);
   expect(next.detailedInterior,b.code).toEqual(b.detailedInterior);
  }
  expect(next.interiorSpaces,b.code).toEqual(b.interiorSpaces);
  expect(next.interiorView,b.code).toEqual(b.interiorView);
 }
 expect(after.spaces).toEqual(before.spaces);
 expect(after.generatedTextures).toEqual(before.generatedTextures);
 const source=await readFile('web/tools/export_scene.py','utf8');expect(source).not.toMatch(/result\/blender\/stage\d+/);
});

test('Carey wall, curved entrance, glass and stone agree in overview and detailed exterior',async()=>{
 const c=await read('dist/models/catalogue.json');const b=c.buildings.find(x=>x.code==='LRB');const summaries=[];
 for(const url of ['/models/campus.glb',b.detailedExterior.url]){
  const data=await readFile('dist'+url);const glb=JSON.parse(data.subarray(20,20+data.readUInt32LE(12)));
  const primitives=[];
  for(const mesh of glb.meshes)for(const p of mesh.primitives){
   const m=glb.materials[p.material];if(!m.name.includes('LRB_V117_carey'))continue;
   const a=glb.accessors[p.attributes.POSITION];
   primitives.push({material:m.name.replace('WEB_DETAIL_','WEB_'),indices:glb.accessors[p.indices].count,min:a.min,max:a.max,pbr:m.pbrMetallicRoughness,finish:m.extras?.surfaceDetail});
  }
  expect(primitives.length).toBe(5);summaries.push(primitives);
 }
 expect(summaries[0]).toEqual(summaries[1]);
});

test('LRB exterior, new street galleries and retained interior load on desktop and phone',async({page})=>{
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 for(const width of [1440,390]){
  await page.setViewportSize({width,height:1000});await page.goto('/#LRB');
  await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-LRB',{timeout:60000});
  await expect(page.locator('#fallback')).toBeHidden();
  for(const name of ['lrb-carey-street','lrb-corner-entrance','lrb-portugal-street']){
   await page.locator(`.detail-gallery img[src*="${name}"]`).click();
   await expect.poll(()=>page.locator('#gallery-image').evaluate(i=>i.complete&&i.naturalWidth>0)).toBeTruthy();
   await page.locator('#gallery-dialog [data-close]').click();
  }
  await page.locator('#interior-view').click();
  await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','interior-LRB',{timeout:60000});
 }
 expect(errors).toEqual([]);
});
