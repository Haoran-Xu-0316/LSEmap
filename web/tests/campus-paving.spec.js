import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';

test('campus GLB includes native paving in the SITE group',async()=>{
  const bytes=await readFile('dist/models/campus.glb');
  const document=JSON.parse(bytes.subarray(20,20+bytes.readUInt32LE(12)).toString());
  const site=document.nodes.find(node=>node.extras?.buildingCode==='SITE');
  expect(site).toBeTruthy();
  const primitives=document.meshes[site.mesh].primitives;
  const paving=primitives.filter(primitive=>document.materials[primitive.material].name.includes('SITE_V44_'));
  expect(paving).toHaveLength(12);
  expect(paving.reduce((sum,primitive)=>sum+document.accessors[primitive.indices].count/3,0)).toBeGreaterThan(14000);
  for(const primitive of paving){
    const material=document.materials[primitive.material];
    expect(material.pbrMetallicRoughness.roughnessFactor).toBeCloseTo(.88,2);
  }
});

test('campus overview loads the updated site without rendering errors',async({page})=>{
  const errors=[];
  page.on('pageerror',error=>errors.push(error.message));
  await page.goto('/');
  await expect(page.locator('#loading')).toBeHidden({timeout:60000});
  await expect(page.locator('canvas')).toBeVisible();
  expect(errors).toEqual([]);
});
