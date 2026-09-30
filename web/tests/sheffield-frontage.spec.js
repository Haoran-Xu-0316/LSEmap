import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';
import {createRequire} from 'node:module';
import {resolve} from 'node:path';

test('SHF front uses the long Sheffield Street edge and preserves other building geometry',async()=>{
 const audit=JSON.parse(await readFile('result/blender/stage50/shf-audit.json'));
 const catalogue=JSON.parse(await readFile('dist/models/catalogue.json'));
 const old=JSON.parse(await readFile('result/blender/stage05/infill-manifest.json'));
 const shf=catalogue.buildings.find(b=>b.code==='SHF');
 expect(audit.frontEdge).toBe(6);expect(audit.frontLength).toBeGreaterThan(15);
 expect(audit.frontRight[0]).toBeCloseTo(-audit.frontOutward[1],5);
 expect(audit.frontRight[1]).toBeCloseTo(audit.frontOutward[0],5);
 expect(audit.changedExistingGeometry).toEqual([]);
 expect(audit.windowBays).toBe(4);expect(audit.dormers).toBe(4);
 expect(audit.whiteBaseHeight).toBeGreaterThan(6);
 expect(audit.windows).toHaveLength(19);
 const direction=[...audit.frontOutward.slice(0,1),.65,-audit.frontOutward[1]];
 const length=Math.hypot(...direction);
 direction.forEach((value,i)=>expect(shf.exteriorDirection[i]).toBeCloseTo(value/length,5));
 expect(shf.exteriorDirection).not.toEqual(old.buildings.find(b=>b.code==='SHF').exteriorDirection);
});

test('SHF retains warm brick, pale window joinery and roof detail in overview and detail',async()=>{
 const catalogue=JSON.parse(await readFile('dist/models/catalogue.json'));
 const shf=catalogue.buildings.find(b=>b.code==='SHF');
 for(const path of ['/models/campus.glb',shf.detailedExterior.url]){
  const bytes=await readFile('dist'+path);
  const doc=JSON.parse(bytes.subarray(20,20+bytes.readUInt32LE(12)).toString());
  const node=doc.nodes.find(n=>n.extras?.buildingCode==='SHF')??doc.nodes.find(n=>n.mesh!==undefined);
  const primitives=doc.meshes[node.mesh].primitives;
  for(const suffix of ['brick','white','frame','slate'])expect(primitives.some(p=>doc.materials[p.material].name.includes('SHF_V50_'+suffix))).toBeTruthy();
  const brick=doc.materials.find(m=>m.name.includes('SHF_V50_brick'));
  if(path!== '/models/campus.glb'){
   expect(brick.extras.surfaceDetail.kind).toBe('brick');
   expect(brick.extras.surfaceDetail.brickWidth).toBeCloseTo(.225,3);
  }
 }
 expect(shf.interior).toBeFalsy();
});

test('SHF gallery loads the current roof view without errors',async({page})=>{
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('/#SHF');
 await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-SHF',{timeout:60000});
 const image=page.locator('.detail-gallery img[src*="shf-roof"]');
 await expect(image).toHaveAttribute('src',/v=51-/);await image.click();
 await expect(page.locator('#gallery-image')).toHaveAttribute('src',/shf-roof/);
 expect(errors).toEqual([]);
});

// Inspect exported UV edges, so rotating the brick courses cannot pass a metadata check.
test('SHF exported brick courses follow horizontal wall metres',async()=>{
 const catalogue=JSON.parse(await readFile('dist/models/catalogue.json'));
 const shf=catalogue.buildings.find(b=>b.code==='SHF');
 const bytes=await readFile('dist'+shf.detailedExterior.url);
 const jsonLength=bytes.readUInt32LE(12);
 const doc=JSON.parse(bytes.subarray(20,20+jsonLength).toString());
 const binary=bytes.subarray(28+jsonLength);
 const primitive=doc.meshes[0].primitives.find(p=>doc.materials[p.material].name.includes('SHF_V50_brick'));
 const compressed=primitive.extensions.KHR_draco_mesh_compression;
 const view=doc.bufferViews[compressed.bufferView];
 const directory=resolve('node_modules/three/examples/jsm/libs/draco/gltf');
 const wrapper={exports:{}};
 new Function('module','exports','require','__dirname',await readFile(directory+'/draco_wasm_wrapper.js','utf8'))(wrapper,wrapper.exports,createRequire(import.meta.url),directory);
 const draco=await wrapper.exports({wasmBinary:await readFile(directory+'/draco_decoder.wasm')});
 const decoder=new draco.Decoder(),buffer=new draco.DecoderBuffer(),mesh=new draco.Mesh();
 const data=binary.subarray(view.byteOffset,view.byteOffset+view.byteLength);
 buffer.Init(data,data.length);const status=decoder.DecodeBufferToMesh(buffer,mesh);
 expect(status.ok()).toBeTruthy();
 const attribute=(semantic,size)=>{
  const array=new draco.DracoFloat32Array();
  decoder.GetAttributeFloatForAllPoints(mesh,decoder.GetAttributeByUniqueId(mesh,compressed.attributes[semantic]),array);
  const values=Array.from({length:mesh.num_points()},(_,i)=>Array.from({length:size},(_,j)=>array.GetValue(i*size+j)));
  draco.destroy(array);return values;
 };
 const positions=attribute('POSITION',3),uvs=attribute('TEXCOORD_0',2),normals=attribute('NORMAL',3);
 let checked=0;
 // Compression reorders vertices; compare all vertical edges. World Y is native height.
 for(let i=0;i<positions.length;i++)for(let j=i+1;j<positions.length;j++){
  const a=positions[i],b=positions[j],height=Math.abs(b[1]-a[1]);
  if(Math.abs(normals[i][1])<.1&&height>.1&&Math.abs(b[0]-a[0])<1e-5&&Math.abs(b[2]-a[2])<1e-5&&normals[i].every((v,k)=>Math.abs(v-normals[j][k])<1e-5)){
   expect(Math.abs(uvs[j][0]-uvs[i][0])).toBeLessThan(1e-4);
   expect(Math.abs(Math.abs(uvs[j][1]-uvs[i][1])-height)).toBeLessThan(.02);checked++;
  }
 }
 draco.destroy(status);draco.destroy(mesh);draco.destroy(buffer);draco.destroy(decoder);
 expect(checked).toBeGreaterThan(20);
});
