import { test, expect } from '@playwright/test';
import { readFile, writeFile } from 'node:fs/promises';
const output='result/blender/stage248';
const read=async path=>JSON.parse(await readFile(path,'utf8'));

test('248 preserves every building and room while restoring the public court enclosure',async()=>{
  const before=await read(`${output}/catalogue-before.json`),after=await read('dist/models/catalogue.json');
  const native=await read('result/blender/court-enclosure248/full-native-verification.json');
  expect(after.version).toBe('248');expect(native.completeNativeReopened).toBe(true);
  expect(native.originalObjectsVerified).toBe(8634);expect(native.originalMaterialGraphsVerified).toBe(2339);
  expect(native.protectedRooms).toBe(35);expect(native.fullEntryCorridorSavedFacesChecked).toBeGreaterThan(10000);
  expect(native.fullEntryCorridorSizeM).toEqual([6,.6,1.9]);
  let exteriors=0,interiors=0,rooms=0;
  for(const original of before.buildings){
    const current=after.buildings.find(b=>b.code===original.code);
    if(original.detailedExterior){expect(current.detailedExterior.sha256,original.code).toBe(original.detailedExterior.sha256);exteriors++;}
    if(original.detailedInterior){expect(current.detailedInterior.sha256,original.code).toBe(original.detailedInterior.sha256);interiors++;}
    for(const room of original.interiorSpaces??[]){expect(current.interiorSpaces.find(r=>r.id===room.id).detailedInterior.sha256,room.id).toBe(room.detailedInterior.sha256);rooms++;}
  }
  expect([exteriors,interiors,rooms]).toEqual([30,25,35]);
  const previous=await read(`${output}/release-before.json`),current=await read('dist/release.json');
  const fallbacks=Object.keys(previous.assets).filter(path=>/^\/models\/[a-z0-9]+-interior\.glb$/.test(path));
  for(const path of fallbacks)expect(current.assets[path].sha256,path).toBe(previous.assets[path].sha256);
  expect(fallbacks).toHaveLength(25);
  await writeFile(`${output}/asset-scope.json`,JSON.stringify({exteriors,interiors,rooms,fallbacks:fallbacks.length,changed:'Public court enclosure only'},null,2)+'\n');
});

test('production Draco keeps the fence perforated and the mapped entry geometrically clear',async({page})=>{
  const errors=[];page.on('pageerror',error=>errors.push(error.message));
  const release=await read('dist/release.json'),module=Object.keys(release.assets).find(p=>/^\/assets\/viewer-.*\.js$/.test(p));
  const plan=await read('result/blender/court-enclosure248/plan.json');
  const html=`<style>body{margin:0}#stage{width:960px;height:768px}#labels{display:none}</style><div id="stage"></div><div id="labels"></div><script type="module">
    import{CampusViewer}from'${module}';
    const catalogue=await(await fetch('/models/catalogue.json')).json();
    const viewer=new CampusViewer(document.querySelector('#stage'),document.querySelector('#labels'),catalogue.buildings,()=>{},()=>{throw Error('Context lost')},()=>{},catalogue.sourceModelSha256);
    window.viewer=viewer;viewer.loadCampusExteriors=async()=>{};await viewer.load();await viewer.environmentReady;
    cancelAnimationFrame(viewer.frame);viewer.transition=null;window.ready=true;
  </script>`;
  try{
    await page.route('**/__court248',route=>route.fulfill({contentType:'text/html',body:html}));
    await page.goto('/__court248');await page.waitForFunction(()=>window.ready,null,{timeout:60000});
    const proof=await page.evaluate(plan=>{
      const v=window.viewer;v.scene.updateMatrixWorld(true);let materials=0,triangles=0;const panels=[];
      v.groups.get('LANDSCAPE').traverse(object=>{
        if(!object.isMesh)return;
        const meshMaterials=Array.isArray(object.material)?object.material:[object.material];
        for(let index=0;index<meshMaterials.length;index++){
          const material=meshMaterials[index];if(!material.userData.wireMesh)continue;
          materials++;const groups=Array.isArray(object.material)?object.geometry.groups.filter(g=>g.materialIndex===index):[{start:0,count:object.geometry.index.count}];
          for(const group of groups){triangles+=group.count/3;for(let at=group.start;at<group.start+group.count;at+=3){
            const points=[];
            for(let i=0;i<3;i++){
              const vertex=object.geometry.index.getX(at+i),position=object.geometry.attributes.position;
              const point=v.controls.target.clone().set(position.getX(vertex),position.getY(vertex),position.getZ(vertex));object.localToWorld(point);points.push([point.x,-point.z,point.y]);
            }
            panels.push(points);
          }}
          if(!material.transparent||material.opacity!==1||material.depthWrite||!material.forceSinglePass||material.metalness!==0)throw Error('Incorrect wire material');
          if(!material.customProgramCacheKey().includes('filtered-wire-grid1'))throw Error('Missing filtered coverage');
          if(!object.geometry.attributes.uv)throw Error('Missing metric UV');
        }
      });
      v.moveCamera(v.camera.position.clone().set(-33,2.3,-102),v.controls.target.clone().set(-24,1.6,-118),false);
      v.renderPipeline.render({moving:false,stabilize:false});v.renderer.getContext().finish();
      return{materials,triangles,panels,source:'Actual production Draco-decoded site geometry and bundled renderer'};
    },plan);
    expect(proof.materials).toBe(1);expect(proof.triangles).toBe(10);
    const gate=plan.plan.entranceConservativeReservation.mappedCentre;
    // No decoded panel edge enters the conservative opening at its two source sides.
    const distance=(p,a,b)=>{const x=b[0]-a[0],y=b[1]-a[1],t=x*x+y*y>0?Math.max(0,Math.min(1,((p[0]-a[0])*x+(p[1]-a[1])*y)/(x*x+y*y))):0;return Math.hypot(p[0]-a[0]-t*x,p[1]-a[1]-t*y);};
    const gateDistances=proof.panels.map(points=>Math.min(...points.map((a,i)=>distance(gate,a,points[(i+1)%points.length]))));
    expect(Math.min(...gateDistances)).toBeGreaterThan(1.99);
    await writeFile(`${output}/production-enclosure.json`,JSON.stringify({...proof,minimumPanelDistanceFromMappedGateM:Math.min(...gateDistances)},null,2)+'\n');
    await page.locator('canvas').screenshot({path:`${output}/production-court-entry.png`});expect(errors).toEqual([]);
  }finally{await page.evaluate(()=>window.viewer?.dispose()).catch(()=>{});}
});
