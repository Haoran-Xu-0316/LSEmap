"""Check the actual SAW floor/stair selection without changing the native file."""
from pathlib import Path
import hashlib,json,sys
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'web/tools'))
from public_interior_objects import public_interior_objects
BASE=ROOT/'result/blender/LSE_campus_detailed_v216.blend'
EXPECTED=json.loads((ROOT/'result/blender/stage216/building-refinement.json').read_text())['sourceModelSha256']
OUT=ROOT/'result/blender/saw-structure216';OUT.mkdir(parents=True,exist_ok=True)
assert hashlib.sha256(BASE.read_bytes()).hexdigest()==EXPECTED
bpy.ops.wm.open_mainfile(filepath=str(BASE));bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE']
for scene in bpy.data.scenes:
 for layer in scene.view_layers:layer.update()
metadata=json.loads((ROOT/'web/tools/building-metadata.json').read_text());record=next(b for b in metadata['buildings'] if b['code']=='SAW')
selected=[o for o in public_interior_objects(record) if o.type=='MESH' and not o.hide_render]
floors=[o for o in selected if o.name.startswith('SAWFLOOR216_registered_floor_') or o.name=='SAW_SAW_floor_0']
assert len(floors)==7,[o.name for o in floors]
rows=[];trees=[]
for obj in floors:
 vertices=[obj.matrix_world@v.co for v in obj.data.vertices];z=sum(v.z for v in vertices)/len(vertices)
 assert max(v.z for v in vertices)-min(v.z for v in vertices)<1e-4
 tree=BVHTree.FromPolygons(vertices,[tuple(f.vertices) for f in obj.data.polygons]);trees.append((z,tree))
 rows.append(dict(name=obj.name,datum=z,vertices=len(vertices),faces=len(obj.data.polygons)))
assert all(abs(a-b)<1e-4 for a,b in zip(sorted(r['datum'] for r in rows),[0,3.45,8.1,11.1,14.1,18,21.9]))
stair=bpy.data.objects['SAW173_registered_main_treads'];stair_points=[stair.matrix_world@v.co for v in stair.data.vertices];probes=[]
for face in stair.data.polygons:
 points=[stair_points[i] for i in face.vertices]
 if max(p.z for p in points)-min(p.z for p in points)>1e-5 or face.normal.z<.9:continue
 centre=sum(points,Vector())/len(points);hits=[];threshold_contacts=[]
 for level,tree in trees:
  if level<=centre.z+.001 or level>centre.z+2.25:continue
  hit=tree.ray_cast(centre+Vector((0,0,.001)),Vector((0,0,1)),2.25)
  if hit[0] is not None:
   clearance=hit[3]+.001
   contact=dict(level=level,clearanceMetres=clearance)
   # The 1mm ray-origin offset must not convert a valid 2.25m
   # threshold contact into an apparent obstruction. Float32 tolerance 0.01mm.
   (hits if clearance<2.25-.00001 else threshold_contacts).append(contact)
 probes.append(dict(centre=list(centre),floorHeadroomHits=hits,thresholdContacts=threshold_contacts))
assert len(probes)>=146,len(probes)
(OUT/'tread-probes.json').write_text(json.dumps(probes,indent=2)+'\n')
assert not any(p['floorHeadroomHits'] for p in probes),'A retained floor obstructs the current stair study'
old=[o for o in selected if '_floor_' not in o.name or 'landing' in o.name]
def bounds(objects):
 points=[o.matrix_world@Vector(p) for o in objects for p in o.bound_box]
 return dict(min=[min(p[i] for p in points) for i in range(3)],max=[max(p[i] for p in points) for i in range(3)])
assert hashlib.sha256(BASE.read_bytes()).hexdigest()==EXPECTED
result=dict(sourceModelSha256=EXPECTED,selectedObjects=len(selected),previousStairOnlyObjects=len(old),floors=rows,beforeNativeBounds=bounds(old),afterNativeBounds=bounds(selected),treadHeadroomProbes=len(probes),floorHeadroomHits=0,sectionCount=len(record['interiorSections']),nativeFileUnchanged=True,scope='Publish source-guided historical upper-floor profiles and coordinated landings together with the retained ground slab and main stair. Absolute world scale, heights and stair topology remain estimates; not a complete current room layout.')
(OUT/'verification.json').write_text(json.dumps(result,indent=2)+'\n');(OUT/'tread-probes.json').write_text(json.dumps(probes,indent=2)+'\n');print('SAW216_NATIVE',result,flush=True)
