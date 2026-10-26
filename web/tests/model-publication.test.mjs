import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtemp,mkdir,writeFile,readFile,rename,rm,stat} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {createHash} from 'node:crypto';
import {promoteVerifiedModels,validateNativeStaging,validateBinaryGltf} from '../tools/publish-model-staging.mjs';
const hash=b=>createHash('sha256').update(b).digest('hex');
function minimalGlb(){const json=Buffer.from(JSON.stringify({asset:{version:'2.0'}})),length=Math.ceil(json.length/4)*4,b=Buffer.alloc(20+length,0x20);b.writeUInt32LE(0x46546c67,0);b.writeUInt32LE(2,4);b.writeUInt32LE(b.length,8);b.writeUInt32LE(length,12);b.writeUInt32LE(0x4e4f534a,16);json.copy(b,20);return b;}

async function fixture(){const root=await mkdtemp(join(tmpdir(),'lsemap-model-publication-'));const stageModels=join(root,'stage/models'),liveModels=join(root,'live/models'),backupModels=join(root,'stage/previous');await mkdir(stageModels,{recursive:true});await mkdir(liveModels,{recursive:true});await writeFile(join(stageModels,'catalogue.json'),'new');await writeFile(join(liveModels,'catalogue.json'),'old');return {root,stageModels,liveModels,backupModels};}
async function missing(p){try{await stat(p);return false;}catch(e){if(e.code==='ENOENT')return true;throw e;}}

test('a rejected incomplete set leaves the active model directory untouched',async()=>{
 const f=await fixture();try{await assert.rejects(promoteVerifiedModels({...f,validate:async()=>{throw Error('Incomplete export');}}),/Incomplete/);assert.equal(await readFile(join(f.liveModels,'catalogue.json'),'utf8'),'old');assert.equal(await readFile(join(f.stageModels,'catalogue.json'),'utf8'),'new');assert(await missing(f.backupModels));}finally{await rm(f.root,{recursive:true});}
});
test('the complete verified set replaces the old directory and removes only its generated backup',async()=>{
 const f=await fixture();try{const proof={version:'270'};assert.equal(await promoteVerifiedModels({...f,validate:async()=>proof}),proof);assert.equal(await readFile(join(f.liveModels,'catalogue.json'),'utf8'),'new');assert(await missing(f.stageModels));assert(await missing(f.backupModels));}finally{await rm(f.root,{recursive:true});}
});
test('a filesystem failure during promotion restores the previous active set',async()=>{
 const f=await fixture();let calls=0;try{await assert.rejects(promoteVerifiedModels({...f,validate:async()=>true,renameOperation:async(a,b)=>{calls++;if(calls===2)throw Object.assign(Error('Injected I/O failure'),{code:'EIO'});return rename(a,b);}}),/Injected/);assert.equal(calls,3);assert.equal(await readFile(join(f.liveModels,'catalogue.json'),'utf8'),'old');assert.equal(await readFile(join(f.stageModels,'catalogue.json'),'utf8'),'new');assert(await missing(f.backupModels));}finally{await rm(f.root,{recursive:true});}
});
test('an unresolved prior backup cannot be overwritten by a later run',async()=>{
 const f=await fixture();try{await mkdir(f.backupModels);await writeFile(join(f.backupModels,'keep'),'prior');await assert.rejects(promoteVerifiedModels({...f,validate:async()=>true}),/backup/);assert.equal(await readFile(join(f.backupModels,'keep'),'utf8'),'prior');assert.equal(await readFile(join(f.liveModels,'catalogue.json'),'utf8'),'old');}finally{await rm(f.root,{recursive:true});}
});

async function exportFixture(){
 const root=await mkdtemp(join(tmpdir(),'lsemap-export-guard-')),version=270,stageRoot=join(root,'result/web/release270/model-staging'),models=join(stageRoot,'models');
 for(const d of[join(root,'web/tools'),join(root,'result/blender/stage270'),join(models,'details')])await mkdir(d,{recursive:true});
 const native=Buffer.from('Synthetic native identity for filesystem guard tests; not a Blender acceptance test.');const source=hash(native);
 await writeFile(join(root,'result/blender/LSE_campus_detailed_v270.blend'),native);
 await writeFile(join(root,'result/blender/stage270/independent-verification.json'),JSON.stringify({status:'passed',freshBlenderProcess:true,completeCampusSavedAndReopened:true,roomMembershipsProtected:35,sourceModelSha256:source}));
 const authoring=Buffer.from(JSON.stringify({sourceVersion:270,buildings:[{code:'A'}]}));await writeFile(join(root,'web/tools/building-metadata.json'),authoring);
 const model=minimalGlb();const descriptor={url:'/models/details/a.glb',bytes:model.length,sha256:hash(model)};
 const catalogue=Buffer.from(JSON.stringify({version:'270',sourceModelSha256:source,buildings:[{code:'A',interior:true,detailedExterior:descriptor}]}));
 const exporter=Buffer.from('Synthetic exporter identity for filesystem guard tests.');await writeFile(join(root,'web/tools/export_scene.py'),exporter);
 const files={'catalogue.json':catalogue,'campus.glb':model,'a-interior.glb':model,'details/a.glb':model};const marker={status:'complete-native-export',version:'270',sourceModelSha256:source,authoringSha256:hash(authoring),exportScriptSha256:hash(exporter),files:{}};
 for(const[p,b]of Object.entries(files)){await writeFile(join(models,p),b);marker.files[p]={bytes:b.length,sha256:hash(b)};}
 await writeFile(join(stageRoot,'model-export.json'),JSON.stringify(marker));return {root,version,stageRoot,models,marker};
}
test('a changed export file cannot pass the staging integrity gate',async()=>{
 const f=await exportFixture();try{await validateNativeStaging(f);await writeFile(join(f.models,'details/a.glb'),'corrupt');await assert.rejects(validateNativeStaging(f));}finally{await rm(f.root,{recursive:true});}
});
test('every required fallback model must be bound by the completed export marker',async()=>{
 const f=await exportFixture();try{delete f.marker.files['a-interior.glb'];await writeFile(join(f.stageRoot,'model-export.json'),JSON.stringify(f.marker));await assert.rejects(validateNativeStaging(f),/omits a-interior/);}finally{await rm(f.root,{recursive:true});}
});

test('an unsafe nested backup is rejected before filesystem mutation',async()=>{
 const f=await fixture();try{await assert.rejects(promoteVerifiedModels({...f,backupModels:join(f.stageModels,'backup'),validate:async()=>true}),/nested/);assert.equal(await readFile(join(f.liveModels,'catalogue.json'),'utf8'),'old');}finally{await rm(f.root,{recursive:true});}
});
test('a malformed binary model cannot pass the structural gate',()=>{
 const model=minimalGlb();assert.equal(validateBinaryGltf(model).asset.version,'2.0');
 const truncated=Buffer.from(model);truncated.writeUInt32LE(model.length+4,8);assert.throws(()=>validateBinaryGltf(truncated),/length/);
 const invalidChunk=Buffer.from(model);invalidChunk.writeUInt32LE(model.length,12);assert.throws(()=>validateBinaryGltf(invalidChunk),/bounds/);
});
test('changing the exporter invalidates an otherwise complete staged set',async()=>{
 const f=await exportFixture();try{await validateNativeStaging(f);await writeFile(join(f.root,'web/tools/export_scene.py'),'changed');await assert.rejects(validateNativeStaging(f),/Exporter changed/);}finally{await rm(f.root,{recursive:true});}
});

test('a failed rollback preserves the previous complete set at its backup path',async()=>{
 const f=await fixture();let calls=0;try{await assert.rejects(promoteVerifiedModels({...f,validate:async()=>({}),renameOperation:async(a,b)=>{calls++;if(calls>1)throw Error('Injected unavailable destination');return rename(a,b);}}),AggregateError);assert.equal(await readFile(join(f.backupModels,'catalogue.json'),'utf8'),'old');assert.equal(await readFile(join(f.stageModels,'catalogue.json'),'utf8'),'new');}finally{await rm(f.root,{recursive:true});}
});
