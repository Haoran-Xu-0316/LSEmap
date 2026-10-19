import {test,expect} from '@playwright/test';
import {readFile,writeFile} from 'node:fs/promises';
const folder='result/blender/stage251';
const read=async path=>JSON.parse(await readFile(path,'utf8'));

test('251 changes only COL exterior and MAR public structure, preserving every room',async()=>{
 const before=await read(`${folder}/catalogue-before.json`),after=await read('dist/models/catalogue.json');
 const native=await read(`${folder}/building-refinement.json`),saved=await read(`${folder}/complete-protection.json`);
 expect(after.version).toBe('251');expect(saved.completeModelReopened).toBe(true);
 expect(saved.originalObjectsProtected).toBe(8639);expect(saved.originalMaterialGraphsProtected).toBe(2341);
 expect(saved.protectedRooms).toBe(35);expect(saved.protectedRoomMembers).toBe(1485);
 expect(native.changedObjects).toEqual([]);
 expect(native.addedObjects).toContain('MAR251_third_south_lift_core_walls');
 expect(native.addedObjects).toContain('COL251_closed_source_height_roof');
 const counts={exteriors:0,interiors:0,rooms:0,fallbacks:0};
 for(const old of before.buildings){const current=after.buildings.find(b=>b.code===old.code);
  if(old.detailedExterior){if(['COL','MAR'].includes(old.code))expect(current.detailedExterior.sha256).not.toBe(old.detailedExterior.sha256);else{expect(current.detailedExterior.sha256,old.code).toBe(old.detailedExterior.sha256);counts.exteriors++;}}
  if(old.detailedInterior){if(old.code==='MAR')expect(current.detailedInterior.sha256).not.toBe(old.detailedInterior.sha256);else{expect(current.detailedInterior.sha256,old.code).toBe(old.detailedInterior.sha256);counts.interiors++;}}
  for(const room of old.interiorSpaces??[]){expect(current.interiorSpaces.find(r=>r.id===room.id).detailedInterior.sha256,room.id).toBe(room.detailedInterior.sha256);counts.rooms++;}
 }
 const previous=await read(`${folder}/release-before.json`),release=await read('dist/release.json');
 for(const path of Object.keys(previous.assets).filter(p=>/^\/models\/[a-z0-9]+-interior\.glb$/.test(p))){if(path==='/models/mar-interior.glb')expect(release.assets[path].sha256).not.toBe(previous.assets[path].sha256);else{expect(release.assets[path].sha256,path).toBe(previous.assets[path].sha256);counts.fallbacks++;}}
 expect(counts).toEqual({exteriors:28,interiors:24,rooms:35,fallbacks:24});
 expect(after.buildings.find(b=>b.code==='MAR').interiorBounds.max[1]).toBeCloseTo(21.9,4);
 const gallery=await read('dist/gallery-manifest.json');expect(gallery.images).toHaveLength(204);
 expect(gallery.images.find(i=>i.name==='mar-third-lift-openings-interior').sectionId).toBe('3');
 expect(gallery.images.some(i=>i.name==='col-houghton')).toBe(true);
 await writeFile(`${folder}/asset-scope.json`,JSON.stringify({unchanged:counts,changed:['COL exterior','MAR exterior','MAR public interior','MAR fallback interior']},null,2)+'\n');
});

test('production Draco models retain open MAR doorways and source-aligned COL frontage',async({page})=>{
 const release=await read('dist/release.json'),module=Object.keys(release.assets).find(p=>/^\/assets\/viewer-.*\.js$/.test(p));
 const marPlan=await read('result/blender/mar-core251/plan.json'),floorProbes=await read('result/blender/mar-third250/ray-probes.json');
 const colSource=await read('result/blender/col-component244/geometry-plan.json'),colPlan=await read('result/blender/col-roof251/geometry-plan.json');
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 const html=`<style>body{margin:0}#stage{width:1000px;height:800px}#labels{display:none}</style><div id="stage"></div><div id="labels"></div><script type="module">import{CampusViewer}from'${module}';const catalogue=await(await fetch('/models/catalogue.json')).json();const v=new CampusViewer(document.querySelector('#stage'),document.querySelector('#labels'),catalogue.buildings,()=>{},()=>{throw Error('Context lost')},()=>{},catalogue.sourceModelSha256);window.viewer=v;window.catalogue=catalogue;v.loadCampusExteriors=async()=>{};await v.load();await v.environmentReady;const mar=catalogue.buildings.find(b=>b.code==='MAR');v.select(mar);await v.loadExterior(mar);await v.showInterior(mar);await v.upgradeModel(mar,'interior');v.setInteriorSection(mar,'3');v.transition=null;window.ready=true;</script>`;
 try{
  await page.route('**/__campus251',route=>route.fulfill({contentType:'text/html',body:html}));await page.goto('/__campus251');await page.waitForFunction(()=>window.ready,null,{timeout:60000});
  const mar=await page.evaluate(({plan,floor})=>{
   const v=viewer,vector=(x,y,z)=>v.controls.target.clone().set(x,y,z),down=vector(0,-1,0),up=vector(0,1,0);
   v.scene.updateMatrixWorld(true);
   const roots=[v.groups.get('MAR'),v.exteriors.get('MAR'),v.interiors.get('MAR:default'),v.activeDetail.group],results=[];
   const hits=(root,origin,direction,far)=>{v.raycaster.far=far;v.raycaster.set(origin,direction);return v.raycaster.intersectObject(root,true);};
   for(const root of roots){let doorRays=0,heads=0,jambs=0,shaftRays=0;const failures=[];
    for(const door of plan.doors){const [x,y]=door.centre,[nx,ny]=door.normal,tx=-ny,ty=nx,dir=vector(nx,0,-ny);
     const origin=(offset,z)=>vector(x+tx*offset-nx*.55,z,-(y+ty*offset-ny*.55));
     for(const offset of [-.3,0,.3])for(const z of [.25,1.05,2]){if(hits(root,origin(offset*door.widthMetres,17.5+z),dir,1.1).length)failures.push({door:door.id,offset,z,type:'blocked'});doorRays++;}
     if(!hits(root,origin(0,19.72),dir,1.1).length)failures.push({door:door.id,type:'missing head'});heads++;
     for(const sign of [-1,1]){if(!hits(root,origin(sign*(door.widthMetres/2+.07),18.5),dir,1.1).length)failures.push({door:door.id,type:'missing jamb'});jambs++;}
    }
    for(const p of floor.voids){if(hits(root,vector(p.point[0],17.51,-p.point[1]),up,4.36).length)failures.push({point:p.point,type:'filled shaft'});shaftRays++;}
    const filledVoids=floor.voids.filter(p=>hits(root,vector(p.point[0],17.55,-p.point[1]),down,.12).length).length;
    const missingBearings=floor.bearings.filter(p=>!hits(root,vector(p.point[0],17.55,-p.point[1]),down,.12).length).length;
    results.push({doorRays,heads,jambs,shaftRays,filledVoids,missingBearings,failures});
   }
   v.raycaster.far=Infinity;return{assets:results,order:['campus','exterior','fallback interior','detailed interior'],section:v.canvas.dataset.interiorSection};
  },{plan:marPlan,floor:floorProbes});
  for(const r of mar.assets){expect(r.failures).toEqual([]);expect(r).toMatchObject({doorRays:36,heads:4,jambs:8,shaftRays:243,filledVoids:0,missingBearings:0});}
  expect(mar.section).toBe('3');await page.screenshot({path:`${folder}/browser-mar-third-core.png`});
  await page.evaluate(async()=>{const b=catalogue.buildings.find(b=>b.code==='COL');viewer.select(b);await viewer.upgradeModel(b,'exterior');viewer.transition=null;});
  const col=await page.evaluate(({source,plan})=>{
   const v=viewer,reg=plan.registration,vector=(x,y,z)=>v.controls.target.clone().set(x,y,z),[ox,oy]=source.sourceOrigin,scale=source.metresPerPoint;
   const [n]=reg.frontageNorthToSouth,[ax,ay]=reg.axis,[ix,iy]=reg.inwardNormal,dir=vector(ix,0,-iy);v.scene.updateMatrixWorld(true);v.raycaster.far=51;
   const results=[];
   for(const root of [v.groups.get('COL'),v.exteriors.get('COL')]){const failures=[];let rays=0,backs=0;
    for(const opening of source.openings){const [x0,y0,x1,y1]=opening.sourceBounds;
     for(const f of [.2,.5,.8]){const u=(x0+(x1-x0)*f-ox)*scale;let z=(oy-y0-(y1-y0)*f)*scale;
      if(opening.role==='entrance-material-unverified'){const low=Math.max((oy-y1)*scale,source.groundRiseNorthM*(1-u/source.sourceWidthM)),head=(oy-y0)*scale;z=head-(head-z)*(head-reg.flatStreetThresholdM)/(head-low);}
      const origin=vector(n[0]+ax*u*reg.horizontalFit-ix*50,z,-(n[1]+ay*u*reg.horizontalFit-iy*50));v.raycaster.set(origin,dir);
      const hits=v.raycaster.intersectObject(root,true),material=h=>{const m=h.object.material;return(Array.isArray(m)?m[h.face.materialIndex]:m).name.replace(/^WEB_(?:DETAIL_)?/,'');};
      const first=hits[0],back=hits.find(h=>material(h).includes('closed_recess_backing'));
      if(!first||!/^COL249_(estimated_(window_glass|dark_joinery)|unverified_ground_infill)$/.test(material(first))||first.distance<49.98||first.distance>50.17)failures.push({id:opening.id,f,type:'first surface',distance:first?.distance,material:first&&material(first)});
      if(!back||Math.abs(back.distance-50.6)>.005)failures.push({id:opening.id,f,type:'backing',distance:back?.distance});else backs++;rays++;
     }
    }
    results.push({rays,backs,failures});
   }
   v.raycaster.far=Infinity;return{assets:results,order:['campus','exterior']};
  },{source:colSource,plan:colPlan});
  for(const r of col.assets){expect(r.failures).toEqual([]);expect(r.rays).toBe(216);expect(r.backs).toBe(216);}
  expect(errors).toEqual([]);await writeFile(`${folder}/production-geometry.json`,JSON.stringify({mar,col,errors},null,2)+'\n');
 }finally{await page.evaluate(()=>window.viewer?.dispose()).catch(()=>{});}
});
