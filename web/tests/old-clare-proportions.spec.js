import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';

test('Clare Market lower facade has narrow glazed bays and preserves other buildings',async()=>{
 const audit=JSON.parse(await readFile('result/blender/stage53/old-clare-proportions-audit.json'));
 expect(audit.changedOtherObjects).toEqual([]);
 expect(audit.bayCount).toBe(5);expect(audit.ordinaryGlazedBays).toBe(4);
 expect(audit.bayWidth).toBeGreaterThan(2);expect(audit.bayWidth).toBeLessThan(3);
 expect(audit.hiddenPreviousObjects.length).toBeGreaterThan(10);
 expect(audit.changedExistingObjects.every(n=>n.startsWith('OLD_'))).toBeTruthy();
 expect(audit.limitations.join(' ')).toContain('dimensions not surveyed');
});

test('OLD overview and detail contain the rebuilt lower facade without obsolete wide-bay materials',async()=>{
 const catalogue=JSON.parse(await readFile('dist/models/catalogue.json'));
 const old=catalogue.buildings.find(b=>b.code==='OLD');
 for(const url of ['/models/campus.glb',old.detailedExterior.url]){
  const bytes=await readFile('dist'+url);const doc=JSON.parse(bytes.subarray(20,20+bytes.readUInt32LE(12)));
  const node=doc.nodes.find(n=>n.extras?.buildingCode==='OLD')??doc.nodes.find(n=>n.mesh!==undefined);
  const names=doc.meshes[node.mesh].primitives.map(p=>doc.materials[p.material].name);
  expect(names.some(n=>n.includes('OLD_V49_'))).toBeFalsy();
  for(const key of ['blue','glass','stone','leaf','red','white'])expect(names.some(n=>n.includes('OLD_V53_'+key))).toBeTruthy();
  expect(names.some(n=>n.includes('OLD_V52_ashlar_0'))).toBeTruthy();
 }
});

test('Clare Market gallery exposes the entire five-bay facade from the current source model',async()=>{
 const catalogue=JSON.parse(await readFile('dist/models/catalogue.json'));
 const gallery=JSON.parse(await readFile('dist/gallery-manifest.json'));
 const image=gallery.images.find(i=>i.name==='old-clare-market');
 expect(image.sourceModelSha256).toBe(catalogue.sourceModelSha256);
 const job=JSON.parse(await readFile('web/tools/gallery-views.json')).find(j=>j.name==='old-clare-market');
 for(const key of ['position','target'])for(let i=0;i<3;i++)expect(image.view[key][i]).toBeCloseTo(job.view[key][i],8);
 expect(image.view.fov).toBe(42);
});
