// Estimated opaque leaf-cluster finish. No species, geometry or animation is inferred.
// Apply after the shared surface finish so both onBeforeCompile hooks are preserved.
const detailedFoliage = new WeakSet();
const VERSION = 'lse-foliage235-v1';

export function isFoliageMaterial(material) {
  if (!material || !(material.isMeshStandardMaterial || material.isMeshPhysicalMaterial)) return false;
  const explicit = material.userData?.webSurfaceRole === 'foliage' ||
    /(?:^|[_\s])foliage(?:[_\s.]|$)/i.test(material.name);
  return explicit && !material.transparent && material.opacity === 1 &&
    !(material.transmission > 0) && !material.map;
}

const foliageFunctions = `
varying vec3 vFoliagePosition;
float foliageHash(vec3 p) {
  p = fract(p * .1031);
  p += dot(p, p.yzx + 33.33);
  return fract((p.x + p.y) * p.z);
}
float foliageNoise(vec3 p) {
  vec3 c = floor(p), f = fract(p);
  // Continuous first and second derivatives avoid hard cell-edge highlights.
  f = f * f * f * (f * (f * 6.0 - 15.0) + 10.0);
  return mix(mix(mix(foliageHash(c), foliageHash(c + vec3(1,0,0)), f.x),
                 mix(foliageHash(c + vec3(0,1,0)), foliageHash(c + vec3(1,1,0)), f.x), f.y),
             mix(mix(foliageHash(c + vec3(0,0,1)), foliageHash(c + vec3(1,0,1)), f.x),
                 mix(foliageHash(c + vec3(0,1,1)), foliageHash(c + vec3(1,1,1)), f.x), f.y), f.z);
}
float filteredFoliage(vec3 p, float visibility) {
  return mix(.5, foliageNoise(p), visibility);
}
`;

export function applyFoliageDetail(material) {
  if (!isFoliageMaterial(material) || detailedFoliage.has(material)) return false;
  detailedFoliage.add(material);
  const previousCompile = material.onBeforeCompile;
  const previousKey = material.customProgramCacheKey();
  material.customProgramCacheKey = () => `${previousKey}|${VERSION}`;
  material.onBeforeCompile = function (shader, renderer) {
    previousCompile.call(this, shader, renderer);
    shader.vertexShader = 'varying vec3 vFoliagePosition;\n' + shader.vertexShader;
    shader.vertexShader = shader.vertexShader.replace('#include <project_vertex>', `
      vFoliagePosition = (modelMatrix * vec4(transformed, 1.0)).xyz;
      #include <project_vertex>
    `);
    shader.fragmentShader = foliageFunctions + shader.fragmentShader;
    shader.fragmentShader = shader.fragmentShader.replace('#include <roughnessmap_fragment>', `
      // Metre-scaled volume coordinates remain fixed during camera movement.
      // Each octave fades before a pixel spans a substantial fraction of its cell.
      vec3 foliageClusterPoint = vFoliagePosition * 3.4;
      vec3 foliageLeafPoint = vFoliagePosition * 14.0 + vec3(17.1, 3.7, 9.2);
      float foliageClusterVisibility = 1.0 - smoothstep(.18, .70, length(fwidth(foliageClusterPoint)));
      float foliageLeafVisibility = 1.0 - smoothstep(.14, .60, length(fwidth(foliageLeafPoint)));
      float foliageCluster = filteredFoliage(foliageClusterPoint, foliageClusterVisibility);
      float foliageLeaf = filteredFoliage(foliageLeafPoint, foliageLeafVisibility);
      // Restrained pockets and leaf faces sit inside the retained crown silhouette.
      float foliageTone = 1.0 + (foliageCluster - .5) * .72 + (foliageLeaf - .5) * .34;
      diffuseColor.rgb *= foliageTone;
      float foliageHeight = (foliageCluster - .5) * .024 + (foliageLeaf - .5) * .006;
      #include <roughnessmap_fragment>
    `);
    shader.fragmentShader = shader.fragmentShader.replace('#include <lights_fragment_begin>', `
      // Surface-gradient relief changes lighting only. Clamp its slope so a
      // grazing crown does not acquire sharp, unstable specular pinpoints.
      vec3 foliageDx = dFdx(-vViewPosition), foliageDy = dFdy(-vViewPosition);
      vec3 foliageR1 = cross(foliageDy, normal), foliageR2 = cross(normal, foliageDx);
      float foliageDet = dot(foliageDx, foliageR1);
      vec3 foliageGradient = (dFdx(foliageHeight) * foliageR1 + dFdy(foliageHeight) * foliageR2) /
        max(abs(foliageDet), 1e-9);
      foliageGradient *= min(1.0, .36 / max(length(foliageGradient), 1e-5));
      normal = normalize(normal - sign(foliageDet) * foliageGradient);
      #include <lights_fragment_begin>
    `);
  };
  material.needsUpdate = true;
  return true;
}
