import { Box3, Matrix4, Vector3 } from 'three';

/** Bounds are cached only for static architecture. Exact mesh raycasts retain
 * glass, openings and occlusion; a nearer box alone never selects a building. */
export function createBuildingPicker() {
  const bounds = new WeakMap();
  const members = new WeakMap();
  const point = new Vector3();
  const intersections = [];
  const entryDistance = (raycaster, object) => {
    let cached = bounds.get(object);
    if (!cached || !cached.matrix.equals(object.matrixWorld)) {
      cached = { box: new Box3().setFromObject(object), matrix: new Matrix4().copy(object.matrixWorld) };
      bounds.set(object, cached);
    }
    const box = cached.box;
    if (box.isEmpty() || !raycaster.ray.intersectBox(box, point)) return Infinity;
    // The observer may be inside a building or a pane's bounds.
    return box.containsPoint(raycaster.ray.origin) ? 0 : raycaster.ray.origin.distanceTo(point);
  };
  return (raycaster, roots) => {
    const candidates = [];
    let order = 0;
    for (const root of roots) {
      root.updateWorldMatrix(true, true);
      if (entryDistance(raycaster, root) > raycaster.far) continue;
      let objects = members.get(root);
      if (!objects) {
        objects = [];
        root.traverse(object => { if (object.isMesh) objects.push(object); });
        members.set(root, objects);
      }
      for (const object of objects) {
        const distance = entryDistance(raycaster, object);
        if (Number.isFinite(distance) && distance <= raycaster.far) candidates.push({ object, distance, order });
        order++;
      }
    }
    candidates.sort((a, b) => a.distance - b.distance || a.order - b.order);
    let nearest = null, nearestOrder = Infinity;
    for (const candidate of candidates) {
      // Later boxes cannot precede this exact hit; retain a small rounding guard.
      if (nearest && candidate.distance > nearest.distance + 1e-7 * Math.max(1, nearest.distance)) break;
      intersections.length = 0;
      raycaster.intersectObject(candidate.object, false, intersections);
      const hit = intersections[0];
      if (hit && (!nearest || hit.distance < nearest.distance ||
          (hit.distance === nearest.distance && candidate.order < nearestOrder))) {
        nearest = hit;
        nearestOrder = candidate.order;
      }
    }
    return nearest;
  };
}
