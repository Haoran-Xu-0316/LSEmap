import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';

function documentFor(bytes){return JSON.parse(bytes.subarray(20,20+bytes.readUInt32LE(12)).toString());}
test('street surfaces retain stone grain and shared furniture retains timber and metal',async()=>{
 const doc=documentFor(await readFile('dist/models/campus.glb'));
 const materials=doc.materials.filter(m=>m.name.includes('SITE_V47_'));
 expect(materials.filter(m=>m.name.includes('wood_'))).toHaveLength(5);
 expect(materials.filter(m=>m.name.includes('edge_'))).toHaveLength(2);
 for(const material of materials.filter(m=>/slab_|yorkstone_|wood_|edge_/.test(m.name))){
  expect(material.extras.surfaceDetail.kind).toBe('noise');
  expect(material.extras.surfaceDetail.bump).toBeGreaterThan(0);
  expect(material.extras.surfaceDetail.bump).toBeLessThan(.001);
 }
 expect(doc.materials.some(m=>m.name.includes('SITE_V44_'))).toBe(false);
 const landscape=doc.nodes.find(n=>n.extras?.buildingCode==='LANDSCAPE');
 const primitives=doc.meshes[landscape.mesh].primitives;
 expect(primitives.some(p=>doc.materials[p.material].name.includes('V47_wood'))).toBe(true);
 expect(primitives.some(p=>doc.materials[p.material].name.includes('V47_steel'))).toBe(true);
 const wood=primitives.filter(p=>doc.materials[p.material].name.includes('V47_wood'));
 const bounds=wood.map(p=>doc.accessors[p.attributes.POSITION]);
 expect(Math.max(...bounds.map(b=>b.max[0]))-Math.min(...bounds.map(b=>b.min[0]))).toBeGreaterThan(90);
 expect(Math.max(...bounds.map(b=>b.max[2]))-Math.min(...bounds.map(b=>b.min[2]))).toBeGreaterThan(60);
});

test('new street material shaders compile in the campus overview',async({page})=>{
 const errors=[];
 page.on('pageerror',e=>errors.push(e.message));
 page.on('console',m=>{if(m.type()==='error')errors.push(m.text());});
 await page.goto('/');
 await expect(page.locator('#loading')).toBeHidden({timeout:60000});
 await expect(page.locator('canvas')).toBeVisible();
 expect(errors).toEqual([]);
});

test('street close-up is accessible from the building gallery',async({page})=>{
 await page.goto('/#MAR');
 await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-MAR',{timeout:60000});
 const image=page.locator('.detail-gallery img[src*="portsmouth-street"]');
 await expect(image).toHaveAttribute('src',/v=50-/);
 await image.click();
 await expect(page.locator('#gallery-image')).toHaveAttribute('src',/portsmouth-street/);
});
