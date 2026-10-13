import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';

const read = async path => JSON.parse(await readFile(path, 'utf8'));
async function model(path) {
  const bytes = await readFile(path);
  const jsonLength = bytes.readUInt32LE(12);
  return {bytes,document:JSON.parse(bytes.subarray(20,20+jsonLength)),binStart:28+jsonLength};
}

test('current complete source was reopened with only listed exterior replacements', async () => {
  const accepted = await read('result/blender/stage194/building-refinement.json');
  const reopened = await read('result/blender/stage194/reopened-verification.json');
  const catalogue = await read('web/public/models/catalogue.json');
  assert.equal(catalogue.version, '194');
  assert.equal(catalogue.sourceModelSha256, accepted.sourceModelSha256);
  assert.equal(reopened.sourceModelSha256, accepted.sourceModelSha256);
  assert.equal(reopened.completeModelReopened, true);
  assert.equal(reopened.originalGeometryUVsAndBindingsPreserved, true);
  assert.equal(reopened.listedVisibilityOnly, true);
  assert.equal(accepted.addedObjects.length, 77);
  assert.equal(accepted.archivedObjects.length, 76);
});

test('every exported surface has a physical role and actual glass preserves dielectric response', async () => {
  const {document} = await model('web/public/models/campus.glb');
  let glazing = 0, opaque = 0;
  for (const material of document.materials) {
    assert.ok(['glazing','opaque'].includes(material.extras?.webSurfaceRole), material.name);
    if (material.extras.webSurfaceRole === 'glazing') {
      glazing++;
      assert.equal(material.pbrMetallicRoughness.metallicFactor ?? 0, 0, material.name);
    } else opaque++;
  }
  assert.ok(glazing > 80 && opaque > 300);
});

test('OLD stone and globe maps retain exact approved bytes and usable UV coordinates', async () => {
  const {bytes,document,binStart} = await model('web/public/models/campus.glb');
  const catalogue = await read('web/public/models/catalogue.json');
  assert.equal(document.images.length, 2);
  assert.equal(catalogue.generatedTextures.length, 2);
  for (const image of document.images) {
    assert.equal(image.uri, undefined);
    const buffer = document.bufferViews[image.bufferView];
    const data = bytes.subarray(binStart+(buffer.byteOffset??0),binStart+(buffer.byteOffset??0)+buffer.byteLength);
    const hash = createHash('sha256').update(data).digest('hex');
    assert.ok(catalogue.generatedTextures.some(texture=>texture.sha256===hash));
  }
  const stone = await read('result/blender/old-exterior194/building-refinement.json');
  assert.ok(catalogue.generatedTextures.some(texture=>texture.sha256===stone.image.sha256));
  const node = document.nodes.find(node=>node.extras?.buildingCode==='OLD');
  const primitives = document.meshes[node.mesh].primitives.filter(primitive=>
    document.materials[primitive.material].name.includes('OLD194_STONE_'));
  assert.ok(primitives.length>20);
  for (const primitive of primitives) {
    const material=document.materials[primitive.material];
    assert.equal(material.extras.webSurfaceRole,'opaque');
    assert.ok(material.pbrMetallicRoughness.baseColorTexture);
    assert.ok(primitive.attributes.TEXCOORD_0!==undefined);
  }
});

test('all existing rooms retain identity and camera scope after the exterior integration', async () => {
  const before = await read('result/blender/stage194/catalogue-before.json');
  const after = await read('web/public/models/catalogue.json');
  assert.equal(after.buildings.length, before.buildings.length);
  for(const building of before.buildings) {
    const current=after.buildings.find(record=>record.code===building.code);
    for(const key of ['interior','interiorStudy','interiorView','interiorCollection'])
      assert.deepEqual(current[key],building[key],`${building.code} ${key}`);
    assert.deepEqual((current.interiorSpaces??[]).map(room=>[room.id,room.label,room.scope,room.interiorView]),
      (building.interiorSpaces??[]).map(room=>[room.id,room.label,room.scope,room.interiorView]),building.code);
  }
});


test('first overview includes the structural and public-space finishes of selected exteriors', async () => {
  const catalogue=await read('web/public/models/catalogue.json');
  const campus=(await model('web/public/models/campus.glb')).document;
  const plain=name=>name.replace(/^WEB_(?:DETAIL_)?/, '');
  for(const code of ['CBG','MAR','CKK','SAW','LRB']) {
    const building=catalogue.buildings.find(building=>building.code===code);
    const detail=(await model('web/public'+building.detailedExterior.url)).document;
    const node=campus.nodes.find(node=>node.extras?.buildingCode===code);
    const overview=new Set(campus.meshes[node.mesh].primitives.map(primitive=>plain(campus.materials[primitive.material].name)));
    for(const material of detail.materials) {
      const name=plain(material.name);
      // Legacy sub-centimetre finish meshes remain the deliberately lighter LOD.
      if(/^V1[67]_/.test(name)) continue;
      assert.ok(overview.has(name),code+': '+name);
    }
  }
});
