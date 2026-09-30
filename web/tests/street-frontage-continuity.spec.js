import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';

test('refined paving preserves buildings and established drainage positions',async()=>{
 const audit=JSON.parse(await readFile('result/blender/stage47/street-audit.json'));
 const old=JSON.parse(await readFile('result/blender/stage46/street-plan.json'));
 const next=JSON.parse(await readFile('result/blender/stage47/street-plan.json'));
 expect(audit.changedExistingObjects).toEqual([]);
 expect(audit.buildingOverlapArea).toBeLessThan(.000001);
 expect(next.gullies).toEqual(old.gullies);
 expect(audit.pavers).toBeGreaterThan(8537);
 for(const street of old.records){
  const refined=next.records.find(r=>r.street===street.street);
  expect(refined.area).toBeGreaterThanOrEqual(street.area-.001);
 }
});

test('drainage grilles have a recessed sump and a separate open-bar level',async()=>{
 const bytes=await readFile('dist/models/campus.glb');
 const doc=JSON.parse(bytes.subarray(20,20+bytes.readUInt32LE(12)).toString());
 const site=doc.nodes.find(n=>n.extras?.buildingCode==='SITE');
 const primitives=doc.meshes[site.mesh].primitives;
 const boundsFor=name=>primitives.filter(p=>doc.materials[p.material].name===name).map(p=>doc.accessors[p.attributes.POSITION]);
 const metal=boundsFor('WEB_SITE_V47_steel');
 const sump=boundsFor('WEB_SITE_V47_iron');
 expect(metal.length).toBeGreaterThan(0);
 expect(sump.length).toBeGreaterThan(0);
 expect(Math.min(...sump.map(a=>a.min[1]))).toBeCloseTo(.027,4);
 expect(Math.min(...metal.map(a=>a.min[1]))).toBeGreaterThan(.04);
});
