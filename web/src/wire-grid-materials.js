import { DoubleSide } from 'three';

const prepared = new WeakSet();
/** Filter the area of thin wires over a screen pixel, rather than drawing an
 * opaque fence sheet or letting subpixel lines shimmer in the overview. */
export function prepareWireGrid(material) {
  const grid = material?.userData?.wireMesh;
  if (!grid || prepared.has(material)) return false;
  prepared.add(material);
  material.transparent = true;
  material.opacity = 1;
  material.depthWrite = false;
  material.side = DoubleSide;
  material.forceSinglePass = true;
  material.metalness = 0;
  material.roughness = .78;
  const previousCompile = material.onBeforeCompile;
  const previousKey = material.customProgramCacheKey();
  material.customProgramCacheKey = () => `${previousKey}|filtered-wire-grid1`;
  material.onBeforeCompile = (shader, renderer) => {
    previousCompile.call(material, shader, renderer);
    shader.uniforms.wirePitch = { value: [grid.pitchX, grid.pitchY] };
    shader.uniforms.wireWidth = { value: grid.width };
    shader.vertexShader = 'varying vec2 wireUv;\n' + shader.vertexShader;
    shader.vertexShader = shader.vertexShader.replace('#include <uv_vertex>', '#include <uv_vertex>\nwireUv = uv;');
    shader.fragmentShader = `
      varying vec2 wireUv;
      uniform vec2 wirePitch;
      uniform float wireWidth;
      float wireIntegral(float x, float width) {
        return floor(x) * width + min(fract(x), width);
      }
      float wireCoverage(float metre, float pitch) {
        float width = wireWidth / pitch;
        float coordinate = metre / pitch + width * .5;
        float pixel = max(fwidth(coordinate), .00001);
        return clamp((wireIntegral(coordinate + pixel * .5, width) -
                      wireIntegral(coordinate - pixel * .5, width)) / pixel, 0.0, 1.0);
      }
    ` + shader.fragmentShader;
    shader.fragmentShader = shader.fragmentShader.replace('#include <alphamap_fragment>', `
      #include <alphamap_fragment>
      vec2 wires = vec2(wireCoverage(wireUv.x, wirePitch.x), wireCoverage(wireUv.y, wirePitch.y));
      diffuseColor.a *= 1.0 - (1.0 - wires.x) * (1.0 - wires.y);
    `);
  };
  material.needsUpdate = true;
  return true;
}
