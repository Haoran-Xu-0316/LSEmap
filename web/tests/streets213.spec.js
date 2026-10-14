import {test,expect} from '@playwright/test';
import {readFile,mkdir,writeFile} from 'node:fs/promises';
const read=async p=>JSON.parse(await readFile(p,'utf8'));

test('street edition213 preserves every exterior and independent room identity',async()=>{
 const before=await read('result/blender/stage213/catalogue-before.json'),current=await read('web/public/models/catalogue.json'),saved=await read('result/blender/stage213/reopened-verification.json'),coverage=await read('result/blender/stage213/street-coverage.json');
 expect(current.version).toBe('213');expect(saved.completeModelReopened).toBe(true);expect(saved.originalsVerified).toBe(7437);expect(saved.addedObjectsVerified).toBe(9);expect(coverage.nativeMeshCoverageVerified).toBe(true);expect(coverage.sourceWays).toBe(218);
 for(const building of current.buildings){const old=before.buildings.find(b=>b.code===building.code);expect(building.detailedExterior??null,building.code).toEqual(old.detailedExterior??null);expect(building.interiorSpaces??null,building.code).toEqual(old.interiorSpaces??null);if(building.code==='LRB')expect(building.detailedInterior.url).not.toBe(old.detailedInterior.url);else expect(building.detailedInterior??null,building.code).toEqual(old.detailedInterior??null);}
});

test('production street surfaces render with route finishes on desktop and mobile',async({page})=>{
 test.setTimeout(150000);const dir='result/blender/stage213/browser';await mkdir(dir,{recursive:true});
 const release=await read('dist/release.json'),module=Object.keys(release.assets).find(p=>/\/viewer-[\w-]+\.js$/.test(p));
 const plan=await read('result/blender/streets213/plan.json');
 const selected=['Kingsway','Carey Street','Portugal Street','Grange Court'].map(name=>plan.regions.filter(r=>r.name===name&&r.body.length&&r.areaM2>1).sort((a,b)=>Math.hypot(a.origin[0]+45,a.origin[1]+55)-Math.hypot(b.origin[0]+45,b.origin[1]+55))[0]);
 const probes=selected.map(r=>{const t=r.body.slice().sort((a,b)=>Math.abs((b[1][0]-b[0][0])*(b[2][1]-b[0][1])-(b[1][1]-b[0][1])*(b[2][0]-b[0][0]))-Math.abs((a[1][0]-a[0][0])*(a[2][1]-a[0][1])-(a[1][1]-a[0][1])*(a[2][0]-a[0][0])))[0];return{name:r.name,kind:r.kind,x:t.reduce((v,p)=>v+p[0],0)/3,z:-t.reduce((v,p)=>v+p[1],0)/3};});
 const html=`<!doctype html><style>html,body{margin:0}#scene{width:100vw;height:100vh}#labels{display:none}</style><div id="scene"></div><div id="labels"></div><script type="module">import{CampusViewer}from'${module}';const c=await(await fetch('/models/catalogue.json')).json();const v=new CampusViewer(document.querySelector('#scene'),document.querySelector('#labels'),c.buildings,()=>{},()=>{throw Error('Context lost')},()=>{},c.sourceModelSha256);window.viewer=v;await v.load();await v.environmentReady;cancelAnimationFrame(v.frame);v.controls.enableDamping=false;v.home(false);v.toggleContext(true);v.transition=null;v.scene.updateMatrixWorld(true);window.ready=true;</script>`;
 await page.route('**/__streets213',r=>r.fulfill({contentType:'text/html',body:html}));const errors=[];page.on('pageerror',e=>errors.push(e.message));await page.goto('/__streets213');await page.waitForFunction(()=>window.ready,null,{timeout:90000});
 const hits=await page.evaluate(probes=>probes.map(p=>{viewer.raycaster.set(viewer.camera.position.clone().set(p.x,.1,p.z),viewer.camera.position.clone().set(0,-1,0));const h=viewer.raycaster.intersectObject(viewer.campus,true)[0];const m=h?(Array.isArray(h.object.material)?h.object.material[h.face.materialIndex]:h.object.material):null;return{...p,height:h?.point.y,material:m?.name,detail:m?.userData?.surfaceDetail};}),probes);
 for(const h of hits){expect(h.height).toBeCloseTo(.024,4);if(h.kind==='asphalt')expect(h.material).toMatch(/asphalt/i);else{expect(h.material).toContain('SITE213_SITE_V47_slab');expect(h.detail.kind).toBe('brick');expect(h.detail.brickWidth).toBeCloseTo(.9,3);}}
 const frames=[];
 for(const width of[1440,390]){await page.setViewportSize({width,height:960});for(const p of probes){const info=await page.evaluate(p=>{viewer.resize();viewer.camera.fov=48;viewer.updateCameraProjection();viewer.moveCamera(viewer.camera.position.clone().set(p.x+16,12,p.z+20),viewer.controls.target.clone().set(p.x,.1,p.z),false);viewer.transition=null;viewer.controls.update();viewer.camera.updateMatrixWorld();viewer.renderPipeline.resetHistory();viewer.renderPipeline.render({moving:true});viewer.renderer.getContext().finish();return{calls:viewer.renderer.info.render.calls,triangles:viewer.renderer.info.render.triangles};},p);await page.locator('canvas').screenshot({path:dir+'/'+p.name.toLowerCase().replaceAll(' ','-')+'-'+width+'.png'});frames.push({width,name:p.name,...info});}}
 expect(errors).toEqual([]);await writeFile(dir+'/acceptance.json',JSON.stringify({hits,frames,errors},null,2)+'\n');await page.evaluate(()=>viewer.dispose());
});

test('library public interior opens after guard repair',async({page})=>{
 await page.goto('/#LRB');await page.waitForFunction(()=>document.querySelector('canvas')?.dataset.detailReady==='exterior-LRB',null,{timeout:60000});await page.locator('#interior-view').click();await page.waitForFunction(()=>document.querySelector('canvas')?.dataset.detailReady?.startsWith('interior-LRB'),null,{timeout:60000});expect(await page.locator('#fallback').isVisible()).toBe(false);await page.screenshot({path:'result/blender/stage213/browser/library-interior.png'});
});
