import {test,expect} from '@playwright/test';
import {readFile,writeFile} from 'node:fs/promises';
const folder='result/web/release275';
const read=async path=>JSON.parse(await readFile(path,'utf8'));
const affected=new Set(['OLD','MAR','CBG']);

async function prepareViewer(page){
 const release=await read('dist/release.json');
 const module=Object.keys(release.assets).find(p=>/^\/assets\/viewer-.*\.js$/.test(p));
 expect(module).toBeTruthy();
 const html=`<!doctype html><link rel="icon" href="data:,"><style>body{margin:0}#stage{width:1000px;height:800px}</style><div id="stage"></div><div id="labels"></div><script type="module">
 import {CampusViewer} from '${module}';const c=await(await fetch('/models/catalogue.json')).json();if(c.version!=='275')throw Error('Wrong campus');
 const v=new CampusViewer(document.querySelector('#stage'),document.querySelector('#labels'),c.buildings,()=>{},()=>{throw Error('Context lost')},()=>{},c.sourceModelSha256);
 window.viewer=v;window.catalogue=c;v.loadCampusExteriors=async()=>{};await v.load();await v.environmentReady;
 for(const code of ['OLD','MAR','CBG'])await v.loadExterior(c.buildings.find(b=>b.code===code));window.ready=true;
 </script>`;
 await page.route('**/__campus275',r=>r.fulfill({contentType:'text/html',body:html}));
 await page.goto('/__campus275');await page.waitForFunction(()=>window.ready,null,{timeout:90000});
}

test('native275 surfaces and four lift shafts survive the overview and selected models',async({page})=>{
 const probes=[...await read('result/blender/stage275/production-probes.json'),
  ...(await read('result/blender/stage269/production-probes.json')).filter(p=>p.code==='LANDSCAPE')];
 const plan=await read('result/blender/mar273/plan.json');
 expect(plan.envelopes).toHaveLength(4);
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 try{
  await prepareViewer(page);
  const rows=await page.evaluate(probes=>{
   const v=viewer,web=p=>v.controls.target.clone().set(p[0],p[2],-p[1]);v.scene.updateMatrixWorld(true);const rows=[];
   for(const code of ['SITE','LANDSCAPE','CONTEXT'])if(!v.groups.get(code)?.children.length)throw Error('Missing public setting '+code);
   for(const p of probes)for(const[level,root,prefix]of(p.code==='LANDSCAPE'?[['overview',v.groups.get(p.code),'WEB_']]:[['overview',v.groups.get(p.code),'WEB_'],['exterior',v.exteriors.get(p.code),'WEB_DETAIL_']])){
    if(!root)throw Error('Missing '+p.code+level);
    v.raycaster.set(web(p.origin),web(p.direction));v.raycaster.near=0;v.raycaster.far=p.distance+.02;
    const hits=v.raycaster.intersectObject(root,true).map(h=>({distance:h.distance,material:(Array.isArray(h.object.material)?h.object.material[h.face.materialIndex]:h.object.material).name}));
    rows.push({...p,level,expectedMaterials:p.materials.map(m=>prefix+m),hits});
   }return rows;
  },probes);
  for(const row of rows)expect(row.hits.some(h=>row.expectedMaterials.includes(h.material)&&Math.abs(h.distance-row.distance)<.001),JSON.stringify(row)).toBeTruthy();
  const boreRows=await page.evaluate(async polygons=>{
   const v=viewer,b=catalogue.buildings.find(b=>b.code==='MAR'),roots=[['overview',v.groups.get('MAR')],['exterior',v.exteriors.get('MAR')]];
   v.select(b);await v.showInterior(b);await v.upgradeModel(b,'interior');roots.push(['interior',v.activeDetail.group]);v.scene.updateMatrixWorld(true);
   const inside=(x,y,p)=>{let odd=false;for(let i=0,j=p.length-1;i<p.length;j=i++){const a=p[i],b=p[j];if((a[1]>y)!==(b[1]>y)&&x<(b[0]-a[0])*(y-a[1])/(b[1]-a[1])+a[0])odd=!odd;}return odd;};
   const rows=[];
   for(const[shaft,poly]of polygons.entries()){
    const xs=poly.map(p=>p[0]),ys=poly.map(p=>p[1]),lo=[Math.min(...xs),Math.min(...ys)],hi=[Math.max(...xs),Math.max(...ys)];let samples=0;
    for(let ix=1;ix<=5;ix++)for(let iy=1;iy<=5;iy++){
     const x=lo[0]+(hi[0]-lo[0])*ix/6,y=lo[1]+(hi[1]-lo[1])*iy/6;if(!inside(x,y,poly))continue;samples++;
     for(const[level,root]of roots){v.raycaster.set(v.controls.target.clone().set(x,21.85,-y),v.controls.target.clone().set(0,-1,0));v.raycaster.near=0;v.raycaster.far=21.85-12.4;rows.push({shaft,level,x,y,hits:v.raycaster.intersectObject(root,true).map(h=>({distance:h.distance,name:h.object.name}))});}
    }if(samples<10)throw Error('Insufficient shaft samples');
   }return rows;
  },plan.envelopes.map(s=>s.outer));
  await writeFile(folder+'/geometry-diagnostic.json',JSON.stringify({rows,boreRows,errors},null,2)+'\n');
  expect(new Set(rows.map(r=>r.code))).toEqual(new Set([...affected,'LANDSCAPE']));expect(boreRows.length).toBeGreaterThan(150);
  for(const row of boreRows)expect(row.hits,JSON.stringify(row)).toEqual([]);expect(errors).toEqual([]);
  await writeFile(folder+'/geometry-verification.json',JSON.stringify({passed:true,nativeSurfaces:rows.length,throughBoreRays:boreRows.length,shafts:4,levels:['overview','exterior','interior'],errors},null,2)+'\n');
 }finally{await page.evaluate(()=>window.viewer?.dispose()).catch(()=>{});}
});

test('unrelated buildings,all35rooms and existing textures retain exact asset identities',async()=>{
 const before=await read(folder+'/catalogue-before.json'),current=await read('dist/models/catalogue.json');
 const priorRelease=await read(folder+'/release-before.json'),release=await read('dist/release.json');
 expect(current.version).toBe('275');expect(current.buildings.map(b=>b.code)).toEqual(before.buildings.map(b=>b.code));expect(current.generatedTextures).toEqual(before.generatedTextures);
 let exteriors=0,interiors=0,rooms=0,fallbacks=0;
 for(const old of before.buildings){const now=current.buildings.find(b=>b.code===old.code);
  if(old.detailedExterior){if(affected.has(old.code))expect(now.detailedExterior.sha256).not.toBe(old.detailedExterior.sha256);else{expect(now.detailedExterior,old.code).toEqual(old.detailedExterior);exteriors++;}}
  if(old.detailedInterior&&!affected.has(old.code)){expect(now.detailedInterior,old.code).toEqual(old.detailedInterior);interiors++;}
  if(old.code==='MAR')expect(now.detailedInterior.sha256).not.toBe(old.detailedInterior.sha256);
  expect(now.interiorSpaces,old.code).toEqual(old.interiorSpaces);rooms+=(old.interiorSpaces??[]).length;
  const path='/models/'+old.code.toLowerCase()+'-interior.glb';if(!affected.has(old.code)&&priorRelease.assets[path]){expect(release.assets[path],path).toEqual(priorRelease.assets[path]);fallbacks++;}
 }
 expect(exteriors).toBe(27);expect(interiors).toBe(22);expect(rooms).toBe(35);expect(fallbacks).toBe(22);
 await writeFile(folder+'/asset-protection.json',JSON.stringify({passed:true,unrelatedExteriors:exteriors,unrelatedPublicInteriors:interiors,detachedRooms:rooms,unrelatedFallbackInteriors:fallbacks,approvedTextureIdentitiesPreserved:true},null,2)+'\n');
});
