import {test, expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';

const read = async path => JSON.parse(await readFile(path, 'utf8'));
const hash = bytes => createHash('sha256').update(bytes).digest('hex');
const fullName = 'The London School of Economics and Political Science';
const mainFolder = 'result/blender/columbia_lettering_next';
const recoveryFolder = 'result/blender/stage137/columbia-recovery';

// Compare exact Draco primitives, including vertex/accessor bounds and PBR.
// The merger gives accepted lettering its own material ID. Compare that
// component at both scales without including intentionally reduced legacy mesh families.
function colPrimitives(bytes, accepted) {
  const jsonLength = bytes.readUInt32LE(12);
  const glb = JSON.parse(bytes.subarray(20, 20 + jsonLength));
  const binStart = 28 + jsonLength;
  const meshes = new Set(glb.nodes.filter(node => node.extras?.buildingCode === 'COL').map(node => node.mesh));
  expect(meshes.size).toBeGreaterThan(0);
  const accessor = index => {
    const value = glb.accessors[index];
    return {count: value.count, type: value.type, componentType: value.componentType, min: value.min, max: value.max};
  };
  return [...meshes].flatMap(index => glb.meshes[index].primitives.filter(primitive => accepted.has(glb.materials[primitive.material].name.replace(/^WEB_(DETAIL_)?/, ''))).map(primitive => {
    const compression = primitive.extensions?.KHR_draco_mesh_compression;
    expect(compression).toBeTruthy();
    const view = glb.bufferViews[compression.bufferView];
    const start = binStart + (view.byteOffset ?? 0);
    const material = glb.materials[primitive.material];
    return {
      material: material.name.replace(/^WEB_(DETAIL_)?/, ''),
      geometrySha256: hash(bytes.subarray(start, start + view.byteLength)),
      decoderAttributes: compression.attributes,
      attributes: Object.fromEntries(Object.entries(primitive.attributes).map(([key, value]) => [key, accessor(value)])),
      indices: accessor(primitive.indices),
      pbr: material.pbrMetallicRoughness,
      alphaMode: material.alphaMode ?? 'OPAQUE',
      doubleSided: material.doubleSided,
      finish: material.extras?.surfaceDetail,
    };
  }));
}

test('Columbia lettering recovery preserves the archived FONT and full glyph layout without rendering', async () => {
  const [audit, proof, recovered, recoveredAudit] = await Promise.all([
    read(mainFolder + '/audit.json'), read(mainFolder + '/verification.json'),
    read(recoveryFolder + '/verification.json'), read(recoveryFolder + '/audit.json'),
  ]);
  expect(audit.ownedObjects).toEqual(['COL_NEXT_complete_school_name']);
  expect(audit.archivedObjects).toEqual(['COL_D4_school_name']);
  expect(audit.fullName).toBe(fullName);
  expect(audit.lettering.ownedHeight).toBe(audit.lettering.originalHeight);
  expect(audit.lettering.actualFullPhraseFrontageWidth).toBeGreaterThan(audit.lettering.oldTextWidth);
  expect(audit.lettering.horizontalScalingApplied).toBe(false);
  expect(proof.savedComponentReopened).toBe(true);
  expect(proof.originalCurvePreserved).toBe(true);
  expect(proof.fullTextReopened).toBe(fullName);
  expect(proof.nativeRenderVisuallyReviewed).toBe(true);
  expect(proof.renderCount).toBe(1);
  expect(hash(await readFile(mainFolder + '/columbia-lettering-component.blend'))).toBe(proof.componentSha256);
  expect(recovered.savedComponentReopened).toBe(true);
  expect(recovered.originalCurvePreserved).toBe(true);
  expect(recovered.originalGeometryPreserved).toBe(true);
  expect(recovered.allOriginalFingerprintsPreserved).toBe(true);
  expect(recovered.fullTextReopened).toBe(fullName);
  expect(recovered.glyphSizeRetained).toBe(true);
  expect(recovered.fontRetained).toBe(true);
  expect(recovered.horizontalScalingApplied).toBe(false);
  expect(recovered.reopenedFrontageBounds).toEqual(proof.reopenedFrontageBounds);
  expect(recovered.frontageMarginLeft).toBeGreaterThan(.35);
  expect(recovered.frontageMarginRight).toBeGreaterThan(.35);
  expect(recovered.rendered).toBe(false);
  expect(recovered.renderCount).toBe(0);
  expect(recovered.nativeRender).toBeUndefined();
  expect(recovered.mainComponentUnchanged).toBe(true);
  expect(recovered.mainComponentSha256).toBe(proof.componentSha256);
  expect(hash(await readFile(recoveryFolder + '/columbia-lettering-component.blend'))).toBe(recovered.componentSha256);
  expect(recoveredAudit.originalCurveSignature).toEqual(audit.originalCurveSignature);
  expect(recovered.recoveryRecords).toHaveLength(2);
  for (const record of recovered.recoveryRecords) {
    expect(record.removedObjects).toEqual(['COL_NEXT_complete_school_name']);
    expect(record.removedCurveVia).toBe('bpy.data.curves.remove');
    expect(record.originalCurveRestored).toBe(true);
    expect(record.allRemainingFingerprintsPreserved).toBe(true);
    expect(record.unrelatedVisibilityPreserved).toBe(true);
  }
});

test('Columbia completed lettering exports identical component geometry and material in campus and detail', async () => {
  const [catalogue, proof, audit, before] = await Promise.all([
    read('dist/models/catalogue.json'), read('result/blender/stage137/saved-verification.json'),
    read(mainFolder + '/audit.json'), read('result/blender/stage137/catalogue-before.json'),
  ]);
  expect(catalogue.version).toBe('137');
  expect(catalogue.sourceModelSha256).toBe(proof.sourceModelSha256);
  expect(proof.ownedObjects).toContain('COL_NEXT_complete_school_name');
  expect(proof.archivedObjects).toContain('COL_D4_school_name');
  expect(proof.originalGeometryRetained).toBe(true);
  const building = catalogue.buildings.find(row => row.code === 'COL');
  expect(building.detailedExterior.sha256).not.toBe(before.buildings.find(row => row.code === 'COL').detailedExterior.sha256);
  const [campus, detail] = await Promise.all([readFile('dist/models/campus.glb'), readFile('dist' + building.detailedExterior.url)]);
  expect(hash(detail)).toBe(building.detailedExterior.sha256);
  const accepted=new Set(proof.ownedMaterialNames.COL);
  const campusPrimitives = colPrimitives(campus,accepted), detailPrimitives = colPrimitives(detail,accepted);
  expect(campusPrimitives.length).toBeGreaterThan(0);
  expect(new Set(campusPrimitives.map(p=>p.material))).toEqual(accepted);
  expect(campusPrimitives).toEqual(detailPrimitives);
  for (const material of audit.originalCurveSignature.materials) {
    const matching = campusPrimitives.filter(primitive => primitive.material.replace(/\.\d{3}$/, '') === 'COL_NEXT_'+material);
    expect(matching.length).toBeGreaterThan(0);
    expect(matching.every(primitive => primitive.attributes.POSITION.count > 0)).toBe(true);
  }
});
