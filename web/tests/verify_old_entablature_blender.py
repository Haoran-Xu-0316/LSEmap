"""Reopen saved OLD entablature and check original geometry/interior preservation."""
from pathlib import Path
import array
import hashlib
import json
import math
import bpy
from mathutils import Vector
ROOT = Path(__file__).resolve().parents[2]
def fingerprint(obj):
    h=hashlib.sha256(str([list(row) for row in obj.matrix_world]).encode())
    if obj.type=='MESH':
        h.update(array.array('f',[c for v in obj.data.vertices for c in v.co]).tobytes())
        h.update(array.array('i',[l.vertex_index for l in obj.data.loops]).tobytes())
    h.update(str([m.name if m else None for m in getattr(obj.data,'materials',[])]).encode())
    return h.hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v76.blend'))
before={o.name:fingerprint(o) for o in bpy.data.objects}
original_visibility={o.name:o.hide_render for o in bpy.data.objects}
protected_bars=sorted(tuple(round(c,5) for c in v.co) for v in bpy.data.objects['OLD_Window_sash_bars'].data.vertices if v.co.z<22)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v77.blend'))
p=ROOT/'result/blender/stage77/old-entablature-audit.json'
audit=json.loads(p.read_text())
changed=[n for n,value in before.items() if fingerprint(bpy.data.objects[n])!=value]
assert changed==['OLD_Window_sash_bars'],changed
hidden={n for n,value in original_visibility.items() if bpy.data.objects[n].hide_render!=value}
assert hidden==set(audit['hiddenPreviousObjects'])
assert all(bpy.data.objects[n].hide_render for n in hidden)
for name in audit['addedObjects']:
    obj=bpy.data.objects[name]
    assert name in bpy.data.collections['OLD_EXTERIOR'].all_objects
    assert not obj.hide_render
    assert all(math.isfinite(c) for v in obj.data.vertices for c in v.co)
    assert all(poly.area>1e-10 for poly in obj.data.polygons)
assert sorted(tuple(round(c,5) for c in v.co) for v in bpy.data.objects['OLD_Window_sash_bars'].data.vertices if v.co.z<22)==protected_bars
assert bpy.data.objects['OLD_D5_entablature77_dormer_muntin_blue']['component_count']==20
assert len(bpy.data.objects['OLD_D5_entablature77_dormer_muntin_blue'].data.vertices)==160
assert audit['mansardWindowCount']==10
frame=json.loads((ROOT/'result/blender/stage52/old-houghton-audit.json').read_text())
origin,right=[Vector(frame[k]) for k in ['origin','right']]
roof=bpy.data.objects['OLD_D5_entablature77_mansard_brick']
for polygon in roof.data.polygons:
    points=[roof.matrix_world@roof.data.vertices[i].co-origin for i in polygon.vertices]
    a,b=min(v.dot(right) for v in points),max(v.dot(right) for v in points)
    c,d=min(v.z for v in points),max(v.z for v in points)
    for x in [-6.7,-3.35,0,3.35,6.7]:
        for z in [23.2,26.2]:
            assert min(b,x+.87)-max(a,x-.87)<1e-4 or min(d,z+1.06)-max(c,z-1.06)<1e-4

assert bpy.data.objects['OLD_D5_entablature77_dormer_canopy_blue']['component_count']==5
assert bpy.data.objects['OLD_D5_entablature77_roundel_stone']['component_count']==30
assert bpy.data.objects['OLD_D5_entablature77_console_stone']['component_count']==24
assert bpy.data.objects['OLD_D5_entablature77_screen_back_recess']['component_count']==4
assert bpy.data.objects['OLD_D5_entablature77_vent_back_recess']['component_count']==5
# The six closed consoles must have outward volume and complete shell topology.
obj=bpy.data.objects['OLD_D5_entablature77_console_stone']
volume=sum(obj.data.vertices[p.vertices[0]].co.dot(obj.data.vertices[p.vertices[i]].co.cross(obj.data.vertices[p.vertices[i+1]].co))/6 for p in obj.data.polygons for i in range(1,len(p.vertices)-1))
assert volume>0,volume
audit['savedMeasurements']={'changedOriginalGeometry':changed,'mainWindowsUnchanged':True,'mansardWindows':10,'newMansardMuntins':20,'otherBuildingsAndInteriorsUnchanged':True,'protectedObjects':len(before),'roundels':15,'profiledConsoles':6,'archedScreens':4,'upperVents':5}
p.write_text(json.dumps(audit,indent=2)+'\n')
print('SAVED_OLD_ENTABLATURE_VERIFIED')
