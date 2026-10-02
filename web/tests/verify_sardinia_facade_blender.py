"""Reopen SAR refinement and verify retained openings and mounted stonework."""
from pathlib import Path
import array,hashlib,json
from collections import Counter
import bpy,bmesh
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'result/blender/stage102'
audit=json.loads((OUT/'sardinia-facade-audit.json').read_text())
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v102.blend'))
def fingerprint(obj):
    h=hashlib.sha256(str([list(row) for row in obj.matrix_world]).encode())
    if obj.type=='MESH':
        h.update(array.array('f',[c for v in obj.data.vertices for c in v.co]).tobytes())
        h.update(array.array('i',[l.vertex_index for l in obj.data.loops]).tobytes())
    if obj.type=='FONT':h.update(str((obj.data.body,obj.data.size,obj.data.font.name,obj.data.extrude)).encode())
    h.update(str([m.name if m else None for m in getattr(obj.data,'materials',[])]).encode())
    return h.hexdigest()

for name,digest in audit['originalFingerprints'].items():assert fingerprint(bpy.data.objects[name])==digest,name
expected=set(audit['addedObjects'])|{r['copy'] for r in audit['copies']}|{r['copy'] for r in audit['partialCopies']}
assert set(o.name for o in bpy.data.objects)-set(audit['originalFingerprints'])==expected
for r in audit['copies']:
 old,new=[bpy.data.objects[r[k]] for k in ['source','copy']]
 assert old.hide_render and not new.hide_render
 assert old.matrix_world==new.matrix_world
 assert [list(v.co) for v in old.data.vertices]==[list(v.co) for v in new.data.vertices]
 assert [l.vertex_index for l in old.data.loops]==[l.vertex_index for l in new.data.loops]
for r in audit['partialCopies']:
 old,new=[bpy.data.objects[r[k]] for k in ['source','copy']]
 assert old.hide_render and not new.hide_render and old.matrix_world==new.matrix_world
 key=lambda p:tuple(round(c,5) for c in p)
 assert Counter(key(v.co) for v in new.data.vertices)==Counter(key(v) for v in r['retainedVertices'])
 assert not (Counter(key(v.co) for v in new.data.vertices)-Counter(key(v.co) for v in old.data.vertices))
assert [r['removedComponents'] for r in audit['partialCopies']]==[8,8,16]
assert len(audit['windows'])==24 and {r['floor'] for r in audit['windows']}=={2,3,4}
origin,u,n=[Vector(audit[k]) for k in ['origin','axis','normal']]
for name in audit['addedObjects']:
 o=bpy.data.objects[name];assert not o.hide_render
 if o.type=='MESH':
  bm=bmesh.new();bm.from_mesh(o.data)
  assert all(e.is_manifold for e in bm.edges),name
  assert bm.calc_volume()>0,name;bm.free()
  points=[o.matrix_world@v.co for v in o.data.vertices]
  assert min((p-origin).dot(n) for p in points)>-.06,name
  assert max(p.z for p in points)<19,name
# Count the saved first-floor bars independently: three verticals and two rails
# across eight retained openings, instead of the former two-column/four-row grid.
o=bpy.data.objects['SAR_V102_first_floor_sashes_sash'];bm=bmesh.new();bm.from_mesh(o.data);seen=set();vertical=horizontal=0
for v in bm.verts:
 if v in seen:continue
 todo=[v];seen.add(v);points=[]
 while todo:
  q=todo.pop();points.append(o.matrix_world@q.co)
  for e in q.link_edges:
   other=e.other_vert(q)
   if other not in seen:seen.add(other);todo.append(other)
 span=max(p.z for p in points)-min(p.z for p in points)
 if span>2:vertical+=1
 else:horizontal+=1
assert (vertical,horizontal)==(24,16)
bm.free()
text=bpy.data.objects['SAR_V102_school_name'];bpy.context.view_layer.update()
assert text.data.body=='The London School of Economics and Political Science'
points=[text.matrix_world@Vector(v) for v in text.bound_box]
assert min(p.z for p in points)>audit['course']-.61
assert max(p.z for p in points)<audit['course']-.13
assert min((p-origin).dot(n) for p in points)>.25
assert all(0<(p-origin).dot(u)<audit['frontLength'] for p in points)
assert (text.matrix_world.to_3x3()@Vector((0,0,1))).dot(n)>.99
audit['savedMeasurements']={'originalObjectsUnchanged':True,'brickCopiesRetainGeometry':True,'twentyFourSurrounds':True,'closedStoneMeshes':True,'fasciaTextMountedAndContained':True,'eightFirstFloorSashesCorrected':True}
(OUT/'sardinia-facade-audit.json').write_text(json.dumps(audit,indent=2)+'\n')
print('SAVED_SARDINIA_FACADE_VERIFIED',len(audit['windows']),len(expected))
