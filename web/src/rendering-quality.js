import * as THREE from "three";
import { EffectComposer } from "three/addons/postprocessing/EffectComposer.js";
import { RenderPass } from "three/addons/postprocessing/RenderPass.js";
import { OutputPass } from "three/addons/postprocessing/OutputPass.js";
import { ShaderPass } from "three/addons/postprocessing/ShaderPass.js";
import { FXAAShader } from "three/addons/shaders/FXAAShader.js";

// Fix the sample grid for the viewport instead of switching it on every gesture.
// Cap large screens at three million scene pixels; mobile keeps its sharp buffer.
export function stablePixelRatio(width, height) {
  const area = Math.max(1, width * height);
  return Math.max(1, Math.min(1.5, Math.sqrt(3_000_000 / area)));
}

// RenderPass clears manually before WebGLBackground updates its color space.
// Bind the scene buffer before computing that clear, avoiding a second sRGB encode.
class ColorManagedRenderPass extends RenderPass {
  constructor(scene, camera) {
    super(scene, camera);
    this.clearColorScratch = new THREE.Color();
  }

  render(renderer, writeBuffer, readBuffer, deltaTime, maskActive) {
    renderer.setRenderTarget(this.renderToScreen ? null : readBuffer);
    renderer.getClearColor(this.clearColorScratch);
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
    resize(width, height) {
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
