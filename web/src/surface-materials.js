import * as THREE from "three";

// Recreate source-node surface parameters without distributing reference photographs.
// Noise is an approximation of Blender's shader, not a baked Cycles result.
const noiseGLSL = `
float surfaceHash(vec3 p) {
  p = fract(p * 0.1031);
  p += dot(p, p.yzx + 33.33);
  return fract((p.x + p.y) * p.z);
}
float surfaceNoise(vec3 p) {
  vec3 cell = floor(p), f = fract(p);
  f = f * f * (3.0 - 2.0 * f);
  return mix(mix(mix(surfaceHash(cell), surfaceHash(cell + vec3(1,0,0)), f.x),
                 mix(surfaceHash(cell + vec3(0,1,0)), surfaceHash(cell + vec3(1,1,0)), f.x), f.y),
             mix(mix(surfaceHash(cell + vec3(0,0,1)), surfaceHash(cell + vec3(1,0,1)), f.x),
                 mix(surfaceHash(cell + vec3(0,1,1)), surfaceHash(cell + vec3(1,1,1)), f.x), f.y), f.z);
}
`;

export function applySurfaceDetail(material) {
  const detail = material.userData.surfaceDetail;
  if (!detail || !["noise", "brick"].includes(detail.kind)) return;
  const brick = detail.kind === "brick";
  const color = (value) => value ? new THREE.Color(...value) : material.color.clone();
  const uniforms = {
    surfaceScale: { value: detail.scale },
    surfaceBump: { value: Math.min(0.015, detail.bump) },
    surfaceColorA: { value: color(detail.colorA) },
    surfaceColorB: { value: color(detail.colorB) },
    surfaceMortar: { value: color(detail.mortarColor) },
    surfaceBrick: { value: new THREE.Vector3(detail.brickWidth || .225, detail.rowHeight || .078, detail.mortarSize || .007) },
  };
  material.customProgramCacheKey = () => `lse-surface-${brick ? "brick" : "noise"}`;
  material.onBeforeCompile = (shader) => {
    Object.assign(shader.uniforms, uniforms);
    shader.vertexShader = `varying vec3 vSurfacePosition;\nvarying vec2 vSurfaceUv;\n` + shader.vertexShader;
    shader.vertexShader = shader.vertexShader.replace("#include <project_vertex>", `
      vSurfacePosition = (modelMatrix * vec4(transformed, 1.0)).xyz;
      vSurfaceUv = uv;
      #include <project_vertex>
    `);
    shader.fragmentShader = `
      varying vec3 vSurfacePosition;
      varying vec2 vSurfaceUv;
      uniform float surfaceScale, surfaceBump;
      uniform vec3 surfaceColorA, surfaceColorB, surfaceMortar, surfaceBrick;
      ${noiseGLSL}
    ` + shader.fragmentShader;
    const pattern = brick ? `
      vec2 brickPoint = vSurfaceUv * surfaceScale;
      float row = floor(brickPoint.y / surfaceBrick.y);
      brickPoint.x += mod(row, 2.0) * surfaceBrick.x * 0.5;
      vec2 inBrick = mod(brickPoint, surfaceBrick.xy);
      vec2 seamDistance = min(inBrick, surfaceBrick.xy - inBrick);
      float edgeWidth = max(fwidth(brickPoint.x), fwidth(brickPoint.y));
      float face = smoothstep(surfaceBrick.z * .45 - edgeWidth,
                              surfaceBrick.z * .45 + edgeWidth,
                              min(seamDistance.x, seamDistance.y));
      float variation = surfaceHash(vec3(floor(brickPoint / surfaceBrick.xy), 1.0));
      vec3 surfaceColor = mix(surfaceMortar, mix(surfaceColorA, surfaceColorB, variation), face);
      float surfaceHeight = face * surfaceBump;
    ` : `
      vec3 surfacePoint = vec3(vSurfacePosition.x, -vSurfacePosition.z, vSurfacePosition.y) * surfaceScale;
      float grain = surfaceNoise(surfacePoint) * .75 + surfaceNoise(surfacePoint * 2.0) * .25;
      vec3 surfaceColor = mix(surfaceColorA, surfaceColorB, grain);
      float surfaceHeight = grain * surfaceBump;
    `;
    shader.fragmentShader = shader.fragmentShader.replace("#include <color_fragment>", `
      #include <color_fragment>
      ${pattern}
      diffuseColor.rgb = surfaceColor;
    `);
    shader.fragmentShader = shader.fragmentShader.replace("#include <normal_fragment_maps>", `
      #include <normal_fragment_maps>
      vec3 surfaceDx = dFdx(-vViewPosition), surfaceDy = dFdy(-vViewPosition);
      vec3 surfaceR1 = cross(surfaceDy, normal), surfaceR2 = cross(normal, surfaceDx);
      float surfaceDet = dot(surfaceDx, surfaceR1);
      if (abs(surfaceDet) > 0.00000001) {
        normal = normalize(abs(surfaceDet) * normal - sign(surfaceDet) *
          (dFdx(surfaceHeight) * surfaceR1 + dFdy(surfaceHeight) * surfaceR2));
      }
    `);
  };
  material.needsUpdate = true;
}

export function prepareDetailedModel(group) {
  group.visible = false;
  group.traverse((object) => {
    if (!object.isMesh) return;
    object.castShadow = true;
    object.receiveShadow = true;
    for (const material of Array.isArray(object.material) ? object.material : [object.material]) {
      material.side = THREE.DoubleSide;
      applySurfaceDetail(material);
    }
  });
}

export function disposeModel(group) {
  group.removeFromParent();
  const geometries = new Set(), materials = new Set();
  group.traverse((object) => {
    if (object.geometry) geometries.add(object.geometry);
    if (object.material)
      for (const material of Array.isArray(object.material) ? object.material : [object.material]) materials.add(material);
  });
  for (const geometry of geometries) geometry.dispose();
  for (const material of materials) material.dispose();
}
