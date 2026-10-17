import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { useTimeBasedDamping, stopControlInertia } from "./control-timing.js";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { DRACOLoader } from "three/addons/loaders/DRACOLoader.js";

import { createRenderPipeline, stablePixelRatio } from "./rendering-quality.js";
import { applyInteriorLighting, disposeInteriorLighting } from "./interior-lighting.js";

import { loadOutdoorEnvironment, DAYLIGHT_DIRECTION } from "./outdoor-environment.js";
import { createGroundTextureState, loadGroundTextures, disposeGroundTextures } from "./ground-textures.js";
import { ModelCache } from "./model-cache.js";
import { loadModelInStages, downloadVerifiedModel, downloadCampusModel } from "./model-loading.js";
import { prepareDetailedModel, disposeModel, applySurfaceDetail, refineMaterialFinish, prepareMeshShadows, prepareGlazingSides, isGlazingMaterial } from "./surface-materials.js";

const HOME_DIRECTION = new THREE.Vector3(-0.7, 0.9, 1).normalize();
const COMPANION_CODES = {PAN: "FAW", FAW: "PAN"};

// Static outdoor radiance for glazing: a pale sky, a neutral horizon and stone
// ground. Generate once; no downloaded panorama or per-frame reflection capture.
function createDaylightTexture() {
  const width = 384, height = 192;
  const pixels = new Float32Array(width * height * 4);
  const sky = [0.42, 0.53, 0.62], horizon = [0.8, 0.82, 0.84], ground = [0.22, 0.20, 0.18];
  const sunColor = [1, 0.96, 0.90];
  for (let row = 0; row < height; row++) {
    const latitude = (row / (height - 1) - 0.5) * Math.PI;
    const up = Math.sin(latitude), horizontal = Math.cos(latitude);
    const blend = Math.pow(Math.abs(up), 0.45);
    const pole = up >= 0 ? sky : ground;
    for (let column = 0; column < width; column++) {
      const longitude = (column / width - 0.5) * Math.PI * 2;
      const facingSun = horizontal * Math.cos(longitude) * DAYLIGHT_DIRECTION.x +
        up * DAYLIGHT_DIRECTION.y + horizontal * Math.sin(longitude) * DAYLIGHT_DIRECTION.z;
      const sun = up > 0 ? 8 * Math.exp((facingSun - 1) * 700) : 0;
      const offset = (row * width + column) * 4;
      for (let channel = 0; channel < 3; channel++)
        pixels[offset + channel] = THREE.MathUtils.lerp(horizon[channel], pole[channel], blend) + sun * sunColor[channel];
      pixels[offset + 3] = 1;
    }
  }
  const texture = new THREE.DataTexture(pixels, width, height, THREE.RGBAFormat, THREE.FloatType);
  texture.mapping = THREE.EquirectangularReflectionMapping;
  texture.colorSpace = THREE.LinearSRGBColorSpace;
  texture.needsUpdate = true;
  return texture;
}

const reducedMotion = matchMedia("(prefers-reduced-motion: reduce)");
// Match the CSS bottom-sheet breakpoint, not the canvas narrowed by a desktop sidebar.
const mobileLayout = matchMedia("(max-width: 700px)");
const boxFromData = ({ min, max }) =>
  new THREE.Box3(new THREE.Vector3(...min), new THREE.Vector3(...max));

/** Rendering and camera state are separate from the accessible HTML interface. */
export class CampusViewer {
  constructor(container, labels, buildings, onPick, onContextLost, onDetailState = () => {}, modelRevision = "", onBearingChange = null) {
    this.container = container;
    this.labelLayer = labels;
    this.buildings = buildings;
    this.modelRevision = modelRevision;
    this.onPick = onPick;
    this.onDetailState = onDetailState;
    this.onBearingChange = onBearingChange;
    this.lastBearing = null;
    this.detailRequest = 0;
    this.activeDetail = null;
    this.disposed = false;
    this.loadController = new AbortController();
    this.groundTextures = createGroundTextureState();
    this.groups = new Map();
    this.interiors = new Map();
    this.interiorLoads = new Map();
    this.activeInterior = null;
    this.exteriors = new Map();
    this.exteriorLoads = new Map();
    this.labels = [];
    this.activeCode = null;
    this.mode = "campus";
    this.labelsVisible = true;
    this.contextVisible = true;
    this.ready = false;
    this.frame = 0;
    this.viewRequest = 0;
    this.needsRender = true;
    this.renderer = new THREE.WebGLRenderer({
      // Keep Metal clipping stable; the output pipeline smooths edges without MSAA.
      antialias: false,
      logarithmicDepthBuffer: true,
      powerPreference: "high-performance",
    });
    this.renderer.setPixelRatio(stablePixelRatio(container.clientWidth, container.clientHeight));
    this.renderer.setClearColor(0xe9e8e3);
    this.renderer.toneMapping = THREE.NeutralToneMapping;
    this.renderer.toneMappingExposure = 0.9;
    this.renderer.outputColorSpace = THREE.SRGBColorSpace;
    this.canvas = this.renderer.domElement;
    this.canvas.tabIndex = 0;
    this.canvas.setAttribute(
      "aria-label",
      "校园3D模型。方向键平移，加减键缩放，Home返回总览。也可使用建筑目录。",
    );
    this.container.append(this.canvas);
    this.scene = new THREE.Scene();
    this.detailGround = new THREE.Mesh(
      new THREE.PlaneGeometry(6000, 6000),
      new THREE.ShadowMaterial({ color: 0x34312b, opacity: 0.2 }),
    );
    this.detailGround.rotation.x = -Math.PI / 2;
    this.detailGround.position.y = -0.03;
    this.detailGround.receiveShadow = true;
    this.detailGround.visible = false;
    this.scene.add(this.detailGround);
    this.camera = new THREE.PerspectiveCamera(38, 1, 0.02, 6000);
    this.camera.position.set(-280, 330, 370);
    this.renderPipeline = createRenderPipeline(this.renderer, this.scene, this.camera,
      () => this.mode === "campus" && !this.activeCode &&
        this.camera.position.distanceTo(this.controls?.target ?? this.camera.position) > 130);
    this.controls = new OrbitControls(this.camera, this.canvas);
    this.controlPosition = new THREE.Vector3();
    this.controlTarget = new THREE.Vector3();
    this.controlRotation = new THREE.Quaternion();
    this.inertiaMoving = false;
    this.controls.enableDamping = true;
    this.controls.dampingFactor = 0.08;
    useTimeBasedDamping(this.controls);
    this.controls.minDistance = 0.25;
    this.controls.maxDistance = 2400;
    this.controls.zoomToCursor = true;
    this.controls.zoomSpeed = 1.25;
    this.controls.maxPolarAngle = Math.PI;
    this.controls.screenSpacePanning = true;
    this.controls.target.set(10, 0, -10);
    this.controls.addEventListener("change", () => {
      // Inertia and keyboard/tween motion also reserve the navigation frame.
      this.lastNavigationAt = performance.now();
      this.needsRender = true;
    });
    this.interacting = false;
    this.lastNavigationAt = 0;
    this.controls.addEventListener("start", () => {
      this.transition = null;
      this.interacting = true;
      this.lastNavigationAt = performance.now();
      this.needsRender = true;
    });
    this.controls.addEventListener("end", () => {
      this.interacting = false;
      this.lastNavigationAt = performance.now();
      this.needsRender = true;
    });
    this.hemisphere = new THREE.HemisphereLight(0xf4f6ff, 0x8d8274, 0.65);
    this.scene.add(this.hemisphere);
    const sun = new THREE.DirectionalLight(0xfff4e4, 3.0);
    sun.position.copy(DAYLIGHT_DIRECTION).multiplyScalar(290);
    sun.castShadow = true;
    sun.shadow.mapSize.set(4096, 4096);
    Object.assign(sun.shadow.camera, {
      left: -310,
      right: 310,
      top: 310,
      bottom: -310,
      near: 1,
      far: 650,
    });
    sun.shadow.normalBias = 0.04;
    sun.shadow.bias = -0.0005;
    this.sun = sun;
    this.scene.add(sun.target);
    this.renderer.shadowMap.enabled = true;
    this.renderer.shadowMap.type = THREE.PCFShadowMap;
    this.renderer.shadowMap.autoUpdate = false;
    this.scene.add(sun);
    const fill = new THREE.DirectionalLight(0xe7edff, 0.25);
    fill.position.set(100, 70, -130);
    this.fill = fill;
    this.scene.add(fill);
    const pmrem = new THREE.PMREMGenerator(this.renderer);
    const environment = createDaylightTexture();
    this.environmentTarget = pmrem.fromEquirectangular(environment);
    this.scene.environment = this.environmentTarget.texture;
    this.scene.environmentIntensity = 0.35;
    environment.dispose();
    pmrem.dispose();
    this.draco = new DRACOLoader()
      .setDecoderPath({
        js: "/draco/draco_wasm_wrapper.js",
        wasm: "/draco/draco_decoder.wasm",
      })
      .setWorkerLimit(Math.min(4, Math.max(2, navigator.hardwareConcurrency || 2)));
    this.draco.preload();
    this.loader = new GLTFLoader().setDRACOLoader(this.draco);
    this.detailCache = new ModelCache(
      async (url) => (await this.loadAsset(url)).scene,
      (group) => { prepareDetailedModel(group, this.environmentTarget.texture, this.groundTextures); this.applyEnvironmentRotation(group); this.scene.add(group); },
      disposeModel,
      matchMedia("(max-width: 720px)").matches ? 2 : 3,
    );
    this.raycaster = new THREE.Raycaster();
    this.pointer = new THREE.Vector2();
    this.canvas.addEventListener("pointerdown", (event) => {
      if (!event.isPrimary) {
        this.pointerStart = null;
        return;
      }
      this.pointerStart = {
        moved: false,
        x: event.clientX,
        y: event.clientY,
        time: performance.now(),
        id: event.pointerId,
      };
    });
    this.canvas.addEventListener("pointermove", (event) => this.trackPointer(event));
    this.canvas.addEventListener("pointercancel", () => { this.pointerStart = null; });
    this.canvas.addEventListener("pointerup", (event) => this.pick(event));
    this.canvas.addEventListener("dblclick", (event) => this.focusSurface(event));
    this.canvas.addEventListener("keydown", (event) => this.onKey(event));
    this.canvas.addEventListener("webglcontextlost", (event) => {
      event.preventDefault();
      this.ready = false;
      onContextLost();
    });
    this.resizeObserver = new ResizeObserver(() => this.resize());
    this.resizeObserver.observe(container);
    this.resize();
    this.tick = this.tick.bind(this);
    this.frame = requestAnimationFrame(this.tick);
  }

  applyEnvironmentRotation(group) {
    group.traverse(object => {
      for (const material of Array.isArray(object.material) ? object.material : [object.material])
        if (material?.envMap) material.envMapRotation?.copy(this.scene.environmentRotation);
    });
  }

  async loadAsset(url, onProgress, beforeDecode) {
    // Fixed model names must follow the freshly loaded catalogue across releases.
    // Detailed models already carry their content hash in the filename.
    if (this.modelRevision && url.startsWith("/models/") && !url.startsWith("/models/details/")) {
      url += `?v=${encodeURIComponent(this.modelRevision)}`;
    }
    const transferController = new AbortController();
    const assets = this.buildings.flatMap(building => [building.detailedExterior,
      building.detailedInterior, ...(building.interiorSpaces || []).map(space => space.detailedInterior)]);
    const expectedSha256 = assets.find(asset => asset?.url === url)?.sha256;
    return loadModelInStages(
      progress => (url.startsWith("/models/campus.glb") ? downloadCampusModel : downloadVerifiedModel)(url, {signal: transferController.signal, onProgress: progress, expectedSha256}),
      bytes => this.loader.parseAsync(bytes, THREE.LoaderUtils.extractUrlBase(url)),
      {
        signal: this.loadController.signal,
        onProgress,
        beforeDecode,
        cancelDownload: () => transferController.abort(),
        discardModel: model => disposeModel(model.scene),
      },
    );
  }

  async load(onProgress) {
    const gltf = await this.loadAsset("/models/campus.glb", onProgress);
    this.campus = gltf.scene;
    this.scene.add(this.campus);
    const codes = new Set(this.buildings.map((b) => b.code));
    this.campus.traverse((object) => {
      const code = object.userData.buildingCode;
      if (code) this.groups.set(code, object);
    });
    const contextMeshes = new Set();
    this.groups.get("CONTEXT")?.traverse((object) => {
      if (object.isMesh) contextMeshes.add(object);
    });
    this.campus.traverse((object) => {
      if (object.isMesh) {
        prepareMeshShadows(object);
        const materials = Array.isArray(object.material)
          ? object.material
          : [object.material];
        object.material = materials.map((material) => {
          const copy = material.clone();
          prepareGlazingSides(copy);
          refineMaterialFinish(copy, this.environmentTarget.texture);
          if (contextMeshes.has(object) && !isGlazingMaterial(copy)) {
            // Calm opaque surroundings without overwriting the same glass
            // reflection finish used by selected campus buildings.
            // Retain authored wall/roof colour roles before shader uniforms exist.
            const luminance = copy.color.r * .2126 + copy.color.g * .7152 + copy.color.b * .0722;
            copy.color.lerp(new THREE.Color(luminance, luminance, luminance), .14);
            const roof = /lead|slate/i.test(copy.name);
            copy.roughness = roof ? .82 : .94;
            copy.metalness = roof ? .2 : 0;
          }
          applySurfaceDetail(copy, this.groundTextures);
          return copy;
        });
        if (object.material.length === 1) object.material = object.material[0];
      }
    });
    this.groups.get("SITE")?.traverse((object) => {
      if (object.isMesh) object.castShadow = false;
    });
    for (const object of contextMeshes) object.castShadow = false;
    this.pickable = [...this.groups]
      .filter(([code]) => codes.has(code))
      .map(([, object]) => object);
    this.campusBounds = new THREE.Box3();
    for (const building of this.buildings) {
      if (building.bounds)
        this.campusBounds.union(boxFromData(building.bounds));
      if (
        building.bounds &&
        (building.status === "detailed" || building.code === "CON")
      )
        this.addLabel(building);
    }
    this.ready = true;
    this.renderer.shadowMap.needsUpdate = true;
    this.home(false);
    this.needsRender = true;
    this.canvas.dataset.ready = "true";
    this.environmentReady = Promise.all([loadOutdoorEnvironment(this), loadGroundTextures(this)]);
    void this.loadCampusExteriors();
  }

  // Exterior geometry belongs to the campus, not to a temporary selection.
  async loadExterior(building, background = false) {
    if (this.exteriors.has(building.code)) return this.exteriors.get(building.code);
    if (this.exteriorLoads.has(building.code)) return this.exteriorLoads.get(building.code);
    const pending = (async () => {
      const { scene: group } = await this.loadAsset(
        building.detailedExterior.url, undefined,
        background ? () => this.waitForBackgroundFrame(() => this.activeCode === building.code) : undefined,
      );
      if (this.disposed) {
        disposeModel(group);
        throw new Error("Viewer disposed");
      }
      if (background && !await this.waitForBackgroundFrame(() => this.activeCode === building.code)) {
        disposeModel(group);
        throw new Error("Viewer disposed");
      }
      prepareDetailedModel(group, this.environmentTarget.texture, this.groundTextures);
      this.applyEnvironmentRotation(group);
      group.userData.buildingCode = building.code;
      this.scene.add(group);
      this.exteriors.set(building.code, group);
      this.toggleContext(this.contextVisible);
      return group;
    })();
    this.exteriorLoads.set(building.code, pending);
    try { return await pending; }
    finally { this.exteriorLoads.delete(building.code); }
  }

  navigationIsBusy() {
    return document.hidden || this.interacting || Boolean(this.transition) ||
      performance.now() - this.lastNavigationAt < 200;
  }

  // Download/decode off the navigation path; attach only after inertia settles.
  // An explicitly selected building keeps priority over background decoration.
  waitForBackgroundFrame(isPriority = () => false) {
    return new Promise((resolve) => {
      const signal = this.loadController.signal;
      let timer = null, idle = null;
      const finish = (ready) => {
        clearTimeout(timer);
        if (idle !== null) cancelIdleCallback(idle);
        signal.removeEventListener("abort", aborted);
        resolve(ready);
      };
      const aborted = () => finish(false);
      const busy = () => !isPriority() && this.navigationIsBusy();
      const completeIfCurrent = () => {
        idle = null;
        if (signal.aborted || this.disposed) return finish(false);
        // A wheel start/end can occur between the idle request and its callback.
        if (busy()) return check();
        finish(true);
      };
      const check = () => {
        if (signal.aborted || this.disposed) return finish(false);
        if (busy()) {
          timer = setTimeout(check, 50);
          return;
        }
        if (isPriority()) return finish(true);
        if (typeof requestIdleCallback === "function") {
          idle = requestIdleCallback(completeIfCurrent, { timeout: 100 });
        } else timer = setTimeout(completeIfCurrent, 0);
      };
      signal.addEventListener("abort", aborted, { once: true });
      check();
    });
  }

  async loadCampusExteriors() {
    const buildings = this.buildings.filter((building) => building.detailedExterior);
    buildings.sort((a, b) => Number(b.code === "MAR") - Number(a.code === "MAR"));
    for (const building of buildings) {
      if (!await this.waitForBackgroundFrame()) return;
      try { await this.loadExterior(building, true); }
      catch (error) {
        if (!this.disposed) console.warn(`Exterior unavailable: ${building.code}`, error);
      }
    }
  }

  addLabel(building) {
    const button = document.createElement("button");
    button.className = "map-label";
    button.dataset.code = building.code;
    button.setAttribute("aria-label", `${building.code} ${building.name}`);
    const code = document.createElement("b");
    code.textContent = building.code;
    const name = document.createElement("span");
    name.className = "label-name";
    name.textContent = building.name;
    button.append(code, name);
    button.addEventListener("click", () => this.onPick(building.code));
    this.labelLayer.append(button);
    const box = boxFromData(building.bounds);
    const position = box.getCenter(new THREE.Vector3());
    position.y = box.max.y + 1;
    this.labels.push({ code: building.code, button, position });
  }

  resize() {
    const width = this.container.clientWidth;
    const height = this.container.clientHeight;
    if (!width || !height) return;
    // Read layout only on ResizeObserver notifications, not every orbit frame.
    this.viewportWidth = width;
    this.viewportHeight = height;
    this.renderer.setPixelRatio(stablePixelRatio(width, height));
    this.renderer.setSize(width, height);
    this.renderPipeline.resize(width, height);
    this.camera.aspect = width / height;
    this.updateCameraProjection();
    this.needsRender = true;
  }

  updateCameraProjection() {
    const width = this.container.clientWidth;
    const height = this.container.clientHeight;
    this.camera.clearViewOffset();
    if ((this.mode === "detail" || (this.mode === "interior" && this.activeInterior?.authoredView)) &&
        mobileLayout.matches && width > 0 && height > 0) {
      // Keep the authored eye inside the room; shift its view above the mobile sheet.
      this.camera.setViewOffset(width, height, 0, height * 0.22, width, height);
    }
    this.camera.updateProjectionMatrix();
  }

  fit(bounds, animate = true, direction = HOME_DIRECTION, framingCorners = null) {
    const box = bounds instanceof THREE.Box3 ? bounds : boxFromData(bounds);
    const corners = framingCorners
      ? framingCorners.map(point => new THREE.Vector3(...point))
      : [box.min.x, box.max.x].flatMap(x => [box.min.y, box.max.y].flatMap(y =>
          [box.min.z, box.max.z].map(z => new THREE.Vector3(x, y, z))));
    const center = framingCorners
      ? corners.reduce((sum, point) => sum.add(point), new THREE.Vector3()).divideScalar(corners.length)
      : box.getCenter(new THREE.Vector3());
    const mobileDetail = mobileLayout.matches && this.activeCode;
    const up = new THREE.Vector3(0, 1, 0);
    const right = new THREE.Vector3().crossVectors(up, direction);
    // An exactly vertical view still needs a horizontal frame for fitting bounds.
    if (right.lengthSq() < 1e-8) right.set(1, 0, 0);
    else right.normalize();
    const cameraUp = new THREE.Vector3().crossVectors(direction, right).normalize();
    const tangent = Math.tan(THREE.MathUtils.degToRad(this.camera.fov / 2));
    let distance = 14;
    for (const point of corners) {
      const corner = point.clone().sub(center);
      const horizontal = Math.abs(corner.dot(right)) / (tangent * this.camera.aspect);
      const vertical = Math.abs(corner.dot(cameraUp)) / (tangent * (mobileDetail ? 0.44 : 0.8));
      distance = Math.max(distance, corner.dot(direction) + Math.max(horizontal, vertical) * 1.2);
    }
    if (mobileDetail) center.addScaledVector(cameraUp, -distance * tangent * 0.44);
    const position = center.clone().addScaledVector(direction, distance);
    this.moveCamera(position, center, animate);
  }

  moveCamera(position, target, animate = true) {
    if (!animate || reducedMotion.matches) {
      // Consume the previous drag's residual motion before installing a new scene pose.
      const nextPosition = position.clone();
      const nextTarget = target.clone();
      const damping = this.controls.enableDamping;
      this.controls.enableDamping = false;
      this.controls.update();
      this.camera.position.copy(nextPosition);
      this.controls.target.copy(nextTarget);
      this.transition = null;
      this.controls.update();
      this.controls.enableDamping = damping;
      this.needsRender = true;
      return;
    }
    stopControlInertia(this.controls);
    this.inertiaMoving = false;
    this.transition = {
      start: performance.now(),
      duration: 620,
      fromPosition: this.camera.position.clone(),
      fromTarget: this.controls.target.clone(),
      position,
      target,
    };
    this.needsRender = true;
  }

  home(animate = true) {
    if (!this.ready) return;
    this.showCampus();
    this.highlight(null);
    this.toggleContext(true);
    this.mode = "campus";
    this.fit(this.campusBounds, animate);
    this.fitSunShadow(this.campusBounds);
  }

  setInteriorLighting(interior) {
    applyInteriorLighting(this, interior);
  }

  showCampus() {
    this.clearInteriorSection();
    this.viewRequest += 1;
    this.detailRequest += 1;
    this.detailCache.activate(null);
    this.detailCache.hideAll();
    this.activeDetail = null;
    this.activeInterior = null;
    delete this.canvas.dataset.interiorSpace;
    delete this.canvas.dataset.detailReady;
    this.campus.visible = true;
    this.controls.maxPolarAngle = Math.PI;
    this.controls.minDistance = 0.25;
    this.camera.fov = 38;
    this.mode = "campus";
    this.setInteriorLighting(false);
    this.updateCameraProjection();
    this.renderer.shadowMap.needsUpdate = true;
    for (const group of this.interiors.values()) group.visible = false;
    this.needsRender = true;
  }

  select(building) {
    if (!this.ready) return;
    this.showCampus();
    this.highlight(building.code);
    this.toggleContext(false);
    // Sidebar changes can precede ResizeObserver; fit using the current canvas size.
    this.resize();
    // Fit the actual shell orientation, including the visible adjoining tower.
    const companion = this.buildings.find(b => b.code === COMPANION_CODES[building.code]);
    const framingCorners = building.exteriorFramingCorners
      ? [...building.exteriorFramingCorners, ...(companion?.exteriorFramingCorners ?? [])]
      : null;
    if (building.bounds)
      this.fit(
        building.bounds,
        true,
        building.exteriorDirection
          ? new THREE.Vector3(...building.exteriorDirection)
          : HOME_DIRECTION,
        framingCorners,
      );
    if (building.bounds) this.fitSunShadow(boxFromData(building.bounds));
    this.upgradeModel(building, "exterior");
  }

  interiorSpace(building, spaceId = null) {
    if (spaceId === null) return building;
    return building.interiorSpaces?.find((space) => space.id === spaceId) ?? null;
  }

  async upgradeModel(building, kind, spaceId = null) {
    const interior = kind === "interior" ? this.interiorSpace(building, spaceId) : null;
    const asset = kind === "interior" ? interior?.detailedInterior : building.detailedExterior;
    if (!asset || !this.ready) return;
    const interiorKey = `${building.code}:${spaceId ?? "default"}`;
    const detailKey = `${kind}-${building.code}${spaceId === null ? "" : `:${spaceId}`}`;
    const isCurrent = () => !this.disposed && request === this.detailRequest &&
      this.activeCode === building.code &&
      (kind !== "interior" || (this.mode === "interior" && this.activeInterior?.key === interiorKey));
    const request = ++this.detailRequest;
    this.onDetailState({ code: building.code, kind, spaceId, state: "loading" });
    try {
      const group = kind === "exterior"
        ? await this.loadExterior(building)
        : await this.detailCache.request(detailKey, asset.url);
      if (!isCurrent()) return;
      this.detailCache.hideAll();
      this.activeDetail = { code: building.code, kind, spaceId, group };
      const base = kind === "exterior" ? this.groups.get(building.code) : this.interiors.get(interiorKey);
      if (base) base.visible = false;
      group.visible = true;
      if (kind === "interior") {
        const section = interior?.interiorSections?.find(item => item.id === this.canvas.dataset.interiorSection);
        this.applyInteriorDisplayGroups(section?.displayGroups);
      }
      this.canvas.dataset.detailReady = detailKey;
      this.renderer.shadowMap.needsUpdate = true;
      this.needsRender = true;
      this.onDetailState({ code: building.code, kind, spaceId, state: "ready" });
    } catch (error) {
      if (!isCurrent() || error.name === "AbortError") return;
      this.onDetailState({ code: building.code, kind, spaceId, state: "error" });
    }
  }

  retryDetails(building) {
    if (this.activeInterior?.code === building.code) {
      return this.showInterior(building, this.activeInterior.spaceId);
    }
    return this.upgradeModel(building, "exterior");
  }

  highlight(code) {
    this.activeCode = code;
    for (const [name, group] of this.groups) {
      if (["SITE", "CONTEXT", "LANDSCAPE"].includes(name)) continue;
      group.traverse((object) => {
        if (!object.isMesh) return;
        const materials = Array.isArray(object.material)
          ? object.material
          : [object.material];
        for (const material of materials) {
          // Authored light artwork keeps its emission across selection changes.
          if (material.userData.webEmission) continue;
          material.emissive?.set(name === code ? 0x521011 : 0x000000);
          material.emissiveIntensity = name === code ? 0.2 : 0;
        }
      });
    }
    if (code && !this.labels.some((label) => label.code === code)) {
      const building = this.buildings.find((b) => b.code === code);
      if (building?.bounds) this.addLabel(building);
    }
    for (const label of this.labels)
      label.button.classList.toggle("is-selected", label.code === code);
    this.needsRender = true;
  }

  showDetail(building) {
    if (!this.ready || !building.detailView) return;
    this.select(building);
    this.mode = "detail";
    const view = building.detailView;
    const target = new THREE.Vector3(...view.target);
    const position = new THREE.Vector3(...view.position);
    this.camera.fov = view.fov;
    this.updateCameraProjection();
    this.controls.minDistance = 0.15;
    if (mobileLayout.matches) {
      // Keep the doorway in the free upper area above the mobile detail sheet.
      target.y -= 0.6;
      position.y -= 0.6;
      const offset = position.clone().sub(target).multiplyScalar(1.45);
      position.copy(target).add(offset);
    }
    this.moveCamera(position, target);
  }

  async loadInterior(building, spaceId, interior) {
    const key = `${building.code}:${spaceId ?? "default"}`;
    if (this.interiors.has(key)) return this.interiors.get(key);
    if (this.interiorLoads.has(key)) return this.interiorLoads.get(key);
    const asset = interior.interiorAsset;
    const url = typeof asset === "string" ? asset : asset?.url;
    // Additional rooms must never silently load the building's default lobby.
    const source = url ?? (spaceId === null ? `/models/${building.code.toLowerCase()}-interior.glb` : null);
    if (!source) throw new Error(`Missing interior asset: ${key}`);
    const loading = (async () => {
      const gltf = await this.loadAsset(source);
      if (this.disposed) {
        disposeModel(gltf.scene);
        return null;
      }
      // The initial interior and its upgraded detail use the same finish and
      // daylight binding, so loading cannot briefly show a different glazing.
      prepareDetailedModel(gltf.scene, this.environmentTarget.texture, this.groundTextures);
      this.applyEnvironmentRotation(gltf.scene);
      this.scene.add(gltf.scene);
      this.interiors.set(key, gltf.scene);
      return gltf.scene;
    })();
    this.interiorLoads.set(key, loading);
    try {
      return await loading;
    } finally {
      this.interiorLoads.delete(key);
    }
  }

  async showInterior(building, spaceId = null) {
    const interior = this.interiorSpace(building, spaceId);
    if (!this.ready || !interior || this.activeCode !== building.code) return false;
    this.detailRequest += 1;
    this.detailCache.activate(null);
    const code = building.code;
    const key = `${code}:${spaceId ?? "default"}`;
    const request = ++this.viewRequest;
    this.activeInterior = { code, spaceId, key, authoredView: Boolean(interior.interiorView) };
    delete this.canvas.dataset.detailReady;
    delete this.canvas.dataset.interiorSpace;
    try {
      await this.loadInterior(building, spaceId, interior);
    } catch (error) {
      if (this.disposed || request !== this.viewRequest || this.activeCode !== code) return false;
      throw error;
    }
    // Check both selection and request generation: even A -> B -> A can finish out of order.
    if (this.disposed || this.activeCode !== code || request !== this.viewRequest ||
        this.activeInterior?.key !== key) return false;
    this.detailCache.hideAll();
    this.activeDetail = null;
    this.canvas.dataset.interiorSpace = spaceId ?? "default";
    this.campus.visible = false;
    for (const [name, group] of this.interiors) group.visible = name === key;
    this.clearInteriorSection();
    this.mode = "interior";
    this.setInteriorLighting(true);
    this.fitSunShadow(boxFromData(interior.interiorBounds));
    this.toggleContext(this.contextVisible);
    this.updateCameraProjection();
    this.controls.maxPolarAngle = Math.PI;
    this.controls.minDistance = 0.15;
    this.renderer.shadowMap.needsUpdate = true;
    if (interior.interiorView) {
      const view = interior.interiorView;
      this.camera.fov = view.fov;
      this.updateCameraProjection();
      // Both models occupy different spaces. Enter at the usable interior pose
      // directly instead of flying through the hidden campus or fitting its shell.
      this.moveCamera(
        new THREE.Vector3(...view.position),
        new THREE.Vector3(...view.target),
        false,
      );
    } else {
      this.fit(
        interior.interiorBounds,
        false,
        new THREE.Vector3(-0.7, 0.55, 1).normalize(),
      );
    }
    // Retain the resolved entry framing as well as authored views. Buildings
    // without a fixed camera still need a reliable return from a level closeup.
    this.activeInterior.defaultView = {
      position: (this.transition?.position ?? this.camera.position).toArray(),
      target: (this.transition?.target ?? this.controls.target).toArray(),
      fov: this.camera.fov,
    };
    this.needsRender = true;
    void this.upgradeModel(building, "interior", spaceId);
    return true;
  }

  applyInteriorDisplayGroups(allowedGroups = null) {
    const allowed = allowedGroups ? new Set(allowedGroups) : null;
    const roots = new Set(this.interiors.values());
    if (this.activeDetail?.kind === "interior") roots.add(this.activeDetail.group);
    for (const root of roots) root.traverse(object => {
      const group = object.userData.interiorDisplayGroup;
      if (group) object.visible = !allowed || allowed.has(group);
    });
  }

  clearInteriorSection() {
    this.applyInteriorDisplayGroups();
    this.renderer.clippingPlanes = [];
    this.renderer.shadowMap.enabled = true;
    this.renderer.shadowMap.needsUpdate = true;
    delete this.canvas.dataset.interiorSection;
    this.needsRender = true;
  }

  setInteriorSection(building, id) {
    if (this.mode !== "interior" || this.activeCode !== building.code) return false;
    const interior = this.interiorSpace(building, this.activeInterior?.spaceId ?? null);
    const section = interior?.interiorSections?.find(item => item.id === id);
    if (id !== "all" && !section) return false;
    const bounds = boxFromData(interior.interiorBounds);
    if (section) {
      if (!Number.isFinite(section.minHeight) || !Number.isFinite(section.maxHeight)
          || section.maxHeight <= section.minHeight) return false;
      bounds.min.y = Math.max(bounds.min.y, section.minHeight);
      bounds.max.y = Math.min(bounds.max.y, section.maxHeight);
      if (bounds.max.y <= bounds.min.y) return false;
    }
    // Validate the new slice before changing the current visible slice.
    this.clearInteriorSection();
    if (section) {
      this.renderer.clippingPlanes = [
        new THREE.Plane(new THREE.Vector3(0, 1, 0), -section.minHeight),
        new THREE.Plane(new THREE.Vector3(0, -1, 0), section.maxHeight),
      ];
      // Hidden upper floors must not cast shadows onto the selected floor.
      this.renderer.shadowMap.enabled = false;
    }
    this.applyInteriorDisplayGroups(section?.displayGroups);
    this.canvas.dataset.interiorSection = id;
    const view = section?.view ?? (id === "all"
      ? interior.interiorView ?? this.activeInterior.defaultView : null);
    // A section preset is an authored interior view even when the building's
    // default entry was fitted automatically. Clear that state again for floor fits.
    this.activeInterior.authoredView = Boolean(section?.view || (id === "all" && interior.interiorView));
    if (view) {
      this.camera.fov = view.fov;
      this.updateCameraProjection();
      const target = new THREE.Vector3(...view.target);
      const position = new THREE.Vector3(...view.position);
      // Preserve the reference composition when a sidebar or phone narrows the
      // canvas. The gallery's reference aspect keeps its original camera pose.
      if (Number.isFinite(view.referenceAspect) && view.referenceAspect > 0) {
        const scale = Math.max(1, view.referenceAspect / this.camera.aspect);
        position.sub(target).multiplyScalar(scale).add(target);
      }
      this.moveCamera(position, target);
    } else {
      this.updateCameraProjection();
      const direction = this.camera.position.clone().sub(this.controls.target).normalize();
      if (direction.y < 0.25) direction.y = 0.65;
      this.fit(bounds, true, direction.normalize());
    }
    this.needsRender = true;
    return true;
  }

  toggleContext(visible) {
    this.contextVisible = visible;
    this.detailGround.visible = this.mode !== "interior" && Boolean(this.activeCode) && !visible;
    const companion = COMPANION_CODES[this.activeCode] ?? null;
    for (const [name, group] of this.groups) {
      if (name === "SITE") {
        group.visible = visible || !this.activeCode;
        continue;
      }
      if (name === "CONTEXT" || name === "LANDSCAPE") group.visible = visible;
      else
        group.visible =
          !this.activeCode ||
          visible ||
          name === this.activeCode ||
          name === companion;
    }
    const visibleExteriors = [];
    for (const [code, group] of this.exteriors) {
      group.visible = this.mode !== "interior" &&
        (!this.activeCode || visible || code === this.activeCode || code === companion);
      if (group.visible) {
        const base = this.groups.get(code);
        if (base) base.visible = false;
        visibleExteriors.push(code);
      }
    }
    this.canvas.dataset.campusDetails = visibleExteriors.sort().join(",");
    this.renderer.shadowMap.needsUpdate = true;
    this.needsRender = true;
  }

  toggleLabels(visible) {
    this.labelsVisible = visible;
    this.needsRender = true;
  }

  // Spend the shadow-map resolution on the space currently being inspected.
  fitSunShadow(bounds) {
    const centre = bounds.getCenter(new THREE.Vector3());
    const radius = Math.max(12, bounds.getSize(new THREE.Vector3()).length() * 0.65);
    this.sun.target.position.copy(centre);
    this.sun.position.copy(centre).addScaledVector(
      DAYLIGHT_DIRECTION, radius * 3,
    );
    Object.assign(this.sun.shadow.camera, {
      left: -radius, right: radius, top: radius, bottom: -radius,
      near: 0.1, far: radius * 6,
    });
    this.sun.shadow.camera.updateProjectionMatrix();
    this.sun.target.updateMatrixWorld();
    this.renderer.shadowMap.needsUpdate = true;
  }

  zoom(factor) {
    const pending = this.transition?.kind === "zoom" ? this.transition : null;
    const target = (pending?.target ?? this.controls.target).clone();
    const offset = (pending?.position ?? this.camera.position)
      .clone().sub(target).multiplyScalar(factor);
    offset.setLength(
      THREE.MathUtils.clamp(
        offset.length(),
        this.controls.minDistance,
        this.controls.maxDistance,
      ),
    );
    this.moveCamera(
      target.clone().add(offset), target,
    );
    if (this.transition) {
      this.transition.kind = "zoom";
      this.transition.duration = 180;
    }
  }

  north() {
    this.moveCamera(
      this.controls.target
        .clone()
        .add(
          new THREE.Vector3(
            0,
            this.camera.position.distanceTo(this.controls.target),
            0.1,
          ),
        ),
      this.controls.target.clone(),
    );
  }

  trackPointer(event) {
    const start = this.pointerStart;
    // Remember the whole gesture, including drags that return to their origin.
    if (start?.id === event.pointerId &&
        Math.hypot(event.clientX - start.x, event.clientY - start.y) > 6) {
      start.moved = true;
    }
  }

  focusSurface(event) {
    if (!this.ready || !this.activeCode || event.button !== 0) return;
    const root = this.activeDetail?.group ??
      (this.activeInterior ? this.interiors.get(this.activeInterior.key) :
        this.exteriors.get(this.activeCode) ?? this.groups.get(this.activeCode));
    if (!root?.visible) return;
    const meshes = [];
    root.traverseVisible(object => { if (object.isMesh) meshes.push(object); });
    const rect = this.canvas.getBoundingClientRect();
    this.pointer.set(
      (event.clientX - rect.left) / rect.width * 2 - 1,
      -(event.clientY - rect.top) / rect.height * 2 + 1,
    );
    this.raycaster.setFromCamera(this.pointer, this.camera);
    const hit = this.raycaster.intersectObjects(meshes, false).find(hit =>
      this.renderer.clippingPlanes.every(plane => plane.distanceToPoint(hit.point) >= 0));
    if (!hit || hit.distance <= this.controls.minDistance) return;
    this.transition = null;
    // Keep the observer in place; subsequent rotation orbits the chosen detail.
    this.controls.target.copy(hit.point);
    this.controls.update();
    this.needsRender = true;
  }

  pick(event) {
    if (
      !this.ready ||
      this.mode !== "campus" ||
      event.button !== 0 ||
      !this.pointerStart
    )
      return;
    const start = this.pointerStart;
    this.pointerStart = null;
    if (
      start.moved ||
      event.detail > 1 ||
      start.id !== event.pointerId ||
      Math.hypot(event.clientX - start.x, event.clientY - start.y) > 6 ||
      performance.now() - start.time > 600
    )
      return;
    const rect = this.canvas.getBoundingClientRect();
    this.pointer.set(
      ((event.clientX - rect.left) / rect.width) * 2 - 1,
      -((event.clientY - rect.top) / rect.height) * 2 + 1,
    );
    this.raycaster.setFromCamera(this.pointer, this.camera);
    const visibleBuildings = this.pickable.filter((group) => group.visible);
    visibleBuildings.push(...[...this.exteriors.values()].filter((group) => group.visible));
    const hit = this.raycaster.intersectObjects(visibleBuildings, true)[0];
    if (!hit) return;
    let object = hit.object;
    while (object && !object.userData.buildingCode) object = object.parent;
    if (object && object.userData.buildingCode !== this.activeCode)
      this.onPick(object.userData.buildingCode);
  }

  onKey(event) {
    if (event.key === "+" || event.key === "=") {
      event.preventDefault();
      this.zoom(0.8);
    } else if (event.key === "-") {
      event.preventDefault();
      this.zoom(1.25);
    } else if (event.key === "Home") {
      event.preventDefault();
      this.onPick(null);
    } else if (
      ["ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight"].includes(event.key)
    ) {
      event.preventDefault();
      this.transition = null;
      const scale =
        this.camera.position.distanceTo(this.controls.target) * 0.04;
      const delta = new THREE.Vector3();
      const horizontal = new THREE.Vector3().setFromMatrixColumn(
        this.camera.matrixWorld,
        0,
      );
      const vertical = new THREE.Vector3().setFromMatrixColumn(
        this.camera.matrixWorld,
        1,
      );
      if (event.key === "ArrowLeft") delta.addScaledVector(horizontal, -scale);
      if (event.key === "ArrowRight") delta.addScaledVector(horizontal, scale);
      if (event.key === "ArrowUp") delta.addScaledVector(vertical, scale);
      if (event.key === "ArrowDown") delta.addScaledVector(vertical, -scale);
      this.camera.position.add(delta);
      this.controls.target.add(delta);
      this.needsRender = true;
    }
  }

  updateLabels() {
    const width = this.viewportWidth;
    const height = this.viewportHeight;
    const occupied = [];
    const mobileDetail = mobileLayout.matches && this.activeCode;
    const ordered = [...this.labels].sort(
      (a, b) =>
        Number(b.code === this.activeCode) - Number(a.code === this.activeCode),
    );
    for (const label of ordered) {
      const projected = label.position.clone().project(this.camera);
      const x = ((projected.x + 1) * width) / 2;
      const y = ((-projected.y + 1) * height) / 2;
      const maxY = mobileDetail ? height * 0.53 : height - 115;
      let visible =
        this.labelsVisible &&
        (this.groups.get(label.code)?.visible || this.exteriors.get(label.code)?.visible || this.activeDetail?.code === label.code) &&
        this.mode === "campus" &&
        projected.z > -1 &&
        projected.z < 1 &&
        x > 24 &&
        x < width - 24 &&
        y > 105 &&
        y < maxY;
      const labelWidth =
        label.code === this.activeCode && width >= 700 ? 210 : 50;
      if (
        visible &&
        occupied.some(
          (other) =>
            Math.abs(x - other.x) < (labelWidth + other.width) / 2 &&
            Math.abs(y - other.y) < 33,
        )
      )
        visible = false;
      if (label.button.hidden === visible) label.button.hidden = !visible;
      if (visible) {
        occupied.push({ x, y, width: labelWidth });
        const transform = `translate(${x}px,${y}px) translate(-50%,-100%)`;
        if (label.transform !== transform) {
          label.button.style.transform = transform;
          label.transform = transform;
        }
      }
    }
  }

  tick(time) {
    this.frame = requestAnimationFrame(this.tick);
    if (document.hidden) return;
    if (this.transition) {
      const state = this.transition;
      const progress = Math.min(1, (time - state.start) / state.duration);
      const ease = 1 - Math.pow(1 - progress, 4);
      this.camera.position.lerpVectors(
        state.fromPosition,
        state.position,
        ease,
      );
      this.controls.target.lerpVectors(state.fromTarget, state.target, ease);
      this.needsRender = true;
      if (progress === 1) this.transition = null;
    }
    this.controlPosition.copy(this.camera.position);
    this.controlTarget.copy(this.controls.target);
    this.controlRotation.copy(this.camera.quaternion);
    this.controls.update();
    const distance = Math.max(0.15, this.camera.position.distanceTo(this.controls.target));
    const angularMovement = this.controlRotation.angleTo(this.camera.quaternion);
    const linearMovement = this.controlPosition.distanceTo(this.camera.position) +
      this.controlTarget.distanceTo(this.controls.target);
    const pixelsPerRadian = this.viewportHeight /
      (2 * Math.tan(THREE.MathUtils.degToRad(this.camera.fov / 2)));
    const pixelMovement = (angularMovement + linearMovement / distance) * pixelsPerRadian;
    // OrbitControls' change epsilon can briefly report stillness before its
    // residual input is exhausted. Resolve the subpixel tail once, without a jump.
    if (pixelMovement > 0.02) {
      this.inertiaMoving = true;
      this.needsRender = true;
      this.lastNavigationAt = performance.now();
    } else if (this.inertiaMoving && !this.interacting && !this.transition) {
      stopControlInertia(this.controls);
      this.inertiaMoving = false;
      this.needsRender = true;
    }
    const moving = this.interacting || this.inertiaMoving || Boolean(this.transition) ||
      performance.now() - this.lastNavigationAt < 200;
    // Wheel start/end events may both precede this RAF. Keep that new frame on
    // the one-scene-draw path, then refine once after the quiet interval.
    const finalStill = this.renderPipeline.needsSettle && !moving;
    if (this.needsRender || finalStill) {
      this.renderPipeline.render({ moving, time, progressive: true, restart: this.needsRender });
      // Refining the same still changes samples, not HTML label positions.
      if (this.needsRender) this.updateLabels();
      if (this.onBearingChange) {
        const bearing = Math.round(this.controls.getAzimuthalAngle() * 1800 / Math.PI) / 10;
        if (bearing !== this.lastBearing) {
          this.lastBearing = bearing;
          this.onBearingChange(bearing);
        }
      }
      this.needsRender = false;
    }
  }

  dispose() {
    disposeInteriorLighting(this);
    this.disposed = true;
    this.loadController.abort();
    this.detailRequest += 1;
    this.detailCache.dispose();
    for (const group of this.exteriors.values()) disposeModel(group);
    this.exteriors.clear();
    cancelAnimationFrame(this.frame);
    this.resizeObserver.disconnect();
    this.controls.dispose();
    this.draco.dispose();
    this.renderPipeline.dispose();
    this.environmentTarget.dispose();
    this.skyTexture?.dispose();
    this.skyBackdrop?.dispose();
    this.skyBackdrop?.image.close();
    disposeGroundTextures(this.groundTextures);
    this.scene.traverse((object) => {
      object.geometry?.dispose();
      if (object.material) {
        const materials = Array.isArray(object.material)
          ? object.material
          : [object.material];
        materials.forEach((material) => material.dispose());
      }
    });
    this.renderer.dispose();
    this.canvas.remove();
    this.labelLayer.replaceChildren();
  }
}
