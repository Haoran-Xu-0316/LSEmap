import * as THREE from 'three';
import {HDRLoader} from 'three/addons/loaders/HDRLoader.js';

export const SKY_BACKDROP_URL = '/environment/daylight-sky-2k.webp';
export const SKY_URL = '/environment/daylight-1k.hdr';
export const OUTDOOR_ATMOSPHERE = Object.freeze({ horizon: 0xc4d9e8, lowerSky: 0xb6cee2 });
// Orient the photographed daylight toward the campus key light. This is a
// presentation sky; its capture location is not campus survey evidence.
// The source sun is at48 degrees elevation. Match its azimuth to the
// campus key light without tilting the horizon or adding a second sun sprite.
const SKY_ROTATION = new THREE.Euler(0, -0.297803, 0);
export const DAYLIGHT_DIRECTION = new THREE.Vector3(
  0.8, Math.tan(48 * Math.PI / 180) * Math.hypot(0.8, 1), 1,
).normalize();
const MAP_BACKGROUND = new THREE.Color(0xe9edf0);

/** Keep one outdoor world throughout an orbit. Isolated elevations and
 * interiors retain their clear study background. */
export function outdoorSkyVisible(mode, verticalDirection, wasVisible = false, isolatedElevation = false) {
  return !isolatedElevation && mode !== 'interior';
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

// A pale atmospheric surround replaces the panorama's mirrored underside.
// Preserve the real upper sky and its single sun; reflections still use the HDR.
function createSkySurround(texture) {
  const material = new THREE.ShaderMaterial({
    side: THREE.BackSide, depthTest: false, depthWrite: false, toneMapped: false,
    uniforms: { sky: { value: texture }, horizon: { value: new THREE.Color(OUTDOOR_ATMOSPHERE.horizon) }, lowerSky: { value: new THREE.Color(OUTDOOR_ATMOSPHERE.lowerSky) }, rotation: { value: new THREE.Matrix3().setFromMatrix4(new THREE.Matrix4().makeRotationFromEuler(SKY_ROTATION)).transpose() } },
    vertexShader: `
      varying vec3 direction;
      void main() {
        direction = position;
        vec4 clip = projectionMatrix * mat4(mat3(viewMatrix)) * vec4(position, 1.0);
        gl_Position = clip.xyww;
      }
    `,
    fragmentShader: `
      uniform sampler2D sky; uniform mat3 rotation; uniform vec3 horizon, lowerSky; varying vec3 direction;
      void main() {
        vec3 ray = normalize(rotation * direction);
        vec2 uv = vec2(atan(ray.z, ray.x) / 6.28318530718 + .5,
                       asin(clamp(ray.y, -1.0, 1.0)) / 3.14159265359 + .5);
        vec3 photograph = texture2D(sky, uv).rgb;
        vec3 atmosphere = mix(horizon, lowerSky, smoothstep(0.0, 1.0, -ray.y));
        float realSky = smoothstep(-.04, .10, ray.y);
        gl_FragColor = vec4(mix(atmosphere, photograph, realSky), 1.0);
        #include <colorspace_fragment>
      }
    `,
  });
  const mesh = new THREE.Mesh(new THREE.BoxGeometry(2, 2, 2), material);
  mesh.name = 'Outdoor sky surround';
  mesh.frustumCulled = false; mesh.renderOrder = -10000;
  mesh.matrixAutoUpdate = false;
  return mesh;
}

/** Upgrade the lightweight startup lighting after the model becomes usable. */
export async function loadOutdoorEnvironment(viewer) {
  let texture, target, backdrop, backdropPending, committed = false;
  try {
    if (viewer.disposed) return false;
    // The tiny sky and independent HDR can transfer together after first frame.
    backdropPending = loadSkyBackdrop(viewer);
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
    backdrop = await backdropPending;
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
    const skySurround = backdrop ? createSkySurround(backdrop) : null;
    if (skySurround) viewer.scene.add(skySurround);
    const haze = new THREE.Fog(0xc4d4e0, 1400, 3000);
    // Reuse one static panorama and one PMREM. Orbiting changes only which
    // existing background is selected; it never recaptures the environment.
    viewer.scene.onBeforeRender = () => {
      if (viewer.disposed) return;
      const isolatedElevation = Boolean(viewer.activeCode) && viewer.mode === 'campus' && !viewer.contextVisible;
      const skyVisible = outdoorSkyVisible(viewer.mode, 0, false, isolatedElevation);
      if (skySurround) skySurround.visible = skyVisible;
      // Haze starts behind the fitted campus, never across a selected facade.
      const orbitDistance = viewer.camera.position.distanceTo(viewer.controls.target);
      haze.near = orbitDistance + 450;
      haze.far = orbitDistance + 2000;
      viewer.scene.fog = skyVisible ? haze : null;
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
    if (!committed) {
      target?.dispose();
      texture?.dispose();
      const unusedBackdrop = backdrop ?? await backdropPending;
      unusedBackdrop?.dispose();
      unusedBackdrop?.image.close();
    }
  }
}
