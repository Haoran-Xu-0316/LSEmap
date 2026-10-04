import * as THREE from "three";
import { EffectComposer } from "three/addons/postprocessing/EffectComposer.js";
import { SSAARenderPass } from "three/addons/postprocessing/SSAARenderPass.js";
import { OutputPass } from "three/addons/postprocessing/OutputPass.js";
import { ShaderPass } from "three/addons/postprocessing/ShaderPass.js";
import { TemporalAntialiasingPass } from "./temporal-antialiasing.js";
import { FXAAShader } from "three/addons/shaders/FXAAShader.js";

// Keep canvas resolution stable; only scene sampling changes during interaction.
// Four samples refine the final still without drawing the whole campus four times per drag frame.
export function stablePixelRatio(width, height) {
  const area = Math.max(1, width * height);
  return Math.max(1, Math.min(1.5, Math.sqrt(3_000_000 / area)));
}

// The sampling pass clears before WebGLBackground updates its color space.
// Bind the scene buffer before computing that clear, avoiding a second sRGB encode.
class ColorManagedRenderPass extends SSAARenderPass {
  constructor(scene, camera) {
    super(scene, camera, new THREE.Color(0xe9e8e3), 1);
    // Four fixed subpixel samples cover horizontal and vertical facade edges.
    // The optional overview resolver reuses these samples between moving frames.
    this.sampleLevel = 2;
    this.clearColorScratch = new THREE.Color();
  }

  render(renderer, writeBuffer, readBuffer, deltaTime, maskActive) {
    renderer.setRenderTarget(this.renderToScreen ? null : writeBuffer);
    renderer.getClearColor(this.clearColorScratch);
    this.clearColor.copy(this.clearColorScratch);
    this.clearAlpha = renderer.getClearAlpha();
    renderer.setClearColor(this.clearColorScratch, renderer.getClearAlpha());
    if (this.captureDepth && !this._sampleRenderTarget?.depthTexture) {
      if (!this._sampleRenderTarget) this._sampleRenderTarget = new THREE.WebGLRenderTarget(
        readBuffer.width, readBuffer.height, { type: THREE.HalfFloatType });
      this._sampleRenderTarget.dispose();
      this._sampleRenderTarget.depthTexture = new THREE.DepthTexture(readBuffer.width, readBuffer.height);
    }
    super.render(renderer, writeBuffer, readBuffer, deltaTime, maskActive);
  }
}

export function createRenderPipeline(renderer, scene, camera, allowTemporal = () => true) {
  const composer = new EffectComposer(renderer);
  const scenePass = new ColorManagedRenderPass(scene, camera);
  const temporalPass = new TemporalAntialiasingPass(scenePass, camera);
  let wideViewport = false;
  let needsSettle = false;
  const outputPass = new OutputPass();
  const antialiasPass = new ShaderPass(FXAAShader);
  // FXAA measures contrast in sRGB, after the existing exposure and tone mapping.
  composer.addPass(scenePass);
  composer.addPass(temporalPass);
  composer.addPass(outputPass);
  composer.addPass(antialiasPass);
  const bufferSize = new THREE.Vector2();
  return {
    composer,
    antialiasPass,
    scenePass,
    temporalPass,
    get needsSettle() { return needsSettle; },
    resetHistory() { temporalPass.reset(); },
    resize(width, height) {
      // Keep narrow views on their existing light sampling budget.
      wideViewport = width > 640;
      scenePass.sampleLevel = wideViewport ? 2 : 0;
      needsSettle = false;
      composer.setPixelRatio(renderer.getPixelRatio());
      composer.setSize(width, height);
      renderer.getDrawingBufferSize(bufferSize);
      antialiasPass.uniforms.resolution.value.set(1 / bufferSize.x, 1 / bufferSize.y);
    },
    render({ stabilize = true, moving, time } = {}) {
      if (moving !== undefined) scenePass.sampleLevel = moving ? 0 : (wideViewport ? 2 : 0);
      temporalPass.enabled = stabilize && wideViewport && camera.isPerspectiveCamera && allowTemporal();
      temporalPass.motion = moving;
      temporalPass.frameTime = time;
      scenePass.captureDepth = temporalPass.enabled;
      if (!temporalPass.enabled || renderer.shadowMap.needsUpdate) temporalPass.reset();
      composer.render();
      // Always refine the final still, including close-up views without temporal AA.
      // Damping remains on the light budget; the final four-sample frame then stops.
      needsSettle = moving === true || (temporalPass.enabled && temporalPass.moving);
    },
    dispose() {
      scenePass.dispose();
      temporalPass.dispose();
      outputPass.dispose();
      antialiasPass.dispose();
      composer.dispose();
    },
  };
}
