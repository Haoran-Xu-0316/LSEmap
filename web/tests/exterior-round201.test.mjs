import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';
const json=async p=>JSON.parse(await readFile(p,'utf8'));
const previous=JSON.parse(execFileSync('git',['show','bc5bacaee29c7d54d55e0e8e0d3887a3fe4fb905:web/public/models/catalogue.json'],{encoding:'utf8'}));

test('complete source reopens and changes only the six registered entrance sources',async()=>{
 const proof=await json('result/blender/stage201/reopened-verification.json');const report=await json('result/blender/stage201/building-refinement.json');
 assert(proof.completeModelReopened&&proof.originalGeometryUVsAndBindingsPreserved);assert.equal(proof.originalsVerified,7038);assert.equal(proof.addedObjectsVerified,7);assert.equal(report.archivedObjects.length,6);
 const component=await json('result/blender/old-exterior201/audit.json');assert.deepEqual(report.archivedObjects,component.archivedObjects);assert(component.savedComponentReopened&&component.originalCornerUVsPreserved&&component.sourceModelUnchanged);
 assert.equal(createHash('sha256').update(await readFile('result/blender/LSE_campus_detailed_v201.blend')).digest('hex'),proof.sourceModelSha256);
 assert.equal(component.portal.sourceOpeningAndLandingRetained,true);assert(component.portal.glazingWidthFactor<1);
 for(const reference of component.references)assert.equal(createHash('sha256').update(await readFile(reference.path)).digest('hex'),reference.sha256);
});

test('all rooms and other exteriors remain identical while OLD overview/detail share the corrected portal',async()=>{
 const catalogue=await json('web/public/models/catalogue.json');assert.equal(catalogue.version,'201');assert.equal(catalogue.sourceModelSha256,(await json('result/blender/stage201/reopened-verification.json')).sourceModelSha256);
 for(const old of previous.buildings){const now=catalogue.buildings.find(b=>b.code===old.code);if(old.code==='OLD')assert.notEqual(now.detailedExterior.sha256,old.detailedExterior.sha256);else assert.equal(now.detailedExterior?.sha256,old.detailedExterior?.sha256,old.code);assert.equal(now.detailedInterior?.sha256,old.detailedInterior?.sha256,old.code);assert.deepEqual(now.interiorSpaces,old.interiorSpaces,old.code);}
 const old=catalogue.buildings.find(b=>b.code==='OLD');
 const parse=bytes=>JSON.parse(bytes.subarray(20,20+bytes.readUInt32LE(12)));
 const countPortalPaintIndices=model=>{const node=model.nodes.find(n=>n.extras?.buildingCode?.startsWith('OLD'));assert(node);return model.meshes[node.mesh].primitives.filter(p=>model.materials[p.material].name.includes('OLD201_CLARE_material_0')).reduce((total,p)=>total+model.accessors[p.indices].count,0);};
 // Export joins the authoring objects by material. The component-owned blue
 // primitive includes both retained joinery and three new closed lining boxes.
 for(const path of ['web/public/models/campus.glb','web/public'+old.detailedExterior.url]){
  const model=parse(await readFile(path));assert.equal(countPortalPaintIndices(model),13752,path);
  const paint=model.materials.find(m=>m.name.includes('OLD201_CLARE_material_0'));assert.equal(paint.extras.webSurfaceRole,'opaque');
  const glass=model.materials.find(m=>m.name.includes('OLD201_CLARE_material_2'));assert.equal(glass.extras.webSurfaceRole,'glazing');assert.equal(glass.alphaMode,'BLEND');
 }
 assert.deepEqual(catalogue.generatedTextures.map(x=>x.sha256),previous.generatedTextures.map(x=>x.sha256));
});

test('CBG primary-source audit records a real topology mismatch without inventing a placed correction',async()=>{
 const audit=await json('result/blender/cbg-built-grid201/audit.json');assert.equal(audit.nativeFileModified,false);assert.equal(audit.builtPhotoGrid.majorAxisCount,8);assert.equal(audit.builtPhotoGrid.majorBayCount,7);assert.equal(audit.builtPhotoGrid.nativeMismatch.axes,7);assert.equal(audit.builtPhotoGrid.nativeMismatch.bays,6);
 for(const source of audit.sources)assert.equal(createHash('sha256').update(await readFile(source.path)).digest('hex'),source.sha256);
 const meta=await json('web/tools/building-metadata.json');assert.equal(meta.cbgBuiltGridReview201.roofCandidateMerged,false);assert.deepEqual(meta.cbgBuiltGridReview201.engineerGridMetres,[6,9]);
});
