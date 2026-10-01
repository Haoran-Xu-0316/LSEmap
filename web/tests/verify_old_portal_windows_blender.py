"""Independently inspect saved portal geometry and protected native objects."""
from pathlib import Path
import array,hashlib,json,math
import bpy
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2]
def fingerprint(obj):
    h=hashlib.sha256(str([list(row) for row in obj.matrix_world]).encode())
    if obj.type=='MESH':
        h.update(array.array('f',[c for v in obj.data.vertices for c in v.co]).tobytes())
        h.update(array.array('i',[l.vertex_index for l in obj.data.loops]).tobytes())
    h.update(str([m.name if m else None for m in getattr(obj.data,'materials',[])]).encode())
    return h.hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v77.blend'))
before={o.name:fingerprint(o) for o in bpy.data.objects}
visibility={o.name:o.hide_render for o in bpy.data.objects}
path=ROOT/'result/blender/stage78/old-portal-windows-audit.json'
audit=json.loads(path.read_text())
origin,right,outward=[Vector(audit['frame'][k]) for k in ['origin','right','outward']]
def local(p):
    p=p-origin
    return (p.dot(right),p.dot(outward),p.z)
def protected(obj):
    return sorted(tuple(round(c,5) for c in obj.matrix_world@v.co) for v in obj.data.vertices
                  if not any(abs(x-center)<1.0 and -.12<d<.70 and 1.05<z<4.15
                             for center in [-6.7,6.7] for x,d,z in [local(obj.matrix_world@v.co)]))
protected_vertices={n:protected(bpy.data.objects[n]) for n in audit['changedExistingObjects']}
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v78.blend'))
changed=[n for n,h in before.items() if fingerprint(bpy.data.objects[n])!=h]
assert set(changed)==set(audit['changedExistingObjects']),changed
assert {n for n,v in visibility.items() if bpy.data.objects[n].hide_render!=v}==set(audit['hiddenPreviousObjects'])
assert all(bpy.data.objects[n].hide_render for n in audit['hiddenPreviousObjects'])
for n,points in protected_vertices.items():assert protected(bpy.data.objects[n])==points,n
for n in audit['addedObjects']:
    obj=bpy.data.objects[n]
    assert n in bpy.data.collections['OLD_EXTERIOR'].all_objects
    assert not obj.hide_render
    assert all(math.isfinite(c) for v in obj.data.vertices for c in v.co)
    assert all(p.area>1e-10 for p in obj.data.polygons)
pane=bpy.data.objects['OLD_D5_portal78_pane_glass']
assert pane['component_count']==2
# Independent mesh bounds confirm both apertures sit between the central doors
# and outer arch shoulder, instead of the outer wall's upper window axis.
coords=[local(pane.matrix_world@v.co) for v in pane.data.vertices]
for center in [-3.55,3.55]:
    points=[p for p in coords if abs(p[0]-center)<.5]
    assert len(points)==8
    assert abs(max(p[0] for p in points)-min(p[0] for p in points)-.73)<1e-4
    assert max(p[1] for p in points)<-.58
shoulder=bpy.data.objects['OLD_D5_portal78_shoulder_stone']
for polygon in shoulder.data.polygons:
    points=[local(shoulder.matrix_world@shoulder.data.vertices[i].co) for i in polygon.vertices]
    a,b=min(p[0] for p in points),max(p[0] for p in points)
    c,d=min(p[2] for p in points),max(p[2] for p in points)
    for x in [-3.55,3.55]:
        assert min(b,x+.41)-max(a,x-.41)<1e-4 or min(d,3.925)-max(c,1.275)<1e-4
assert bpy.data.objects['OLD_D5_portal78_muntin_blue']['component_count']==8
audit['savedMeasurements']={'windows':2,'columns':2,'rows':4,'oldWindowAxes':[-6.7,6.7],
                           'portalWindowAxes':[-3.55,3.55],'protectedVerticesUnchanged':True,
                           'otherBuildingsAndInteriorsUnchanged':True,'protectedObjects':len(before)}
path.write_text(json.dumps(audit,indent=2)+'\n')
print('SAVED_OLD_PORTAL_WINDOWS_VERIFIED')
