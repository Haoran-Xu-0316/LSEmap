import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';
const read=async path=>JSON.parse(await readFile(path,'utf8'));
test('verified KGS and PAR components match the saved release and both viewing scales',async()=>{
 const proof=await read('result/blender/stage120/saved-verification.json');
 const catalogue=await read('dist/models/catalogue.json');
 expect(catalogue.version).toBe('120');expect(catalogue.sourceModelSha256).toBe(proof.sourceModelSha256);
 expect(proof.savedSceneReopened).toBe(true);expect(proof.unrelatedVisibilityPreserved).toBe(true);expect(proof.ownedObjects).toHaveLength(19);
 for(const code of ['KGS','PAR']){
  const building=catalogue.buildings.find(b=>b.code===code);const summaries=[];
  for(const url of ['/models/campus.glb',building.detailedExterior.url]){
   const data=await readFile('dist'+url);const glb=JSON.parse(data.subarray(20,20+data.readUInt32LE(12)));
   const primitives=[];
   for(const mesh of glb.meshes)for(const p of mesh.primitives){
    const m=glb.materials[p.material];if(!m.name.includes(code+'_NEXT_'))continue;
    const a=glb.accessors[p.attributes.POSITION];primitives.push({material:m.name.replace('WEB_DETAIL_','WEB_'),indices:glb.accessors[p.indices].count,min:a.min,max:a.max,pbr:m.pbrMetallicRoughness,finish:m.extras?.surfaceDetail});
   }
   expect(primitives.length).toBeGreaterThan(0);summaries.push(primitives);
  }
  expect(summaries[0],code).toEqual(summaries[1]);
 }
});
test('KGS and PAR exterior and retained interior load on desktop and phone',async({page})=>{
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 for(const width of [1440,390])for(const code of ['KGS','PAR']){
  await page.setViewportSize({width,height:1000});await page.goto('/#'+code);
  await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-'+code,{timeout:60000});
  await expect(page.locator('#fallback')).toBeHidden();
  await page.locator('#interior-view').click();
  await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','interior-'+code,{timeout:60000});
 }
 expect(errors).toEqual([]);
});
