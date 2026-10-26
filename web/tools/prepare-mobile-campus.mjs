/** Derive a mobile overview from the accepted campus; full buildings stay separate. */
import {NodeIO} from '@gltf-transform/core';
import {ALL_EXTENSIONS,KHRDracoMeshCompression} from '@gltf-transform/extensions';
import {weldPrimitive,simplifyPrimitive,prune} from '@gltf-transform/functions';
import draco3d from 'draco3dgltf';
import {MeshoptSimplifier} from 'meshoptimizer';
import {readFile,writeFile,mkdir} from 'node:fs/promises';
import {createHash} from 'node:crypto';
const source='web/public/models/campus.glb';
const hash=bytes=>createHash('sha256').update(bytes).digest('hex');
const sourceBytes=await readFile(source),catalogue=JSON.parse(await readFile('web/public/models/catalogue.json'));
const out='result/web/release'+catalogue.version+'/mobile';
const io=new NodeIO().registerExtensions(ALL_EXTENSIONS).registerDependencies({'draco3d.decoder':await draco3d.createDecoderModule(),'draco3d.encoder':await draco3d.createEncoderModule()});
await MeshoptSimplifier.ready;
// Permit removal of subpixel seams and disconnected ornaments in the distant
// overview. Full authored primitives remain in each selected building asset.
const overviewSimplifier={...MeshoptSimplifier,simplify:(indices,positions,stride,count,error)=>
  MeshoptSimplifier.simplify(indices,positions,stride,count,error,['Permissive','Prune'])};
const document=await io.readBinary(sourceBytes);
function owner(node){for(let p=node;p;p=p.getParentNode()){const code=p.getExtras().buildingCode;if(code)return code;}return 'OTHER';}
function stats(doc){const grouped={};for(const node of doc.getRoot().listNodes())if(node.getMesh()){
 const code=owner(node),row=grouped[code]??={vertices:0,triangles:0,decodedBytes:0,zeroTriangles:0,min:[Infinity,Infinity,Infinity],max:[-Infinity,-Infinity,-Infinity]};
 for(const p of node.getMesh().listPrimitives()){
  const pos=p.getAttribute('POSITION');row.vertices+=pos.getCount();row.triangles+=(p.getIndices()?.getCount()??pos.getCount())/3;
  for(const a of [...p.listAttributes(),p.getIndices()].filter(Boolean))row.decodedBytes+=a.getArray().byteLength;
  if(['SITE','LANDSCAPE','CONTEXT'].includes(code)){
   const v=pos.getArray(),ind=p.getIndices().getArray();
   for(let i=0;i<ind.length;i+=3){const a=ind[i]*3,b=ind[i+1]*3,c=ind[i+2]*3;
    const ux=v[b]-v[a],uy=v[b+1]-v[a+1],uz=v[b+2]-v[a+2],vx=v[c]-v[a],vy=v[c+1]-v[a+1],vz=v[c+2]-v[a+2];
    if(Math.hypot(uy*vz-uz*vy,uz*vx-ux*vz,ux*vy-uy*vx)/2<1e-14)row.zeroTriangles++;
   }
  }
  const min=pos.getMin([]),max=pos.getMax([]);for(let i=0;i<3;i++){row.min[i]=Math.min(row.min[i],min[i]);row.max[i]=Math.max(row.max[i],max[i]);}
 }
 }return grouped;}
const before=stats(document);
const meshes=new Map();for(const node of document.getRoot().listNodes())if(node.getMesh())meshes.set(node.getMesh(),owner(node));
for(const[mesh,code]of meshes){
 if(['SITE','LANDSCAPE','CONTEXT','OTHER'].includes(code))continue;
 for(const p of mesh.listPrimitives())if(p.getAttribute('POSITION').getCount()>1200){weldPrimitive(p);simplifyPrimitive(p,{simplifier:overviewSimplifier,ratio:.12,error:.008,lockBorder:false});}
}
await document.transform(prune({keepExtras:true,keepAttributes:true,keepSolidTextures:true}));
// Configure Draco directly: its convenience transform would also weld the
// protected public setting. Keep those original primitives and indices intact.
document.createExtension(KHRDracoMeshCompression).setRequired(true).setEncoderOptions({
 method:KHRDracoMeshCompression.EncoderMethod.EDGEBREAKER,encodeSpeed:5,decodeSpeed:10,
 quantizationBits:{POSITION:20,NORMAL:10,TEX_COORD:12,COLOR:8,GENERIC:12}});
const bytes=await io.writeBinary(document),reopened=await io.readBinary(bytes),after=stats(reopened);
for(const mesh of reopened.getRoot().listMeshes())for(const primitive of mesh.listPrimitives()){
 if(primitive.getMaterial()?.getExtras().surfaceDetail?.kind==='brick'&&!primitive.getAttribute('TEXCOORD_0'))
  throw Error('Procedural masonry lost its authored coordinates');
}
const decodedBytes=Object.values(after).reduce((sum,row)=>sum+row.decodedBytes,0);
const report={sourceCampusSha256:hash(sourceBytes),sourceModelSha256:catalogue.sourceModelSha256,sourceBytes:sourceBytes.length,bytes:bytes.length,decodedBytes,before,after};
await mkdir(out,{recursive:true});await writeFile(out+'/mobile-asset-review.json',JSON.stringify(report,null,2)+'\n');
if(bytes.length>=25*1024*1024||decodedBytes>96*1024*1024)throw Error('Mobile asset exceeds the reviewed memory budget: '+decodedBytes);
if(JSON.stringify(Object.keys(before).sort())!==JSON.stringify(Object.keys(after).sort()))throw Error('A campus group was lost');
for(const code of ['SITE','LANDSCAPE','CONTEXT']){
 const removed=before[code].triangles-after[code].triangles;
 // Draco drops degenerate faces; no public-setting simplification is run.
 if(removed<0||removed>before[code].zeroTriangles)throw Error('Public setting changed: '+code);
}
const sha256=hash(bytes),url='/models/details/campus-mobile-'+sha256.slice(0,12)+'.glb';
await writeFile('web/public'+url,bytes);
const manifest={version:catalogue.version,url,sha256,bytes:bytes.length,decodedBytes,sourceModelSha256:catalogue.sourceModelSha256,sourceCampusSha256:hash(sourceBytes),buildingCodes:Object.keys(after).sort()};
await writeFile('web/public/models/mobile-campus.json',JSON.stringify(manifest,null,2)+'\n');
console.log(JSON.stringify({url,bytes:bytes.length,decodedBytes,sourceDecodedBytes:Object.values(before).reduce((sum,r)=>sum+r.decodedBytes,0)}));
