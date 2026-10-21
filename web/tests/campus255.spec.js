import {createHash} from 'node:crypto';
import {test,expect} from '@playwright/test';
import {readFile,writeFile} from 'node:fs/promises';
const folder='result/blender/stage255';
const read=async path=>JSON.parse(await readFile(path,'utf8'));
const glb=bytes=>JSON.parse(bytes.subarray(20,20+bytes.readUInt32LE(12)).toString());

test('255 changes only the two reviewed facades and preserves interior assets and glass optics',async()=>{
 const before=await read(`${folder}/catalogue-before.json`),after=await read('dist/models/catalogue.json'),proof=await read(`${folder}/complete-protection.json`);
 expect(after.version).toBe('255');expect(proof.completeModelReopened).toBe(true);expect(proof.originalObjectsProtected).toBe(8675);expect(proof.originalMaterialGraphsProtected).toBe(2348);expect(proof.roomStudiesProtected).toBe(35);expect(proof.roomMembershipUnchanged).toBe(true);expect(proof.campusRoomMembershipUnchanged).toBe(true);
 const counts={exteriors:0,interiors:0,rooms:0,fallbacks:0};const optics=[];
 for(const old of before.buildings){
  const current=after.buildings.find(b=>b.code===old.code);
  if(old.detailedExterior){if(['SHF','COW'].includes(old.code))expect(current.detailedExterior.sha256).not.toBe(old.detailedExterior.sha256);else{expect(current.detailedExterior.sha256,old.code).toBe(old.detailedExterior.sha256);counts.exteriors++;}}
  if(old.detailedInterior){expect(current.detailedInterior.sha256,old.code).toBe(old.detailedInterior.sha256);counts.interiors++;}
  for(const room of old.interiorSpaces??[]){expect(current.interiorSpaces.find(r=>r.id===room.id).detailedInterior.sha256,room.id).toBe(room.detailedInterior.sha256);counts.rooms++;}
  if(['SHF','COW'].includes(old.code)){
   const earlier=glb(await readFile(`${folder}/${old.code.toLowerCase()}-before.glb`)),latest=glb(await readFile('dist'+current.detailedExterior.url));
   const glass=doc=>doc.materials.filter(m=>m.extras?.webSurfaceRole==='glazing').sort((a,b)=>a.name.localeCompare(b.name));
   expect(glass(earlier).length).toBeGreaterThan(0);expect(glass(latest)).toEqual(glass(earlier));optics.push({code:old.code,unchangedMaterialFamilies:glass(latest).length});
  }
 }
 const previous=await read(`${folder}/release-before.json`),release=await read('dist/release.json');
 for(const path of Object.keys(previous.assets).filter(p=>/^\/models\/[a-z0-9]+-interior\.glb$/.test(p))){expect(release.assets[path].sha256,path).toBe(previous.assets[path].sha256);counts.fallbacks++;}
 expect(counts).toEqual({exteriors:28,interiors:25,rooms:35,fallbacks:25});
 const oldGallery=await read(`${folder}/gallery-before.json`),gallery=await read('dist/gallery-manifest.json');expect(gallery.images).toHaveLength(206);
 const changed=gallery.images.filter(image=>image.sha256!==oldGallery.images.find(old=>old.name===image.name)?.sha256);
 expect(changed.map(i=>i.name)).toEqual(expect.arrayContaining(['shf-blind-wall','cow-short-street']));
 expect(changed.every(image=>image.code==='CAMPUS'||(['SHF','COW'].includes(image.code)&&image.mode==='exterior'))).toBe(true);
 await writeFile(`${folder}/asset-scope.json`,JSON.stringify({unchanged:counts,changedExteriors:['SHF','COW'],unchangedGlassFamilies:optics,changedImages:changed.map(i=>i.name)},null,2)+'\n');
});

test('overview and detail both render solid SHF blind wall and unbroken COW short-side brick',async({page})=>{
 const release=await read('dist/release.json'),module=Object.keys(release.assets).find(p=>/^\/assets\/viewer-.*\.js$/.test(p));
 const shf=await read('result/blender/shf255/audit.json');const site=await read('result/blender/site_geometry.json');
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 const html=`<!doctype html><link rel="icon" href="data:,"><style>body{margin:0}#stage{width:1000px;height:800px}#labels{display:none}</style><div id="stage"></div><div id="labels"></div><script type="module">
 import{CampusViewer}from'${module}';const cat=await(await fetch('/models/catalogue.json')).json();const v=new CampusViewer(document.querySelector('#stage'),document.querySelector('#labels'),cat.buildings,()=>{},()=>{throw Error('Context lost')},()=>{},cat.sourceModelSha256);window.viewer=v;v.loadCampusExteriors=async()=>{};await v.load();await v.environmentReady;for(const code of ['SHF','COW'])await v.loadExterior(cat.buildings.find(b=>b.code===code));window.ready=true;</script>`;
 try{
  await page.route('**/__campus255',r=>r.fulfill({contentType:'text/html',body:html}));await page.goto('/__campus255');await page.waitForFunction(()=>window.ready,null,{timeout:60000});
  const proof=await page.evaluate(({shf,site})=>{
   const v=window.viewer,vector=(x,y,z)=>v.controls.target.clone().set(x,y,z),web=p=>vector(p[0],p[2],-p[1]);v.scene.updateMatrixWorld(true);
   const hit=(root,point,direction)=>{v.raycaster.set(web(point),web(direction));v.raycaster.far=2;const h=v.raycaster.intersectObject(root,true)[0];if(!h)return null;const list=h.object.material,m=Array.isArray(list)?list[h.face.materialIndex]:list;return{material:m.name,distance:h.distance};};
   const rows=[],frame=shf.registration;
   for(const [level,root]of[['overview',v.groups.get('SHF')],['detail',v.exteriors.get('SHF')]])for(const p of shf.afterBlindWallProbes){
    const origin=frame.origin.map((n,i)=>n+frame.right[i]*p.x+frame.outward[i]*.5);origin[2]=p.z;
    const result=hit(root,origin,frame.outward.map(n=>-n));rows.push({code:'SHF',level,point:[p.x,p.z],...result});
   }
   const ring=site.buildings.find(b=>b.code==='COW').rings[0],a=ring[5],b=ring[6],length=Math.hypot(b[0]-a[0],b[1]-a[1]),t=[(b[0]-a[0])/length,(b[1]-a[1])/length],n=[-t[1],t[0]];
   for(const[level,root]of[['overview',v.groups.get('COW')],['detail',v.exteriors.get('COW')]])for(const fraction of [.2,.4,.5,.6,.8])for(const offset of [-.001,-.0001,0,.0001,.001]){
    const origin=[a[0]+t[0]*length*fraction+n[0]*.7,a[1]+t[1]*length*fraction+n[1]*.7,4.9+offset];const result=hit(root,origin,[-n[0],-n[1],0]);rows.push({code:'COW',level,fraction,offset,...result});
   }
   return rows;
  },{shf,site});
  await writeFile(`${folder}/production-facades-diagnostic.json`,JSON.stringify({rays:proof,errors},null,2)+'\n');
  expect(proof).toHaveLength(86);
  for(const row of proof){if(row.code==='COW'&&row.offset===0)continue;expect(row.material,JSON.stringify(row)).toBeTruthy();if(row.code==='SHF'){expect(row.material).toContain('SHF_V50_white');expect(row.distance).toBeGreaterThan(.45);expect(row.distance).toBeLessThan(.55);}else{expect(row.material,JSON.stringify(row)).toMatch(/brick/i);expect(row.material).not.toMatch(/cornice|trim/i);}}
  const decoded=await read('result/blender/cow255/decoded-join-export-verification.json');
  const independent=await read('result/blender/cow255/verification.json');
  expect(decoded.passed).toBe(true);expect(decoded.reports).toHaveLength(2);
  for(const report of decoded.reports){
   const bytes=await readFile(report.path);expect(createHash('sha256').update(bytes).digest('hex')).toBe(report.sha256);
   expect(independent.actualProductionExports.find(item=>item.detail===report.detail).sha256).toBe(report.sha256);
   expect(report.allPrevious12mmCornerGroovesClosed).toBe(true);expect(report.decodedActualTriangleRays).toHaveLength(90);
   for(const row of report.decodedActualTriangleRays){expect(row.hit.material).toMatch(/brick/i);expect(row.hit.distance).toBeLessThan(1.5);}
   for(const seam of report.compressionSeams)expect(seam.widthMetres).toBeLessThan(.00005);
  }
  expect(errors).toEqual([]);await writeFile(`${folder}/production-facades.json`,JSON.stringify({passed:true,rays:proof,errors},null,2)+'\n');
 }finally{await page.evaluate(()=>window.viewer?.dispose()).catch(()=>{});}
});
