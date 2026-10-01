"""Reopen CLM roof candidate and check lower fabric and other buildings."""
from pathlib import Path
import array, hashlib, json, math
import bpy
ROOT = Path(__file__).resolve().parents[2]
def fingerprint(obj):
    h = hashlib.sha256(str([list(row) for row in obj.matrix_world]).encode())
    if obj.type == 'MESH':
        h.update(array.array('f', [c for v in obj.data.vertices for c in v.co]).tobytes())
        h.update(array.array('i', [l.vertex_index for l in obj.data.loops]).tobytes())
    h.update(str([m.name if m else None for m in getattr(obj.data, 'materials', [])]).encode())
    return h.hexdigest()
def lower_vertices(obj):
    return sorted(tuple(round(c, 5) for c in p) for v in obj.data.vertices if (p := obj.matrix_world @ v.co).z <= 22.83)
bpy.ops.wm.open_mainfile(filepath=str(ROOT / 'result/blender/LSE_campus_detailed_v72.blend'))
owned = {o.name for o in bpy.data.collections['CLM_EXTERIOR'].all_objects}
before = {o.name: fingerprint(o) for o in bpy.data.objects if o.name not in owned}
lower = {o.name: lower_vertices(o) for o in bpy.data.collections['CLM_EXTERIOR'].all_objects if o.type == 'MESH'}
bpy.ops.wm.open_mainfile(filepath=str(ROOT / 'result/blender/LSE_campus_detailed_v73.blend'))
assert all(fingerprint(bpy.data.objects[name]) == value for name, value in before.items())
assert all(lower_vertices(bpy.data.objects[name]) == value for name, value in lower.items())
path = ROOT / 'result/blender/stage73/clement-roof-audit.json'
a = json.loads(path.read_text())
for name in owned:
    obj = bpy.data.objects[name]
    if obj.type == 'MESH' and not obj.hide_render and any(k in name.lower() for k in ['window', 'recess', 'sash', 'glazing', 'bead', '_v16_', '_v17_']):
        assert all((obj.matrix_world @ v.co).z <= 22.831 for v in obj.data.vertices), name
for name in a['hiddenPreviousObjects']:
    assert bpy.data.objects[name].hide_render
for name, count in [('CLM_D5_roof73_dormer_glass', 40), ('CLM_D5_roof73_attic_glass', 56), ('CLM_D5_roof73_chimneys_stone', 32)]:
    assert len(bpy.data.objects[name].data.vertices) == count, name
caps = bpy.data.objects['CLM_D5_roof73_caps_metal']
assert len(caps.data.polygons) == 120
assert all(poly.normal.z > .95 and poly.area > .00001 for poly in caps.data.polygons)
for name in a['addedObjects']:
    obj = bpy.data.objects[name]
    assert not obj.hide_render
    assert all(math.isfinite(c) for v in obj.data.vertices for c in v.co)
    assert all(p.area > .00000001 for p in obj.data.polygons), name
roof = bpy.data.objects['CLM_D3_mansard_flat_top']
assert abs(max(v.co.z for v in roof.data.vertices) - 27.20) < .0001
assert roof.data.materials[0].name == 'CLM_V73_asphalt'
assert all(name in owned for name in a['changedExistingObjects'])
a['savedMeasurements'] = {'otherNativeObjectsProtected': len(before), 'lowerFacadeUnchanged': True, 'dormerCount': 5, 'chimneyCount': 4, 'upwardFacingCaps': 120, 'roofHeight': 27.20}
path.write_text(json.dumps(a, indent=2) + '\n')
print('SAVED_CLEMENT_ROOF_VERIFIED')
