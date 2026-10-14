import * as THREE from 'three';

// One pair of uniform slots per viewer serves overview and selected buildings.
// Slots update after optional downloads without recompiling every road material.
export const GROUND_FINISHES = Object.freeze([
  {kind:'asphalt',url:'/environment/asphalt-finish-512.webp',reliefUrl:'/environment/asphalt-relief-512.webp',metres:3,mean:0.105896,height:.002},
  {kind:'stone',url:'/environment/stone-finish-512.webp',reliefUrl:'/environment/stone-relief-512.webp',metres:2,mean:0.16799,height:.0025},
]);

export function createGroundTextureState() {
  return {asphalt:{value:null},stone:{value:null},asphaltRelief:{value:null},stoneRelief:{value:null},ready:{value:0},reliefReady:{value:0}};
}

export async function loadGroundTextures(viewer) {
  const loaded = [];
  try {
    for (const asset of GROUND_FINISHES) {
      const response = await fetch(asset.url, {signal:viewer.loadController.signal});
      if (!response.ok) throw new Error('Ground finish unavailable');
      const bitmap = await createImageBitmap(await response.blob());
      const texture = new THREE.Texture(bitmap);
      loaded.push({kind:asset.kind,texture});
      texture.colorSpace = THREE.SRGBColorSpace;
      texture.wrapS = texture.wrapT = THREE.RepeatWrapping;
      texture.minFilter = THREE.LinearMipmapLinearFilter;
      texture.magFilter = THREE.LinearFilter;
      texture.anisotropy = Math.min(4, viewer.renderer.capabilities.getMaxAnisotropy());
      texture.needsUpdate = true;
      viewer.loadController.signal.throwIfAborted();
    }
    for (const {kind,texture} of loaded) viewer.groundTextures[kind].value = texture;
    viewer.groundTextures.ready.value = 1;
    viewer.canvas.dataset.groundReady = 'true';
    await loadGroundRelief(viewer);
    viewer.renderPipeline.resetHistory();
    viewer.needsRender = true;
    return true;
  } catch {
    for (const {texture} of loaded) { texture.dispose();texture.image.close(); }
    if (!viewer.disposed) viewer.canvas.dataset.groundReady = 'fallback';
    return false;
  }
}

// Relief is optional independently of colour: a missing data map must not
// discard the already usable road finish or hold up the first campus frame.
async function loadGroundRelief(viewer) {
  const loaded = [];
  try {
    for (const asset of GROUND_FINISHES) {
      const response = await fetch(asset.reliefUrl, {signal:viewer.loadController.signal});
      if (!response.ok) throw new Error('Ground relief unavailable');
      const bitmap = await createImageBitmap(await response.blob(), {colorSpaceConversion:'none'});
      const texture = new THREE.Texture(bitmap);
      loaded.push({kind:asset.kind,texture});
      texture.colorSpace = THREE.NoColorSpace;
      texture.wrapS = texture.wrapT = THREE.RepeatWrapping;
      texture.minFilter = THREE.LinearMipmapLinearFilter;
      texture.magFilter = THREE.LinearFilter;
      texture.anisotropy = Math.min(4, viewer.renderer.capabilities.getMaxAnisotropy());
      texture.needsUpdate = true;
      viewer.loadController.signal.throwIfAborted();
    }
    for (const {kind,texture} of loaded) viewer.groundTextures[kind+'Relief'].value = texture;
    viewer.groundTextures.reliefReady.value = 1;
    viewer.canvas.dataset.groundReliefReady = 'true';
  } catch {
    for (const {texture} of loaded) { texture.dispose();texture.image.close(); }
    if (!viewer.disposed) viewer.canvas.dataset.groundReliefReady = 'fallback';
  }
}

export function disposeGroundTextures(state) {
  for (const kind of ['asphalt','stone','asphaltRelief','stoneRelief']) {
    const texture = state[kind].value;
    texture?.dispose();texture?.image.close();state[kind].value = null;
  }
  state.ready.value = 0;
  state.reliefReady.value = 0;
}
