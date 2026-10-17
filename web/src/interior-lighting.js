import * as THREE from "three";

// Presentation bounce for the existing cutaway/interior assets, not surveyed
// luminaire positions or a simulation of physical indoor illumination.
// Reuse the viewer's three lights and PMREM; allocate no GPU resources.
const savedLighting = new WeakMap();

function lightState(light) {
  return {
    color: light.color.clone(),
    intensity: light.intensity,
    position: light.position.clone(),
    targetPosition: light.target?.position.clone(),
    groundColor: light.groundColor?.clone(),
    shadowCamera: light.shadow && Object.fromEntries(
      ['left', 'right', 'top', 'bottom', 'near', 'far', 'zoom'].map(key => [key, light.shadow.camera[key]])),
  };
}

function restoreLight(light, state) {
  light.color.copy(state.color);
  light.intensity = state.intensity;
  light.position.copy(state.position);
  if (state.groundColor) light.groundColor.copy(state.groundColor);
  if (state.targetPosition) {
    light.target.position.copy(state.targetPosition);
    light.target.updateMatrixWorld();
  }
  if (state.shadowCamera) {
    Object.assign(light.shadow.camera, state.shadowCamera);
    light.shadow.camera.updateProjectionMatrix();
  }
  light.updateMatrixWorld();
}

function interiorBounds(viewer, supplied) {
  if (supplied?.isBox3) {
    return [...supplied.min.toArray(), ...supplied.max.toArray()].every(Number.isFinite) ? supplied : null;
  }
  const active = viewer.activeInterior;
  const building = viewer.buildings?.find(item => item.code === active?.code);
  const data = supplied ?? (building && viewer.interiorSpace(building, active.spaceId)?.interiorBounds);
  if (Array.isArray(data?.min) && Array.isArray(data?.max) &&
      data.min.length === 3 && data.max.length === 3 &&
      [...data.min, ...data.max].every(Number.isFinite)) {
    return new THREE.Box3(new THREE.Vector3(...data.min), new THREE.Vector3(...data.max));
  }
  return null;
}

/** Call instead of the old setInteriorLighting body. Bounds may be a Box3 or
 * catalogue bounds; omitted bounds resolve the active public interior or room.
 * Repeated room switches retain the original exterior snapshot. */
export function applyInteriorLighting(viewer, interior, bounds) {
  if (!interior) {
    const saved = savedLighting.get(viewer);
    if (!saved) return;
    for (const name of ["hemisphere", "sun", "fill"]) restoreLight(viewer[name], saved[name]);
    viewer.scene.environmentIntensity = saved.environmentIntensity;
    savedLighting.delete(viewer);
    viewer.renderer.shadowMap.needsUpdate = true;
    viewer.needsRender = true;
    return;
  }
  if (!savedLighting.has(viewer)) {
    savedLighting.set(viewer, {
      hemisphere: lightState(viewer.hemisphere),
      sun: lightState(viewer.sun),
      fill: lightState(viewer.fill),
      environmentIntensity: viewer.scene.environmentIntensity,
    });
  }
  viewer.hemisphere.color.setHex(0xf4f6ff);
  viewer.hemisphere.groundColor.setHex(0xd1c9bc);
  viewer.hemisphere.intensity = 1.05;
  viewer.sun.intensity = 1.65;
  viewer.fill.color.setHex(0xfff8ef);
  viewer.fill.intensity = 1.7;
  viewer.scene.environmentIntensity = 0.48;
  const box = interiorBounds(viewer, bounds);
  if (box && !box.isEmpty()) {
    const centre = box.getCenter(new THREE.Vector3());
    const size = box.getSize(new THREE.Vector3());
    const span = Math.max(4, size.x, size.z);
    // A broad unshadowed reflected-light direction lifts soffits and ceilings.
    // Its direction is stable under camera rotation and translated with rooms.
    viewer.fill.target.position.copy(centre);
    viewer.fill.position.copy(centre).add(new THREE.Vector3(span * .65, -span * .55, span * .35));
    viewer.fill.target.updateMatrixWorld();
    viewer.fill.updateMatrixWorld();
  }
  viewer.renderer.shadowMap.needsUpdate = true;
  viewer.needsRender = true;
}

/** Restore a pending exterior snapshot before disposing the viewer. */
export function disposeInteriorLighting(viewer) {
  applyInteriorLighting(viewer, false);
}
