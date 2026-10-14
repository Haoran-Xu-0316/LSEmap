import {test} from 'node:test';
import assert from 'node:assert/strict';
import * as THREE from 'three';
import {outdoorSurfaceKind,refineMaterialFinish,applySurfaceDetail} from '../src/surface-materials.js';
import {createGroundTextureState} from '../src/ground-textures.js';

test('mapped hardcourt reuses the asphalt finish without darkening its authored grey',()=>{
 const name='WEB_COURTS212_estimated_neutral_grey_tarmac',color=new THREE.Color(.19,.21,.20);
 const material=new THREE.MeshStandardMaterial({name,color});const state=createGroundTextureState();
 assert.equal(outdoorSurfaceKind(name),'asphalt');refineMaterialFinish(material);assert(material.color.equals(color));assert.equal(material.roughness,.97);
 applySurfaceDetail(material,state);const shader={uniforms:{},vertexShader:'#include <project_vertex>',fragmentShader:'#include <color_fragment>\n#include <roughnessmap_fragment>\n#include <normal_fragment_maps>'};material.onBeforeCompile(shader);
 assert.equal(shader.uniforms.groundFinish,state.asphalt);assert.equal(material.map,null);
 assert.equal(outdoorSurfaceKind('WEB_COURTS212_white_tennis_paint'),null);assert.equal(outdoorSurfaceKind('WEB_COURTS212_estimated_green_net_posts'),null);
});
