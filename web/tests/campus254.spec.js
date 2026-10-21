import {test,expect} from '@playwright/test';
import {readFile,writeFile} from 'node:fs/promises';
const folder='result/blender/stage254';
const read=async path=>JSON.parse(await readFile(path,'utf8'));

test('254 replaces only Three Tuns glass while preserving the rest of campus assets',async()=>{
 const before=await read(`${folder}/catalogue-before.json`);
 const after=await read('dist/models/catalogue.json');
 const proof=await read(`${folder}/complete-protection.json`);
 expect(after.version).toBe('254');expect(proof.completeModelReopened).toBe(true);
 expect(proof.originalObjectsProtected).toBe(8674);expect(proof.roomStudies).toBe(35);
 expect(proof.otherRoomMembershipsProtected).toBe(34);expect(proof.campusRoomMembershipUnchanged).toBe(true);
 const counts={exteriors:0,interiors:0,rooms:0,fallbacks:0};
 for(const old of before.buildings){
  const current=after.buildings.find(b=>b.code===old.code);
  for(const [field,key]of [['detailedExterior','exteriors'],['detailedInterior','interiors']])if(old[field]){
   expect(current[field].sha256,old.code+field).toBe(old[field].sha256);counts[key]++;
  }
  for(const room of old.interiorSpaces??[]){
   const currentRoom=current.interiorSpaces.find(r=>r.id===room.id);
   if(room.id==='saw-three-tuns')expect(currentRoom.detailedInterior.sha256).not.toBe(room.detailedInterior.sha256);
   else{expect(currentRoom.detailedInterior.sha256,room.id).toBe(room.detailedInterior.sha256);counts.rooms++;}
  }
 }
 const previous=await read(`${folder}/release-before.json`),release=await read('dist/release.json');
 for(const path of Object.keys(previous.assets).filter(p=>/^\/models\/[a-z0-9]+-interior\.glb$/.test(p))){
  expect(release.assets[path].sha256,path).toBe(previous.assets[path].sha256);counts.fallbacks++;
 }
 expect(counts).toEqual({exteriors:30,interiors:25,rooms:34,fallbacks:25});
 const oldRoom=before.buildings.find(b=>b.code==='SAW').interiorSpaces.find(r=>r.id==='saw-three-tuns');
 const room=after.buildings.find(b=>b.code==='SAW').interiorSpaces.find(r=>r.id==='saw-three-tuns');
 const parse=bytes=>JSON.parse(bytes.subarray(20,20+bytes.readUInt32LE(12)).toString());
 const oldBytes=await readFile(`${folder}/three-tuns-before.glb`),bytes=await readFile('dist'+room.detailedInterior.url);
 const oldDoc=parse(oldBytes),doc=parse(bytes);
 const geometry=(document,bytes)=>{
  const bin=bytes.subarray(28+bytes.readUInt32LE(12));
  const data=index=>{
   const accessor=document.accessors[index];
   if(accessor.bufferView===undefined)return {type:accessor.type,componentType:accessor.componentType,count:accessor.count,min:accessor.min,max:accessor.max};
   const view=document.bufferViews[accessor.bufferView];
   const sizes={5120:1,5121:1,5122:2,5123:2,5125:4,5126:4},widths={SCALAR:1,VEC2:2,VEC3:3,VEC4:4};
   const size=sizes[accessor.componentType]*widths[accessor.type],stride=view.byteStride??size;
   const start=(view.byteOffset??0)+(accessor.byteOffset??0),values=[];
   for(let i=0;i<accessor.count;i++)values.push(bin.subarray(start+i*stride,start+i*stride+size).toString('base64'));
   return {type:accessor.type,componentType:accessor.componentType,count:accessor.count,normalized:accessor.normalized??false,values};
  };
  const draco=primitive=>{const ext=primitive.extensions?.KHR_draco_mesh_compression;if(!ext)return null;const view=document.bufferViews[ext.bufferView],start=view.byteOffset??0;return {attributes:ext.attributes,bytes:bin.subarray(start,start+view.byteLength).toString('base64')};};
  return document.meshes.flatMap(mesh=>mesh.primitives.map(primitive=>({
   material:document.materials[primitive.material].name.replace('SAW254_three_tuns_clear_glass','SAW_V48_TUNS_glass'),
   mode:primitive.mode??4,draco:draco(primitive),indices:data(primitive.indices),attributes:Object.fromEntries(Object.entries(primitive.attributes).sort().map(([key,index])=>[key,data(index)])),
  }))).sort((a,b)=>a.material.localeCompare(b.material));
 };
 expect(geometry(doc,bytes)).toEqual(geometry(oldDoc,oldBytes));
 const material=doc.materials.find(m=>m.name==='WEB_DETAIL_SAW254_three_tuns_clear_glass');
 expect(material.alphaMode).toBe('BLEND');expect(material.pbrMetallicRoughness.baseColorFactor[3]).toBeCloseTo(.30,6);
 expect(material.pbrMetallicRoughness.metallicFactor).toBe(0);
 expect(doc.extensionsUsed??[]).not.toContain('KHR_materials_transmission');
 expect(doc.images??[]).toEqual(oldDoc.images??[]);
 const imageBefore=await read(`${folder}/gallery-before.json`),gallery=await read('dist/gallery-manifest.json');
 expect(gallery.images).toHaveLength(204);
 const changed=gallery.images.filter(image=>image.sha256!==imageBefore.images.find(old=>old.name===image.name).sha256).map(image=>image.name);
 expect(changed).toEqual(['saw-three-tuns-interior']);
 await writeFile(`${folder}/asset-scope.json`,JSON.stringify({unchanged:counts,changedRoom:room.id,previousURL:oldRoom.detailedInterior.url,currentURL:room.detailedInterior.url,perMaterialGeometryUnchanged:true,changedImages:changed},null,2)+'\n');
});

test('Three Tuns scene renders prepared transparent glass and retains its lettering',async({page})=>{
 const release=await read('dist/release.json');
 const module=Object.keys(release.assets).find(p=>/^\/assets\/viewer-.*\.js$/.test(p));
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 const html=`<!doctype html><link rel="icon" href="data:,"><style>body{margin:0}#stage{width:1000px;height:800px}#labels{display:none}</style><div id="stage"></div><div id="labels"></div><script type="module">
 import{CampusViewer}from'${module}';const cat=await(await fetch('/models/catalogue.json')).json();
 const v=new CampusViewer(document.querySelector('#stage'),document.querySelector('#labels'),cat.buildings,()=>{},()=>{throw Error('Context lost')},()=>{},cat.sourceModelSha256);window.viewer=v;v.loadCampusExteriors=async()=>{};await v.load();await v.environmentReady;
 const b=cat.buildings.find(b=>b.code==='SAW');v.select(b);await v.upgradeModel(b,'exterior');await v.showInterior(b,'saw-three-tuns');await v.upgradeModel(b,'interior','saw-three-tuns');window.ready=true;</script>`;
 try{
  await page.route('**/__campus254',r=>r.fulfill({contentType:'text/html',body:html}));await page.goto('/__campus254');await page.waitForFunction(()=>window.ready,null,{timeout:60000});
  const result=await page.evaluate(()=>{const v=window.viewer,root=v.interiors.get('SAW:saw-three-tuns');const materials=[];root.traverse(o=>{if(o.isMesh)for(const m of Array.isArray(o.material)?o.material:[o.material])materials.push({name:m.name,opacity:m.opacity,transparent:m.transparent,metalness:m.metalness,transmission:m.transmission??0});});return{ready:v.canvas.dataset.detailReady,glass:materials.find(m=>m.name.includes('SAW254_three_tuns_clear_glass')),hasLettering:materials.some(m=>m.name.includes('TUNS_letter')),sameScene:v.detailCache.models.size===0};});
  expect(result.ready).toBe('interior-SAW:saw-three-tuns');expect(result.glass.opacity).toBeCloseTo(.30,6);expect(result.glass.transparent).toBe(true);expect(result.glass.metalness).toBe(0);expect(result.glass.transmission).toBe(0);expect(result.hasLettering).toBe(true);expect(result.sameScene).toBe(true);expect(errors).toEqual([]);
  await writeFile(`${folder}/production-room.json`,JSON.stringify({...result,errors},null,2)+'\n');
 }finally{await page.evaluate(()=>window.viewer?.dispose()).catch(()=>{});}
});
