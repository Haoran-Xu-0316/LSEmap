import {test} from 'node:test';
import assert from 'node:assert/strict';
import * as THREE from 'three';
import {outdoorSurfaceKind,refineMaterialFinish,applySurfaceDetail} from '../src/surface-materials.js';

test('all road and paving families receive their intended shared surface treatment',()=>{
  for(const [name,kind] of [['WEB_Road asphalt','asphalt'],['WEB_CLM_V73_asphalt','asphalt'],
    ['WEB_Pale campus paving','paving-grid'],['WEB_MAR25_paving','paving-grid'],
    ['WEB_SITE172_SITE_V47_slab_2_Houghton','stone'],['WEB_SITE172_SITE_V47_slab_2_Watkins','stone'],
    ['WEB_Lincoln Inn Fields grass','grass']]) assert.equal(outdoorSurfaceKind(name),kind);
  assert.equal(outdoorSurfaceKind('WEB_CBG_D_warm_grey_frame'),null);
});
test('plain stone gains filtered seams while authored physical pavers retain their geometry pattern',()=>{
  for(const name of ['WEB_Pale campus paving','WEB_SITE172_SITE_V47_slab_2_Houghton']) {
    const material=new THREE.MeshStandardMaterial({name});refineMaterialFinish(material);applySurfaceDetail(material);
    const shader={uniforms:{},vertexShader:'#include <project_vertex>',fragmentShader:'#include <color_fragment>\n#include <roughnessmap_fragment>\n#include <normal_fragment_maps>'};
    material.onBeforeCompile(shader);
    assert.equal(shader.fragmentShader.includes('slabVisibility'),name.includes('Pale'));
    assert(shader.fragmentShader.includes('fwidth(surfacePoint)'));
    assert(shader.fragmentShader.includes('roughnessFactor'));
  }
});
test('street asphalt is matte and distinct from stone without modifying existing dark asphalt',()=>{
  const road=new THREE.MeshStandardMaterial({name:'WEB_Road asphalt',color:new THREE.Color(.2,.215,.225)});
  const clm=new THREE.MeshStandardMaterial({name:'WEB_CLM_V73_asphalt',color:new THREE.Color(.039,.042,.041)});
  const color=clm.color.clone();refineMaterialFinish(road);refineMaterialFinish(clm);
  assert(road.color.r<.1);assert.equal(road.roughness,.97);assert(clm.color.equals(color));
});
