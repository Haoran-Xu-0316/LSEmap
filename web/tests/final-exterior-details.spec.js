import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';
const read=async p=>JSON.parse(await readFile(p,'utf8'));
test('current campus export has no historical stage dependency and preserves unaffected assets',async()=>{
 const before=await read('result/blender/stage116/catalogue-before.json');
 const after=await read('dist/models/catalogue.json');
 const proof=await read('result/blender/stage116/saved-verification.json');
 expect(after.version).toBe('116');expect(after.sourceModelSha256).toBe(proof.sourceModelSha256);
 expect(proof.originalGeometryRetained).toBeTruthy();expect(proof.candidateIdentityRetained).toBeTruthy();
 const source=await readFile('web/tools/export_scene.py','utf8');
 expect(source).not.toMatch(/result\/blender\/stage\d+/);
 for(const b of before.buildings){
  const next=after.buildings.find(x=>x.code===b.code);
  if(!['OLD','MAR'].includes(b.code))expect(next.detailedExterior).toEqual(b.detailedExterior);
  expect(next.detailedInterior).toEqual(b.detailedInterior);
  expect(next.interiorSpaces).toEqual(b.interiorSpaces);
  expect(next.interiorView).toEqual(b.interiorView);
  expect(next.detailView).toEqual(b.detailView);
 }
 expect(after.generatedTextures).toEqual([expect.objectContaining({sha256:proof.globeImageSha256,nativeImage:proof.globeImage})]);
});
test('new MAR screen and OLD approach steps match in overview and selected building',async()=>{
 const c=await read('dist/models/catalogue.json');
 for(const [code,match] of [['MAR','MAR_V115_fin'],['OLD','OLD_V116']]){
  const b=c.buildings.find(x=>x.code===code);const summaries=[];
  for(const url of ['/models/campus.glb',b.detailedExterior.url]){
   const data=await readFile('dist'+url);const glb=JSON.parse(data.subarray(20,20+data.readUInt32LE(12)));
   const primitives=[];
   for(const mesh of glb.meshes)for(const p of mesh.primitives){
    const m=glb.materials[p.material];if(!m.name.includes(match))continue;
    const a=glb.accessors[p.attributes.POSITION];
    primitives.push({indices:glb.accessors[p.indices].count,min:a.min,max:a.max,pbr:m.pbrMetallicRoughness});
   }
   expect(primitives.length).toBeGreaterThan(0);summaries.push(primitives);
  }
  expect(summaries[0]).toEqual(summaries[1]);
 }
});
for(const code of ['MAR','OLD','SAW'])test(`${code} exterior and gallery load at desktop and phone sizes`,async({page})=>{
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 for(const width of [1440,390]){
  await page.setViewportSize({width,height:1000});await page.goto('/#'+code);
  await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-'+code,{timeout:60000});
  await expect(page.locator('#fallback')).toBeHidden();
  const name=code==='SAW'?'saw-globe':code.toLowerCase()+'-exterior';
  await page.locator(`.detail-gallery img[src*="${name}"]`).click();
  await expect.poll(()=>page.locator('#gallery-image').evaluate(i=>i.complete&&i.naturalWidth>0)).toBeTruthy();
  await page.locator('#gallery-dialog [data-close]').click();
 }
 expect(errors).toEqual([]);
});
