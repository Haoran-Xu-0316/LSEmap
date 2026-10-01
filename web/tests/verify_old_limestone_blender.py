"""Inspect the saved limestone scene and compare it with the previous native scene."""
from pathlib import Path
import array
import hashlib
import json
import bpy
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'result/blender/stage86'
audit = json.loads((OUT / 'old-limestone-audit.json').read_text())
bpy.ops.wm.open_mainfile(filepath=str(ROOT / 'result/blender/LSE_campus_detailed_v86.blend'))

def geometry_hash(obj):
    digest = hashlib.sha256(str([list(row) for row in obj.matrix_world]).encode())
    if obj.type == 'MESH':
        digest.update(array.array('f', [c for v in obj.data.vertices for c in v.co]).tobytes())
        digest.update(array.array('i', [loop.vertex_index for loop in obj.data.loops]).tobytes())
    return digest.hexdigest()

expected = {(a['object'], a['slot']): a for a in audit['assignments']}
assert set(bpy.data.objects.keys()) == set(audit['baselineObjects'])
for name, record in audit['baselineObjects'].items():
    obj = bpy.data.objects[name]
    assert geometry_hash(obj) == record['geometry'], name
    for slot, original in enumerate(record['materials']):
        material = obj.data.materials[slot]
        target = expected.get((name, slot))
        assert (material.name if material else None) == (target['material'] if target else original), (name, slot)
for name in audit['materials']:
    material = bpy.data.materials[name]
    assert material['siteDetail']
    assert not any(n.type == 'TEX_IMAGE' for n in material.node_tree.nodes)
    shader = next(n for n in material.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    assert shader.inputs['Base Color'].is_linked and shader.inputs['Normal'].is_linked
    assert abs(shader.inputs['Roughness'].default_value - .87) < .00001
    assert shader.inputs['Metallic'].default_value == 0
    noise = next(n for n in material.node_tree.nodes if n.type == 'TEX_NOISE')
    bump = next(n for n in material.node_tree.nodes if n.type == 'BUMP')
    assert noise.inputs['Scale'].default_value == 2
    assert abs(bump.inputs['Distance'].default_value * bump.inputs['Strength'].default_value - .0003) < .000001
    assert material.diffuse_color[0] - material.diffuse_color[2] < .04
audit['savedMeasurements'] = {'allGeometryUnchanged': True, 'onlyDeclaredMaterialSlotsChanged': True,
                               'proceduralMaterials': len(audit['materials']), 'assignedSlots': len(expected),
                               'photoTextures': 0, 'bumpMetres': .0003}
(OUT / 'old-limestone-audit.json').write_text(json.dumps(audit, indent=2) + '\n')
print('SAVED_OLD_LIMESTONE_VERIFIED', audit['savedMeasurements'], flush=True)
