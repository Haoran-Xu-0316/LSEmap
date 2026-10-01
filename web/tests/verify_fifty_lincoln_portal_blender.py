"""Check saved No.50 joinery and isolation from all other native objects."""
from pathlib import Path
import array, hashlib, json, math
import bpy
from mathutils import Vector
ROOT = Path(__file__).resolve().parents[2]
def fingerprint(obj):
    h = hashlib.sha256(str([list(row) for row in obj.matrix_world]).encode())
    if obj.type == 'MESH':
        h.update(array.array('f', [c for v in obj.data.vertices for c in v.co]).tobytes())
        h.update(array.array('i', [l.vertex_index for l in obj.data.loops]).tobytes())
    h.update(str([m.name if m else None for m in getattr(obj.data, 'materials', [])]).encode())
    return h.hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(ROOT / 'result/blender/LSE_campus_detailed_v71.blend'))
before = {o.name: fingerprint(o) for o in bpy.data.objects}
bpy.ops.wm.open_mainfile(filepath=str(ROOT / 'result/blender/LSE_campus_detailed_v72.blend'))
changed = [name for name, value in before.items() if fingerprint(bpy.data.objects[name]) != value]
assert not changed, changed
path = ROOT / 'result/blender/stage72/fifty-lincoln-portal-audit.json'
a = json.loads(path.read_text())
for name in a['hiddenPreviousObjects']:
    assert name.startswith('50L_') and bpy.data.objects[name].hide_render
for name in ['50L_V19_REM_portal_roundel_rim_stone', '50L_V19_REM_portal_roundel_recess_shadow', '50L_V20_EXT_fanlight_radial_bar_bronze']:
    assert bpy.data.objects[name].hide_render
origin, right, outward = [Vector(a['frame'][k]) for k in ['origin', 'right', 'outward']]
panel = bpy.data.objects['50L_D5_portal72_panel']
assert len(panel.data.vertices) == 48
centers = []
for start in range(0, 48, 8):
    p = sum((panel.matrix_world @ v.co for v in panel.data.vertices[start:start + 8]), Vector()) / 8
    centers.append([round((p - origin).dot(right), 3), round(p.z, 3)])
assert len(set(tuple(p) for p in centers)) == 6
assert len(set(z for x, z in centers)) == 3
step = bpy.data.objects['50L_D5_portal72_step']
assert abs(max((step.matrix_world @ v.co).z for v in step.data.vertices) - .26) < .0001
for name in a['addedObjects']:
    obj = bpy.data.objects[name]
    assert not obj.hide_render
    if obj.type == 'MESH':
        assert all(math.isfinite(c) for v in obj.data.vertices for c in v.co)
        assert all(p.area > .00000001 for p in obj.data.polygons), name
assert bpy.data.objects['OLD_D5_relief71_stone'].hide_render == False
a['savedMeasurements'] = {'protectedOriginalObjects': len(before), 'changedOriginalObjects': changed, 'panelCenters': centers, 'topStepHeight': .26, 'obsoleteRoundelsAndRadialBarsHidden': True}
path.write_text(json.dumps(a, indent=2) + '\n')
print('SAVED_FIFTY_LINCOLN_PORTAL_VERIFIED')
