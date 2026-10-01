"""Reopen saved 5LF refinement and independently inspect retained geometry."""
from pathlib import Path
import array, hashlib, json
import bpy, bmesh
from mathutils import Vector
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'result/blender/stage91'
audit = json.loads((OUT/'five-rainwater-audit.json').read_text())
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v91.blend'))
def fingerprint(obj):
    h = hashlib.sha256(str([list(r) for r in obj.matrix_world]).encode())
    if obj.type == 'MESH':
        h.update(array.array('f', [c for v in obj.data.vertices for c in v.co]).tobytes())
        h.update(array.array('i', [loop.vertex_index for loop in obj.data.loops]).tobytes())
    h.update(str([m.name if m else None for m in getattr(obj.data, 'materials', [])]).encode())
    return h.hexdigest()
assert all(fingerprint(bpy.data.objects[n]) == value for n, value in audit['baselineFingerprint'].items())
assert set(bpy.data.objects.keys())-set(audit['baselineFingerprint']) == set(audit['addedObjects'])
source, stack = [bpy.data.objects[audit[k]] for k in ['sourceStack', 'ownedStack']]
assert source.hide_render and not stack.hide_render
assert [list(v.co) for v in source.data.vertices] == [list(v.co) for v in stack.data.vertices]
assert [list(p.vertices) for p in source.data.polygons] == [list(p.vertices) for p in stack.data.polygons]
assert source.data.materials[0].name == '5LF_brick'
assert stack.data.materials[0].name == '5LF_V91_weathered_chimney_brick'
measured = []
for record in audit['pipes']:
    obj = bpy.data.objects[record['name']]
    points = [obj.matrix_world@v.co for v in obj.data.vertices]
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    assert all(e.is_manifold for e in bm.edges)
    assert bm.calc_volume(signed=True) > 0
    bm.free()
    centers = []
    for row in range(4):
        center = sum(points[row*12:(row+1)*12], Vector())/12
        centers.append(center)
        assert (center-Vector(record['centerline'][row])).length < 2e-5
        assert all(abs((p-center).length-.035) < 2e-5 for p in points[row*12:(row+1)*12])
    assert abs(centers[-1].z-centers[0].z-13.37) < 2e-5
    measured.append({'name': obj.name, 'heightSpan': centers[-1].z-centers[0].z, 'closed': True})
audit['savedMeasurements'] = {'originalObjectsUnchanged': True, 'stackGeometryPreserved': True, 'pipes': measured}
(OUT/'five-rainwater-audit.json').write_text(json.dumps(audit, indent=2)+'\n')
print('SAVED_FIVE_RAINWATER_VERIFIED', measured, flush=True)
