"""Reopen saved Cowdray model; verify sash replacement and protected geometry."""
from pathlib import Path
import array
import hashlib
import json
import math
import bpy
ROOT = Path(__file__).resolve().parents[2]
def fingerprint(obj):
    h = hashlib.sha256(str([list(row) for row in obj.matrix_world]).encode())
    if obj.type == 'MESH':
        h.update(array.array('f', [c for v in obj.data.vertices for c in v.co]).tobytes())
        h.update(array.array('i', [l.vertex_index for l in obj.data.loops]).tobytes())
    h.update(str([m.name if m else None for m in getattr(obj.data, 'materials', [])]).encode())
    return h.hexdigest()
def retained_rails(obj):
    return sorted(tuple(round(c,5) for c in v.co) for v in obj.data.vertices if v.co.z < 5 or v.co.z > 18)
bpy.ops.wm.open_mainfile(filepath=str(ROOT / 'result/blender/LSE_campus_detailed_v75.blend'))
owned = {o.name for o in bpy.data.collections['COW_EXTERIOR'].all_objects}
before = {o.name: fingerprint(o) for o in bpy.data.objects if o.name not in owned}
protected_rails = retained_rails(bpy.data.objects['COW_D5_sash_glazing_bar_frame'])
cow_before = {o.name: fingerprint(o) for o in bpy.data.collections['COW_EXTERIOR'].all_objects}
roof_before = [tuple(v.co) for v in bpy.data.objects['COW_D5_roof'].data.vertices]
bpy.ops.wm.open_mainfile(filepath=str(ROOT / 'result/blender/LSE_campus_detailed_v76.blend'))
assert all(fingerprint(bpy.data.objects[n]) == value for n, value in before.items())
assert retained_rails(bpy.data.objects['COW_D5_sash_glazing_bar_frame']) == protected_rails
p = ROOT / 'result/blender/stage76/cowdray-joinery-audit.json'
audit = json.loads(p.read_text())
assert audit['windowCount'] == 72
assert audit['removedHorizontalRails'] == 144
rail = bpy.data.objects['COW_D5_joinery76_six_row_rail_frame']
assert len(rail.data.vertices) == 288*8
for name in audit['addedObjects']:
    obj = bpy.data.objects[name]
    assert not obj.hide_render
    assert all(math.isfinite(c) for v in obj.data.vertices for c in v.co)
    assert all(poly.area > 1e-9 for poly in obj.data.polygons)
for name in audit['hiddenPreviousObjects']:
    assert bpy.data.objects[name].hide_render
assert bpy.data.objects['COW_D5_roof'].data.materials[0].name == 'COW_V76_slate'
# Roof shape must stay identical even though its owned material slot changes.
assert [tuple(v.co) for v in bpy.data.objects['COW_D5_roof'].data.vertices] == roof_before
changed = {n for n, value in cow_before.items() if fingerprint(bpy.data.objects[n]) != value}
assert changed == {'COW_D5_sash_glazing_bar_frame', 'COW_D5_roof', 'COW_D5_dormer_back_slate'}, changed
assert all(n in owned for n in audit['changedExistingObjects'])
audit['savedMeasurements'] = {'otherBuildingsAndInteriorsUnchanged': True, 'protectedObjects': len(before), 'groundAndDormerRailsUnchanged': True, 'sixRowWindows': 72, 'newHorizontalRails': 288}
p.write_text(json.dumps(audit,indent=2)+'\n')
print('SAVED_COWDRAY_JOINERY_VERIFIED')
