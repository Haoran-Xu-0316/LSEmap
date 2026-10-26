import {throwIfAborted} from "./abort-utils.js";
import * as THREE from 'three';

// One set of uniform slots per viewer serves overview and selected buildings.
export const GROUND_FINISHES = Object.freeze([
  {kind:'asphalt',url:'/environment/asphalt-finish-512.webp',reliefUrl:'/environment/asphalt-relief-512.webp',metres:2.1,mean:0.061517,height:.0012},
  {kind:'stone',url:'/environment/stone-finish-512.webp',reliefUrl:'/environment/stone-relief-512.webp',metres:2,mean:0.16799,height:.0025,roughnessMean:.51713553},
]);

export function createGroundTextureState() {
  return {asphalt:{value:null},stone:{value:null},asphaltRelief:{value:null},stoneRelief:{value:null},ready:{value:0},reliefReady:{value:0}};
}

function releaseTexture(texture) {
  texture.dispose();
  texture.image.close();
}

// Fetch each independent pair together, but settle both before releasing a
// failed batch: a slower bitmap must never escape after its peer fails.
async function loadTexturePair(viewer, relief) {
  const results = await Promise.allSettled(GROUND_FINISHES.map(async asset => {
    let bitmap, texture;
    try {
      const response = await fetch(relief ? asset.reliefUrl : asset.url, {signal:viewer.loadController.signal});
      if (!response.ok) throw new Error('Ground finish unavailable');
      bitmap = await createImageBitmap(await response.blob(), relief ? {colorSpaceConversion:'none'} : {});
      throwIfAborted(viewer.loadController.signal);
      if (viewer.disposed) throw new Error('Viewer disposed');
      texture = new THREE.Texture(bitmap);
      texture.colorSpace = relief ? THREE.NoColorSpace : THREE.SRGBColorSpace;
      texture.wrapS = texture.wrapT = THREE.RepeatWrapping;
      texture.minFilter = THREE.LinearMipmapLinearFilter;
      texture.magFilter = THREE.LinearFilter;
      texture.anisotropy = Math.min(4, viewer.renderer.capabilities.getMaxAnisotropy());
      texture.needsUpdate = true;
      return {slot:asset.kind + (relief ? 'Relief' : ''),texture};
    } catch (error) {
      texture?.dispose();
      bitmap?.close();
      throw error;
    }
  }));
  const loaded = results.filter(result => result.status === 'fulfilled').map(result => result.value);
  if (viewer.disposed || viewer.loadController.signal.aborted || results.some(result => result.status === 'rejected')) {
    for (const {texture} of loaded) releaseTexture(texture);
    throw new Error('Ground texture batch unavailable');
  }
  return loaded;
}

function refreshGround(viewer) {
  viewer.renderPipeline.resetHistory();
  viewer.needsRender = true;
}

export async function loadGroundTextures(viewer) {
  try {
    if (viewer.disposed) return false;
    const colours = await loadTexturePair(viewer, false);
    for (const {slot,texture} of colours) viewer.groundTextures[slot].value = texture;
    viewer.groundTextures.ready.value = 1;
    viewer.canvas.dataset.groundReady = 'true';
    // Show the small colour maps immediately; larger optional relief must not
    // delay the first textured road frame on a slow connection.
    refreshGround(viewer);
  } catch {
    if (!viewer.disposed) viewer.canvas.dataset.groundReady = 'fallback';
    return false;
  }
  try {
    const relief = await loadTexturePair(viewer, true);
    for (const {slot,texture} of relief) viewer.groundTextures[slot].value = texture;
    viewer.groundTextures.reliefReady.value = 1;
    viewer.canvas.dataset.groundReliefReady = 'true';
    refreshGround(viewer);
  } catch {
    // Optional relief failure retains the already published colour pair.
    if (!viewer.disposed) viewer.canvas.dataset.groundReliefReady = 'fallback';
  }
  return true;
}

export function disposeGroundTextures(state) {
  for (const kind of ['asphalt','stone','asphaltRelief','stoneRelief']) {
    const texture = state[kind].value;
    if (texture) releaseTexture(texture);
    state[kind].value = null;
  }
  state.ready.value = 0;
  state.reliefReady.value = 0;
}
