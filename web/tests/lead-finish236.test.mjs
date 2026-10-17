import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import * as THREE from 'three';
import {refineMaterialFinish} from '../src/surface-materials.js';
const explicitLead=/(?:^|[_\s])lead(?:[_\s.]|$)/i;
async function glb(url){const bytes=await readFile('web/public'+url);return JSON.parse(bytes.toString('utf8',20,20+bytes.readUInt32LE(12)));}

test('all production lead finishes retain their authored roughness and metalness at both scales',async()=>{
 const catalogue=JSON.parse(await readFile('web/public/models/catalogue.json','utf8'));
 const exterior=catalogue.buildings.filter(row=>row.detailedExterior);
 const variants=[['CAMPUS','/models/campus.glb'],...exterior.map(row=>[row.code,row.detailedExterior.url])];
 const covered=new Set();let checked=0;
 for(const [code,url]of variants){
  const document=await glb(url);
  for(const source of document.materials.filter(row=>explicitLead.test(row.name))){
   const pbr=source.pbrMetallicRoughness??{};
   const material=new THREE.MeshStandardMaterial({name:source.name,roughness:pbr.roughnessFactor??1,metalness:pbr.metallicFactor??1});
   const before={roughness:material.roughness,metalness:material.metalness};
   refineMaterialFinish(material);refineMaterialFinish(material);
   assert.deepEqual({roughness:material.roughness,metalness:material.metalness},before,code+':'+source.name);
   if(code!=='CAMPUS')covered.add(code);checked++;material.dispose();
  }
 }
 assert.equal(exterior.length,30);assert.deepEqual([...covered].sort(),['CKK','CON','COW','KGS','OCS','PAR']);assert.equal(checked,15);
});

test('zinc and aluminium retain their separate finish while non-lead words are not matched',()=>{
 for(const name of ['roof_zinc','roof_aluminium','roof_aluminum']){
  const material=new THREE.MeshStandardMaterial({name,metalness:.3,roughness:.8});
  refineMaterialFinish(material);assert.equal(material.roughness,.48);assert.equal(material.metalness,.65);material.dispose();
 }
 const material=new THREE.MeshStandardMaterial({name:'student_leadership_wall',metalness:0,roughness:.82});
 refineMaterialFinish(material);assert.equal(material.roughness,.82);assert.equal(material.metalness,0);material.dispose();
});
