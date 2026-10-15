import {test,expect} from '@playwright/test';
import {readFile,mkdir,writeFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
const read=async p=>JSON.parse(await readFile(p,'utf8'));
const proof='result/blender/streets215';

test('street changes preserve every building asset and reduce asphalt transfer',async()=>{
 const baseline=await read(proof+'/baseline.json');
 for(const [path,sha] of Object.entries(baseline.models).filter(([p])=>!p.endsWith('/campus.glb')&&!p.endsWith('/catalogue.json')))expect(createHash('sha256').update(await readFile(path)).digest('hex'),path).toBe(sha);
 const native=await read(proof+'/verification.json');expect(native.nativeCoverageVerified).toBe(true);expect(native.removedInternalBandAreaM2).toBeGreaterThan(40);expect(native.sourceWays).toBe(218);expect(native.originalMaterialNodesVerified).toBe(1958);const saved=await read('result/blender/stage215/reopened-verification.json');expect(saved.originalsVerified).toBe(7459);expect(saved.addedObjectsVerified).toBe(2);expect(saved.completeModelReopened).toBe(true);
 const manifest=await read('web/public/environment/sources.json');
 const asphalt=manifest.assets.filter(a=>a.path.includes('/asphalt-'));
 expect(asphalt).toHaveLength(2);expect(asphalt.reduce((s,a)=>s+a.bytes,0)).toBeLessThan(baseline.asphaltBytes/2);
 for(const a of asphalt){expect(a.source).toBe('https://polyhaven.com/a/clean_asphalt');expect(a.repeatMetres).toBe(2.1);expect(a.license).toBe('CC0-1.0');expect(createHash('sha256').update(await readFile('web/public'+a.path)).digest('hex')).toBe(a.sha256);}
});

test('production street views show ground surfaces on desktop and mobile without shader errors',async({page})=>{
 test.setTimeout(150000);await mkdir(proof+'/browser',{recursive:true});
 const release=await read('dist/release.json'),module=Object.keys(release.assets).find(p=>/\/viewer-[\w-]+\.js$/.test(p));
 const html=`<!doctype html><style>html,body{margin:0}#scene{width:100vw;height:100vh}#labels{display:none}</style><div id="scene"></div><div id="labels"></div><script type="module">import{CampusViewer}from'${module}';const c=await(await fetch('/models/catalogue.json')).json();window.viewer=new CampusViewer(document.querySelector('#scene'),document.querySelector('#labels'),c.buildings,()=>{},()=>{throw Error('Context lost')},()=>{},c.sourceModelSha256);await viewer.load();await viewer.environmentReady;await new Promise(r=>setTimeout(r,1200));cancelAnimationFrame(viewer.frame);viewer.controls.enableDamping=false;viewer.home(false);viewer.toggleContext(true);viewer.transition=null;viewer.scene.updateMatrixWorld(true);window.ready=true;</script>`;
 await page.route('**/__streets215',r=>r.fulfill({contentType:'text/html',body:html}));
 const errors=[];page.on('pageerror',e=>errors.push(e.message));page.on('console',m=>{if(m.type()==='error')errors.push(m.text());});
 await page.goto('/__streets215');await page.waitForFunction(()=>window.ready,null,{timeout:90000});
 await expect(page.locator('canvas')).toHaveAttribute('data-ground-relief-ready','true');
 const views=[{name:'houghton',target:[10,.05,70],position:[2,14,86],material:/Houghton/},{name:'sheffield',target:[-54,.05,13],position:[-58,14,30],material:/SITE_V47_slab/},{name:'portugal',target:[-64,.03,36],position:[-78,16,41],material:/asphalt/},{name:'portugal-edge',target:[-2.599731,.024,-2.034429],position:[-7.599731,5,-7.034429],material:/flush_edge_courses/},{name:'portugal-join',target:[-3.473047974,.024,-1.89008],position:[-8.473047974,5,-6.89008],material:/footway_courses/}];
 const records=[];
 for(const width of[1440,390]){await page.setViewportSize({width,height:960});for(const v of views){
  const result=await page.evaluate(v=>{const w=viewer;w.resize();w.transition=null;w.camera.position.fromArray(v.position);w.controls.target.fromArray(v.target);w.controls.update();w.camera.updateMatrixWorld();w.renderPipeline.resetHistory();for(let i=0;i<4;i++)w.renderPipeline.render({moving:false});const renderer=w.renderer;renderer.info.autoReset=false;renderer.info.reset();w.renderPipeline.render({moving:true});const calls=renderer.info.render.calls,triangles=renderer.info.render.triangles;renderer.info.autoReset=true;renderer.getContext().finish();w.raycaster.set(w.camera.position.clone().set(v.target[0],3,v.target[2]),w.camera.position.clone().set(0,-1,0));const hit=w.raycaster.intersectObject(w.campus,true)[0];const material=hit?(Array.isArray(hit.object.material)?hit.object.material[hit.face.materialIndex]:hit.object.material):null;w.raycaster.setFromCamera({x:0,y:0},w.camera);const centreHit=w.raycaster.intersectObject(w.campus,true)[0];const targetError=centreHit?.point.distanceTo(w.controls.target);return{targetError,calls,triangles,groundHeight:hit?.point.y,material:material?.name,geometries:renderer.info.memory.geometries,textures:renderer.info.memory.textures};},v);
  expect(result.targetError,v.name+' centre ray sees the selected pavement').toBeLessThan(.1);expect(result.groundHeight).toBeGreaterThan(.02);expect(result.groundHeight).toBeLessThan(.06);expect(result.material).toMatch(v.material);expect(result.triangles).toBeGreaterThan(1000);
  await page.locator('canvas').screenshot({path:proof+'/browser/'+v.name+'-'+width+'.png'});records.push({width,name:v.name,...result});
 }}
 // A short real orbit checks shader stability during navigation, rather than
 // repeatedly redrawing a stationary frame or asserting a hardware-specific FPS.
 const orbit=await page.evaluate(()=>{const w=viewer,values=[],target=w.controls.target.clone(),start=w.camera.position.clone().sub(target);for(let i=0;i<36;i++){const a=i*.006,c=Math.cos(a),s=Math.sin(a);w.camera.position.set(target.x+start.x*c-start.z*s,target.y+start.y,target.z+start.x*s+start.z*c);w.camera.lookAt(target);w.camera.updateMatrixWorld();const begin=performance.now();w.renderPipeline.render({moving:true});w.renderer.getContext().finish();values.push(performance.now()-begin);}values.sort((a,b)=>a-b);return{frames:values.length,medianFrameMs:values[18],p95FrameMs:values[34],textures:w.renderer.info.memory.textures};});
 expect(errors).toEqual([]);await writeFile(proof+'/browser/acceptance.json',JSON.stringify({records,orbit,errors},null,2)+'\n');await page.evaluate(()=>viewer.dispose());
});
