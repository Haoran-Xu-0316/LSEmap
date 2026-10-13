import * as THREE from 'three';
import {HDRLoader} from 'three/addons/loaders/HDRLoader.js';

export const SKY_URL = '/environment/kloppenheim-sky-1k.hdr';
// Align the photographed sun's azimuth with the existing campus daylight.
// Sky capture location is a presentation choice, not campus survey evidence.
const SKY_ROTATION = new THREE.Euler(0, -0.27, 0);
const MAP_BACKGROUND = new THREE.Color(0xe9edf0);

/** Upgrade the lightweight startup lighting after the model becomes usable. */
export async function loadOutdoorEnvironment(viewer) {
  try {
    const response = await fetch(SKY_URL, {signal:viewer.loadController.signal});
    if (!response.ok) throw new Error('Sky asset unavailable');
    const bytes = await response.arrayBuffer();
    viewer.loadController.signal.throwIfAborted();
    const data = new HDRLoader().parse(bytes);
    const texture = new THREE.DataTexture(data.data, data.width, data.height,
      THREE.RGBAFormat, data.type);
    texture.mapping = THREE.EquirectangularReflectionMapping;
    texture.colorSpace = THREE.LinearSRGBColorSpace;
    texture.flipY = true;
    texture.minFilter = texture.magFilter = THREE.LinearFilter;
    texture.needsUpdate = true;
    const generator = new THREE.PMREMGenerator(viewer.renderer);
    let target;
    try { target = generator.fromEquirectangular(texture); }
    finally { generator.dispose(); }
    const previous = viewer.environmentTarget;
    viewer.environmentTarget = target;
    viewer.skyTexture = texture;
    viewer.scene.environment = target.texture;
    viewer.scene.environmentRotation.copy(SKY_ROTATION);
    viewer.scene.environmentIntensity = 0.25;
    const direction = new THREE.Vector3();
    // Downward map views keep a bright neutral surround. The photographic sky
    // becomes visible as the user lowers the camera toward the streets.
    viewer.scene.onBeforeRender = () => {
      viewer.camera.getWorldDirection(direction);
      viewer.scene.background = viewer.mode !== 'interior' && direction.y > -.42
        ? texture : MAP_BACKGROUND;
    };
    viewer.scene.backgroundRotation.copy(SKY_ROTATION);
    viewer.scene.backgroundIntensity = 0.8;
    viewer.scene.backgroundBlurriness = 0.015;
    viewer.scene.traverse(object => {
      for (const material of Array.isArray(object.material) ? object.material : [object.material]) {
        if (material?.envMap === previous.texture) {
          material.envMap = target.texture;
          material.envMapRotation?.copy(SKY_ROTATION);
          material.needsUpdate = true;
        }
      }
    });
    previous.dispose();
    viewer.renderPipeline.resetHistory();
    viewer.needsRender = true;
    viewer.canvas.dataset.skyReady = 'true';
    return true;
  } catch (error) {
    // Offline/aborted optional lighting retains the startup environment.
    if (!viewer.disposed) viewer.canvas.dataset.skyReady = 'fallback';
    return false;
  }
}
