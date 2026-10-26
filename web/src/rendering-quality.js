import * as THREE from "three";
import { deviceBudget } from "./device-budget.js";
import { EffectComposer } from "three/addons/postprocessing/EffectComposer.js";
import { SSAARenderPass } from "three/addons/postprocessing/SSAARenderPass.js";
import { OutputPass } from "three/addons/postprocessing/OutputPass.js";
import { ShaderPass } from "three/addons/postprocessing/ShaderPass.js";
import { TemporalAntialiasingPass } from "./temporal-antialiasing.js";
import { ProgressiveStill } from "./progressive-still.js";
import { FXAAShader } from "three/addons/shaders/FXAAShader.js";

// Keep canvas resolution stable; only scene sampling changes during interaction.
// Four samples refine the final still without drawing the whole campus four times per drag frame.
export function stablePixelRatio(width, height) {
  const area = Math.max(1, width * height);
  return Math.max(1, Math.min(deviceBudget().pixelRatio, Math.sqrt(3_000_000 / area)));
}

// The sampling pass clears before WebGLBackground updates its color space.
// Bind the scene buffer before computing that clear, avoiding a second sRGB encode.
class ColorManagedRenderPass extends SSAARenderPass {
  constructor(scene, camera, rasterSamples) {
    super(scene, camera, new THREE.Color(0xe9e8e3), 1);
    this.rasterSamples = rasterSamples;
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
    // Thin stone joints and railings need coverage samples while the camera moves.
    // Resolve MSAA in the scene buffer, keeping one scene draw per moving frame.
    // The default framebuffer remains single-sampled for section/clipping stability.
    if (!this._sampleRenderTarget) this._sampleRenderTarget = new THREE.WebGLRenderTarget(
      readBuffer.width, readBuffer.height, {
        type: THREE.HalfFloatType, samples: this.rasterSamples,
      });
    if (this.captureDepth && !this._sampleRenderTarget.depthTexture) {
      this._sampleRenderTarget.dispose();
      this._sampleRenderTarget.depthTexture = new THREE.DepthTexture(readBuffer.width, readBuffer.height);
    }
    if (this.stillTexture) {
      this._copyUniforms.tDiffuse.value = this.stillTexture;
      this._copyUniforms.opacity.value = 1;
      renderer.setClearColor(0x000000, 0);
      renderer.clear();
      this._fsQuad.render(renderer);
      renderer.setClearColor(this.clearColor, this.clearAlpha);
      return;
    }
    super.render(renderer, writeBuffer, readBuffer, deltaTime, maskActive);
  }
}

export function createRenderPipeline(renderer, scene, camera, allowTemporal = () => true) {
  if (deviceBudget().mobile) {
    // Render straight to the antialiased display framebuffer. Tone mapping stays
    // on the scene materials; no half-float composer/history allocations on iOS.
    const scenePass={sampleLevel:0};
    return {scenePass,temporalPass:{enabled:false,history:null},get needsSettle(){return false;},
      resetHistory(){},resize(){},render(){renderer.render(scene,camera);},dispose(){}};
  }
  const composer = new EffectComposer(renderer);
  const desktopRasterSamples = Math.min(2, renderer.capabilities.maxSamples);
  const scenePass = new ColorManagedRenderPass(scene, camera, desktopRasterSamples);
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
  const still = new ProgressiveStill(scene, camera);
  return {
    composer,
    antialiasPass,
    scenePass,
    temporalPass,
    get needsSettle() { return needsSettle; },
    resetHistory() { temporalPass.reset(); still.reset(); },
    resize(width, height) {
      // Keep narrow views on their existing light sampling budget.
      wideViewport = width > 640;
      scenePass.rasterSamples = wideViewport ? desktopRasterSamples : 0;
      if (scenePass._sampleRenderTarget && scenePass._sampleRenderTarget.samples !== scenePass.rasterSamples) {
        scenePass._sampleRenderTarget.dispose();
        scenePass._sampleRenderTarget.samples = scenePass.rasterSamples;
      }
      scenePass.sampleLevel = wideViewport ? 2 : 0;
      needsSettle = false;
      composer.setPixelRatio(renderer.getPixelRatio());
      composer.setSize(width, height);
      renderer.getDrawingBufferSize(bufferSize);
      if (still.sample) still.setSize(bufferSize.x, bufferSize.y);
      antialiasPass.uniforms.resolution.value.set(1 / bufferSize.x, 1 / bufferSize.y);
    },
    render({ stabilize = true, moving, time, progressive = false, restart = false } = {}) {
      scenePass.stillTexture = null;
      if (progressive && moving === false && wideViewport) {
        if (!still.sample) still.setSize(bufferSize.x, bufferSize.y);
        if (restart) still.reset();
        needsSettle = !still.accumulate(renderer);
        if (needsSettle) return;
        scenePass.sampleLevel = 2;
        scenePass.stillTexture = still.accumulation.texture;
        // The finished image already contains all four samples; no moving history.
        temporalPass.enabled = false;
        temporalPass.reset();
        try { composer.render(); }
        finally { scenePass.stillTexture = null; }
        return;
      }
      still.reset();
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
      still.dispose();
    },
  };
}
