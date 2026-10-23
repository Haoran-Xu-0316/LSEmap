import * as THREE from 'three';

const MARGIN = 12;
const GROUND_LEVEL = -.06;
const identity = new THREE.Matrix4();
const point = new THREE.Vector3();
const CANCELLED = Symbol('Street context request superseded');

class BuildJob {
  constructor() { this.cancelled = false; this.started = performance.now(); this.blockStarted = this.started; this.cpuMs = 0; this.maxBlockMs = 0; this.yields = 0; }
  async checkpoint(force = false) {
    if (this.cancelled) throw CANCELLED;
    const duration = performance.now() - this.blockStarted;
    if (!force && duration < 4) return;
    this.cpuMs += duration; this.maxBlockMs = Math.max(this.maxBlockMs, duration); this.yields++;
    await new Promise(resolve => typeof requestAnimationFrame === 'function' && !globalThis.document?.hidden ? requestAnimationFrame(resolve) : setTimeout(resolve, 0));
    if (this.cancelled) throw CANCELLED;
    this.blockStarted = performance.now();
  }
  finish() { const duration = performance.now() - this.blockStarted; this.cpuMs += duration; this.maxBlockMs = Math.max(this.maxBlockMs, duration); }
}

function isVegetation(material) {
  return /foliage|(?:^|_)bark(?:\.|$)|Oak public interior/i.test(material.name);
}

function isGround(material, box) {
  return box.max.y < .26 && !/planter/i.test(material.name) &&
    /asphalt|tarmac|paving|slab|yorkstone|grout|grass|gravel|_edge_/i.test(material.name);
}

// Public park buildings belong to the full surroundings, not to a street crop.
function isPublicBuilding(material) {
  return /PARK233_estimated_(?:plinth|roof_tiles|timber|fascia|glass|metal_roof)/i.test(material.name);
}

function overlaps(a, b) {
  return a.max.x >= b.min.x && a.min.x <= b.max.x && a.max.z >= b.min.z && a.min.z <= b.max.z;
}

function contains(box, x, z) {
  return x >= box.min.x && x <= box.max.x && z >= box.min.z && z <= box.max.z;
}

async function meshData(object, job) {
  const geometry = object.geometry;
  if (!geometry.boundingBox) geometry.computeBoundingBox();
  const matrix = object.matrixWorld.clone();
  const direct = matrix.equals(identity);
  const position = geometry.attributes.position;
  const world = direct ? position : new THREE.BufferAttribute(new Float32Array(position.count * 3), 3);
  if (!direct) for (let i = 0; i < position.count; i++) {
    point.fromBufferAttribute(position, i).applyMatrix4(matrix);
    world.setXYZ(i, point.x, point.y, point.z);
    if ((i & 1023) === 0) await job.checkpoint();
  }
  const attributes = Object.entries(geometry.attributes).map(([name, attribute]) => ({ name, attribute, size: attribute.itemSize }));
  return { object, geometry, world, attributes, direct, normalMatrix: new THREE.Matrix3().getNormalMatrix(matrix),
    box: geometry.boundingBox.clone().applyMatrix4(matrix), components: null };
}

// Closed crowns retain every triangle of their original connected component.
// Components also keep furniture faces intact instead of cutting through seats.
async function components(data, job) {
  if (data.components) return data.components;
  const { geometry, world } = data, count = world.count;
  const parent = Int32Array.from({ length: count }, (_, i) => i);
  const find = i => { while (parent[i] !== i) { parent[i] = parent[parent[i]]; i = parent[i]; } return i; };
  const join = (a, b) => { const x = find(a), y = find(b); if (x !== y) parent[x] = y; };
  const at = geometry.index ? i => geometry.index.array[i] : i => i;
  const length = geometry.index?.count ?? count;
  // Indexed GLTF also duplicates positions at UV and hard-normal seams.
  // Weld connectivity only; output keeps each original vertex and its attributes.
  const positions = new Map();
  for (let i = 0; i < count; i++) {
    const key = `${world.getX(i).toFixed(5)},${world.getY(i).toFixed(5)},${world.getZ(i).toFixed(5)}`;
    if (positions.has(key)) join(i, positions.get(key)); else positions.set(key, i);
    if ((i & 511) === 0) await job.checkpoint();
  }
  for (let i = 0; i < length; i += 3) {
    join(at(i), at(i + 1)); join(at(i), at(i + 2));
    if (i % 1536 === 0) await job.checkpoint();
  }
  const islands = new Map();
  for (let i = 0; i < length; i += 3) {
    if (i % 1536 === 0) await job.checkpoint();
    const key = find(at(i));
    if (!islands.has(key)) islands.set(key, { indices: [], box: new THREE.Box3() });
    const island = islands.get(key);
    for (let j = 0; j < 3; j++) {
      const index = at(i + j); island.indices.push(index);
      point.fromBufferAttribute(world, index); island.box.expandByPoint(point);
    }
  }
  data.components = [...islands.values()];
  return data.components;
}

function vertex(data, index) {
  const result = [];
  for (const { name, attribute, size } of data.attributes) {
    if (name === 'position') result.push(data.world.getX(index), data.world.getY(index), data.world.getZ(index));
    else if (name === 'normal' && !data.direct) {
      point.fromBufferAttribute(attribute, index).applyMatrix3(data.normalMatrix).normalize(); result.push(point.x, point.y, point.z);
    } else for (let c = 0; c < size; c++) result.push(attribute.getComponent(index, c));
  }
  return result;
}

// Sutherland-Hodgman clips crossing triangles and interpolates every attribute.
// A district-size floor triangle must never pull the entire city into a crop.
function clip(vertices, axis, limit, sign, positionOffset) {
  const output = [];
  for (let i = 0; i < vertices.length; i++) {
    const a = vertices[i], b = vertices[(i + 1) % vertices.length];
    const da = (a[positionOffset + axis] - limit) * sign, db = (b[positionOffset + axis] - limit) * sign;
    if (da >= 0) output.push(a);
    if ((da >= 0) !== (db >= 0)) {
      const t = da / (da - db); output.push(a.map((value, c) => value + (b[c] - value) * t));
    }
  }
  return output;
}

async function cropGround(data, bounds, job) {
  const kept = [], clipped = [], { geometry, world } = data;
  const at = geometry.index ? i => geometry.index.array[i] : i => i;
  const length = geometry.index?.count ?? world.count;
  const positionOffset = data.attributes.slice(0, data.attributes.findIndex(a => a.name === 'position')).reduce((sum, a) => sum + a.size, 0);
  for (let i = 0; i < length; i += 3) {
    if (i % 768 === 0) await job.checkpoint();
    const ids = [at(i), at(i + 1), at(i + 2)];
    const xs = ids.map(id => world.getX(id)), zs = ids.map(id => world.getZ(id)), ys = ids.map(id => world.getY(id));
    if (Math.max(...xs) < bounds.min.x || Math.min(...xs) > bounds.max.x || Math.max(...zs) < bounds.min.z || Math.min(...zs) > bounds.max.z || Math.max(...ys) < GROUND_LEVEL) continue;
    if (ids.every((id, j) => contains(bounds, xs[j], zs[j]) && ys[j] >= GROUND_LEVEL)) { kept.push(...ids); continue; }
    let polygon = ids.map(id => vertex(data, id));
    for (const [axis, limit, sign] of [[0, bounds.min.x, 1], [0, bounds.max.x, -1], [2, bounds.min.z, 1], [2, bounds.max.z, -1], [1, GROUND_LEVEL, 1]]) {
      polygon = clip(polygon, axis, limit, sign, positionOffset); if (polygon.length < 3) break;
    }
    for (let j = 1; j + 1 < polygon.length; j++) clipped.push(polygon[0], polygon[j], polygon[j + 1]);
  }
  return { kept, clipped };
}

async function copyGeometry(data, kept, clipped, job) {
  if (!kept.length && !clipped.length) return null;
  const values = data.attributes.map(() => []), indices = [], remap = new Map();
  const append = valuesAtVertex => {
    let offset = 0;
    for (let a = 0; a < data.attributes.length; a++) for (let c = 0; c < data.attributes[a].size; c++) values[a].push(valuesAtVertex[offset++]);
    return values[0].length / data.attributes[0].size - 1;
  };
  let copied = 0;
  for (const index of kept) {
    if ((copied++ & 511) === 0) await job.checkpoint();
    if (!remap.has(index)) remap.set(index, append(vertex(data, index)));
    indices.push(remap.get(index));
  }
  for (const valuesAtVertex of clipped) {
    if ((copied++ & 511) === 0) await job.checkpoint();
    indices.push(append(valuesAtVertex));
  }
  const geometry = new THREE.BufferGeometry();
  for (let a = 0; a < data.attributes.length; a++) geometry.setAttribute(data.attributes[a].name, new THREE.Float32BufferAttribute(values[a], data.attributes[a].size));
  geometry.setIndex(indices); geometry.computeBoundingBox();
  geometry.boundingSphere = geometry.boundingBox.getBoundingSphere(new THREE.Sphere());
  return geometry;
}

/** Nearby public ground, planting and furniture share their accepted materials.
 * Only runtime geometry copies are owned here; buildings and materials stay owned
 * by CampusViewer. No city scan or geometry creation runs during pointer motion. */
export class LocalSceneContext {
  constructor(roots, capacity = 3) {
    this.root = new THREE.Group(); this.root.name = 'Nearby public street'; this.root.visible = false;
    this.capacity = capacity; this.cache = new Map(); this.data = new WeakMap(); this.sources = []; this.anchors = null; this.activeGroup = null;
    for (const root of roots.filter(Boolean)) root.traverse(object => { if (object.isMesh) this.sources.push(object); });
  }

  async source(object, job) {
    if (!this.data.has(object)) this.data.set(object, await meshData(object, job));
    return this.data.get(object);
  }

  async treeAnchors(job) {
    if (this.anchors) return this.anchors;
    const anchors = [];
    for (const object of this.sources) {
      await job.checkpoint();
      const material = Array.isArray(object.material) ? object.material[0] : object.material;
      if (!isVegetation(material) || /foliage/i.test(material.name)) continue;
      for (const island of await components(await this.source(object, job), job)) {
        if (island.box.min.y > .8 || island.box.max.y - island.box.min.y < 1) continue;
        const centre = island.box.getCenter(new THREE.Vector3());
        if (!anchors.some(p => Math.hypot(p.x - centre.x, p.z - centre.z) < .8)) anchors.push(centre);
      }
    }
    this.anchors = anchors;
    return anchors;
  }

  async build(code, bounds, job) {
    const group = new THREE.Group(), region = bounds.clone();
    region.min.x -= MARGIN; region.max.x += MARGIN; region.min.z -= MARGIN; region.max.z += MARGIN;
    const anchors = await this.treeAnchors(job);
    group.name = `Nearby street ${code}`;
    job.group = group;
    for (const object of this.sources) {
      await job.checkpoint();
      const material = Array.isArray(object.material) ? object.material[0] : object.material;
      if (isPublicBuilding(material)) continue;
      const data = await this.source(object, job);
      if (!overlaps(data.box, region) || data.box.max.y < GROUND_LEVEL) continue;
      let kept = [], clipped = [];
      if (isGround(material, data.box)) ({ kept, clipped } = await cropGround(data, region, job));
      else for (const island of await components(data, job)) {
        const centre = island.box.getCenter(new THREE.Vector3());
        let owner = centre;
        if (isVegetation(material)) {
          let nearest = 6;
          for (const anchor of anchors) { const distance = Math.hypot(anchor.x - centre.x, anchor.z - centre.z); if (distance < nearest) { owner = anchor; nearest = distance; } }
        }
        if (island.box.min.y >= GROUND_LEVEL && contains(region, owner.x, owner.z)) {
          let copied = 0;
          for (const index of island.indices) { kept.push(index); if ((copied++ & 1023) === 0) await job.checkpoint(); }
        }
      }
      const geometry = await copyGeometry(data, kept, clipped, job);
      if (!geometry) continue;
      const mesh = new THREE.Mesh(geometry, object.material);
      mesh.name = object.name; mesh.castShadow = object.castShadow; mesh.receiveShadow = object.receiveShadow;
      mesh.matrixAutoUpdate = false; group.add(mesh);
    }
    group.matrixAutoUpdate = false;
    job.finish();
    group.userData.streetContext = { code, margin: MARGIN, buildMs: performance.now() - job.started, cpuMs: job.cpuMs, maxBlockMs: job.maxBlockMs, yields: job.yields,
      meshes: group.children.length, triangles: group.children.reduce((sum, mesh) => sum + mesh.geometry.index.count / 3, 0),
      bounds: { min: region.min.toArray(), max: region.max.toArray() } };
    return group;
  }

  show(code, group) {
    this.cache.delete(code); this.cache.set(code, group);
    if (group.parent !== this.root) this.root.add(group);
    for (const entry of this.cache.values()) entry.visible = entry === group;
    while (this.cache.size > this.capacity) {
      const [oldCode, oldGroup] = this.cache.entries().next().value;
      oldGroup.traverse(object => object.geometry?.dispose()); oldGroup.removeFromParent(); this.cache.delete(oldCode);
    }
    this.activeGroup = group; this.root.visible = true;
  }

  activate(code, bounds) {
    if (!code || !bounds) { this.hide(); return Promise.resolve(null); }
    if (this.pending?.code === code) return this.pending.promise;
    if (this.pending) this.pending.job.cancelled = true;
    const cached = this.cache.get(code);
    if (cached) { this.pending = null; this.show(code, cached); return Promise.resolve(cached); }
    this.root.visible = false; this.activeGroup = null;
    const job = new BuildJob(), pending = { code, job, promise: null };
    this.pending = pending;
    pending.promise = (async () => {
      let group;
      try {
        // Let the selected building and camera respond before any crop work.
        await job.checkpoint(true);
        group = await this.build(code, bounds, job);
        if (job.cancelled || this.pending !== pending) throw CANCELLED;
        this.show(code, group); this.pending = null;
        return group;
      } catch (error) {
        const discarded = group ?? job.group;
        discarded?.traverse(object => object.geometry?.dispose());
        discarded?.clear(); job.group = null;
        if (this.pending === pending) this.pending = null;
        if (error !== CANCELLED) throw error;
        return null;
      }
    })();
    return pending.promise;
  }

  hide() {
    if (this.pending) this.pending.job.cancelled = true;
    this.pending = null; this.root.visible = false; this.activeGroup = null;
  }

  get ready() { return this.pending?.promise ?? Promise.resolve(this.activeGroup); }

  dispose() {
    this.hide();
    for (const group of this.cache.values()) group.traverse(object => object.geometry?.dispose());
    this.cache.clear(); this.root.clear(); this.root.removeFromParent(); this.data = new WeakMap(); this.activeGroup = null; this.sources = []; this.anchors = null;
  }
}
