import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
const read=async p=>JSON.parse(await readFile(p,'utf8'));
const glb=async p=>{const b=await readFile(p);return JSON.parse(b.subarray(20,20+b.readUInt32LE(12)));};

test('edition157 smooths only mapped vegetation and preserves every building asset',async()=>{
 const proof=await read('result/blender/stage157/vegetation-shading.json');
 const catalogue=await read('web/public/models/catalogue.json');
 const before=await read('result/blender/stage157/catalogue-before.json');
 expect(catalogue.version).toBe('157');expect(proof.allMeshPositionsAndTopologyUnchanged).toBe(true);expect(proof.objects).toBe(5917);
 const native=await readFile('result/blender/LSE_campus_detailed_v157.blend');
 expect(createHash('sha256').update(native).digest('hex')).toBe(catalogue.sourceModelSha256);
 for(const record of proof.changedObjects){expect(record.smoothFacesAfter).toBe(record.faces);expect(record.flatFacesBefore).toBe(record.faces);}
 expect(proof.changedObjects).toHaveLength(2);
 for(const current of catalogue.buildings){
  const previous=before.buildings.find(b=>b.code===current.code);
  expect(current.detailedExterior,current.code).toEqual(previous.detailedExterior);
  expect(current.interiorAsset,current.code).toEqual(previous.interiorAsset);
 }
 const campus=await glb('web/public/models/campus.glb');
 const foliage=campus.materials.findIndex(m=>m.name==='WEB_London plane foliage');
 expect(campus.materials[foliage].pbrMetallicRoughness.roughnessFactor).toBeCloseTo(.88,4);
 const primitive=campus.meshes.flatMap(m=>m.primitives).find(p=>p.material===foliage);
 expect(campus.accessors[primitive.attributes.POSITION].count).toBeLessThan(125280*.5);
 expect(campus.accessors[primitive.indices].count).toBe(125280);
});
