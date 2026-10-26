import {test,expect} from '@playwright/test';
import {readFile,writeFile} from 'node:fs/promises';

const folder='result/web/release269';
const read=async path=>JSON.parse(await readFile(path,'utf8'));

async function prepareViewer(page){
 const release=await read('dist/release.json');
 const module=Object.keys(release.assets).find(path=>/^\/assets\/viewer-.*\.js$/.test(path));
 expect(module).toBeTruthy();
 const html=`<!doctype html><link rel="icon" href="data:,"><style>body{margin:0}#stage{width:1000px;height:800px}</style><div id="stage"></div><div id="labels"></div><script type="module">
 import {CampusViewer} from '${module}';
 const c=await(await fetch('/models/catalogue.json')).json();if(c.version!=='269')throw Error('Wrong campus');
 const v=new CampusViewer(document.querySelector('#stage'),document.querySelector('#labels'),c.buildings,()=>{},()=>{throw Error('Context lost')},()=>{},c.sourceModelSha256);
 window.viewer=v;window.catalogue=c;v.loadCampusExteriors=async()=>{};await v.load();await v.environmentReady;
 await v.loadExterior(c.buildings.find(b=>b.code==='MAR'));window.ready=true;
 </script>`;
 await page.route('**/__campus269',route=>route.fulfill({contentType:'text/html',body:html}));
 await page.goto('/__campus269');await page.waitForFunction(()=>window.ready,null,{timeout:60000});
}

test('new native surfaces and all three complete second-floor bores survive web export',async({page})=>{
 const probes=await read('result/blender/stage269/production-probes.json');
 const evidence=await read('result/blender/mar269-evidence.json');
 const geometry=await read('result/blender/mar269/fresh-process-verification.json');
 const stack=geometry.actualMeshProof.completeStackZ;
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 try{
  await prepareViewer(page);
  const rows=await page.evaluate(probes=>{
   const v=window.viewer;v.scene.updateMatrixWorld(true);
   const web=p=>v.controls.target.clone().set(p[0],p[2],-p[1]);const rows=[];
   for(const probe of probes){
    const roots=probe.code==='LANDSCAPE'?[['overview',v.groups.get('LANDSCAPE'),'WEB_']]:[['overview',v.groups.get('MAR'),'WEB_'],['exterior',v.exteriors.get('MAR'),'WEB_DETAIL_']];
    for(const[level,root,prefix]of roots){
     if(!root)throw Error('Missing '+probe.code+level);
     v.raycaster.set(web(probe.origin),web(probe.direction));v.raycaster.near=0;v.raycaster.far=probe.distance+.02;
     const hits=v.raycaster.intersectObject(root,true).map(h=>({distance:h.distance,material:(Array.isArray(h.object.material)?h.object.material[h.face.materialIndex]:h.object.material).name}));
     rows.push({...probe,level,expectedMaterials:probe.materials.map(m=>prefix+m),hits});
    }
   }return rows;
  },probes);
  // Presence is checked at the exact native surface. Adjacent floor finishes
  // legitimately cover structural interfaces, so first-visible-hit is not the test.
  for(const row of rows){
   expect(row.hits.some(hit=>row.expectedMaterials.includes(hit.material)&&Math.abs(hit.distance-row.distance)<.001),JSON.stringify(row)).toBeTruthy();
  }
  const shafts=evidence.confirmedGap.newSecondSourceShafts;
  const boreRows=await page.evaluate(async({shafts,stack})=>{
   const v=window.viewer,m=window.catalogue.buildings.find(b=>b.code==='MAR');
   const roots=[['overview',v.groups.get('MAR')],['exterior',v.exteriors.get('MAR')]];
   v.select(m);await v.showInterior(m);await v.upgradeModel(m,'interior');
   if(v.canvas.dataset.detailReady!=='interior-MAR')throw Error('MAR interior detail not ready');
   roots.push(['interior',v.activeDetail.group]);v.scene.updateMatrixWorld(true);
   const inside=(x,y,poly)=>{let odd=false;for(let i=0,j=poly.length-1;i<poly.length;j=i++){const a=poly[i],b=poly[j];if((a[1]>y)!==(b[1]>y)&&x<(b[0]-a[0])*(y-a[1])/(b[1]-a[1])+a[0])odd=!odd;}return odd;};
   const rows=[];
   for(const shaft of shafts){
    const poly=shaft.cutWorldXY,xs=poly.map(p=>p[0]),ys=poly.map(p=>p[1]);
    const lo=[Math.min(...xs),Math.min(...ys)],hi=[Math.max(...xs),Math.max(...ys)];let samples=0;
    for(let ix=1;ix<=5;ix++)for(let iy=1;iy<=5;iy++){
     const x=lo[0]+(hi[0]-lo[0])*ix/6,y=lo[1]+(hi[1]-lo[1])*iy/6;
     if(!inside(x,y,poly))continue;samples++;
     for(const[level,root]of roots){
      v.raycaster.set(v.controls.target.clone().set(x,stack[1]+.05,-y),v.controls.target.clone().set(0,-1,0));
      v.raycaster.near=0;v.raycaster.far=stack[1]-stack[0]+.1;
      rows.push({shaft:shaft.id,level,x,y,hits:v.raycaster.intersectObject(root,true).map(h=>({distance:h.distance,name:h.object.name}))});
     }
    }if(samples<10)throw Error('Insufficient interior bore samples');
   }return rows;
  },{shafts,stack});
  await writeFile(folder+'/geometry-diagnostic.json',JSON.stringify({rows,boreRows,errors},null,2)+'\n');
  expect(boreRows.length).toBeGreaterThan(100);
  for(const row of boreRows)expect(row.hits,JSON.stringify(row)).toEqual([]);
  expect(errors).toEqual([]);
  await writeFile(folder+'/geometry-verification.json',JSON.stringify({passed:true,nativeSurfaces:rows.length,throughBoreRays:boreRows.length,levels:['overview','exterior','interior'],errors},null,2)+'\n');
 }finally{await page.evaluate(()=>window.viewer?.dispose()).catch(()=>{});}
});

test('unrelated buildings,all35rooms and the current material maps retain their identities',async()=>{
 const before=await read(folder+'/catalogue-before.json'),current=await read('dist/models/catalogue.json');
 const priorRelease=await read(folder+'/release-before.json'),release=await read('dist/release.json');
 expect(current.version).toBe('269');expect(current.buildings.map(b=>b.code)).toEqual(before.buildings.map(b=>b.code));
 expect(current.generatedTextures).toEqual(before.generatedTextures);
 let exteriors=0,interiors=0,rooms=0,fallbacks=0;
 for(const old of before.buildings){
  const now=current.buildings.find(b=>b.code===old.code);
  if(old.detailedExterior){if(old.code==='MAR')expect(now.detailedExterior.sha256).not.toBe(old.detailedExterior.sha256);else{expect(now.detailedExterior,old.code).toEqual(old.detailedExterior);exteriors++;}}
  if(old.detailedInterior){if(old.code==='MAR')expect(now.detailedInterior.sha256).not.toBe(old.detailedInterior.sha256);else{expect(now.detailedInterior,old.code).toEqual(old.detailedInterior);interiors++;}}
  expect(now.interiorSpaces,old.code).toEqual(old.interiorSpaces);rooms+=(old.interiorSpaces??[]).length;
  const path='/models/'+old.code.toLowerCase()+'-interior.glb';
  if(old.code!=='MAR'&&priorRelease.assets[path]){expect(release.assets[path],path).toEqual(priorRelease.assets[path]);fallbacks++;}
 }
 expect(exteriors).toBe(29);expect(interiors).toBe(24);expect(rooms).toBe(35);expect(fallbacks).toBe(24);
 await writeFile(folder+'/asset-protection.json',JSON.stringify({passed:true,unrelatedExteriors:exteriors,unrelatedPublicInteriors:interiors,detachedRooms:rooms,unrelatedFallbackInteriors:fallbacks,approvedTextureIdentitiesPreserved:true},null,2)+'\n');
});
