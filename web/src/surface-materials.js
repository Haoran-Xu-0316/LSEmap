import * as THREE from "three";
import { GROUND_FINISHES } from "./ground-textures.js";
import { applyFoliageDetail } from "./foliage-materials.js";
import { OUTDOOR_ATMOSPHERE } from "./outdoor-environment.js";
import { prepareWireGrid } from "./wire-grid-materials.js";

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

// The exporter records the physical role. Collection names such as GLAZING
// also contain stone, painted joinery and lights, so they are not material roles.
export function isGlazingMaterial(material) {
  const role = material.userData?.webSurfaceRole;
  if (role === "glazing" || role === "opaque") return role === "glazing";
  // Older assets retain a narrow fallback for actual glass names. A GLAZING
  // collection prefix alone must never turn stone or paint into reflective glass.
  return /(?:^|_)glass(?:_|\.|$)/i.test(material.name) ||
    /(?:^|_)glazing(?:\.\d+)?$/i.test(material.name) ||
    /(?:^|_)glazing_(?:clear|optical|neutral|reflective|tinted)(?:_|$)/i.test(material.name) ||
    /^(?:WEB_(?:DETAIL_)?)?MAR168_0[0-3]_0[01]_dielectric$/.test(material.name);
}

// Stable semantic roles apply to both merged campus and individual buildings.
export function outdoorSurfaceKind(name) {
  if (/asphalt|tarmac/i.test(name)) return 'asphalt';
  if (/Lincoln Inn Fields grass/i.test(name)) return 'grass';
  if (/PARK233_estimated_gravel/i.test(name)) return 'gravel';
  if (/Pale campus paving|MAR25_paving|CKK_V80_paving/i.test(name)) return 'paving-grid';
  if (/SITE_V47_(?:slab|yorkstone|edge)|PORTSMOUTH_estimated_yorkstone|(?:^|_)pale_gray_stone_\d+(?:\.|$)|CBG(?:203_ROOF|205_PODIUM)_paving|LRB_NEXT_PLAZA155_stone/i.test(name)) return 'stone';
  if (/SITE_V47_wood/i.test(name)) return 'timber';
  if (/(?:^|_)soil$/i.test(name)) return 'soil';
  if (/(?:^|_)bark$/i.test(name)) return 'bark';
  if (/foliage/i.test(name)) return 'foliage';
  return null;
}

const preparedMaterials = new WeakSet();
const detailedMaterials = new WeakSet();

// Presentation refinements are deliberately separate from source-model parameters.
// They describe a material finish, not measured ageing or photographic textures.
export function refineMaterialFinish(material, environmentMap = null) {
  const name = material.name.toLowerCase();
  const outdoorKind = outdoorSurfaceKind(name);
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
  if (prepareWireGrid(material)) return;
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
  } else if (matches(/SITE_V47_steel$|OLD_NEXT_(?:OLD_NEXT_)?(?:ACCESS_steel|APPROACH_silver)$/i)) {
    // Reuse the shared sky for exposed street steel and photographed OLD silver rails.
    // This separates their soft metallic highlight from painted street furniture.
    material.metalness = 0.9;
    material.roughness = 0.43;
    material.envMapIntensity = 0.7;
    if (environmentMap && !material.envMap) material.envMap = environmentMap;
  } else if (matches(/SITE_V47_wood/i)) {
    material.metalness = 0;
    material.roughness = 0.76;
  } else if (matches(/SITE172_SITE_V47_grout_Houghton/i)) {
    material.metalness = 0;
    material.roughness = .94;
    material.color.setRGB(.125, .133, .128);
  } else if (outdoorKind === "paving-grid" || outdoorKind === "stone" || matches(/SITE_V47_grout/i)) {
    material.metalness = 0;
    material.roughness = 0.9;
    if (outdoorKind === "paving-grid")
      material.color.lerp(new THREE.Color(.31, .32, .305), .65);
  } else if (matches(/foliage|Lincoln Inn Fields grass|(?:^|_)soil$|(?:^|_)bark$/i)) {
    material.metalness = 0;
    material.roughness = matches(/foliage/) ? 0.88 : 0.96;
    if (outdoorKind === "grass")
      material.color.lerp(new THREE.Color(.10, .23, .09), .65);
  } else if (outdoorKind === "gravel") {
    material.metalness = 0;
    material.roughness = 1;
  } else if (outdoorKind === "asphalt") {
    material.metalness = 0;
    material.roughness = 0.97;
    // Keep the already dark Clement House asphalt; correct the pale base roads.
    if (matches(/Road asphalt/i))
      material.color.lerp(new THREE.Color(.065, .075, .082), .8);
  } else if (matches(/gold|bronze|brass|copper/)) {
    material.metalness = Math.max(material.metalness, 0.72);
    material.roughness = Math.min(material.roughness, 0.34);
    material.envMapIntensity = 0.9;
  } else if (matches(/(?:^|[_\s])lead(?:[_\s.]|$)/)) {
    // Lead roofs already carry an authored finish. Preserve those coefficients
    // rather than polishing a rough cupola or making a painted cowl metallic.
    material.envMapIntensity = 0.75;
  } else if (matches(/zinc|aluminium|aluminum/)) {
    material.metalness = Math.max(material.metalness, 0.65);
    material.roughness = 0.48;
    material.envMapIntensity = 0.75;
  }
  material.needsUpdate = true;
}

export function applySurfaceDetail(material, groundTextures = null) {
  if (detailedMaterials.has(material)) return;
  const kind = outdoorSurfaceKind(material.name);
  const asphalt = kind === 'asphalt', bark = kind === 'bark';
  const outdoor = Boolean(kind), timber = kind === 'timber';
  const pavingGrid = kind === 'paving-grid';
  const edgeCourse = /SITE213_SITE_V47_slab_flush_edge_courses/i.test(material.name);
  const houghtonPaving = /SITE(?:172_SITE_V47_slab_\d+_Houghton|173_SITE_V47_slab_Houghton_paving_continuation)/i.test(material.name);
  const paving = pavingGrid || kind === 'stone' || asphalt;
  const grass = kind === 'grass', gravel = kind === 'gravel';
  let detail = material.userData.surfaceDetail;
  // An approved authored map already supplies the visible finish. Do not
  // overwrite its sampled colour with the procedural approximation below.
  if (material.map) return;
  if (!detail && outdoor) {
    // Preserve mapped geometry and palette; resolve aggregate and foliage tones
    // in the shared renderer rather than adding subpixel blades or leaf meshes.
    detail = {
      kind: "noise", scale: /foliage|grass/i.test(material.name) ? 1.8 : bark ? 5 : gravel ? 32 : asphalt ? 28 : 9,
      bump: /foliage|grass/.test(material.name) ? 0 : bark ? 0.0012 : gravel ? .001 : /asphalt|soil/.test(material.name) ? 0.0008 : 0.00035,
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
  // Keep the authored slab-to-slab variation, while giving the photographed
  // Houghton grey setts a calmer daylight finish. This is a display palette,
  // not a measured stone reflectance or a change to source material metadata.
  const color = (value) => {
    const result = value ? new THREE.Color(...value) : material.color.clone();
    return houghtonPaving ? result.lerp(new THREE.Color(.29, .30, .285), .70) : result;
  };
  const uniforms = {
    surfaceScale: { value: detail.scale },
    surfaceBump: { value: Math.min(0.006, Math.max(brick ? 0.0008 : 0, detail.bump || 0)) },
    surfaceColorA: { value: color(detail.colorA) },
    surfaceColorB: { value: color(detail.colorB) },
    surfaceMortar: { value: houghtonPaving ? new THREE.Color(.125, .133, .128) : color(detail.mortarColor) },
    surfaceBrick: { value: new THREE.Vector3(detail.brickWidth || .225, detail.rowHeight || .078, detail.mortarSize || .007) },
  };
  const groundAsset = groundTextures && paving ? GROUND_FINISHES.find(asset => asset.kind === (asphalt ? 'asphalt' : 'stone')) : null;
  if (groundAsset) {
    uniforms.groundFinish = groundTextures[groundAsset.kind];
    uniforms.groundRelief = groundTextures[groundAsset.kind+"Relief"];
    uniforms.groundReliefReady = groundTextures.reliefReady;
    uniforms.groundHeight = {value:groundAsset.height};
    uniforms.groundReady = groundTextures.ready;
    uniforms.groundMetres = {value:groundAsset.metres};
    uniforms.groundMean = {value:groundAsset.mean};
    // Measured channel mean keeps wear variation centred on the authored dry finish.
    uniforms.groundRoughnessMean = {value:groundAsset.roughnessMean ?? .5};
  }
  material.customProgramCacheKey = () => `lse-surface-finish14-${groundAsset ? "captured" : "procedural"}-${edgeCourse ? "edge-course" : pavingGrid ? "grid" : grass ? "grass" : asphalt ? "asphalt" : brick ? "brick" : timber ? "timber" : bark ? "bark" : paving ? "paving" : outdoor ? "outdoor" : "noise"}`;
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
      ${groundAsset ? 'uniform sampler2D groundFinish, groundRelief; uniform float groundReady, groundReliefReady, groundMetres, groundMean, groundHeight, groundRoughnessMean;' : ''}
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
      vec3 surfaceColor = mix(surfaceColorA, surfaceColorB, 0.5 + (grain - 0.5) * ${paving ? "0.45" : outdoor ? "1.2" : "0.32"});
      float surfaceHeight = resolvedGrain * surfaceBump * noiseVisibility;
      ${edgeCourse ? `
      // The existing flush bands carry route-aligned metric UVs. Resolve
      // short stone lengths without adding coplanar meshes or raised kerbs.
      float coursePoint = vSurfaceUv.x;
      float courseFootprint = fwidth(coursePoint);
      float courseVisibility = 1.0 - smoothstep(.18, .60, courseFootprint);
      float courseDistance = min(mod(coursePoint, .60), .60 - mod(coursePoint, .60));
      float courseFace = smoothstep(.002 - courseFootprint, .002 + courseFootprint, courseDistance);
      float courseTone = surfaceHash(vec3(floor(coursePoint / .60), 13.0, 2.0));
      surfaceColor *= mix(1.0, mix(.68, .97 + courseTone * .06, courseFace), courseVisibility);
      surfaceHeight += courseFace * .0006 * courseVisibility;
      ` : pavingGrid ? `
      // Metre-scale staggered slabs on otherwise plain approach surfaces only.
      // Existing modelled setts retain their own borders and grout geometry.
      vec2 slabPoint = mat2(.52992, .84805, -.84805, .52992) * vSurfacePosition.xz;
      vec2 slabSize = vec2(.60, .40);
      vec2 slabFootprint = fwidth(slabPoint);
      float slabVisibility = 1.0 - smoothstep(.32, .85,
        max(slabFootprint.x / slabSize.x, slabFootprint.y / slabSize.y));
      slabPoint.x += mod(floor(slabPoint.y / slabSize.y), 2.0) * slabSize.x * .5;
      vec2 inSlab = mod(slabPoint, slabSize);
      vec2 seamDistance = min(inSlab, slabSize - inSlab);
      vec2 seamFace = smoothstep(vec2(.003) - slabFootprint,
                                 vec2(.003) + slabFootprint, seamDistance);
      float slabFace = min(seamFace.x, seamFace.y);
      float slabTone = surfaceHash(vec3(floor(slabPoint / slabSize), 3.0));
      surfaceColor *= mix(1.0, mix(.66, .96 + slabTone * .08, slabFace), slabVisibility);
      surfaceHeight += slabFace * .0012 * slabVisibility;
      ` : grass ? `
      // Quiet broad turf tones, with faint maintenance bands rather than large
      // camouflage patches. This is an estimated finish, not surveyed mowing.
      float turf = surfaceNoise(vec3(vSurfacePosition.x * .045, 9.0, vSurfacePosition.z * .045));
      float mowPoint = (vSurfacePosition.x * .8 + vSurfacePosition.z * .6) / 3.5;
      float mowVisibility = 1.0 - smoothstep(.25, .8, fwidth(mowPoint));
      float mow = sin(mowPoint * 3.14159265) * .025 * mowVisibility;
      surfaceColor *= .94 + turf * .12 + mow;
      ` : asphalt ? `
      surfaceColor *= .97 + coarseGrain * .06;
      ` : ""}

    `;
    if (pavingGrid || kind === 'stone' || asphalt) {
      shader.uniforms.surfaceHorizon = { value: new THREE.Color(OUTDOOR_ATMOSPHERE.horizon) };
      shader.uniforms.surfaceLowerSky = { value: new THREE.Color(OUTDOOR_ATMOSPHERE.lowerSky) };
      shader.fragmentShader = 'uniform vec3 surfaceHorizon, surfaceLowerSky;\n' + shader.fragmentShader;
      shader.fragmentShader = shader.fragmentShader.replace('#include <dithering_fragment>', `
        // Feather only the outermost 55m of the existing district excerpt.
        // Keep the mapped campus, park, thresholds and raised furniture intact.
        // Native SITE216 base top is -.05m; flat peripheral roads are +.024m.
        if (vSurfacePosition.y < .03) {
          float mapMargin = min(min(vSurfacePosition.x + 375.0, 350.0 - vSurfacePosition.x),
                                min(vSurfacePosition.z + 415.0, 375.0 - vSurfacePosition.z));
          float edgeHaze = 1.0 - smoothstep(0.0, 55.0, mapMargin);
          vec3 viewRay = normalize(vSurfacePosition - cameraPosition);
          vec3 surround = mix(surfaceHorizon, surfaceLowerSky, smoothstep(0.0, .24, -viewRay.y));
          gl_FragColor.rgb = mix(gl_FragColor.rgb, surround, edgeHaze);
        }
        #include <dithering_fragment>
      `);
    }
    shader.fragmentShader = shader.fragmentShader.replace("#include <color_fragment>", `
      #include <color_fragment>
      ${pattern}
      // Fade fine grain before it becomes a subpixel pattern at campus scale.
      vec3 finePoint = vSurfacePosition * 85.0;
      float grainVisibility = 1.0 - smoothstep(0.35, 1.4, length(fwidth(finePoint)));
      float fineGrain = grainVisibility > .001 ? (surfaceNoise(finePoint) - 0.5) * grainVisibility : 0.0;
      ${groundAsset ? `
      float capturedRoughness = .5;
      float capturedFace = 0.0;
      if (groundReady > .5) {
        // World metres retain the same scale on base campus and detailed meshes.
        // Keep the photographed stone subtle enough to reveal individual slabs.
        // The existing palette, joints and shallow relief remain independent.
        vec3 groundSample = texture2D(groundFinish, vSurfacePosition.xz / groundMetres).rgb;
        float groundTone = dot(groundSample, vec3(.2126, .7152, .0722)) / groundMean;
        // The same mip-filtered photo supplies centimetre-scale wear. Fade its
        // added contrast as a pixel grows beyond the visible surface features.
        float groundDetailVisibility = 1.0 - smoothstep(.03, .16, length(fwidth(vSurfacePosition.xz)));
        vec3 groundNormal = normalize(cross(dFdx(vSurfacePosition), dFdy(vSurfacePosition)));
        float groundFace = smoothstep(.65, .95, abs(groundNormal.y));
        surfaceColor *= mix(1.0, clamp(groundTone, .72, 1.26), groundFace * ${groundAsset.kind === 'stone' ? 'mix(.10, .15, groundDetailVisibility)' : '.30'});
        if (groundReliefReady > .5) {
          // One filtered sample supplies both wear and shallow relief. World
          // coordinates align it exactly with the captured colour map.
          vec2 reliefPoint = vSurfacePosition.xz / groundMetres;
          vec2 reliefData = texture2D(groundRelief, reliefPoint).rg;
          float reliefVisibility = 1.0 - smoothstep(.5, 2.0, length(fwidth(reliefPoint * ${groundAsset.kind === 'stone' ? '32.0' : '512.0'})));
          surfaceHeight += (reliefData.r - .5) * groundHeight * reliefVisibility * groundFace;
          capturedRoughness = .5 + (reliefData.g - groundRoughnessMean);
          capturedFace = groundFace${groundAsset.kind === 'stone' ? ' * groundDetailVisibility' : ''};
        }
      }
      ` : ''}
      diffuseColor.rgb = surfaceColor * (1.0 + fineGrain * 0.08);
      surfaceHeight += fineGrain * 0.00018;
    `);
    shader.fragmentShader = shader.fragmentShader.replace("#include <roughnessmap_fragment>", `
      #include <roughnessmap_fragment>
      ${groundAsset ? `roughnessFactor = clamp(roughnessFactor + (capturedRoughness - .5) * ${groundAsset.kind === 'stone' ? '.65' : '.18'} * capturedFace, .72, 1.0);` : ""}
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
  // Preserve the existing surface hook and use the same finish at every scale.
  if (kind === "foliage") applyFoliageDetail(material);
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
  object.castShadow = !clearGlazing && !materials.some(material => material?.userData?.wireMesh);
  object.receiveShadow = true;
}

// A certified closed shell contributes only its near outward surface. Flat
// panes need both viewing directions, but never a second transparency draw.
export function prepareGlazingSides(material) {
  const side = material.userData.webClosedGlazing === true ? THREE.FrontSide : THREE.DoubleSide;
  if (material.side !== side) { material.side = side; material.needsUpdate = true; }
  if (material.transparent && (isGlazingMaterial(material) || /optics/i.test(material.name))) material.forceSinglePass = true;
}

/** Architecture has fixed local transforms; visibility, materials and parent
 * transforms remain live. Keep world-matrix propagation enabled for reparenting. */
export function prepareStaticModel(group) {
  group.traverse((object) => {
    if (object.matrixAutoUpdate) object.updateMatrix();
    object.matrixAutoUpdate = false;
  });
}

export function prepareDetailedModel(group, environmentMap = null, groundTextures = null) {
  group.visible = false;
  group.traverse((object) => {
    if (!object.isMesh) return;
    prepareMeshShadows(object);
    for (const material of Array.isArray(object.material) ? object.material : [object.material]) {
      prepareGlazingSides(material);
      refineMaterialFinish(material, environmentMap);
      applySurfaceDetail(material, groundTextures);
    }
  });
  prepareStaticModel(group);
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
