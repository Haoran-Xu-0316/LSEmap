import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';

test('photo-guided landmarks preserve buildings and export the current globe texture',async()=>{
 const audit=JSON.parse(await readFile('result/blender/stage48/landmark-audit.json'));
 const labels=JSON.parse(await readFile('result/blender/stage48/globe-labels.json'));
 const catalogue=JSON.parse(await readFile('dist/models/catalogue.json'));
 expect(audit.changedExistingGeometry).toEqual([]);
 expect(audit.addedObjects.filter(n=>n.startsWith('MAR_'))).toHaveLength(6);
 expect(labels.labels.length).toBeGreaterThan(50);
 expect(labels.labels.every(l=>l.orientationDegrees===180)).toBeTruthy();
 expect(catalogue.generatedTextures[0].sha256).toBe(audit.globeTextureSha256);
 const bytes=await readFile('dist/models/campus.glb');
 const jsonLength=bytes.readUInt32LE(12);
 const doc=JSON.parse(bytes.subarray(20,20+jsonLength).toString());
 const binaryStart=28+jsonLength;
 const embedded=doc.images.map(i=>doc.bufferViews[i.bufferView]).map(v=>bytes.subarray(binaryStart+(v.byteOffset??0),binaryStart+(v.byteOffset??0)+v.byteLength));
 expect(embedded.some(b=>createHash('sha256').update(b).digest('hex')===audit.globeTextureSha256)).toBeTruthy();
 const mar=doc.nodes.find(n=>n.extras?.buildingCode==='MAR');
 const names=doc.meshes[mar.mesh].primitives.map(p=>doc.materials[p.material].name);
 expect(names.some(n=>n.includes('LSE_red_face'))).toBeTruthy();
 expect(names.some(n=>n.includes('LSE_white_sides'))).toBeTruthy();
});

test('Three Tuns is labelled as a historical entrance and plan study',async()=>{
 const catalogue=JSON.parse(await readFile('dist/models/catalogue.json'));
 const saw=catalogue.buildings.find(b=>b.code==='SAW');
 const space=saw.interiorSpaces.find(s=>s.id==='saw-three-tuns');
 expect(space.label).toContain('2014');
 expect(space.scope).toContain('不代表2026');
 expect(space.detailedInterior.url).toContain('three-tuns');
});

test('Houghton Street uses smaller staggered setts with one merged mesh',async()=>{
 const plan=JSON.parse(await readFile('result/blender/stage48/houghton-plan.json'));
 expect(plan.stoneDimensions).toEqual([.30,.15]);
 expect(plan.tiles.length).toBeGreaterThan(20000);
 const bytes=await readFile('dist/models/campus.glb');
 const doc=JSON.parse(bytes.subarray(20,20+bytes.readUInt32LE(12)).toString());
 expect(doc.nodes.filter(n=>n.extras?.buildingCode==='SITE')).toHaveLength(1);
});
