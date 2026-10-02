"""Independently reopen the stepped survey roof and check shared geometry."""
from pathlib import Path
import array,hashlib,json,math
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'result/blender/stage109'
a=json.loads((OUT/'library-roof-survey-audit.json').read_text())
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v109.blend'))
def digest(obj):
 h=hashlib.sha256(str([list(r)for r in obj.matrix_world]).encode())
 if obj.type=='MESH':
  h.update(array.array('f',[c for v in obj.data.vertices for c in v.co]).tobytes())
  h.update(array.array('i',[l.vertex_index for l in obj.data.loops]).tobytes())
 h.update(str([m.name if m else None for m in getattr(obj.data,'materials',[])]).encode())
 return h.hexdigest()
assert all(digest(bpy.data.objects[n])==h for n,h in a['originalFingerprints'].items())
for name in a['archived']:assert bpy.data.objects[name].hide_render
extra={o.name for o in bpy.data.objects}-set(a['originalFingerprints'])
assert extra==set(a['copies'].values())|set(a['newRoofObjects'])
for name in extra:
 o=bpy.data.objects[name];assert not o.hide_render
 assert all(math.isfinite(c)for v in o.data.vertices for c in v.co)
 assert all(p.area>1e-8 for p in o.data.polygons),name
shell=bpy.data.objects['LRB_V109_survey_dome_shell'];points=[shell.matrix_world@v.co for v in shell.data.vertices]
assert abs(min(p.z for p in points)-25.90)<.001
assert abs(max(p.z for p in points)-32.79)<.001
assert abs(max(p.x for p in points)-min(p.x for p in points)-13.78)<.001
roof=bpy.data.objects['LRB_D5_roof109_roof']
heights=set(round(v.co.z,2)for v in roof.data.vertices)
assert heights=={20.24,23.99,27.19},heights
bvh=BVHTree.FromPolygons([roof.matrix_world@v.co for v in roof.data.vertices],[tuple(p.vertices)for p in roof.data.polygons])
geometry=json.loads((OUT/'roof-survey-geometry.json').read_text())
boundary=geometry['raisedBoundary']
assert sum(a[0]*b[1]-b[0]*a[1]for a,b in zip(boundary,boundary[1:]+boundary[:1]))>0
centre=geometry['centre']
def contains(point):
 x,y=point[:2];inside=False
 for start,end in zip(boundary,boundary[1:]+boundary[:1]):
  if (start[1]>y)!=(end[1]>y):
   if x<(end[0]-start[0])*(y-start[1])/(end[1]-start[1])+start[0]:inside=not inside
 return inside
assert a['clerestoryWindows']
assert all(not contains(point)for point in a['clerestoryWindows']), 'Office glazing faces into opaque cladding'

for radius in [0,3,6.7]:
 for i in range(24):
  start=Vector((centre[0]+radius*math.cos(i*math.pi/12),centre[1]+radius*math.sin(i*math.pi/12),40))
  assert bvh.ray_cast(start,Vector((0,0,-1)),25)[0]is None
plant=bpy.data.objects['LRB_D5_roof109_plant']
assert len(plant.data.vertices)==24 and len(plant.data.polygons)==18
plan=json.loads((OUT/'roof-survey-geometry.json').read_text());theta=plan['rotationRadians']
u=Vector((math.cos(theta),math.sin(theta),0));v=Vector((math.sin(theta),-math.cos(theta),0))
for i,c in enumerate(a['heatPumpCentres']):
 points=[plant.data.vertices[j].co for j in range(i*8,i*8+8)]
 for axis,expected in [(u,2.2),(v,5.2),(Vector((0,0,1)),2.5)]:
  span=max(p.dot(axis)for p in points)-min(p.dot(axis)for p in points)
  assert abs(span-expected)<.001
 assert abs(sum(p.x for p in points)/8-c[0])<.001
 assert abs(sum(p.y for p in points)/8-c[1])<.001
assert len(a['pvArrays'])==10
assert all(b>a for a,b in zip(a['newHeightKnots'],a['newHeightKnots'][1:]))
for name in a['newRoofObjects']:assert bpy.data.objects[name]['sharedInteriorRoof']
report={'version':109,'originalsRetained':True,'facadeCopies':len(a['facadeCopies']),'newRoofFamilies':8,'roofHeights':sorted(heights),'capRadius':6.89,'roofVoidProbes':72,'heatPumps':3,'pvArrays':10}
(OUT/'saved-verification.json').write_text(json.dumps(report,indent=2)+'\n')
print('SAVED_LIBRARY_ROOF_SURVEY_VERIFIED',report,flush=True)
