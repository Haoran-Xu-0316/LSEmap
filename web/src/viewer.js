import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { DRACOLoader } from "three/addons/loaders/DRACOLoader.js";
import { RoomEnvironment } from "three/addons/environments/RoomEnvironment.js";

const HOME_DIRECTION = new THREE.Vector3(-0.7, 0.9, 1).normalize();
const reducedMotion = matchMedia("(prefers-reduced-motion: reduce)");
const boxFromData = ({ min, max }) =>
  new THREE.Box3(new THREE.Vector3(...min), new THREE.Vector3(...max));

/** Rendering and camera state are separate from the accessible HTML interface. */
export class CampusViewer {
  constructor(container, labels, buildings, onPick, onContextLost) {
    this.container = container;
    this.labelLayer = labels;
    this.buildings = buildings;
    this.onPick = onPick;
    this.groups = new Map();
    this.interiors = new Map();
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
      antialias: true,
      logarithmicDepthBuffer: true,
      powerPreference: "high-performance",
    });
    this.renderer.setPixelRatio(Math.min(devicePixelRatio, 1.75));
    this.renderer.setClearColor(0xe7ecef);
    this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
    this.renderer.toneMappingExposure = 0.95;
    this.renderer.outputColorSpace = THREE.SRGBColorSpace;
    this.canvas = this.renderer.domElement;
    this.canvas.tabIndex = 0;
    this.canvas.setAttribute(
      "aria-label",
      "校园3D模型。方向键平移，加减键缩放，Home返回总览。也可使用建筑目录。",
    );
    this.container.append(this.canvas);
    this.scene = new THREE.Scene();
    this.camera = new THREE.PerspectiveCamera(38, 1, 0.1, 3000);
    this.camera.position.set(-280, 330, 370);
    this.controls = new OrbitControls(this.camera, this.canvas);
    this.controls.enableDamping = true;
    this.controls.dampingFactor = 0.08;
    this.controls.minDistance = 5;
    this.controls.maxDistance = 1100;
    this.controls.maxPolarAngle = Math.PI * 0.49;
    this.controls.screenSpacePanning = true;
    this.controls.target.set(10, 0, -10);
    this.controls.addEventListener("change", () => {
      this.needsRender = true;
    });
    this.controls.addEventListener("start", () => {
      this.transition = null;
    });
    this.scene.add(new THREE.HemisphereLight(0xf5faff, 0x89958a, 1.3));
    const sun = new THREE.DirectionalLight(0xfff7e9, 2.2);
    sun.position.set(-120, 240, 100);
    sun.castShadow = true;
    sun.shadow.mapSize.set(2048, 2048);
    Object.assign(sun.shadow.camera, {
      left: -310,
      right: 310,
      top: 310,
      bottom: -310,
      near: 1,
      far: 650,
    });
    sun.shadow.normalBias = 0.25;
    this.renderer.shadowMap.enabled = true;
    this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    this.renderer.shadowMap.autoUpdate = false;
    this.scene.add(sun);
    const fill = new THREE.DirectionalLight(0xe2edff, 0.7);
    fill.position.set(100, 70, -130);
    this.scene.add(fill);
    const pmrem = new THREE.PMREMGenerator(this.renderer);
    const environment = new RoomEnvironment();
    this.environmentTarget = pmrem.fromScene(environment, 0.04);
    this.scene.environment = this.environmentTarget.texture;
    this.scene.environmentIntensity = 0.55;
    environment.dispose();
    pmrem.dispose();
    this.draco = new DRACOLoader()
      .setDecoderPath({
        js: "/draco/draco_wasm_wrapper.js",
        wasm: "/draco/draco_decoder.wasm",
      })
      .setWorkerLimit(2);
    this.loader = new GLTFLoader().setDRACOLoader(this.draco);
    this.raycaster = new THREE.Raycaster();
    this.pointer = new THREE.Vector2();
    this.canvas.addEventListener("pointerdown", (event) => {
      this.pointerStart = {
        x: event.clientX,
        y: event.clientY,
        time: performance.now(),
        id: event.pointerId,
      };
    });
    this.canvas.addEventListener("pointerup", (event) => this.pick(event));
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

  async loadAsset(url, onProgress) {
    let timer;
    try {
      return await Promise.race([
        this.loader.loadAsync(url, onProgress),
        new Promise((_, reject) => {
          timer = setTimeout(
            () => reject(new Error("Model loading timed out")),
            45000,
          );
        }),
      ]);
    } finally {
      clearTimeout(timer);
    }
  }

  async load(onProgress) {
    const gltf = await this.loadAsset("/models/campus.glb", onProgress);
    this.campus = gltf.scene;
    this.scene.add(this.campus);
    const codes = new Set(this.buildings.map((b) => b.code));
    this.campus.traverse((object) => {
      const code = object.userData.buildingCode;
      if (code) this.groups.set(code, object);
      if (object.isMesh) {
        object.castShadow = true;
        object.receiveShadow = true;
        const materials = Array.isArray(object.material)
          ? object.material
          : [object.material];
        object.material = materials.map((material) => {
          const copy = material.clone();
          copy.side = THREE.DoubleSide;
          return copy;
        });
        if (object.material.length === 1) object.material = object.material[0];
      }
    });
    const context = this.groups.get("CONTEXT");
    context?.traverse((object) => {
      if (!object.isMesh) return;
      object.castShadow = false;
      const materials = Array.isArray(object.material)
        ? object.material
        : [object.material];
      for (const material of materials) {
        material.color.set(0xc5cdd2);
        material.roughness = 1;
        material.metalness = 0;
      }
    });
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
    this.renderer.setSize(width, height);
    this.camera.aspect = width / height;
    this.camera.updateProjectionMatrix();
    this.needsRender = true;
  }

  fit(bounds, animate = true, direction = HOME_DIRECTION) {
    const box = bounds instanceof THREE.Box3 ? bounds : boxFromData(bounds);
    const center = box.getCenter(new THREE.Vector3());
    const mobileDetail = this.container.clientWidth < 700 && this.activeCode;
    const up = new THREE.Vector3(0, 1, 0);
    const right = new THREE.Vector3().crossVectors(up, direction);
    // An exactly vertical view still needs a horizontal frame for fitting bounds.
    // A zero cross product otherwise collapses both projected extents to zero.
    if (right.lengthSq() < 1e-8) right.set(1, 0, 0);
    else right.normalize();
    const cameraUp = new THREE.Vector3()
      .crossVectors(direction, right)
      .normalize();
    const tangent = Math.tan(THREE.MathUtils.degToRad(this.camera.fov / 2));
    let distance = 14;
    for (const x of [box.min.x, box.max.x]) {
      for (const y of [box.min.y, box.max.y]) {
        for (const z of [box.min.z, box.max.z]) {
          const corner = new THREE.Vector3(x, y, z).sub(center);
          const horizontal =
            Math.abs(corner.dot(right)) / (tangent * this.camera.aspect);
          const vertical =
            Math.abs(corner.dot(cameraUp)) /
            (tangent * (mobileDetail ? 0.44 : 0.8));
          distance = Math.max(
            distance,
            corner.dot(direction) + Math.max(horizontal, vertical) * 1.2,
          );
        }
      }
    }
    if (mobileDetail)
      center.addScaledVector(cameraUp, -distance * tangent * 0.44);
    const position = center.clone().addScaledVector(direction, distance);
    this.moveCamera(position, center, animate);
  }

  moveCamera(position, target, animate = true) {
    if (!animate || reducedMotion.matches) {
      this.camera.position.copy(position);
      this.controls.target.copy(target);
      this.transition = null;
      this.controls.update();
      this.needsRender = true;
      return;
    }
    this.transition = {
      start: performance.now(),
      duration: 900,
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
  }

  showCampus() {
    this.viewRequest += 1;
    this.campus.visible = true;
    this.controls.maxPolarAngle = Math.PI * 0.49;
    this.controls.minDistance = 5;
    this.camera.fov = 38;
    this.camera.updateProjectionMatrix();
    this.renderer.shadowMap.needsUpdate = true;
    for (const group of this.interiors.values()) group.visible = false;
    this.mode = "campus";
    this.needsRender = true;
  }

  select(building) {
    if (!this.ready) return;
    this.showCampus();
    this.highlight(building.code);
    this.toggleContext(false);
    if (building.bounds)
      this.fit(
        building.bounds,
        true,
        building.exteriorDirection
          ? new THREE.Vector3(...building.exteriorDirection)
          : HOME_DIRECTION,
      );
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
    this.camera.updateProjectionMatrix();
    this.controls.minDistance = 1;
    if (this.container.clientWidth < 700) {
      // Keep the doorway in the free upper area above the mobile detail sheet.
      target.y -= 0.6;
      position.y -= 0.6;
      const offset = position.clone().sub(target).multiplyScalar(1.45);
      position.copy(target).add(offset);
      const right = new THREE.Vector3().crossVectors(this.camera.up, offset).normalize();
      const cameraUp = new THREE.Vector3().crossVectors(offset, right).normalize();
      const shift = -offset.length() * Math.tan(THREE.MathUtils.degToRad(view.fov / 2)) * 0.44;
      target.addScaledVector(cameraUp, shift);
      position.addScaledVector(cameraUp, shift);
    }
    this.moveCamera(position, target);
  }

  async showInterior(building) {
    const code = building.code;
    const request = ++this.viewRequest;
    if (!this.interiors.has(code)) {
      const gltf = await this.loadAsset(
        `/models/${code.toLowerCase()}-interior.glb`,
      );
      gltf.scene.visible = false;
      gltf.scene.traverse((object) => {
        if (!object.isMesh) return;
        const materials = Array.isArray(object.material)
          ? object.material
          : [object.material];
        for (const material of materials) material.side = THREE.DoubleSide;
      });
      this.scene.add(gltf.scene);
      this.interiors.set(code, gltf.scene);
    }
    // Selection can change while the model is downloading.
    if (this.activeCode !== code || request !== this.viewRequest) return false;
    this.campus.visible = false;
    for (const [name, group] of this.interiors) group.visible = name === code;
    this.mode = "interior";
    this.controls.maxPolarAngle = Math.PI * 0.94;
    this.controls.minDistance = 0.5;
    this.renderer.shadowMap.needsUpdate = true;
    if (building.interiorView) {
      const view = building.interiorView;
      this.camera.fov = view.fov;
      this.camera.updateProjectionMatrix();
      this.moveCamera(
        new THREE.Vector3(...view.position),
        new THREE.Vector3(...view.target),
      );
    } else {
      this.fit(
        building.interiorBounds,
        true,
        new THREE.Vector3(-0.7, 0.55, 1).normalize(),
      );
    }
    this.needsRender = true;
    return true;
  }

  toggleContext(visible) {
    this.contextVisible = visible;
    const companion =
      this.activeCode === "PAN"
        ? "FAW"
        : this.activeCode === "FAW"
          ? "PAN"
          : null;
    for (const [name, group] of this.groups) {
      if (name === "SITE") continue;
      if (name === "CONTEXT" || name === "LANDSCAPE") group.visible = visible;
      else
        group.visible =
          !this.activeCode ||
          visible ||
          name === this.activeCode ||
          name === companion;
    }
    this.renderer.shadowMap.needsUpdate = true;
    this.needsRender = true;
  }

  toggleLabels(visible) {
    this.labelsVisible = visible;
    this.needsRender = true;
  }

  zoom(factor) {
    const offset = this.camera.position
      .clone()
      .sub(this.controls.target)
      .multiplyScalar(factor);
    offset.setLength(
      THREE.MathUtils.clamp(
        offset.length(),
        this.controls.minDistance,
        this.controls.maxDistance,
      ),
    );
    this.moveCamera(
      this.controls.target.clone().add(offset),
      this.controls.target.clone(),
    );
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
    const hit = this.raycaster.intersectObjects(visibleBuildings, true)[0];
    if (!hit) return;
    let object = hit.object;
    while (object && !object.userData.buildingCode) object = object.parent;
    if (object) this.onPick(object.userData.buildingCode);
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
    const width = this.container.clientWidth;
    const height = this.container.clientHeight;
    const occupied = [];
    const mobileDetail = width < 700 && this.activeCode;
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
        this.groups.get(label.code)?.visible &&
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
      label.button.hidden = !visible;
      if (visible) {
        occupied.push({ x, y, width: labelWidth });
        label.button.style.transform = `translate(${x}px,${y}px) translate(-50%,-100%)`;
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
    this.controls.update();
    if (this.needsRender) {
      this.renderer.render(this.scene, this.camera);
      this.updateLabels();
      this.needsRender = false;
    }
  }

  dispose() {
    cancelAnimationFrame(this.frame);
    this.resizeObserver.disconnect();
    this.controls.dispose();
    this.draco.dispose();
    this.environmentTarget.dispose();
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
