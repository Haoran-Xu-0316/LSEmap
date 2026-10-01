"""Reopen the saved CKK pavilion and verify geometry, transparency and scope."""
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
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v79.blend'))
before={o.name:fingerprint(o) for o in bpy.data.objects}
visible={o.name:o.hide_render for o in bpy.data.objects}
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v80.blend'))
path=ROOT/'result/blender/stage80/ckk-roof-pavilion-audit.json'
audit=json.loads(path.read_text())
assert all(fingerprint(bpy.data.objects[n])==h for n,h in before.items())
assert {n for n,v in visible.items() if bpy.data.objects[n].hide_render!=v}==set(audit['hiddenPreviousObjects'])
assert bpy.data.objects['CKK_setback_roof_wing'].hide_render
for name in audit['addedObjects']:
    obj=bpy.data.objects[name]
    assert name in bpy.data.collections['CKK_EXTERIOR'].all_objects
    assert not obj.hide_render
    assert all(math.isfinite(c) for v in obj.data.vertices for c in v.co)
    assert all(p.area>1e-10 for p in obj.data.polygons)
for family,count in [('glazing_glass',18),('louvre_steel',14),('loggia_post_steel',5),('brace_steel',4)]:
    obj=bpy.data.objects['CKK_D5_pavilion80_'+family]
    assert obj['component_count']==count
    assert len(obj.data.vertices)==count*8
    volume=sum(obj.data.vertices[p.vertices[0]].co.dot(obj.data.vertices[p.vertices[i]].co.cross(obj.data.vertices[p.vertices[i+1]].co))/6 for p in obj.data.polygons for i in range(1,len(p.vertices)-1))
    assert volume>0,(family,volume)
mat=bpy.data.materials['CKK_V80_glass']
assert abs(mat.node_tree.nodes['Principled BSDF'].inputs['Alpha'].default_value-.55)<1e-5
audit['savedMeasurements']={'glazingPanels':18,'sunshadeLouvres':14,'loggiaPosts':5,'diagonalBraces':4,
    'newObjects':len(audit['addedObjects']),'originalGeometryUnchanged':True,
    'otherBuildingsAndInteriorsUnchanged':True,'protectedObjects':len(before),'glassAlpha':.55}
path.write_text(json.dumps(audit,indent=2)+'\n')
print('SAVED_CKK_ROOF_PAVILION_VERIFIED')
