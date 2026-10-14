import * as THREE from 'three';
import {HDRLoader} from 'three/addons/loaders/HDRLoader.js';

export const SKY_BACKDROP_URL = '/environment/daylight-sky-2k.webp';
export const SKY_URL = '/environment/kloppenheim-daylight-1k.hdr';
// Orient the photographed daylight toward the campus key light. This is a
// presentation sky; its capture location is not campus survey evidence.
const SKY_ROTATION = new THREE.Euler(0, -0.27, 0);
const MAP_BACKGROUND = new THREE.Color(0xe9edf0);

/** Keep downward elevation studies clear; reveal the sky near street level.
 * The small hysteresis band prevents flicker while orbiting near the boundary.
 */
export function outdoorSkyVisible(mode, verticalDirection, wasVisible = false) {
  return mode !== 'interior' && verticalDirection > (wasVisible ? -.26 : -.18);
}

// A sharp LDR background and the filtered HDR reflections have separate roles.
// Failure here keeps the existing HDR sky; it never discards usable lighting.
async function loadSkyBackdrop(viewer) {
  let bitmap;
  try {
    const response = await fetch(SKY_BACKDROP_URL, {signal:viewer.loadController.signal});
    if (!response.ok) return null;
    // ImageBitmap ignores Texture.flipY during GPU upload. Orient its pixels here.
    bitmap = await createImageBitmap(await response.blob(), {imageOrientation:'flipY'});
    viewer.loadController.signal.throwIfAborted();
    if (viewer.disposed) { bitmap.close(); return null; }
    const texture = new THREE.Texture(bitmap);
    texture.mapping = THREE.EquirectangularReflectionMapping;
    texture.colorSpace = THREE.SRGBColorSpace;
    texture.minFilter = THREE.LinearMipmapLinearFilter;
    texture.magFilter = THREE.LinearFilter;
    texture.needsUpdate = true;
    return texture;
  } catch { bitmap?.close(); return null; }
}

/** Upgrade the lightweight startup lighting after the model becomes usable. */
export async function loadOutdoorEnvironment(viewer) {
  let texture, target, backdrop, committed = false;
  try {
    if (viewer.disposed) return false;
    const response = await fetch(SKY_URL, {signal:viewer.loadController.signal});
    if (!response.ok) throw new Error('Sky asset unavailable');
    const bytes = await response.arrayBuffer();
    viewer.loadController.signal.throwIfAborted();
    if (viewer.disposed) return false;
    const data = new HDRLoader().parse(bytes);
    texture = new THREE.DataTexture(data.data, data.width, data.height,
      THREE.RGBAFormat, data.type);
    texture.mapping = THREE.EquirectangularReflectionMapping;
    texture.colorSpace = THREE.LinearSRGBColorSpace;
    texture.flipY = true;
    texture.minFilter = texture.magFilter = THREE.LinearFilter;
    texture.needsUpdate = true;
    const generator = new THREE.PMREMGenerator(viewer.renderer);
    try { target = generator.fromEquirectangular(texture); }
    finally { generator.dispose(); }
    viewer.loadController.signal.throwIfAborted();
    if (viewer.disposed) return false;
    backdrop = await loadSkyBackdrop(viewer);
    viewer.loadController.signal.throwIfAborted();
    if (viewer.disposed) return false;
    const previousBackdrop = viewer.skyBackdrop;
    const previous = viewer.environmentTarget;
    const previousSky = viewer.skyTexture;
    viewer.environmentTarget = target;
    viewer.skyTexture = texture;
    viewer.skyBackdrop = backdrop;
    viewer.scene.environment = target.texture;
    viewer.scene.environmentRotation.copy(SKY_ROTATION);
    viewer.scene.environmentIntensity = 0.25;
    const direction = new THREE.Vector3();
    let skyVisible = false;
    // Reuse one static panorama and one PMREM. Orbiting changes only which
    // existing background is selected; it never recaptures the environment.
    viewer.scene.onBeforeRender = () => {
      if (viewer.disposed) return;
      viewer.camera.getWorldDirection(direction);
      skyVisible = outdoorSkyVisible(viewer.mode, direction.y, skyVisible);
      const background = skyVisible ? (backdrop ?? texture) : MAP_BACKGROUND;
      if (viewer.scene.background !== background) viewer.scene.background = background;
    };
    viewer.scene.backgroundRotation.copy(SKY_ROTATION);
    viewer.scene.backgroundIntensity = 1.0;
    viewer.scene.backgroundBlurriness = 0;
    viewer.scene.traverse(object => {
      for (const material of Array.isArray(object.material) ? object.material : [object.material]) {
        if (material?.envMap === previous?.texture) {
          material.envMap = target.texture;
          material.envMapRotation?.copy(SKY_ROTATION);
          material.needsUpdate = true;
        }
      }
    });
    previous?.dispose();
    previousSky?.dispose();
    previousBackdrop?.dispose();previousBackdrop?.image.close();
    committed = true;
    viewer.renderPipeline.resetHistory();
    viewer.needsRender = true;
    viewer.canvas.dataset.skyReady = 'true';
    viewer.canvas.dataset.skyBackdropReady = backdrop ? 'true' : 'fallback';
    return true;
  } catch (error) {
    // Offline/aborted optional lighting retains the startup environment.
    if (!viewer.disposed) viewer.canvas.dataset.skyReady = 'fallback';
    return false;
  } finally {
    if (!committed) { target?.dispose(); texture?.dispose();backdrop?.dispose();backdrop?.image.close(); }
  }
}
