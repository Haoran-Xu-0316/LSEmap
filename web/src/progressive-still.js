import * as THREE from "three";
import { FullScreenQuad } from "three/addons/postprocessing/Pass.js";
import { CopyShader } from "three/addons/shaders/CopyShader.js";

// The same four offsets and unbiased weights as Three.js SSAARenderPass level 2.
const OFFSETS = [[-2, -6], [6, -2], [-6, 2], [2, 6]];

/** Refine one unchanged pose over four frames, presenting only the completed image. */
export class ProgressiveStill {
  constructor(scene, camera) {
    this.scene = scene;
    this.camera = camera;
    this.samples = 0;
    this.sample = null;
    this.accumulation = null;
    this.clearColor = new THREE.Color();
    this.uniforms = THREE.UniformsUtils.clone(CopyShader.uniforms);
    this.material = new THREE.ShaderMaterial({
      uniforms: this.uniforms,
      vertexShader: CopyShader.vertexShader,
      fragmentShader: CopyShader.fragmentShader,
      transparent: true,
      depthTest: false,
      depthWrite: false,
      premultipliedAlpha: true,
      blending: THREE.AdditiveBlending,
    });
    this.quad = new FullScreenQuad(this.material);
  }

  reset() { this.samples = 0; }

  setSize(width, height) {
    if (!this.sample) {
      this.sample = new THREE.WebGLRenderTarget(width, height, { type: THREE.HalfFloatType });
      this.accumulation = new THREE.WebGLRenderTarget(width, height, {
        type: THREE.HalfFloatType, depthBuffer: false,
      });
    } else {
      this.sample.setSize(width, height);
      this.accumulation.setSize(width, height);
    }
    this.reset();
  }

  accumulate(renderer) {
    const { camera, sample, accumulation } = this;
    const index = this.samples;
    if (index >= OFFSETS.length) return true;
    const previousTarget = renderer.getRenderTarget();
    const autoClear = renderer.autoClear;
    // Match SSAARenderPass's working colour space before reading the clear colour.
    renderer.setRenderTarget(accumulation);
    renderer.getClearColor(this.clearColor);
    const clearAlpha = renderer.getClearAlpha();
    const originalView = camera.view ? { ...camera.view } : null;
    const view = originalView?.enabled ? originalView : {
      fullWidth: sample.width, fullHeight: sample.height,
      offsetX: 0, offsetY: 0, width: sample.width, height: sample.height,
    };
    try {
      renderer.autoClear = false;
      camera.setViewOffset(view.fullWidth, view.fullHeight,
        view.offsetX + OFFSETS[index][0] / 16,
        view.offsetY + OFFSETS[index][1] / 16, view.width, view.height);
      renderer.setRenderTarget(sample);
      renderer.setClearColor(this.clearColor, clearAlpha);
      renderer.clear();
      renderer.render(this.scene, camera);
      renderer.setRenderTarget(accumulation);
      if (index === 0) {
        renderer.setClearColor(0x000000, 0);
        renderer.clear();
      }
      this.uniforms.tDiffuse.value = sample.texture;
      this.uniforms.opacity.value = 1 / 4 + (1 / 32) * (-0.5 + (index + 0.5) / 4);
      this.quad.render(renderer);
      this.samples++;
    } finally {
      if (originalView?.enabled) camera.setViewOffset(originalView.fullWidth,
        originalView.fullHeight, originalView.offsetX, originalView.offsetY,
        originalView.width, originalView.height);
      else camera.clearViewOffset();
      renderer.autoClear = autoClear;
      renderer.setRenderTarget(previousTarget);
      renderer.setClearColor(this.clearColor, clearAlpha);
    }
    return this.samples === OFFSETS.length;
  }

  dispose() {
    this.sample?.dispose();
    this.accumulation?.dispose();
    this.material.dispose();
    this.quad.dispose();
  }
}
