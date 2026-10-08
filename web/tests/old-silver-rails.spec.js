import {test,expect} from '@playwright/test';
import * as THREE from 'three';
import {refineMaterialFinish} from '../src/surface-materials.js';
test('photographed OLD silver rails share sky reflection in overview and detail',()=>{
 const sky=new THREE.Texture();
 for(const prefix of ['WEB_','WEB_DETAIL_'])for(const family of ['OLD_NEXT_OLD_NEXT_ACCESS_steel','OLD_NEXT_OLD_NEXT_APPROACH_silver']){
  const m=new THREE.MeshStandardMaterial({color:new THREE.Color(.46,.49,.50),metalness:.85,roughness:.28});m.name=prefix+family;
  const color=m.color.clone();refineMaterialFinish(m,sky);
  expect(m.envMap).toBe(sky);expect(m.envMapIntensity).toBe(.7);expect(m.roughness).toBe(.43);expect(m.color.equals(color)).toBe(true);
  expect(m.transparent).toBe(false);refineMaterialFinish(m,sky);expect(m.envMapIntensity).toBe(.7);
 }
});
test('OLD blue frames and unrelated metal finishes retain authored values',()=>{
 const sky=new THREE.Texture();
 for(const name of ['WEB_OLD_NEXT_OLD_NEXT_ACCESS_frame','WEB_DETAIL_OLD174_foyer_steel','WEB_OLD_NEXT_OLD_NEXT_SSC_metal']){
  const m=new THREE.MeshStandardMaterial({metalness:.3,roughness:.5});m.name=name;refineMaterialFinish(m,sky);
  expect(m.envMap).toBe(null);expect(m.metalness).toBe(.3);expect(m.roughness).toBe(.5);
 }
});
