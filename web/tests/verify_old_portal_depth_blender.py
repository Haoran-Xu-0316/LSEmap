"""Reopen saved OLD refinement and measure the actual stone and sign positions."""
from pathlib import Path
import array, hashlib, json
import bpy, bmesh
from mathutils import Vector
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'result/blender/stage97'
audit = json.loads((OUT / 'old-portal-depth-audit.json').read_text())
bpy.ops.wm.open_mainfile(filepath=str(ROOT / 'result/blender/LSE_campus_detailed_v97.blend'))
bpy.context.window.scene = bpy.data.scenes['00_CAMPUS_COMPLETE']
origin, right, outward = [Vector(audit['frame'][k]) for k in ['origin', 'right', 'outward']]

def fingerprint(obj):
    digest = hashlib.sha256(str([list(row) for row in obj.matrix_world]).encode())
    if obj.type == 'MESH':
        digest.update(array.array('f', [c for v in obj.data.vertices for c in v.co]).tobytes())
        digest.update(array.array('i', [l.vertex_index for l in obj.data.loops]).tobytes())
    if obj.type == 'FONT': digest.update(obj.data.body.encode())
    digest.update(str([m.name if m else None for m in getattr(obj.data, 'materials', [])]).encode())
    return digest.hexdigest()

for name, digest in audit['originalFingerprints'].items():
    assert fingerprint(bpy.data.objects[name]) == digest, name
assert set(bpy.data.objects) - {bpy.data.objects[n] for n in audit['originalFingerprints']} == {bpy.data.objects[n] for n in audit['addedObjects']} | {bpy.data.objects[r['copy']] for r in audit['copies']}
measurements = {}
for record in audit['copies']:
    source, copy = [bpy.data.objects[record[k]] for k in ['source', 'copy']]
    assert source.hide_render and not copy.hide_render
    if copy.type == 'MESH':
        assert len(copy.data.vertices) == len(source.data.vertices)
        assert [l.vertex_index for l in copy.data.loops] == [l.vertex_index for l in source.data.loops]
        for a, b in zip(source.data.vertices, copy.data.vertices):
            delta = copy.matrix_world @ b.co - source.matrix_world @ a.co
            assert abs(delta.dot(right)) < 2e-5 and abs(delta.z) < 2e-5
        if 'newDepth' in record:
            ds = [(copy.matrix_world @ v.co - origin).dot(outward) for v in copy.data.vertices]
            assert abs(min(ds) - record['newDepth'][0]) < 2e-5
            assert abs(max(ds) - record['newDepth'][1]) < 2e-5
            bm = bmesh.new(); bm.from_mesh(copy.data)
            assert all(edge.is_manifold for edge in bm.edges), copy.name
            assert abs(bm.calc_volume()) > 1e-6
            bm.free()
            measurements[record['source']] = {'depth': [min(ds), max(ds)], 'unchangedFrontageAndHeight': True}
    if 'translationDepth' in record:
        delta = copy.matrix_world.translation - source.matrix_world.translation
        assert abs(delta.dot(outward) - record['translationDepth']) < 2e-5
        assert abs(delta.dot(right)) < 2e-5 and abs(delta.z) < 2e-5
backing = bpy.data.objects[audit['addedObjects'][0]]
bm = bmesh.new(); bm.from_mesh(backing.data)
assert all(edge.is_manifold for edge in bm.edges) and bm.calc_volume() > 0
bm.free()
assert abs(max((backing.matrix_world @ v.co - origin).dot(outward) for v in backing.data.vertices) - .23) < 2e-5
# Signs have a small mount clearance; raised lettering remains in front of them.
plaques = bpy.data.objects['OLD_V97_LSE_entrance_signs']
plaque_ds = [(plaques.matrix_world @ v.co - origin).dot(outward) for v in plaques.data.vertices]
assert .02 < min(plaque_ds) - .270 < .03
for suffix in ['', '.001']:
    lse = bpy.data.objects['OLD_V97_LSE_entry_sign' + suffix]
    name = bpy.data.objects['OLD_V97_Old_Building_name' + suffix]
    assert .01 < (lse.matrix_world.translation - origin).dot(outward) - max(plaque_ds) < .025
    assert .01 < (name.matrix_world.translation - origin).dot(outward) - .270 < .025
material = bpy.data.materials['OLD_V97_entry_glass']
shader = next(n for n in material.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
assert abs(shader.inputs['Transmission Weight'].default_value - .55) < 1e-6
assert abs(material['webOpacity'] - .46) < 1e-6
assert material != bpy.data.objects['OLD_D5_entry65_glass'].data.materials[0]
audit['savedMeasurements'] = {'originalObjectsUnchanged': True, 'unchangedFrontageAndHeight': True,
                             'stoneDepths': measurements, 'mountedSignsVerified': True,
                             'independentDoorGlassMaterial': True}
(OUT / 'old-portal-depth-audit.json').write_text(json.dumps(audit, indent=2) + '\n')
print('SAVED_OLD_PORTAL_DEPTH_VERIFIED', len(audit['copies']))
