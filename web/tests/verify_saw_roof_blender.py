"""Inspect saved SAW panes against the inherited folded masonry boundaries."""
from pathlib import Path
import array,hashlib,json,math
import bpy,bmesh
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'result/blender/stage83'
a=json.loads((OUT/'saw-roof-audit.json').read_text())
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v83.blend'))
def fingerprint(o):
 h=hashlib.sha256(str([list(r)for r in o.matrix_world]).encode())
 if o.type=='MESH':
  h.update(array.array('f',[c for v in o.data.vertices for c in v.co]).tobytes())
  h.update(array.array('i',[l.vertex_index for l in o.data.loops]).tobytes())
 h.update(str([m.name if m else None for m in getattr(o.data,'materials',[])]).encode())
 return h.hexdigest()
assert all(fingerprint(bpy.data.objects[n])==v for n,v in a['baselineFingerprint'].items())
for n in a['hiddenObjects']:assert bpy.data.objects[n].hide_render
assert set(bpy.data.objects.keys())-set(a['baselineFingerprint'])==set(a['addedObjects'])
for n in a['addedObjects']:
 o=bpy.data.objects[n]
 assert not o.hide_render and all(math.isfinite(x)for v in o.data.vertices for x in v.co)
 assert all(p.area>1e-8 for p in o.data.polygons)
def obj(family):return bpy.data.objects['SAW_D5_roof83_'+family]
pv=obj('pv_modules')
assert len(pv.data.polygons)==159
area=sum(p.area for p in pv.data.polygons)
assert abs(area-254.4)<.02,area
for name,z in [('upper_terrace',21.9),('green_roof',18.0)]:
 assert all(abs((obj(name).matrix_world@v.co).z-z)<.001 for v in obj(name).data.vertices)
deck=obj('upper_terrace')
assert abs(sum(p.area for p in deck.data.polygons)-115)<.02
roof=obj('metal_fields');assert len(roof.data.polygons)==13
for face,expected in zip(roof.data.polygons,a['plan']['roofTriangles']):
 actual=[roof.matrix_world@roof.data.vertices[i].co for i in face.vertices]
 assert all(min((p-Vector(q)).length for q in expected)<.001 for p in actual)
 assert face.normal.z>0
chimneys=obj('chimneys')
assert len(chimneys.data.polygons)==12
assert abs(max(v.co.z for v in chimneys.data.vertices)-28.9)<.001
for family in ['chimneys','pv_frames','upper_mullions','lower_mullions']:
 bm=bmesh.new();bm.from_mesh(obj(family).data)
 assert bm.calc_volume(signed=True)>0
 bm.free()
a['savedMeasurements']={'originalGeometryAndMaterialsUnchanged':True,'newMeshObjects':len(a['addedObjects']),'pvModules':159,'pvArea':round(area,3),'upperTerraceArea':round(sum(p.area for p in deck.data.polygons),3),'upperLevel':21.9,'greenLevel':18.0,'chimneys':2,'retainedRoofTriangles':13}
(OUT/'saw-roof-audit.json').write_text(json.dumps(a,indent=2)+'\n')
print('SAVED_SAW_ROOF_VERIFIED',a['savedMeasurements'],flush=True)
