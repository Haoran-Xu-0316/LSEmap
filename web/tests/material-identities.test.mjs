import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import * as THREE from 'three';
import {isGlazingMaterial, refineMaterialFinish, prepareMeshShadows} from '../src/surface-materials.js';

const opaqueNames = [
  'WEB_49L_NEXT_49L_NEXT_GLAZING_fireexit_louvre_dark',
  'WEB_49L_NEXT_50L_NEXT_GLAZING_50A_photographic_warm_stone',
  'WEB_50L_NEXT_50L_NEXT_GLAZING_50A_photographic_warm_stone',
  'WEB_50L_NEXT_50L_NEXT_GLAZING_50A_handbook_dark_blue_paint',
  'WEB_50L_NEXT_50L_NEXT_GLAZING_50A_opaque_external_light',
];

test('actual campus stone, blue paint and louvers retain their opaque finish', async () => {
  const bytes = await readFile('web/public/models/campus.glb');
  const document = JSON.parse(bytes.subarray(20, 20 + bytes.readUInt32LE(12)));
  for (const name of opaqueNames) {
    const source = document.materials.find(material => material.name === name);
    assert.ok(source, name);
    const pbr = source.pbrMetallicRoughness;
    const material = new THREE.MeshStandardMaterial({
      color: new THREE.Color(...pbr.baseColorFactor.slice(0, 3)),
      roughness: pbr.roughnessFactor,
      metalness: pbr.metallicFactor ?? 0,
    });
    material.name = name;
    material.userData = source.extras ?? {};
    const color = material.color.toArray();
    assert.equal(isGlazingMaterial(material), false, name);
    refineMaterialFinish(material, new THREE.Texture());
    assert.deepEqual(material.color.toArray(), color, name);
    assert.equal(material.roughness, pbr.roughnessFactor, name);
    assert.equal(material.envMap, null, name);
    const object = new THREE.Mesh(new THREE.BoxGeometry(), material);
    prepareMeshShadows(object);
    assert.equal(object.castShadow, true, name);
  }
});

test('physical role identifies unnamed clear panes without changing recorded opacity', () => {
  const material = new THREE.MeshPhysicalMaterial({transparent:true, opacity:.32, roughness:.15});
  material.name = 'Entry_tempered_optics';
  material.userData.webSurfaceRole = 'glazing';
  assert.equal(isGlazingMaterial(material), true);
  const sky = new THREE.Texture();
  refineMaterialFinish(material, sky);
  assert.equal(material.opacity, .32);
  assert.equal(material.envMap, sky);
  const object = new THREE.Mesh(new THREE.PlaneGeometry(), material);
  prepareMeshShadows(object);
  assert.equal(object.castShadow, false);
});

test('explicit opaque role takes precedence over a historic component prefix', () => {
  const material = new THREE.MeshStandardMaterial({color:0x164779, roughness:.57});
  material.name = 'Glass_assembly_blue_paint';
  material.userData.webSurfaceRole = 'opaque';
  const color = material.color.toArray();
  assert.equal(isGlazingMaterial(material), false);
  refineMaterialFinish(material, new THREE.Texture());
  assert.deepEqual(material.color.toArray(), color);
  assert.equal(material.roughness, .57);
});

test('legacy optical pane families keep the narrow compatibility fallback', () => {
  for (const name of ['Facade_glass', 'WEB_GLASS181_sheet_CBG_NEXT_neutral_glazing',
    'WEB_DETAIL_MAR168_02_01_dielectric', 'Atrium_glazing_clear'])
    assert.equal(isGlazingMaterial({name,userData:{}}), true, name);
});
