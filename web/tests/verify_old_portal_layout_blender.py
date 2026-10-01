"""Verify four portal-side windows and restored outer geometry from saved files."""
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
path=ROOT/'result/blender/stage79/old-portal-layout-audit.json'
audit=json.loads(path.read_text())
origin,right,outward=[Vector(audit['frame'][k]) for k in ['origin','right','outward']]
def local(p):
    p=p-origin
    return p.dot(right),p.dot(outward),p.z
def outer_vertices(obj):
    return sorted(tuple(round(c,5) for c in obj.matrix_world@v.co) for v in obj.data.vertices
                  if any(abs(x-center)<1.0 and -.12<d<.70 and 1.05<z<4.15
                         for center in [-6.7,6.7] for x,d,z in [local(obj.matrix_world@v.co)]))
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v77.blend'))
expected={n:outer_vertices(bpy.data.objects[n]) for n in audit['sourceComponents']}
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v78.blend'))
before={o.name:fingerprint(o) for o in bpy.data.objects}
visibility={o.name:o.hide_render for o in bpy.data.objects}
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v79.blend'))
assert all(fingerprint(bpy.data.objects[n])==h for n,h in before.items())
assert {n for n,v in visibility.items() if bpy.data.objects[n].hide_render!=v}==set(audit['hiddenPreviousObjects'])
for name in audit['addedObjects']:
    obj=bpy.data.objects[name]
    assert name in bpy.data.collections['OLD_EXTERIOR'].all_objects
    assert not obj.hide_render
    assert all(math.isfinite(c) for v in obj.data.vertices for c in v.co)
    assert all(p.area>1e-10 for p in obj.data.polygons)
for source,points in expected.items():
    name='OLD_D5_portal79_'+source.removeprefix('OLD_')
    restored=bpy.data.objects[name]
    actual=sorted(tuple(round(c,5) for c in restored.matrix_world@v.co) for v in restored.data.vertices)
    assert actual==points,source
    assert restored['component_count']==audit['sourceComponents'][source]
inner=bpy.data.objects['OLD_D5_portal78_pane_glass']
outer=bpy.data.objects['OLD_D5_portal79_Window_glazing']
assert inner['component_count']==outer['component_count']==2
assert not inner.hide_render and not outer.hide_render
assert bpy.data.objects['OLD_D5_portal78_outer_infill_stone'].hide_render
assert bpy.data.objects['OLD_Houghton_flanking_wings'].hide_render
assert len(audit['wingWindowHoles'])==48
stone_count=0
for name in audit['addedObjects']:
    if '_wings79_' not in name:continue
    obj=bpy.data.objects[name];stone_count+=obj['component_count']
    for polygon in obj.data.polygons:
        points=[local(obj.matrix_world@obj.data.vertices[i].co) for i in polygon.vertices]
        a,b=min(p[0] for p in points),max(p[0] for p in points)
        c,d=min(p[2] for p in points),max(p[2] for p in points)
        for aa,bb,cc,dd in audit['wingWindowHoles']:
            assert min(b,bb)-max(a,aa)<1e-4 or min(d,dd)-max(c,cc)<1e-4
assert stone_count==audit['wingStoneBlocks']
audit['savedMeasurements']={'totalGroundWindows':4,'innerWindows':2,'outerWindows':2,
                           'wingWindowHoles':48,'wingStoneBlocks':stone_count,
                           'outerWindowGeometryRestoredExactly':True,'allOriginalGeometryUnchanged':True,
                           'otherBuildingsAndInteriorsUnchanged':True,'protectedObjects':len(before)}
path.write_text(json.dumps(audit,indent=2)+'\n')
print('SAVED_OLD_PORTAL_LAYOUT_VERIFIED')
