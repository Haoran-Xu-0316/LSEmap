import {test, expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';
import * as THREE from 'three';
import {isGlazingMaterial, prepareDetailedModel, prepareMeshShadows, prepareGlazingSides, refineMaterialFinish} from '../src/surface-materials.js';

async function modelDocument(url) {
  const bytes = await readFile('web/public' + url);
  return JSON.parse(bytes.subarray(20, 20 + bytes.readUInt32LE(12)));
}

// Exercise the actual released names and optical values in both rendering paths.
test('MAR legacy pane families receive identical glazing treatment in overview and detail', async () => {
  const catalogue = JSON.parse(await readFile('web/public/models/catalogue.json'));
  const mar = catalogue.buildings.find(building => building.code === 'MAR');
  const environment = new THREE.Texture();
  const outcomes = [];
  for (const [index, url] of ['/models/campus.glb', mar.detailedExterior.url].entries()) {
    const document = await modelDocument(url);
    const panes = document.materials.filter(material => /MAR168_\d\d_\d\d_dielectric$|MAR188_(middle_)?retained_dielectric_glass$/.test(material.name));
    expect(panes.map(p=>p.name.replace(/^WEB_(DETAIL_)?/, '')).sort()).toEqual([
      'MAR168_01_00_dielectric','MAR168_02_00_dielectric','MAR168_02_01_dielectric','MAR168_03_00_dielectric',
      'MAR188_middle_retained_dielectric_glass','MAR188_retained_dielectric_glass',
    ].sort());
    const results = [];
    for (const descriptor of panes) {
      const pbr = descriptor.pbrMetallicRoughness;
      const material = new THREE.MeshStandardMaterial({
        color: new THREE.Color(...pbr.baseColorFactor.slice(0, 3)),
        roughness: pbr.roughnessFactor, metalness: pbr.metallicFactor,
        opacity: pbr.baseColorFactor[3], transparent: descriptor.alphaMode === 'BLEND',
      });
      material.name = descriptor.name;
      const mesh = new THREE.Mesh(new THREE.PlaneGeometry(), material);
      if (index === 0) {
        prepareMeshShadows(mesh); prepareGlazingSides(material); refineMaterialFinish(material, environment);
      } else {
        const group = new THREE.Group(); group.add(mesh); prepareDetailedModel(group, environment);
      }
      expect(isGlazingMaterial(material)).toBe(true);
      expect(material.envMap).toBe(environment);
      expect(material.envMapIntensity).toBe(1.65);
      expect(material.opacity).toBe(pbr.baseColorFactor[3]);
      expect(mesh.castShadow).toBe(!material.transparent);
      if (material.transparent) {
        expect(material.depthWrite).toBe(false);
        expect(material.forceSinglePass).toBe(true);
        const shader = {fragmentShader: '#include <opaque_fragment>'};
        material.onBeforeCompile(shader);
        expect(shader.fragmentShader).toContain('glazingGrazing');
      }
      results.push({name: material.name.replace(/^WEB_(DETAIL_)?/, ''), color: material.color.toArray(), opacity: material.opacity, shadow: mesh.castShadow});
      mesh.geometry.dispose(); material.dispose();
    }
    outcomes.push(results.sort((a, b) => a.name.localeCompare(b.name)));
  }
  expect(outcomes[0]).toEqual(outcomes[1]);
  environment.dispose();
});

test('ordinary dielectric walls and mixed frame meshes remain opaque shadow casters', () => {
  const wall = new THREE.MeshStandardMaterial(); wall.name = 'MAR_concrete_dielectric';
  const glass = new THREE.MeshStandardMaterial({transparent: true, opacity: .55});
  glass.name = 'WEB_DETAIL_MAR168_03_00_dielectric';
  expect(isGlazingMaterial(wall)).toBe(false);
  const mixed = new THREE.Mesh(new THREE.BoxGeometry(), [wall, glass]);
  prepareMeshShadows(mixed); expect(mixed.castShadow).toBe(true);
  mixed.geometry.dispose(); wall.dispose(); glass.dispose();
});
