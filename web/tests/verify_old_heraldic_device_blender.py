"""Independently inspect the saved OLD heraldry and protected originals."""
from pathlib import Path
import array
import hashlib
import json
import math
import bpy
ROOT=Path(__file__).resolve().parents[2]
def fingerprint(obj):
    h=hashlib.sha256(str([list(row) for row in obj.matrix_world]).encode())
    if obj.type=='MESH':
        h.update(array.array('f',[c for v in obj.data.vertices for c in v.co]).tobytes())
        h.update(array.array('i',[l.vertex_index for l in obj.data.loops]).tobytes())
    h.update(str([m.name if m else None for m in getattr(obj.data,'materials',[])]).encode())
    return h.hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v73.blend'))
before={o.name:fingerprint(o) for o in bpy.data.objects}
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v74.blend'))
assert all(fingerprint(bpy.data.objects[n])==v for n,v in before.items())
a=json.loads((ROOT/'result/blender/stage74/old-heraldic-device-audit.json').read_text())
frame=json.loads((ROOT/'result/blender/stage52/old-houghton-audit.json').read_text())
from mathutils import Vector
origin,right,outward=[Vector(frame[k]) for k in ['origin','right','outward']]
for name in a['addedObjects']:
    obj=bpy.data.objects[name]
    assert obj.name in bpy.data.collections['OLD_EXTERIOR'].all_objects
    assert not obj.hide_render
    assert all(math.isfinite(c) for v in obj.data.vertices for c in v.co)
    assert all(p.area>1e-9 for p in obj.data.polygons)
    for v in obj.data.vertices:
        pos=obj.matrix_world@v.co;delta=pos-origin
        assert abs(delta.dot(right))<.80 and .77<delta.dot(outward)<.93 and 9.17<pos.z<10.9
assert len(a['addedObjects'])==3
assert len(bpy.data.objects['OLD_D5_arms74_stone'].data.vertices)>1000
assert a['bookCount']==2 and a['beaverCount']==1
assert bpy.data.objects['OLD_V69_scroll_motto'].data.body=='RERUM COGNOSCERE CAUSAS'
a['savedMeasurements']={'originalObjectsProtected':len(before),'withinReservedShield':True,'bookCount':2,'beaverCount':1,'mottoRetained':True}
(ROOT/'result/blender/stage74/old-heraldic-device-audit.json').write_text(json.dumps(a,indent=2)+'\n')
print('SAVED_OLD_HERALDIC_DEVICE_VERIFIED')
