import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';

test('LCH rebuilt frontage preserves other buildings and exports brick UVs',async()=>{
 const before=JSON.parse(await readFile('web/tests/fixtures/edition41-models.json','utf8'));
 const catalogue=JSON.parse(await readFile('dist/models/catalogue.json','utf8'));
 expect(catalogue.version).toBe('43');
 for(const b of catalogue.buildings){
  for(const key of ['detailedInterior','interiorSpaces'])expect(b[key]??null,`${b.code}:${key}`).toEqual(before[b.code][key]);
  if(b.code==='LCH')expect(b.detailedExterior.sha256).not.toBe(before.LCH.detailedExterior.sha256);
  else expect(b.detailedExterior??null,b.code).toEqual(before[b.code].detailedExterior);
 }
 const building=catalogue.buildings.find(b=>b.code==='LCH');
 expect(building.detailView.position).toEqual([-17.7,3.9,-31.7]);
 expect(building.detailView.target).toEqual([-22.4,2.1,-22.1]);
 const bytes=await readFile('dist'+building.detailedExterior.url);
 const gltf=JSON.parse(bytes.subarray(20,20+bytes.readUInt32LE(12)).toString());
 const brickIndex=gltf.materials.findIndex(m=>m.name.includes('LCH_V42_brick'));
 expect(brickIndex).toBeGreaterThanOrEqual(0);
 expect(gltf.materials[brickIndex].extras.surfaceDetail).toBeTruthy();
 const primitives=gltf.meshes.flatMap(m=>m.primitives).filter(p=>p.material===brickIndex);
 expect(primitives.length).toBeGreaterThan(0);
 for(const primitive of primitives)expect(primitive.attributes.TEXCOORD_0).toBeDefined();
});

test('LCH entrance view loads the relocated porch',async({page})=>{
 await page.goto('/#LCH');
 await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-LCH',{timeout:60000});
 await page.locator('#detail-view').click();
 await expect(page.locator('#view-mode')).toHaveText('入口细节');
 await page.screenshot({path:'result/blender/stage42/web-entrance.png'});
});
