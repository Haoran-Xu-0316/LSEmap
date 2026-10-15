/** Verify room lighting improves diffuse fill and fully restores outdoor state. */
import assert from 'node:assert/strict';
import {writeFile} from 'node:fs/promises';
import * as THREE from 'three';
globalThis.matchMedia=()=>({matches:false,addEventListener(){},removeEventListener(){}});
const {CampusViewer}=await import('../src/viewer.js');
const hemisphere=new THREE.HemisphereLight(0xf4f6ff,0x8d8274,.65);
const sun=new THREE.DirectionalLight(0xfff4e4,3);
const fill=new THREE.DirectionalLight(0xe7edff,.25);
const viewer={hemisphere,sun,fill,needsRender:false};
const state=()=>({hemi:hemisphere.intensity,ground:hemisphere.groundColor.getHex(),
 sun:sun.intensity,fill:fill.intensity,sky:hemisphere.color.getHex(),
 sunColour:sun.color.getHex(),fillColour:fill.color.getHex()});
const daylight=state();
CampusViewer.prototype.setInteriorLighting.call(viewer,true);
assert(hemisphere.intensity>daylight.hemi);
assert(sun.intensity<daylight.sun);
assert(fill.intensity>daylight.fill);
assert.equal(state().sky,daylight.sky);assert.equal(state().sunColour,daylight.sunColour);
assert.equal(viewer.needsRender,true);
const indoors=state();
CampusViewer.prototype.setInteriorLighting.call(viewer,true);
assert.deepEqual(state(),indoors,'Switching between rooms must not accumulate exposure');
CampusViewer.prototype.setInteriorLighting.call(viewer,false);
assert.deepEqual(state(),daylight,'Exterior and campus lighting must be fully restored');
assert.equal(viewer.hemisphere,hemisphere);assert.equal(viewer.sun,sun);assert.equal(viewer.fill,fill);
await writeFile('result/blender/stage220/lighting-verification.json',JSON.stringify({daylight,indoors,roomSwitchingStable:true,daylightRestoredExactly:true,lightInstancesReused:3})+'\n');
console.log('LIGHTING220: diffuse room fill; stable room switching; exact daylight restoration; no new lights');
