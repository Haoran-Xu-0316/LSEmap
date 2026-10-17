import {test,expect} from '@playwright/test';
import {readFile,writeFile,mkdir} from 'node:fs/promises';
import {galleryRendererSignature} from '../tools/gallery_signature.mjs';
const read=async p=>JSON.parse(await readFile(p,'utf8'));
test('239 changes the OLD exterior while preserving all other buildings and rooms',async()=>{
 const before=await read('result/blender/stage239/catalogue-before.json'),after=await read('dist/models/catalogue.json');
 const native=await read('result/blender/stage239/native-verification.json'),reliefs=await read('result/blender/stage239/relief-geometry-verification.json');
 expect(after.version).toBe('239');expect(native.originalObjectsVerified).toBe(8601);expect(native.originalMaterialNodesVerified).toBe(2336);expect(native.originalMeshNormalsVerified).toBe(8364);expect([native.sourceRoomsVerified,native.sourceRoomObjectsVerified]).toEqual([35,1485]);
 expect(reliefs.checks).toHaveLength(5);expect(reliefs.frontageOrder).toEqual(['G','E','F','D','H']);expect(reliefs.totalReliefTriangles).toBeLessThan(115000);expect(reliefs.checks.every(c=>c.headAndTorsoInOneConnectedSurface&&c.nonmanifoldEdges===0)).toBe(true);
 let rooms=0,interiors=0,exteriors=0;
 for(const old of before.buildings){const current=after.buildings.find(b=>b.code===old.code);
  if(old.detailedExterior){exteriors++;if(old.code==='OLD'){expect(current.detailedExterior.sha256).not.toBe(old.detailedExterior.sha256);expect(current.detailedExterior.bytes-old.detailedExterior.bytes).toBeLessThan(500000);expect(current.detailedExterior.triangles-old.detailedExterior.triangles).toBeLessThan(100000);expect(current.detailedExterior.bounds).toEqual(old.detailedExterior.bounds);}else expect(current.detailedExterior.sha256,old.code).toBe(old.detailedExterior.sha256);}
  if(old.detailedInterior){interiors++;expect(current.detailedInterior.sha256,old.code).toBe(old.detailedInterior.sha256);}
  for(const room of old.interiorSpaces||[]){rooms++;expect(current.interiorSpaces.find(r=>r.id===room.id).detailedInterior.sha256,room.id).toBe(room.detailedInterior.sha256);}
 }
 expect([exteriors,interiors,rooms]).toEqual([30,25,35]);
 const gallery=await read('dist/gallery-manifest.json');expect(gallery.images).toHaveLength(194);expect(gallery.images.every(image=>image.sceneSamples===4)).toBe(true);expect(gallery.rendererSha256).toBe(await galleryRendererSignature());expect(gallery.images.every(r=>r.sourceModelSha256===after.sourceModelSha256)).toBe(true);
});
for(const width of [1440,390])test(`239 OLD exterior and retained interior load at ${width}px`,async({page})=>{
 test.setTimeout(120000);await mkdir('result/blender/stage239/browser',{recursive:true});await page.setViewportSize({width,height:width===390?844:1000});const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('/#OLD');await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-OLD',{timeout:60000});await page.locator('#detail-view').click();await expect(page.locator('#view-mode')).toHaveText('Clare Market');await page.screenshot({path:`result/blender/stage239/browser/old-${width}.png`});await page.locator('#interior-view').click();await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','interior-OLD',{timeout:60000});await expect(page.locator('#fallback')).toBeHidden();expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);expect(errors).toEqual([]);
});
test('overview and close view contain the same continuous Clare relief surfaces',async({page})=>{
 test.setTimeout(120000);
 const release=await read('dist/release.json'),audit=await read('result/blender/old-clare239/audit.json');
 const moduleUrl=Object.keys(release.assets).find(p=>/^\/assets\/viewer-.*\.js$/.test(p));
 const frame={...audit.frame,centres:audit.changes.map(c=>c.centre)};
 const html=`<style>html,body{margin:0}#canvas{width:1200px;height:900px}#labels{display:none}</style><div id="canvas"></div><div id="labels"></div><script type="module">
 import {CampusViewer} from '${moduleUrl}';
 const catalogue=await(await fetch('/models/catalogue.json')).json(),frame=${JSON.stringify(frame)};
 const viewer=new CampusViewer(document.querySelector('#canvas'),document.querySelector('#labels'),catalogue.buildings,()=>{},()=>{throw Error('Context lost')},()=>{},catalogue.sourceModelSha256);
 const collect=group=>{viewer.scene.updateMatrixWorld(true);const positions=[];let triangles=0;group.traverse(o=>{if(!o.geometry)return;const g=o.geometry,p=g.attributes.position,idx=g.index,n=idx?idx.count:p.count;for(let i=0;i<n;i+=3){const tri=[];for(let k=0;k<3;k++){const j=idx?idx.getX(i+k):i+k;const v=viewer.camera.position.clone().fromBufferAttribute(p,j).applyMatrix4(o.matrixWorld);tri.push(v.toArray());}const local=tri.map(p=>{const d=[p[0]-frame.origin[0],-p[2]-frame.origin[1]];return [d[0]*frame.right[0]+d[1]*frame.right[1],d[0]*frame.outward[0]+d[1]*frame.outward[1],p[1]];});if(frame.centres.some(c=>local.every(p=>Math.abs(p[0]-c)<1.17&&p[1]>.06&&p[1]<.225&&p[2]>5.34&&p[2]<6.33))){positions.push(...tri);triangles++;}}});positions.sort((a,b)=>a[0]-b[0]||a[1]-b[1]||a[2]-b[2]);return {positions,triangles};};
 await viewer.load();await viewer.environmentReady;const campus=collect(viewer.groups.get('OLD'));const b=catalogue.buildings.find(r=>r.code==='OLD');viewer.select(b);await viewer.upgradeModel(b,'exterior');viewer.transition=null;const detail=collect(viewer.activeDetail.group);viewer.dispose();window.parity={campus,detail};
 </script>`;
 await page.route('**/__relief239-parity',route=>route.fulfill({contentType:'text/html',body:html}));await page.goto('/__relief239-parity');await page.waitForFunction(()=>window.parity,null,{timeout:60000});const result=await page.evaluate(()=>window.parity);
 expect(result.campus.triangles).toBeGreaterThanOrEqual(95552);expect(result.detail.triangles).toBe(result.campus.triangles);expect(result.campus.positions).toHaveLength(result.detail.positions.length);
 // Draco may reorder equal-coordinate vertices independently. Compare both
 // point sets spatially rather than pairing a lexicographic tie arbitrarily.
 const maximumDistance=(source,target)=>{
  const cell=.0002,grid=new Map(),seen=new Set(),cache=new Map();
  const key=p=>p.map(v=>Math.floor(v/cell)).join(',');
  for(const p of target){const exact=p.join(',');if(seen.has(exact))continue;seen.add(exact);const k=key(p);if(!grid.has(k))grid.set(k,[]);grid.get(k).push(p);}
  let maximum=0;
  for(const p of source){const exact=p.join(',');if(cache.has(exact))continue;const c=p.map(v=>Math.floor(v/cell));let nearest=Infinity;
   for(let x=-1;x<=1;x++)for(let y=-1;y<=1;y++)for(let z=-1;z<=1;z++)for(const q of grid.get([c[0]+x,c[1]+y,c[2]+z].join(','))||[])nearest=Math.min(nearest,Math.hypot(p[0]-q[0],p[1]-q[1],p[2]-q[2]));
   cache.set(exact,nearest);maximum=Math.max(maximum,nearest);
  }
  return maximum;
 };
 const error=Math.max(maximumDistance(result.campus.positions,result.detail.positions),maximumDistance(result.detail.positions,result.campus.positions));expect(error).toBeLessThan(.0001);
 await writeFile('result/blender/stage239/overview-detail-parity.json',JSON.stringify({regionTriangles:result.campus.triangles,worldPositionMaximumDifferenceM:error,comparison:"bidirectional nearest world positions independent of Draco ordering",actualBuiltViewerAndBothProductionGlbs:true},null,2)+'\n');
});
