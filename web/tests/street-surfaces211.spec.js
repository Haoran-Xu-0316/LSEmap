import {test,expect} from '@playwright/test';
import {readFile,mkdir,writeFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
const read=async p=>JSON.parse(await readFile(p,'utf8'));

test('street edition211 preserves every building and independent room asset',async()=>{
 const before=await read('result/blender/stage211/catalogue-before.json'),current=await read('web/public/models/catalogue.json');
 const saved=await read('result/blender/stage211/reopened-verification.json'),ground=await read('result/blender/street-surfaces211/saved-ground-audit.json'),coverage=await read('result/blender/street-surfaces211/coverage-verification.json');
 expect(current.version).toBe('211');expect(saved.originalsVerified).toBe(7412);expect(saved.addedObjectsVerified).toBe(9);expect(saved.completeModelReopened).toBe(true);
 expect(createHash('sha256').update(await readFile('result/blender/LSE_campus_detailed_v211.blend')).digest('hex')).toBe(current.sourceModelSha256);
 for(const building of current.buildings){const old=before.buildings.find(b=>b.code===building.code);for(const key of ['detailedExterior','detailedInterior','interiorSpaces','interiorView'])expect(building[key]??null,building.code+key).toEqual(old[key]??null);}
 expect(ground.mappedWalkingProbes).toBe(246);expect(ground.misplacedAsphaltAbsentAtEveryProbe).toBe(true);expect(ground.originalMaterialsVerified).toBe(1918);expect(coverage.nativeMeshCoverageVerified).toBe(true);
 const park=await read('result/blender/park-boundary211/reopened-verification.json'),budget=(await read('result/blender/park-boundary211/audit.json')).geometryBudget;
 expect(park.all16MappedBoundarySegmentsPresent).toBe(true);expect(budget.triangles).toBeLessThan(40000);
});

test('production map shows repaired streets and open park entrances on desktop and mobile',async({page})=>{
 test.setTimeout(150000);const directory='result/blender/stage211/browser';await mkdir(directory,{recursive:true});
 const release=await read('dist/release.json'),module=Object.keys(release.assets).find(p=>/\/viewer-[\w-]+\.js$/.test(p));
 const plan=await read('result/blender/street-surfaces211/surface-plan.json');
 const probes=plan.areas.flatMap(area=>area.tiles.filter((_,i)=>i%Math.ceil(area.tiles.length/12)===0).map(tile=>{
  const tri=tile.triangles[0];return{x:tri.reduce((n,p)=>n+p[0],0)/3,z:-tri.reduce((n,p)=>n+p[1],0)/3};
 }));
 const html=`<!doctype html><style>html,body{margin:0}#scene{width:100vw;height:100vh}#labels{display:none}</style><div id="scene"></div><div id="labels"></div><script type="module">
 import {CampusViewer}from '${module}';const catalogue=await(await fetch('/models/catalogue.json')).json();
 const viewer=new CampusViewer(document.querySelector('#scene'),document.querySelector('#labels'),catalogue.buildings,()=>{},()=>{throw Error('Context lost')},()=>{},catalogue.sourceModelSha256);
 window.viewer=viewer;await viewer.load();await viewer.environmentReady;cancelAnimationFrame(viewer.frame);viewer.controls.enableDamping=false;viewer.home(false);viewer.toggleContext(true);viewer.transition=null;viewer.scene.updateMatrixWorld(true);window.ready=true;
 </script>`;
 await page.route('**/__streets211',r=>r.fulfill({contentType:'text/html',body:html}));const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('/__streets211');await page.waitForFunction(()=>window.ready,null,{timeout:80000});
 const hits=await page.evaluate(probes=>probes.map(p=>{
  viewer.raycaster.set(viewer.camera.position.clone().set(p.x,.3,p.z),viewer.camera.position.clone().set(0,-1,0));
  const hit=viewer.raycaster.intersectObject(viewer.campus,true)[0];const m=hit?(Array.isArray(hit.object.material)?hit.object.material[hit.face.materialIndex]:hit.object.material):null;
  return{point:p,height:hit?.point.y,material:m?.name};
 }),probes);
 for(const hit of hits){expect(hit.height).toBeCloseTo(.024,4);expect(hit.material).toContain('SITE211_SITE_V47_yorkstone');}
 const frames=[];
 for(const width of [1440,390]){await page.setViewportSize({width,height:960});
  for(const view of ['sheffield','strand','park']){
   const info=await page.evaluate(view=>{
    viewer.resize();const views={sheffield:[[-45,10,35],[-48,1,-12]],strand:[[166,55,228],[192,.1,163]],park:[[-28,4,-277],[-20.4,.8,-256.3]]};
    const [position,target]=views[view];viewer.camera.fov=48;viewer.updateCameraProjection();viewer.moveCamera(viewer.camera.position.clone().fromArray(position),viewer.controls.target.clone().fromArray(target),false);viewer.transition=null;viewer.controls.update();viewer.camera.updateMatrixWorld();viewer.renderPipeline.resetHistory();viewer.renderPipeline.render({moving:true});viewer.renderer.getContext().finish();
    const times=[];viewer.renderer.info.autoReset=false;let budget;for(let i=0;i<7;i++){viewer.camera.position.x+=.025;viewer.camera.lookAt(viewer.controls.target);viewer.camera.updateMatrixWorld();viewer.renderer.info.reset();const t=performance.now();viewer.renderPipeline.render({moving:true});viewer.renderer.getContext().finish();times.push(performance.now()-t);budget={calls:viewer.renderer.info.render.calls,triangles:viewer.renderer.info.render.triangles};}viewer.renderer.info.autoReset=true;viewer.renderPipeline.render();
    return{medianFrameMs:times.sort((a,b)=>a-b)[3],...budget};
   },view);expect(info.medianFrameMs).toBeLessThan(80);await page.locator('canvas').screenshot({path:directory+'/'+view+'-'+width+'.png'});frames.push({view,width,...info});
  }
 }
 expect(errors).toEqual([]);await writeFile(directory+'/acceptance.json',JSON.stringify({hits,frames,errors},null,2)+'\n');await page.evaluate(()=>viewer.dispose());
});
