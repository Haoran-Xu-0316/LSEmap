import * as THREE from "three";
import {fetchStartupJson} from "./startup-metadata.js";
import {deviceBudget} from "./device-budget.js";
import {combineAbortSignals} from "./abort-utils.js";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { useTimeBasedDamping, stopControlInertia } from "./control-timing.js";
import { createBuildingPicker } from "./building-picking.js";
import { LocalSceneContext } from "./scene-context.js";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { DRACOLoader } from "three/addons/loaders/DRACOLoader.js";

import { createRenderPipeline, stablePixelRatio } from "./rendering-quality.js";
import { applyInteriorLighting, disposeInteriorLighting } from "./interior-lighting.js";

import { loadOutdoorEnvironment, DAYLIGHT_DIRECTION } from "./outdoor-environment.js";
import { createGroundTextureState, loadGroundTextures, disposeGroundTextures } from "./ground-textures.js";
import { ModelCache } from "./model-cache.js";
import { loadModelInStages, downloadVerifiedModel, downloadCampusModel } from "./model-loading.js";
import { prepareDetailedModel, prepareStaticModel, disposeModel, applySurfaceDetail, refineMaterialFinish, prepareMeshShadows, prepareGlazingSides, isGlazingMaterial } from "./surface-materials.js";

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
    this.budget = deviceBudget();
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
      antialias: this.budget.mobile,
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
      "校园3D模型。拖动平移，右键或Shift拖动旋转，滚轮指向缩放。方向键平移，加减键缩放，Home返回总览。",
    );
    this.container.append(this.canvas);
    this.scene = new THREE.Scene();
    // This root stays at identity; lights and model parents still update normally.
    this.scene.matrixAutoUpdate = false;
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
    // Capture first: use the actual surface distance before OrbitControls dollies.
    this.canvas.addEventListener('wheel', event => this.handleWheel(event),
      { capture: true, passive: false, signal: this.loadController.signal });
    this.zoomTouches = new Map();
    this.canvas.addEventListener('pointerdown', event => {
      if (event.pointerType !== 'touch') return;
      this.zoomTouches.set(event.pointerId, { x: event.clientX, y: event.clientY });
      if (this.zoomTouches.size === 2) {
        const [a, b] = this.zoomTouches.values();
        this.prepareSurfaceZoom({ clientX: (a.x + b.x) / 2, clientY: (a.y + b.y) / 2 });
      }
    }, { capture: true, signal: this.loadController.signal });
    this.canvas.addEventListener('pointermove', event => {
      if (this.zoomTouches.has(event.pointerId))
        this.zoomTouches.set(event.pointerId, { x: event.clientX, y: event.clientY });
    }, { capture: true, signal: this.loadController.signal });
    for (const type of ['pointerup', 'pointercancel'])
      this.canvas.addEventListener(type, event => this.zoomTouches.delete(event.pointerId),
        { capture: true, signal: this.loadController.signal });
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
    // Labels sit above the canvas, so their wheel events cannot reach controls.
    // Preserve the pointer coordinates and pinch modifiers across that overlay.
    this.labelLayer.addEventListener('wheel', event => {
      event.preventDefault();
      this.canvas.dispatchEvent(new WheelEvent('wheel', {
        bubbles: true, cancelable: true,
        clientX: event.clientX, clientY: event.clientY,
        deltaX: event.deltaX, deltaY: event.deltaY, deltaZ: event.deltaZ,
        deltaMode: event.deltaMode, ctrlKey: event.ctrlKey,
        shiftKey: event.shiftKey, metaKey: event.metaKey,
      }));
    }, { passive: false, signal: this.loadController.signal });
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
    sun.shadow.mapSize.set(this.budget.shadowSize, this.budget.shadowSize);
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
      .setWorkerLimit(this.budget.decoderWorkers);
    this.draco.preload();
    this.loader = new GLTFLoader().setDRACOLoader(this.draco);
    this.detailCache = new ModelCache(
      async (url, signal) => (await this.loadAsset(url, undefined, undefined, {signal})).scene,
      (group) => { prepareDetailedModel(group, this.environmentTarget.texture, this.groundTextures); this.applyEnvironmentRotation(group); this.scene.add(group); },
      disposeModel,
      this.budget.mobile ? 1 : (matchMedia("(max-width: 720px)").matches ? 2 : 3),
    );
    this.raycaster = new THREE.Raycaster();
    this.pickBuilding = createBuildingPicker();
    this.pickSurface = createBuildingPicker();
    this.pointer = new THREE.Vector2();
    // Pointer capture lets a drag starting on a label continue on the model.
    // A stationary tap still activates that label; keyboard clicks stay native.
    this.labelLayer.addEventListener('contextmenu', event => event.preventDefault(),
      { signal: this.loadController.signal });
    this.labelLayer.addEventListener('pointerdown', event => {
      const button = event.target.closest('button');
      if (!button) return;
      this.labelPointer = event.isPrimary ? { id: event.pointerId, button } : null;
      this.canvas.dispatchEvent(new PointerEvent('pointerdown', {
        pointerId: event.pointerId, pointerType: event.pointerType,
        isPrimary: event.isPrimary, button: event.button, buttons: event.buttons,
        clientX: event.clientX, clientY: event.clientY,
        shiftKey: event.shiftKey, ctrlKey: event.ctrlKey, metaKey: event.metaKey,
        bubbles: true, cancelable: true,
      }));
    }, { signal: this.loadController.signal });
    this.canvas.addEventListener("pointerdown", (event) => {
      if (event.isTrusted) this.labelPointer = null;
      clearTimeout(this.pickTimer);
      this.surfaceZoom = null;
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
    this.canvas.addEventListener("pointercancel", () => { this.pointerStart = null; this.labelPointer = null; });
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
    this.configureNavigation();
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

  async loadAsset(url, onProgress, beforeDecode, {priority = "high", signal: requestSignal, sha256, expectedBytes, fallbackUrl} = {}) {
    const cancellation = combineAbortSignals([this.loadController.signal, requestSignal]);
    const signal = cancellation.signal;
    // Fixed model names must follow the freshly loaded catalogue across releases.
    // Detailed models already carry their content hash in the filename.
    if (this.modelRevision && url.startsWith("/models/") && !url.startsWith("/models/details/")) {
      url += `?v=${encodeURIComponent(this.modelRevision)}`;
    }
    const transferController = new AbortController();
    const assets = this.buildings.flatMap(building => [building.detailedExterior,
      building.detailedInterior, ...(building.interiorSpaces || []).map(space => space.detailedInterior)]);
    const asset = assets.find(asset => asset?.url === url);
    const expectedSha256 = sha256 ?? asset?.sha256;
    expectedBytes ??= asset?.bytes;
    return loadModelInStages(
      progress => (url.startsWith("/models/campus.glb") ? downloadCampusModel : downloadVerifiedModel)(url, {signal: transferController.signal, onProgress: progress, expectedSha256, expectedBytes, fallbackUrl, priority}),
      bytes => this.loader.parseAsync(bytes, THREE.LoaderUtils.extractUrlBase(url)),
      {
        signal,
        onProgress,
        beforeDecode,
        cancelDownload: () => transferController.abort(),
        discardModel: model => disposeModel(model.scene),
      },
    ).finally(cancellation.dispose);
  }

  async load(onProgress, {sourceModelSha256, startupModel} = {}) {
    let startup={url:"/models/campus.glb"};
    if (this.budget.mobile) {
      startup=await (startupModel ?? fetchStartupJson('/models/mobile-campus.json',{signal:this.loadController.signal}));
      if(!/^\/models\/details\/campus-mobile-[a-f0-9]{12}\.glb$/.test(startup.url)||
         !/^[a-f0-9]{64}$/.test(startup.sha256)||startup.decodedBytes>96*1024*1024)
        throw Error('Invalid mobile campus');
      const source=sourceModelSha256 ?? (await fetchStartupJson('/models/catalogue.json',{signal:this.loadController.signal})).sourceModelSha256;
      if(startup.sourceModelSha256!==source)throw Error('Mobile campus revision differs');
      if(startup.transport && (startup.transport.encoding!=='gzip'||startup.transport.url!==startup.url+'.gz'))
        throw Error('Invalid mobile transport');
    }
    const gltf = await this.loadAsset(startup.transport?.url ?? startup.url, onProgress, undefined, {
      sha256:startup.sha256, expectedBytes:startup.bytes, fallbackUrl:startup.transport ? startup.url : undefined,
    });
    this.canvas.dataset.resourceProfile=this.budget.mobile?'mobile':'desktop';
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
    prepareStaticModel(this.campus);
    this.campus.updateMatrixWorld(true);
    this.localContext = new LocalSceneContext([this.groups.get("SITE"), this.groups.get("LANDSCAPE")]);
    this.scene.add(this.localContext.root);
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
        background ? () => this.waitForBackgroundFrame(() => this.activeCode === building.code && this.mode !== "interior") : undefined,
        {priority: background ? "low" : "high"},
      );
      if (this.disposed) {
        disposeModel(group);
        throw new Error("Viewer disposed");
      }
      if (background && !await this.waitForBackgroundFrame(() => this.activeCode === building.code && this.mode !== "interior")) {
        disposeModel(group);
        throw new Error("Viewer disposed");
      }
      prepareDetailedModel(group, this.environmentTarget.texture, this.groundTextures);
      this.applyEnvironmentRotation(group);
      group.userData.buildingCode = building.code;
      this.scene.add(group);
      this.exteriors.set(building.code, group);
      if(this.budget.mobile) {
        const retained=new Set([this.activeCode,COMPANION_CODES[this.activeCode]]);
        for(const [code,oldGroup] of this.exteriors) {
          if(this.exteriors.size<=this.budget.exteriorLimit)break;
          if(retained.has(code))continue;
          oldGroup.removeFromParent();disposeModel(oldGroup, true);this.exteriors.delete(code);
        }
      }
      this.toggleContext(this.contextVisible);
      return group;
    })();
    this.exteriorLoads.set(building.code, pending);
    try { return await pending; }
    finally { this.exteriorLoads.delete(building.code); }
  }

  navigationIsBusy() {
    return document.hidden || this.mode === "interior" || this.interacting || Boolean(this.transition) ||
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
    if (this.budget.mobile) return;
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
    clearTimeout(this.pickTimer);
    this.surfaceZoom = null;
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
    this.cancelInteriorLoads();
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
      const interiorUrl = typeof interior?.interiorAsset === "string"
        ? interior.interiorAsset : interior?.interiorAsset?.url;
      // Room studies already load their final hashed GLB on entry. Reuse that
      // prepared scene instead of downloading, decoding and retaining it twice.
      const sharedInterior = kind === "interior" && interiorUrl === asset.url
        ? this.interiors.get(interiorKey) : null;
      const group = kind === "exterior"
        ? await this.loadExterior(building)
        : sharedInterior ?? await this.detailCache.request(detailKey, asset.url);
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

  cancelInteriorLoads(exceptKey = null) {
    for (const [key, request] of this.interiorLoads) {
      if (key === exceptKey) continue;
      request.controller.abort(new DOMException("Interior changed", "AbortError"));
      this.interiorLoads.delete(key);
    }
  }

  async loadInterior(building, spaceId, interior) {
    const key = `${building.code}:${spaceId ?? "default"}`;
    if (this.interiors.has(key)) return this.interiors.get(key);
    if (this.interiorLoads.has(key)) return this.interiorLoads.get(key).promise;
    const asset = interior.interiorAsset;
    const url = typeof asset === "string" ? asset : asset?.url;
    const source = url ?? (spaceId === null ? `/models/${building.code.toLowerCase()}-interior.glb` : null);
    if (!source) throw new Error(`Missing interior asset: ${key}`);
    const request = {controller: new AbortController(), promise: null};
    request.promise = (async () => {
      const gltf = await this.loadAsset(source, undefined, undefined, {signal: request.controller.signal});
      if (this.disposed || request.controller.signal.aborted) {
        disposeModel(gltf.scene);
        throw new DOMException("Interior changed", "AbortError");
      }
      prepareDetailedModel(gltf.scene, this.environmentTarget.texture, this.groundTextures);
      this.applyEnvironmentRotation(gltf.scene);
      this.scene.add(gltf.scene);
      this.interiors.set(key, gltf.scene);
      if(this.budget.mobile)for(const [oldKey,oldGroup] of this.interiors){
        if(this.interiors.size<=2)break;
        if(oldKey===this.activeInterior?.key||oldKey===key)continue;
        oldGroup.removeFromParent();disposeModel(oldGroup, true);this.interiors.delete(oldKey);
      }
      return gltf.scene;
    })();
    this.interiorLoads.set(key, request);
    try { return await request.promise; }
    finally {
      if (this.interiorLoads.get(key) === request) this.interiorLoads.delete(key);
    }
  }

  async showInterior(building, spaceId = null) {
    const interior = this.interiorSpace(building, spaceId);
    if (!this.ready || !interior || this.activeCode !== building.code) return false;
    this.detailRequest += 1;
    const code = building.code;
    const key = `${code}:${spaceId ?? "default"}`;
    this.detailCache.activate(`interior-${code}${spaceId === null ? "" : `:${spaceId}`}`);
    this.cancelInteriorLoads(key);
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
    const localBuilding = this.buildings.find(building => building.code === this.activeCode);
    if (this.mode !== "interior" && !visible && localBuilding?.bounds)
      this.localContext?.activate(this.activeCode, boxFromData(localBuilding.bounds)).then(group => {
        if (!group || this.disposed || this.activeCode !== group.userData.streetContext.code || this.contextVisible || this.mode === "interior") return;
        this.renderer.shadowMap.needsUpdate = true;
        this.renderPipeline.resetHistory();
        this.needsRender = true;
      }).catch(error => { if (!this.disposed) console.error("Nearby street unavailable", error); });
    else this.localContext?.hide();
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
    // Toolbar and keyboard zoom follow the surface in the middle of the view,
    // rather than an orbit centre left behind on the far side of the campus.
    if (this.transition?.kind !== "zoom") {
      const rect = this.canvas.getBoundingClientRect();
      this.prepareSurfaceZoom({ clientX: rect.left + rect.width / 2,
        clientY: rect.top + rect.height / 2 });
    }
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

  configureNavigation() {
    // One gesture vocabulary in the campus, building and room views. No mode
    // switch can leave the next view unexpectedly orbiting instead of panning.
    this.controls.mouseButtons.LEFT = THREE.MOUSE.PAN;
    this.controls.mouseButtons.RIGHT = THREE.MOUSE.ROTATE;
    this.controls.touches.ONE = THREE.TOUCH.PAN;
    this.controls.touches.TWO = THREE.TOUCH.DOLLY_ROTATE;
    this.canvas.style.cursor = 'grab';
  }

  surfaceAt(event) {
    const root = this.activeDetail?.group ??
      (this.activeInterior ? this.interiors.get(this.activeInterior.key) :
        this.exteriors.get(this.activeCode) ?? this.groups.get(this.activeCode));
    const roots = this.activeCode ? [root] : [...this.groups.values(), ...this.exteriors.values()];
    if (this.mode !== "interior" && this.activeCode) {
      if (this.contextVisible) roots.push(this.groups.get("SITE"), this.groups.get("LANDSCAPE"));
      else if (this.localContext?.root.visible) roots.push(this.localContext.activeGroup);
    }
    const rect = this.canvas.getBoundingClientRect();
    this.pointer.set((event.clientX - rect.left) / rect.width * 2 - 1,
      -(event.clientY - rect.top) / rect.height * 2 + 1);
    this.camera.updateMatrixWorld();
    this.raycaster.setFromCamera(this.pointer, this.camera);
    return this.pickSurface(this.raycaster, roots.filter(group => group?.visible), hit =>
      this.renderer.clippingPlanes.every(plane => plane.distanceToPoint(hit.point) >= 0));
  }

  handleWheel(event) {
    if (!this.ready || !this.controls.enabled) return;
    const now = performance.now();
    const continuing = this.wheelGesture && now - this.wheelGesture.time < 180;
    // Trackpads send two axes. OrbitControls consumes only deltaY, losing
    // sideways movement entirely. Keep one interpretation for each gesture so
    // a diagonal tail cannot suddenly turn a pan into a zoom. Pinch stays zoom.
    const pan = !event.ctrlKey && (event.shiftKey ||
      (continuing ? this.wheelGesture.pan : Math.abs(event.deltaX) > Math.abs(event.deltaY)));
    this.wheelGesture = { time: now, pan };
    if (!pan) {
      this.prepareSurfaceZoom(event);
      return;
    }
    event.preventDefault();
    event.stopImmediatePropagation();
    if (!this.controls.enablePan) return;
    this.transition = null;
    this.surfaceZoom = null;
    clearTimeout(this.pickTimer);
    const unit = event.deltaMode === 1 ? 16 : event.deltaMode === 2 ? this.canvas.clientHeight : 1;
    const x = event.shiftKey && !event.deltaX ? event.deltaY : event.deltaX;
    const y = event.shiftKey && !event.deltaX ? 0 : event.deltaY;
    this.controls.pan(-x * unit, -y * unit);
  }

  prepareSurfaceZoom(event) {
    if (!this.ready || !this.controls.enabled || !this.controls.enableZoom) return;
    const now = performance.now();
    const previous = this.surfaceZoom;
    const fresh = !previous || now - previous.time > 180 ||
      Math.hypot(event.clientX - previous.x, event.clientY - previous.y) > 6;
    if (fresh) {
      this.transition = null;
      stopControlInertia(this.controls);
      const hit = this.surfaceAt(event);
      this.surfaceZoom = { time: now, x: event.clientX, y: event.clientY,
        point: hit?.point.clone() ?? null };
    } else previous.time = now;
    const point = this.surfaceZoom.point;
    if (!point) return;
    // Keep the viewing direction and screen anchor; replace only the stale
    // campus-centre distance. A wheel burst reuses one exact surface query.
    const distance = Math.max(this.controls.minDistance, this.camera.position.distanceTo(point));
    const forward = this.camera.getWorldDirection(new THREE.Vector3());
    this.controls.target.copy(this.camera.position).addScaledVector(forward, distance);
  }

  focusSurface(event) {
    clearTimeout(this.pickTimer);
    if (!this.ready || event.button !== 0) return;
    const hit = this.surfaceAt(event);
    if (!hit || hit.distance <= this.controls.minDistance) return;
    this.transition = null;
    if (!this.activeCode) {
      const position = this.camera.position.clone().lerp(hit.point, .55);
      this.moveCamera(position, hit.point.clone());
      return;
    }
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
    const label = this.labelPointer;
    this.labelPointer = null;
    if (label?.id === event.pointerId) {
      label.button.click();
      return;
    }
    const rect = this.canvas.getBoundingClientRect();
    this.pointer.set(
      ((event.clientX - rect.left) / rect.width) * 2 - 1,
      -((event.clientY - rect.top) / rect.height) * 2 + 1,
    );
    this.raycaster.setFromCamera(this.pointer, this.camera);
    const visibleBuildings = this.pickable.filter((group) => group.visible);
    visibleBuildings.push(...[...this.exteriors.values()].filter((group) => group.visible));
    const hit = this.pickBuilding(this.raycaster, visibleBuildings);
    if (!hit) return;
    let object = hit.object;
    while (object && !object.userData.buildingCode) object = object.parent;
    if (object && object.userData.buildingCode !== this.activeCode) {
      const code = object.userData.buildingCode;
      clearTimeout(this.pickTimer);
      // Leave the double-click gesture available for approaching this surface.
      this.pickTimer = setTimeout(() => {
        if (!this.disposed && this.mode === 'campus') this.onPick(code);
      }, 300);
    }
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
    // Exterior orbits may look up at facades, but must not pass under the
    // district's ground and expose its black underside against the sky.
    if (this.mode !== 'interior' && this.camera.position.y < 0.25) {
      this.camera.position.y = 0.25;
      stopControlInertia(this.controls);
      this.needsRender = true;
    }
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
    clearTimeout(this.pickTimer);
    disposeInteriorLighting(this);
    this.disposed = true;
    this.cancelInteriorLoads();
    this.loadController.abort();
    this.detailRequest += 1;
    this.detailCache.dispose();
    this.localContext?.dispose();
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
