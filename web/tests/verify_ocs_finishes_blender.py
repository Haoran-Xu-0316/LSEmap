"""Inspect saved OCS finishes independently of the builder."""
from pathlib import Path
import array,hashlib,json
import bpy
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'result/blender/stage81'
a=json.loads((OUT/'ocs-finish-audit.json').read_text())
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v81.blend'))
def geometry(o):
 h=hashlib.sha256(str([list(r) for r in o.matrix_world]).encode())
 if o.type=='MESH':
  h.update(array.array('f',[x for v in o.data.vertices for x in v.co]).tobytes())
  h.update(array.array('i',[l.vertex_index for l in o.data.loops]).tobytes())
 return h.hexdigest()
assert set(a['baselineGeometry'])==set(bpy.data.objects.keys())
assert all(a['baselineGeometry'][o.name]==geometry(o)for o in bpy.data.objects)
for name,slots in a['otherMaterialSlots'].items():
 assert slots==[m.name if m else None for m in getattr(bpy.data.objects[name].data,'materials',[])]
upper=0
for row in a['changedObjects']:
 o=bpy.data.objects[row['name']]
 for i,key in row['slots'].items():
  assert o.data.materials[int(i)].name=='OCS_V81_'+key
 for i in row['upperFaces']:
  p=o.data.polygons[i]
  assert o.data.materials[p.material_index].name=='OCS_V81_'+row['upperFinish']
  assert min((o.matrix_world@o.data.vertices[v].co).z for v in p.vertices)>3
  upper+=1
assert upper==a['upperReassignedFaces'] and upper>0
for key,color in a['palette'].items():
 m=bpy.data.materials['OCS_V81_'+key]
 assert all(abs(x-y)<1e-6 for x,y in zip(m.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value[:3],color))
a['savedMeasurements']={'geometryUnchanged':True,'otherBuildingsAndInteriorsUnchanged':True,'upperFaces':upper,'changedObjects':len(a['changedObjects'])}
(OUT/'ocs-finish-audit.json').write_text(json.dumps(a,indent=2)+'\n')
print('SAVED_OCS_FINISH_VERIFIED',len(a['changedObjects']),upper,flush=True)
