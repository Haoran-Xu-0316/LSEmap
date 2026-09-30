import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';

test('inverted globe has a four-metre textured surface embedded in the campus GLB',async()=>{
 const bytes=await readFile('dist/models/campus.glb');
 const doc=JSON.parse(bytes.subarray(20,20+bytes.readUInt32LE(12)).toString());
 const landscape=doc.nodes.find(node=>node.extras?.buildingCode==='LANDSCAPE');
 const primitive=doc.meshes[landscape.mesh].primitives.find(p=>doc.materials[p.material].name.includes('V45_globe'));
 expect(primitive).toBeTruthy();
 const bounds=doc.accessors[primitive.attributes.POSITION];
 for(let axis=0;axis<3;axis++)expect(bounds.max[axis]-bounds.min[axis]).toBeCloseTo(4,2);
 expect(bounds.min[1]).toBeCloseTo(.05,2);
 expect(primitive.attributes.TEXCOORD_0).toBeDefined();
 const material=doc.materials[primitive.material];
 const texture=doc.textures[material.pbrMetallicRoughness.baseColorTexture.index];
 expect(doc.images[texture.source].bufferView).toBeDefined();
});

test('SAW gallery exposes the globe view from the current release',async({page})=>{
 await page.goto('/#SAW');
 await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-SAW',{timeout:60000});
 const image=page.locator('.detail-gallery img[src*="saw-globe"]');
 await expect(image).toHaveAttribute('src',/v=50-/);
 await image.click();
 await expect(page.locator('#gallery-image')).toHaveAttribute('src',/saw-globe/);
});
