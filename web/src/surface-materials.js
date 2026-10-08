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

// These legacy MAR names lost the word “glass” during Blender material copying.
// Match only the authored pane family; “dielectric” alone also describes stone.
export function isGlazingMaterial(material) {
  return /glass|glazing/i.test(material.name) ||
    /^(?:WEB_(?:DETAIL_)?)?MAR168_0[0-3]_0[01]_dielectric$/.test(material.name);
}

const preparedMaterials = new WeakSet();
const detailedMaterials = new WeakSet();

// Presentation refinements are deliberately separate from source-model parameters.
// They describe a material finish, not measured ageing or photographic textures.
export function refineMaterialFinish(material, environmentMap = null) {
  const name = material.name.toLowerCase();
  const matches = (pattern) => pattern.test(name);
  // With a scene-inherited environment, Three.js uses scene intensity instead
  // of material intensity. Bind the shared PMREM explicitly for glazing so its
  // selected finish actually reaches the renderer. No additional capture or
  // texture allocation is needed, and existing authored maps remain intact.
  if (environmentMap && isGlazingMaterial(material) && !material.envMap) {
    material.envMap = environmentMap;
    material.needsUpdate = true;
  }
  if (preparedMaterials.has(material)) return;
  preparedMaterials.add(material);
  if (isGlazingMaterial(material)) {
    // Preserve tinted glazing while reducing the exaggerated cyan in older assets.
    const luminance = material.color.r * .2126 + material.color.g * .7152 + material.color.b * .0722;
    material.color.lerp(new THREE.Color(luminance, luminance, luminance), .28);
    material.roughness = THREE.MathUtils.clamp(material.roughness, .12, .22);
    material.metalness = 0;
    material.envMapIntensity = 1.65;
    if (material.isMeshPhysicalMaterial) {
      material.ior = 1.5;
      material.specularIntensity = 1;
    }
    // Keep the recorded tint and face-on transparency. At grazing angles the
    // pane reflects more and reveals less behind it, without a refraction pass.
    if (material.transparent) {
      material.depthWrite = false;
      material.forceSinglePass = true;
      const previousCompile = material.onBeforeCompile;
      const previousKey = material.customProgramCacheKey();
      material.customProgramCacheKey = () => `${previousKey}-lse-glazing-fresnel1`;
      material.onBeforeCompile = (shader, renderer) => {
        previousCompile.call(material, shader, renderer);
        shader.fragmentShader = shader.fragmentShader.replace("#include <opaque_fragment>", `
          float glazingFacing = clamp(abs(dot(normal, normalize(vViewPosition))), 0.0, 1.0);
          float glazingGrazing = pow(1.0 - glazingFacing, 5.0);
          diffuseColor.a += (1.0 - diffuseColor.a) * glazingGrazing;
          #include <opaque_fragment>
        `);
      };
    }
  } else if (matches(/SITE_V47_iron$/i)) {
    // Bollards, bench supports and tree grates are painted iron: the coating
    // reflects as a dielectric, rather than dark polished bare metal.
    material.metalness = 0;
    material.roughness = 0.72;
  } else if (matches(/SITE_V47_steel$/i)) {
    // Reuse the existing sky capture for exposed cycle hoops and bench fixings.
    // This separates their soft metallic highlight from painted street furniture.
    material.metalness = 0.9;
    material.roughness = 0.43;
    material.envMapIntensity = 0.7;
    if (environmentMap && !material.envMap) material.envMap = environmentMap;
  } else if (matches(/SITE_V47_wood/i)) {
    material.metalness = 0;
    material.roughness = 0.76;
  } else if (matches(/SITE_V47_(?:slab|yorkstone|edge|grout)|campus paving|MAR25_paving|CKK_V80_paving/i)) {
    material.metalness = 0;
    material.roughness = 0.9;
  } else if (matches(/foliage|Lincoln Inn Fields grass|(?:^|_)soil$|(?:^|_)bark$/i)) {
    material.metalness = 0;
    material.roughness = matches(/foliage/) ? 0.88 : 0.96;
  } else if (matches(/Road asphalt/i)) {
    material.metalness = 0;
    material.roughness = 0.97;
  } else if (matches(/gold|bronze|brass|copper/)) {
    material.metalness = Math.max(material.metalness, 0.72);
    material.roughness = Math.min(material.roughness, 0.34);
    material.envMapIntensity = 0.9;
  } else if (matches(/lead|zinc|aluminium|aluminum/)) {
    material.metalness = Math.max(material.metalness, 0.65);
    material.roughness = 0.48;
    material.envMapIntensity = 0.75;
  }
  material.needsUpdate = true;
}

export function applySurfaceDetail(material) {
  if (detailedMaterials.has(material)) return;
  const landscape = /(?:^|_)(?:soil|bark)$|London plane foliage|Lincoln Inn Fields grass/i.test(material.name);
  const asphalt = /Road asphalt/i.test(material.name);
  const bark = /(?:^|_)bark$/i.test(material.name);
  const outdoor = landscape || /SITE_V47_(?:slab|yorkstone|edge|soil|wood)|campus paving|MAR25_paving|CKK_V80_paving|Road asphalt|Lincoln Inn Fields grass|London plane foliage/i.test(material.name);
  const timber = /SITE_V47_wood/i.test(material.name);
  const paving = /SITE_V47_(?:slab|yorkstone|edge)|campus paving|MAR25_paving|CKK_V80_paving|Road asphalt/i.test(material.name);
  let detail = material.userData.surfaceDetail;
  if (!detail && outdoor) {
    // Preserve mapped geometry and palette; resolve aggregate and foliage tones
    // in the shared renderer rather than adding subpixel blades or leaf meshes.
    detail = {
      kind: "noise", scale: /foliage|grass/.test(material.name) ? 1.8 : bark ? 5 : asphalt ? 22 : 9,
      bump: /foliage|grass/.test(material.name) ? 0 : bark ? 0.0012 : /asphalt|soil/.test(material.name) ? 0.0008 : 0.00035,
      colorA: material.color.clone().multiplyScalar(0.82).toArray(),
      colorB: material.color.clone().multiplyScalar(1.10).toArray(),
    };
  }
  if (!detail && /stone|concrete|limestone|sandstone|render|stucco/i.test(material.name)) {
    detail = {
      kind: "noise", scale: 3, bump: 0.00035,
      colorA: material.color.clone().multiplyScalar(0.96).toArray(),
      colorB: material.color.clone().multiplyScalar(1.025).toArray(),
    };
  }
  if (!detail || !["noise", "brick"].includes(detail.kind)) return;
  detailedMaterials.add(material);
  const brick = detail.kind === "brick";
  const color = (value) => value ? new THREE.Color(...value) : material.color.clone();
  const uniforms = {
    surfaceScale: { value: detail.scale },
    surfaceBump: { value: Math.min(0.006, Math.max(brick ? 0.0008 : 0, detail.bump || 0)) },
    surfaceColorA: { value: color(detail.colorA) },
    surfaceColorB: { value: color(detail.colorB) },
    surfaceMortar: { value: color(detail.mortarColor) },
    surfaceBrick: { value: new THREE.Vector3(detail.brickWidth || .225, detail.rowHeight || .078, detail.mortarSize || .007) },
  };
  material.customProgramCacheKey = () => `lse-surface-finish7-${brick ? "brick" : timber ? "timber" : bark ? "bark" : paving ? "paving" : outdoor ? "outdoor" : "noise"}`;
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
      // Measure the unshifted coordinates: staggered row offsets are discontinuous.
      vec2 footprint = fwidth(brickPoint);
      float tileVisibility = 1.0 - smoothstep(0.45, 1.25,
        max(footprint.x / surfaceBrick.x, footprint.y / surfaceBrick.y));
      float row = floor(brickPoint.y / surfaceBrick.y);
      brickPoint.x += mod(row, 2.0) * surfaceBrick.x * 0.5;
      vec2 inBrick = mod(brickPoint, surfaceBrick.xy);
      vec2 seamDistance = min(inBrick, surfaceBrick.xy - inBrick);
      float edgeWidth = max(footprint.x, footprint.y);
      float face = smoothstep(surfaceBrick.z * .45 - edgeWidth,
                              surfaceBrick.z * .45 + edgeWidth,
                              min(seamDistance.x, seamDistance.y));
      float variation = surfaceHash(vec3(floor(brickPoint / surfaceBrick.xy), 1.0));
      vec3 resolvedColor = mix(surfaceMortar, mix(surfaceColorA, surfaceColorB, variation), face);
      // Subpixel tiles converge to their area-weighted colour instead of aliasing.
      float averageFace = (1.0 - surfaceBrick.z * .9 / surfaceBrick.x) *
                          (1.0 - surfaceBrick.z * .9 / surfaceBrick.y);
      vec3 averageColor = mix(surfaceMortar, mix(surfaceColorA, surfaceColorB, .5), averageFace);
      vec3 surfaceColor = mix(averageColor, resolvedColor, tileVisibility);
      float surfaceHeight = face * surfaceBump * tileVisibility;
    ` : `
      vec3 surfacePoint = vec3(vSurfacePosition.x, -vSurfacePosition.z, vSurfacePosition.y) * surfaceScale;
      ${timber ? "surfacePoint *= vec3(0.12, 2.5, 1.0);" : bark ? "surfacePoint *= vec3(2.4, 2.4, 0.16);" : ""}
      float noiseVisibility = 1.0 - smoothstep(0.35, 1.4, length(fwidth(surfacePoint)));
      // Filter coarse variation independently, keeping broad landscape tones
      // readable while aggregate and wood grain disappear into distant pixels.
      float coarseVisibility = 1.0 - smoothstep(0.35, 1.4, length(fwidth(surfacePoint * .16)));
      float coarseGrain = coarseVisibility > .001 ? mix(.5, surfaceNoise(surfacePoint * .16), coarseVisibility) : .5;
      float resolvedGrain = noiseVisibility > .001 ? mix(.5, surfaceNoise(surfacePoint), noiseVisibility) : .5;
      float grain = ${outdoor ? "resolvedGrain * .55 + coarseGrain * .45" : "resolvedGrain"};
      // Keep the source palette midpoint without oversized concrete blotches.
      vec3 surfaceColor = mix(surfaceColorA, surfaceColorB, 0.5 + (grain - 0.5) * ${outdoor ? "1.2" : "0.32"});
      float surfaceHeight = resolvedGrain * surfaceBump * noiseVisibility;
    `;
    shader.fragmentShader = shader.fragmentShader.replace("#include <color_fragment>", `
      #include <color_fragment>
      ${pattern}
      // Fade fine grain before it becomes a subpixel pattern at campus scale.
      vec3 finePoint = vSurfacePosition * 85.0;
      float grainVisibility = 1.0 - smoothstep(0.35, 1.4, length(fwidth(finePoint)));
      float fineGrain = grainVisibility > .001 ? (surfaceNoise(finePoint) - 0.5) * grainVisibility : 0.0;
      diffuseColor.rgb = surfaceColor * (1.0 + fineGrain * 0.08);
      surfaceHeight += fineGrain * 0.00018;
    `);
    shader.fragmentShader = shader.fragmentShader.replace("#include <roughnessmap_fragment>", `
      #include <roughnessmap_fragment>
      // Reuse the resolved grain. No additional noise evaluations are needed
      // for the worn satin wood and dry stone microfacet variation.
      roughnessFactor = clamp(roughnessFactor + fineGrain * ${timber ? "0.22" : paving ? "0.18" : "0.12"}
        ${!brick && (timber || paving) ? "+ (grain - 0.5) * 0.08" : ""}, 0.04, 1.0);
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

// PCF depth shadows treat alpha-blended panes as opaque occluders. Keep their
// reflections and received shadows, but let daylight reach the room behind.
// This is an unattenuated daylight approximation, not coloured glass caustics.
// Opaque, masked and mixed frame/pane meshes keep their structural shadows.
export function prepareMeshShadows(object) {
  const materials = Array.isArray(object.material) ? object.material : [object.material];
  const clearGlazing = materials.length > 0 && materials.every((material) =>
    material && isGlazingMaterial(material) &&
    ((material.transparent && material.opacity < 1) || material.transmission > 0) &&
    material.alphaTest === 0 && !material.alphaToCoverage
  );
  object.castShadow = !clearGlazing;
  object.receiveShadow = true;
}

// A certified closed shell contributes only its near outward surface. Flat
// panes need both viewing directions, but never a second transparency draw.
export function prepareGlazingSides(material) {
  const side = material.userData.webClosedGlazing === true ? THREE.FrontSide : THREE.DoubleSide;
  if (material.side !== side) { material.side = side; material.needsUpdate = true; }
  if (material.transparent && (isGlazingMaterial(material) || /optics/i.test(material.name))) material.forceSinglePass = true;
}

export function prepareDetailedModel(group, environmentMap = null) {
  group.visible = false;
  group.traverse((object) => {
    if (!object.isMesh) return;
    prepareMeshShadows(object);
    for (const material of Array.isArray(object.material) ? object.material : [object.material]) {
      prepareGlazingSides(material);
      refineMaterialFinish(material, environmentMap);
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
