import {test,expect} from '@playwright/test';
import {readFile,mkdir} from 'node:fs/promises';
import {galleryRendererSignature} from '../tools/gallery_signature.mjs';
const read=async p=>JSON.parse(await readFile(p,'utf8'));
test('238 changes only the reviewed PEL exterior and preserves every room',async()=>{
 const before=await read('result/blender/stage238/catalogue-before.json'),after=await read('dist/models/catalogue.json');
 const native=await read('result/blender/stage238/native-verification.json');
 const entry=await read('result/blender/stage238/entry-geometry-verification.json');
 expect(after.version).toBe('238');expect(native.originalObjectsVerified).toBe(8586);expect(native.originalMaterialNodesVerified).toBe(2327);expect(native.originalMeshNormalsVerified).toBe(8349);expect([native.sourceRoomsVerified,native.sourceRoomObjectsVerified]).toEqual([35,1485]);
 expect(entry.revolvingAndLseLogoOnSameLeftSide).toBe(true);expect(entry.sideDoorHandleOnRight).toBe(true);expect(entry.curvedGlassToCentralFrameClearanceM).toBeGreaterThan(.15);expect(entry.entireRevolvingProjectionBackedByRetainedOpaqueRearPane).toBe(true);
 let rooms=0,interiors=0,exteriors=0;
 for(const old of before.buildings){const current=after.buildings.find(b=>b.code===old.code);
  if(old.detailedExterior){exteriors++;if(old.code==='PEL'){expect(current.detailedExterior.sha256).not.toBe(old.detailedExterior.sha256);expect(current.detailedExterior.triangles).toBe(old.detailedExterior.triangles);expect(current.detailedExterior.bounds).toEqual(old.detailedExterior.bounds);}else expect(current.detailedExterior.sha256,old.code).toBe(old.detailedExterior.sha256);}
  if(old.detailedInterior){interiors++;expect(current.detailedInterior.sha256,old.code).toBe(old.detailedInterior.sha256);}
  for(const room of old.interiorSpaces||[]){rooms++;expect(current.interiorSpaces.find(r=>r.id===room.id).detailedInterior.sha256,room.id).toBe(room.detailedInterior.sha256);}
 }
 expect([exteriors,interiors,rooms]).toEqual([30,25,35]);
 const gallery=await read('dist/gallery-manifest.json');expect(gallery.images).toHaveLength(194);expect(gallery.rendererSha256).toBe(await galleryRendererSignature());expect(gallery.images.every(r=>r.sourceModelSha256===after.sourceModelSha256)).toBe(true);
});
for(const width of [1440,390])test(`238 PEL entrance and retained studio load at ${width}px`,async({page})=>{
 test.setTimeout(120000);await mkdir('result/blender/stage238/browser',{recursive:true});await page.setViewportSize({width,height:width===390?844:1000});const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('/#PEL');await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-PEL',{timeout:60000});await page.locator('#detail-view').click();await expect(page.locator('#view-mode')).toHaveText('入口细节');await page.screenshot({path:`result/blender/stage238/browser/pel-${width}.png`});await page.locator('#interior-view').click();await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','interior-PEL',{timeout:60000});await expect(page.locator('#fallback')).toBeHidden();expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);expect(errors).toEqual([]);
});

test('overview and close view decode the same corrected revolving entrance',async({page})=>{
 test.setTimeout(120000);
 const release=await read('dist/release.json');const moduleUrl=Object.keys(release.assets).find(p=>/^\/assets\/viewer-.*\.js$/.test(p));
 const html=`<style>html,body{margin:0}#canvas{width:1200px;height:900px}#labels{display:none}</style><div id="canvas"></div><div id="labels"></div><script type="module">
 import {CampusViewer} from '${moduleUrl}';
 const catalogue=await(await fetch('/models/catalogue.json')).json();
 const viewer=new CampusViewer(document.querySelector('#canvas'),document.querySelector('#labels'),catalogue.buildings,()=>{},()=>{throw Error('Context lost')},()=>{},catalogue.sourceModelSha256);
 const collect=group=>{viewer.scene.updateMatrixWorld(true);const positions=[],materials=[];let triangles=0;group.traverse(o=>{if(!o.geometry)return;const m=Array.isArray(o.material)?o.material[0]:o.material;if(!m.name.includes('PEL238_revolving_glass'))return;materials.push({opacity:m.opacity,metalness:m.metalness,role:m.userData.webSurfaceRole});const g=o.geometry,p=g.attributes.position,idx=g.index;const count=idx?idx.count:p.count;triangles+=count/3;for(let i=0;i<count;i++){const j=idx?idx.getX(i):i;const v=viewer.camera.position.clone().fromBufferAttribute(p,j).applyMatrix4(o.matrixWorld);positions.push(v.toArray());}});positions.sort((a,b)=>a[0]-b[0]||a[1]-b[1]||a[2]-b[2]);return {positions,triangles,materials};};
 await viewer.load();await viewer.environmentReady;const campus=collect(viewer.groups.get('PEL'));const b=catalogue.buildings.find(r=>r.code==='PEL');viewer.select(b);await viewer.upgradeModel(b,'exterior');viewer.transition=null;const detail=collect(viewer.activeDetail.group);viewer.dispose();window.parity={campus,detail};
 </script>`;
 await page.route('**/__entry238-parity',route=>route.fulfill({contentType:'text/html',body:html}));await page.goto('/__entry238-parity');await page.waitForFunction(()=>window.parity,null,{timeout:60000});const result=await page.evaluate(()=>window.parity);
 expect(result.campus.triangles).toBe(40);expect(result.detail.triangles).toBe(40);expect(result.campus.materials).toEqual(result.detail.materials);expect(result.campus.materials[0].opacity).toBeCloseTo(.68,5);expect(result.campus.materials[0].role).toBe('glazing');expect(result.campus.positions).toHaveLength(result.detail.positions.length);
 let error=0;for(let i=0;i<result.campus.positions.length;i++)for(let k=0;k<3;k++)error=Math.max(error,Math.abs(result.campus.positions[i][k]-result.detail.positions[i][k]));expect(error).toBeLessThan(.0001);
 const axis=[.8186488849695666,-.5742943523473701],origin=[109.09975115798566,-88.88292847380751],width=Math.hypot(114.7297651367445-origin[0],-92.83246690353144-origin[1]);
 const mean=result.campus.positions.reduce((sum,p)=>sum+(p[0]-origin[0])*axis[0]+(-p[2]-origin[1])*axis[1]-width/2,0)/result.campus.positions.length;expect(mean).toBeCloseTo(.86,3);
 await (await import('node:fs/promises')).writeFile('result/blender/stage238/overview-detail-parity.json',JSON.stringify({triangles:40,worldPositionMaximumDifferenceM:error,meanFacadeAxisOffsetM:mean,materials:result.campus.materials,actualBuiltViewerAndBothProductionGlbs:true},null,2)+'\n');
});
