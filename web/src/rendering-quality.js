import * as THREE from "three";
import { EffectComposer } from "three/addons/postprocessing/EffectComposer.js";
import { SSAARenderPass } from "three/addons/postprocessing/SSAARenderPass.js";
import { OutputPass } from "three/addons/postprocessing/OutputPass.js";
import { ShaderPass } from "three/addons/postprocessing/ShaderPass.js";
import { FXAAShader } from "three/addons/shaders/FXAAShader.js";

// Fix the sample grid for the viewport instead of switching it on every gesture.
// Cap the stable grid at three million pixels; sampling never switches on a gesture.
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
    // No frame history means no ghost trails, and demand rendering stays idle.
    this.sampleLevel = 2;
    this.clearColorScratch = new THREE.Color();
  }

  render(renderer, writeBuffer, readBuffer, deltaTime, maskActive) {
    renderer.setRenderTarget(this.renderToScreen ? null : writeBuffer);
    renderer.getClearColor(this.clearColorScratch);
    this.clearColor.copy(this.clearColorScratch);
    this.clearAlpha = renderer.getClearAlpha();
    renderer.setClearColor(this.clearColorScratch, renderer.getClearAlpha());
    super.render(renderer, writeBuffer, readBuffer, deltaTime, maskActive);
  }
}

export function createRenderPipeline(renderer, scene, camera) {
  const composer = new EffectComposer(renderer);
  const scenePass = new ColorManagedRenderPass(scene, camera);
  const outputPass = new OutputPass();
  const antialiasPass = new ShaderPass(FXAAShader);
  // FXAA measures contrast in sRGB, after the existing exposure and tone mapping.
  composer.addPass(scenePass);
  composer.addPass(outputPass);
  composer.addPass(antialiasPass);
  const bufferSize = new THREE.Vector2();
  return {
    composer,
    antialiasPass,
    scenePass,
    resize(width, height) {
      // Keep narrow views on their existing light sampling budget.
      scenePass.sampleLevel = width <= 640 ? 0 : 2;
      composer.setPixelRatio(renderer.getPixelRatio());
      composer.setSize(width, height);
      renderer.getDrawingBufferSize(bufferSize);
      antialiasPass.uniforms.resolution.value.set(1 / bufferSize.x, 1 / bufferSize.y);
    },
    render() { composer.render(); },
    dispose() {
      scenePass.dispose();
      outputPass.dispose();
      antialiasPass.dispose();
      composer.dispose();
    },
  };
}
