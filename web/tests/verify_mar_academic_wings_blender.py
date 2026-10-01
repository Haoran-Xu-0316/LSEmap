"""Reopen MAR candidate and verify aperture replacement and protected interiors."""
from pathlib import Path
import array,hashlib,json,math
import bpy
ROOT=Path(__file__).resolve().parents[2]
def digest(o):
 h=hashlib.sha256(str([list(row) for row in o.matrix_world]).encode())
 if o.type=='MESH':
  h.update(array.array('f',[c for v in o.data.vertices for c in v.co]).tobytes());h.update(array.array('i',[l.vertex_index for l in o.data.loops]).tobytes())
 h.update(str([m.name if m else None for m in getattr(o.data,'materials',[])]).encode());return h.hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v74.blend'))
owned={o.name for o in bpy.data.collections['MAR_EXTERIOR'].all_objects}
before={o.name:digest(o) for o in bpy.data.objects if o.name not in owned}
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v75.blend'))
assert all(digest(bpy.data.objects[n])==v for n,v in before.items())
p=ROOT/'result/blender/stage75/mar-academic-wings-audit.json';a=json.loads(p.read_text())
assert a['surfaceCount']==5 and a['windowCount']==245
assert a['removedWindowComponents']['MAR_recessed_window_glass']==245
assert len(bpy.data.objects['MAR_D5_wings75_glass'].data.vertices)==245*8
for name in a['hiddenPreviousObjects']:assert bpy.data.objects[name].hide_render
for name in a['addedObjects']:
 o=bpy.data.objects[name];assert not o.hide_render
 assert all(math.isfinite(c) for v in o.data.vertices for c in v.co)
 assert all(poly.area>1e-9 for poly in o.data.polygons)
assert all(n in owned for n in a['changedExistingObjects'])
for name in a['recoloredObjects']:assert any(m.name=='MAR_V75_concrete' for m in bpy.data.objects[name].data.materials)
a['savedMeasurements']={'protectedObjects':len(before),'otherBuildingsAndInteriorsUnchanged':True,'newApertures':245,'removedGlassPanels':245,'replacedFacades':5}
p.write_text(json.dumps(a,indent=2)+'\n');print('SAVED_MAR_ACADEMIC_WINGS_VERIFIED')
