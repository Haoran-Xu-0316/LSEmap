/** Promote a complete native+mobile model set after all checks, with rollback. */
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {createReadStream} from 'node:fs';
import {readFile,writeFile,stat,access,rename,rm} from 'node:fs/promises';
import {join,resolve,relative,dirname} from 'node:path';
import {pathToFileURL} from 'node:url';
import {prepareMobileCampus} from './prepare-mobile-campus.mjs';

const hash=bytes=>createHash('sha256').update(bytes).digest('hex');
const read=async path=>JSON.parse(await readFile(path,'utf8'));
async function fileHash(path){const h=createHash('sha256');for await(const bytes of createReadStream(path))h.update(bytes);return h.digest('hex');}
async function exists(path){try{await access(path);return true;}catch(error){if(error.code==='ENOENT')return false;throw error;}}
function checkedRelative(path){assert(typeof path==='string'&&path&&!path.startsWith('/')&&!path.split(/[\\/]/).includes('..'),'Invalid model path');return path;}
function assetPath(root,url){assert(url.startsWith('/models/'),'Unexpected model URL');return join(root,checkedRelative(url.slice('/models/'.length)));}

export function validateBinaryGltf(bytes,label='model') {
 assert(bytes.length>=20,'Truncated GLB: '+label);
 assert.equal(bytes.readUInt32LE(0),0x46546c67,'Invalid GLB header: '+label);
 assert.equal(bytes.readUInt32LE(4),2,'Unsupported GLB version: '+label);
 assert.equal(bytes.readUInt32LE(8),bytes.length,'GLB length mismatch: '+label);
 let offset=12,json;
 while(offset<bytes.length){
  assert(offset+8<=bytes.length,'Truncated GLB chunk: '+label);
  const length=bytes.readUInt32LE(offset),type=bytes.readUInt32LE(offset+4);
  assert(length%4===0&&offset+8+length<=bytes.length,'Invalid GLB chunk bounds: '+label);
  if(offset===12){assert.equal(type,0x4e4f534a,'Missing GLB JSON: '+label);json=JSON.parse(bytes.subarray(offset+8,offset+8+length).toString('utf8'));}
  offset+=8+length;
 }
 assert.equal(offset,bytes.length);assert.equal(json?.asset?.version,'2.0','Invalid glTF asset version: '+label);
 return json;
}

export async function validateNativeStaging({root=process.cwd(),version,stageRoot}){
 const authoringPath=join(root,'web/tools/building-metadata.json');
 const authoringBytes=await readFile(authoringPath),authoring=JSON.parse(authoringBytes);
 assert(Number.isInteger(version)&&version>0&&Number(authoring.sourceVersion)===version,'Wrong authoring edition');
 const marker=await read(join(stageRoot,'model-export.json'));
 assert(marker.status==='complete-native-export'&&marker.version===String(version),'Native export is incomplete');
 assert.equal(marker.authoringSha256,hash(authoringBytes),'Authoring changed after native export');
 assert.equal(marker.exportScriptSha256,await fileHash(join(root,'web/tools/export_scene.py')),'Exporter changed after native export');
 const native=join(root,`result/blender/LSE_campus_detailed_v${version}.blend`);
 assert.equal(await fileHash(native),marker.sourceModelSha256,'Native source changed');
 const proof=await read(join(root,`result/blender/stage${version}/independent-verification.json`));
 assert(['passed','passed-bounded-integration'].includes(proof.status)&&proof.freshBlenderProcess,'Missing independent native acceptance');
 assert(proof.completeCampusSavedAndReopened&&proof.roomMembershipsProtected===35,'Incomplete campus preservation proof');
 assert.equal(proof.sourceModelSha256,marker.sourceModelSha256);
 const models=join(stageRoot,'models');assert((await stat(models)).isDirectory());
 assert(Object.keys(marker.files).length>0,'Empty export');
 for(const[path,record]of Object.entries(marker.files)){
  const file=join(models,checkedRelative(path)),bytes=await readFile(file);
  assert.equal(bytes.length,record.bytes,path);assert.equal(hash(bytes),record.sha256,path);
  if(path.endsWith('.glb'))validateBinaryGltf(bytes,path);
 }
 const catalogue=await read(join(models,'catalogue.json'));
 assert.equal(catalogue.version,String(version));assert.equal(catalogue.sourceModelSha256,marker.sourceModelSha256);
 assert.deepEqual(catalogue.buildings.map(b=>b.code),authoring.buildings.map(b=>b.code),'Campus coverage changed');
 const declared=new Set(['catalogue.json','campus.glb']);
 for(const b of catalogue.buildings){
  if(b.interior)declared.add(b.code.toLowerCase()+'-interior.glb');
  for(const a of[b.detailedExterior,b.detailedInterior,...(b.interiorSpaces??[]).map(s=>s.detailedInterior)].filter(Boolean)){
   const path=assetPath(models,a.url),bytes=await readFile(path);
   assert.equal(bytes.length,a.bytes,a.url);assert.equal(hash(bytes),a.sha256,a.url);
   declared.add(checkedRelative(a.url.slice('/models/'.length)));
  }
 }
 for(const path of declared)assert(marker.files[path],'Export marker omits '+path);
 return {catalogue,marker,models};
}

export async function promoteVerifiedModels({stageModels,liveModels,backupModels,validate,renameOperation=rename}){
 const source=resolve(stageModels),target=resolve(liveModels),backup=resolve(backupModels);
 assert(source!==target&&source!==backup&&target!==backup,'Model directories must be distinct');
 for(const a of[source,target,backup])for(const b of[source,target,backup])if(a!==b){
  const distance=relative(a,b);assert(distance==='..'||distance.startsWith('../'),'Model directories must not be nested');
 }
 assert((await stat(source)).isDirectory()&&(await stat(target)).isDirectory());
 assert(!await exists(backup),'Previous model backup must be resolved before publishing');
 const verification=await validate();
 let previousMoved=false,promoted=false;
 try{
  await renameOperation(target,backup);previousMoved=true;
  await renameOperation(source,target);promoted=true;
 }catch(error){
  if(previousMoved&&!promoted){
   try{await renameOperation(backup,target);}
   catch(restoreError){throw new AggregateError([error,restoreError],'Promotion failed and automatic restoration failed; the previous complete set remains at '+backup);}
  }
  throw error;
 }
 // Delete only the previous generated model tree, after the complete set is live.
 try{await rm(backup,{recursive:true});}
 catch(error){verification.cleanupPending={path:backup,reason:error.message};}
 return verification;
}

export async function publishModelStaging({root=process.cwd()}={}){
 root=resolve(root);
 const authoring=await read(join(root,'web/tools/building-metadata.json'));
 const version=Number(authoring.sourceVersion);assert(Number.isInteger(version)&&version>0);
 const stageRoot=join(root,`result/web/release${version}/model-staging`);
 const initial=await validateNativeStaging({root,version,stageRoot});
 const mobile=await prepareMobileCampus({publicRoot:stageRoot,reviewRoot:join(root,`result/web/release${version}/mobile`)});
 assert.equal(mobile.manifest.sourceModelSha256,initial.marker.sourceModelSha256);
 assert.equal(mobile.manifest.sourceCampusSha256,await fileHash(join(initial.models,'campus.glb')));
 const mobileBytes=await readFile(assetPath(initial.models,mobile.manifest.url));
 assert.equal(hash(mobileBytes),mobile.manifest.sha256);validateBinaryGltf(mobileBytes,'mobile overview');
 const record=await promoteVerifiedModels({stageModels:initial.models,liveModels:join(root,'web/public/models'),backupModels:join(stageRoot,'previous-models'),validate:async()=>{
  await validateNativeStaging({root,version,stageRoot});
  const descriptor=await read(join(initial.models,'mobile-campus.json'));
  assert.deepEqual(descriptor,mobile.manifest,'Mobile descriptor changed before promotion');
  assert.equal(await fileHash(assetPath(initial.models,descriptor.url)),descriptor.sha256);
  return {status:'published-complete-model-set',version:String(version),sourceModelSha256:initial.marker.sourceModelSha256,mobileSha256:descriptor.sha256,mobileDecodedBytes:descriptor.decodedBytes,modelFiles:Object.keys(initial.marker.files).length+2};
 }});
 await writeFile(join(dirname(stageRoot),'model-publication.json'),JSON.stringify(record,null,2)+'\n');
 console.log(JSON.stringify(record));return record;
}

if(process.argv[1]&&import.meta.url===pathToFileURL(resolve(process.argv[1])).href)await publishModelStaging();
