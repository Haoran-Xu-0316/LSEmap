"""Reopen both native files and verify the OLD-only relief replacement."""
from pathlib import Path
import array, hashlib, json, math
import bpy
ROOT=Path(__file__).resolve().parents[2]
def fingerprint(obj):
 h=hashlib.sha256(str([list(row) for row in obj.matrix_world]).encode())
 if obj.type=='MESH':
  h.update(array.array('f',[c for v in obj.data.vertices for c in v.co]).tobytes())
  h.update(array.array('i',[l.vertex_index for l in obj.data.loops]).tobytes())
 h.update(str([m.name if m else None for m in getattr(obj.data,'materials',[])]).encode())
 return h.hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v70.blend'))
before={o.name:fingerprint(o) for o in bpy.data.objects}
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v71.blend'))
changed=[name for name,value in before.items() if fingerprint(bpy.data.objects[name])!=value]
assert not changed,changed
path=ROOT/'result/blender/stage71/old-relief-drapery-audit.json'
a=json.loads(path.read_text())
for name in a['hiddenPreviousObjects']:assert bpy.data.objects[name].hide_render
counts={}
for name in a['addedObjects']:
 obj=bpy.data.objects[name];assert not obj.hide_render
 assert all(math.isfinite(c) for v in obj.data.vertices for c in v.co)
 assert all(p.area>.00000001 for p in obj.data.polygons),name
 counts[name]=len(obj.data.vertices)
assert len(counts)==4
assert counts['OLD_D5_relief71_stone']>13000
for name in ['OLD_D5_arch69_stone','OLD_D5_entry65_glass','OLD_D5_entry65_steel','OLD_V53_Clare_blue']:
 assert not bpy.data.objects[name].hide_render
assert a['figureCount']==5 and a['basketCount']==2
a['savedMeasurements']={'protectedOriginalObjects':len(before),'changedOriginalObjects':changed,'newVertexCounts':counts,'archDoorsAndClareRetained':True}
path.write_text(json.dumps(a,indent=2)+'\n')
print('SAVED_OLD_RELIEF_VERIFIED',counts)
