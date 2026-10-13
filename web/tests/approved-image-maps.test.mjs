import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {verifyApprovedImageMaps} from '../tools/approved_image_maps.mjs';
const catalogue=JSON.parse(await readFile('web/public/models/catalogue.json','utf8'));
const read=async path=>{
  const buffer=await readFile(path);
  return {buffer,document:JSON.parse(buffer.subarray(20,20+buffer.readUInt32LE(12)))};
};

test('exact approved stone bytes survive both campus and selected OLD models',async()=>{
  const old=catalogue.buildings.find(building=>building.code==='OLD');
  for(const path of ['web/public/models/campus.glb','web/public'+old.detailedExterior.url]) {
    const {buffer,document}=await read(path);
    const maps=verifyApprovedImageMaps(buffer,document,catalogue.generatedTextures,path);
    assert.ok(maps.some(map=>map.kind==='material-finish'));
  }
});

test('a modified embedded image cannot pass the release gate',async()=>{
  const {buffer,document}=await read('web/public/models/campus.glb');
  const view=document.bufferViews[document.images[0].bufferView];
  const changed=Buffer.from(buffer);
  changed[28+buffer.readUInt32LE(12)+(view.byteOffset??0)+20]^=1;
  assert.throws(()=>verifyApprovedImageMaps(changed,document,catalogue.generatedTextures),/unapproved/);
});

test('an external image URI cannot bypass the approved image byte checks',async()=>{
  const {buffer,document}=await read('web/public/models/campus.glb');
  document.images[0]={name:document.images[0].name,uri:'https://example.invalid/reference.jpg'};
  assert.throws(()=>verifyApprovedImageMaps(buffer,document,catalogue.generatedTextures),/self-contained/);
});

test('an unlisted image remains forbidden even if its display name is approved',async()=>{
  const {buffer,document}=await read('web/public/models/campus.glb');
  const record=catalogue.generatedTextures.find(record=>record.name===document.images[0].name);
  const excluded=catalogue.generatedTextures.filter(candidate=>candidate!==record);
  assert.throws(()=>verifyApprovedImageMaps(buffer,document,excluded),/unapproved/);
});
