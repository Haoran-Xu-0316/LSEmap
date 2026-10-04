import * as THREE from "three";
import { Pass, FullScreenQuad } from "three/addons/postprocessing/Pass.js";

const vertexShader = `
  varying vec2 vUv;
  void main() { vUv = uv; gl_Position = vec4(position.xy, 0.0, 1.0); }
`;

// Reproject the static campus by camera motion, before tone mapping. Reject
// disoccluded surfaces and clamp history to the current local colour range.
// Source glazing does not write depth; history is restricted to overview views.
export class TemporalAntialiasingPass extends Pass {
  constructor(scenePass, camera) {
    super();
    this.scenePass = scenePass;
    this.camera = camera;
    this.enabled = false;
    this.valid = false;
    this.frame = 0;
    this.size = new THREE.Vector2(1, 1);
    this.history = null;
    this.previousView = new THREE.Matrix4();
    this.previousProjection = new THREE.Matrix4();
    this.previousWorld = new THREE.Matrix4();
    this.previousPosition = new THREE.Vector3();
    this.previousRotation = new THREE.Quaternion();
    this.position = new THREE.Vector3();
    this.rotation = new THREE.Quaternion();
    this.lastTime = 0;
    this.moving = false;
    this.uniforms = {
      currentColor: { value: null }, currentDepth: { value: null },
      previousColor: { value: null }, pixelSize: { value: new THREE.Vector2() },
      inverseProjection: { value: new THREE.Matrix4() },
      cameraWorld: { value: new THREE.Matrix4() },
      previousView: { value: this.previousView },
      previousProjection: { value: this.previousProjection },
      logFar: { value: 1 }, logarithmicDepth: { value: true },
      historyWeight: { value: 0 },
    };
    this.material = new THREE.ShaderMaterial({
      uniforms: this.uniforms, vertexShader, depthTest: false, depthWrite: false,
      fragmentShader: `
        varying vec2 vUv;
        uniform sampler2D currentColor, currentDepth, previousColor;
        uniform vec2 pixelSize;
        uniform mat4 inverseProjection, cameraWorld, previousView, previousProjection;
        uniform float logFar, historyWeight;
        uniform bool logarithmicDepth;
        // Cubic reconstruction avoids repeatedly blurring history during rotation
        // or zoom. Nine bilinear reads reproduce the sixteen-tap cubic kernel.
        vec3 reconstructHistory(vec2 uv) {
          vec2 location = uv / pixelSize;
          vec2 center = floor(location - 0.5) + 0.5;
          vec2 f = location - center;
          vec2 w0 = f * (-0.5 + f * (1.0 - 0.5 * f));
          vec2 w1 = 1.0 + f * f * (-2.5 + 1.5 * f);
          vec2 w2 = f * (0.5 + f * (2.0 - 1.5 * f));
          vec2 w3 = f * f * (-0.5 + 0.5 * f);
          vec2 w12 = w1 + w2;
          vec2 p0 = (center - 1.0) * pixelSize;
          vec2 p12 = (center + w2 / w12) * pixelSize;
          vec2 p3 = (center + 2.0) * pixelSize;
          return texture2D(previousColor, vec2(p0.x, p0.y)).rgb * w0.x * w0.y +
            texture2D(previousColor, vec2(p12.x, p0.y)).rgb * w12.x * w0.y +
            texture2D(previousColor, vec2(p3.x, p0.y)).rgb * w3.x * w0.y +
            texture2D(previousColor, vec2(p0.x, p12.y)).rgb * w0.x * w12.y +
            texture2D(previousColor, p12).rgb * w12.x * w12.y +
            texture2D(previousColor, vec2(p3.x, p12.y)).rgb * w3.x * w12.y +
            texture2D(previousColor, vec2(p0.x, p3.y)).rgb * w0.x * w3.y +
            texture2D(previousColor, vec2(p12.x, p3.y)).rgb * w12.x * w3.y +
            texture2D(previousColor, p3).rgb * w3.x * w3.y;
        }
        void main() {
          vec3 current = texture2D(currentColor, vUv).rgb;
          float depth = texture2D(currentDepth, vUv).r;
          vec4 view = inverseProjection * vec4(vUv * 2.0 - 1.0, depth * 2.0 - 1.0, 1.0);
          view /= view.w;
          if (logarithmicDepth) {
            float distance = exp2(depth * logFar) - 1.0;
            view.xyz *= -distance / view.z;
          }
          vec4 oldView = previousView * cameraWorld * view;
          vec4 projected = previousProjection * oldView;
          vec2 oldUv = projected.xy / projected.w * 0.5 + 0.5;
          vec4 history = texture2D(previousColor, oldUv);
          float oldDistance = exp2(history.a * logFar) - 1.0;
          float mismatch = abs(oldDistance + oldView.z) / max(1.0, -oldView.z);
          float inside = step(0.0, oldUv.x) * step(oldUv.x, 1.0) *
                         step(0.0, oldUv.y) * step(oldUv.y, 1.0) * step(0.0, projected.w);
          vec3 minimum = current, maximum = current, mean = vec3(0.0), squares = vec3(0.0);
          for (int y = -1; y <= 1; y++) for (int x = -1; x <= 1; x++) {
            vec3 sampleColor = texture2D(currentColor, vUv + vec2(float(x), float(y)) * pixelSize).rgb;
            minimum = min(minimum, sampleColor); maximum = max(maximum, sampleColor);
            mean += sampleColor; squares += sampleColor * sampleColor;
          }
          mean /= 9.0;
          vec3 deviation = sqrt(max(squares / 9.0 - mean * mean, vec3(0.0)));
          minimum = min(current, max(minimum, mean - deviation * 1.5));
          maximum = max(current, min(maximum, mean + deviation * 1.5));
          vec3 retained = clamp(reconstructHistory(oldUv), minimum, maximum);
          float weight = historyWeight * inside * (1.0 - smoothstep(0.002, 0.01, mismatch)) * step(depth, 0.99999);
          float savedDepth = log2(1.0 - view.z) / logFar;
          gl_FragColor = vec4(mix(current, retained, weight), savedDepth);
        }
      `,
    });
    this.quad = new FullScreenQuad(this.material);
    this.copyMaterial = new THREE.ShaderMaterial({
      depthTest: false, depthWrite: false, vertexShader,
      uniforms: { image: { value: null } },
      fragmentShader: `varying vec2 vUv; uniform sampler2D image;
        void main() { gl_FragColor = vec4(texture2D(image, vUv).rgb, 1.0); }`,
    });
    this.copyQuad = new FullScreenQuad(this.copyMaterial);
  }

  reset() { this.valid = false; this.moving = false; }

  setSize(width, height) {
    this.size.set(width, height);
    this.uniforms.pixelSize.value.set(1 / width, 1 / height);
    this.history?.forEach(target => target.setSize(width, height));
    this.reset();
  }

  render(renderer, writeBuffer, readBuffer) {
    if (!this.history) this.history = [0, 1].map(() =>
      new THREE.WebGLRenderTarget(this.size.x, this.size.y, {
        type: THREE.HalfFloatType, depthBuffer: false,
      }));
    const camera = this.camera;
    const now = performance.now();
    camera.getWorldPosition(this.position);
    camera.getWorldQuaternion(this.rotation);
    const angle = this.rotation.angleTo(this.previousRotation);
    const distance = this.position.distanceTo(this.previousPosition);
    this.moving = !camera.matrixWorld.equals(this.previousWorld);
    const reusable = this.valid && this.moving && now - this.lastTime < 200 &&
      camera.projectionMatrix.equals(this.previousProjection) && angle < 0.08 &&
      distance < Math.max(2, this.position.length() * 0.05);
    const uniforms = this.uniforms;
    uniforms.currentColor.value = readBuffer.texture;
    uniforms.currentDepth.value = this.scenePass._sampleRenderTarget.depthTexture;
    uniforms.previousColor.value = this.history[(this.frame + 1) % 2].texture;
    uniforms.inverseProjection.value.copy(camera.projectionMatrixInverse);
    uniforms.cameraWorld.value.copy(camera.matrixWorld);
    uniforms.logFar.value = Math.log2(camera.far + 1);
    uniforms.logarithmicDepth.value = renderer.capabilities.logarithmicDepthBuffer;
    uniforms.historyWeight.value = reusable ? 0.7 : 0;
    const target = this.history[this.frame % 2];
    renderer.setRenderTarget(target);
    this.quad.render(renderer);
    this.copyMaterial.uniforms.image.value = target.texture;
    renderer.setRenderTarget(this.renderToScreen ? null : writeBuffer);
    this.copyQuad.render(renderer);
    this.previousView.copy(camera.matrixWorldInverse);
    this.previousProjection.copy(camera.projectionMatrix);
    this.previousWorld.copy(camera.matrixWorld);
    this.previousPosition.copy(this.position);
    this.previousRotation.copy(this.rotation);
    this.lastTime = now;
    this.valid = true;
    this.frame++;
  }

  dispose() {
    this.history?.forEach(target => target.dispose());
    this.material.dispose(); this.copyMaterial.dispose();
    this.quad.dispose(); this.copyQuad.dispose();
  }
}
