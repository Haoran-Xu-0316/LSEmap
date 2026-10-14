"""Reopen the full campus and probe real landmark/court geometry and materials."""
from pathlib import Path
import hashlib
import json
import sys
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'web/tools'))
from refine_portsmouth_exterior207 import material_fingerprint
STAGE=ROOT/'result/blender/stage212'
BASE=ROOT/'result/blender/LSE_campus_detailed_v211.blend'
CURRENT=ROOT/'result/blender/LSE_campus_detailed_v212.blend'
bpy.ops.wm.open_mainfile(filepath=str(BASE))
materials={m.name:material_fingerprint(m) for m in bpy.data.materials}
bpy.ops.wm.open_mainfile(filepath=str(CURRENT))
bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE']
for name,value in materials.items():assert material_fingerprint(bpy.data.materials[name])==value,name

def tree(objects):
 vertices,faces=[],[]
 for obj in objects:
  offset=len(vertices);vertices.extend(obj.matrix_world@v.co for v in obj.data.vertices);faces.extend(tuple(offset+i for i in f.vertices) for f in obj.data.polygons)
 return BVHTree.FromPolygons(vertices,faces)

courts=json.loads((ROOT/'result/blender/park-courts212/audit.json').read_text())
for name in courts['archivedObjects']:assert bpy.data.objects[name].hide_render
court_objects=[bpy.data.objects[n] for n in courts['addedObjects'] if 'net_' not in n]
court_tree=tree(court_objects)
footprint=bpy.data.objects['COURTS212_whole_tarmac_surface'];points=[footprint.matrix_world@v.co for v in footprint.data.vertices]
x0,x1=min(p.x for p in points),max(p.x for p in points);y0,y1=min(p.y for p in points),max(p.y for p in points)
plan_courts=json.loads((ROOT/'result/blender/park-courts212/court-plan.json').read_text())
expected_vertices=[Vector((p[0],p[1],.1)) for tri in plan_courts['surfaceTriangles'] for p in tri]
expected_tree=BVHTree.FromPolygons(expected_vertices,[(i,i+1,i+2) for i in range(0,len(expected_vertices),3)])
rays=[];expected_count=0
for ix in range(24):
 for iy in range(18):
  x=x0+(x1-x0)*(ix+.5)/24;y=y0+(y1-y0)*(iy+.5)/18
  hit=court_tree.ray_cast(Vector((x,y,.25)),Vector((0,0,-1)),.3)
  expected=expected_tree.ray_cast(Vector((x,y,.25)),Vector((0,0,-1)),.3)[0] is not None
  assert (hit[0] is not None)==expected,(x,y)
  expected_count+=int(expected)
  if hit[0] is not None:
   assert .05699<hit[0].z<.05801
   rays.append(dict(x=x,y=y,z=hit[0].z))
assert len(rays)==expected_count and expected_count>200
church=json.loads((ROOT/'result/blender/strand-church212/audit.json').read_text())
plan=json.loads((ROOT/'result/blender/strand-church212/geometry-plan.json').read_text())
church_tree=tree([bpy.data.objects[n] for n in church['addedObjects']])
c,s=__import__('math').cos(plan['angle']),__import__('math').sin(plan['angle']);cx,cy=plan['centre'];tx,ty=plan['towerCentre']
tower=(cx+c*tx-s*ty,cy+s*tx+c*ty)
top=church_tree.ray_cast(Vector((*tower,60)),Vector((0,0,-1)),60)[0]
assert top is not None and top.z>41
apex=max((bpy.data.objects[n].matrix_world@v.co).z for n in church['addedObjects'] for v in bpy.data.objects[n].data.vertices)
assert abs(apex-plan['estimatedOverallHeight'])<.0001
nave=church_tree.ray_cast(Vector((cx,cy,60)),Vector((0,0,-1)),60)[0]
assert nave is not None and abs(nave.z-17.5)<.01
body=bpy.data.objects['CHURCH212_nave_walls'];floor_faces=[]
for f in body.data.polygons:
 p=[body.matrix_world@body.data.vertices[i].co for i in f.vertices]
 if all(abs(v.z-.05)<1e-6 for v in p):floor_faces.append([[v.x,v.y] for v in p])
old=bpy.data.objects['OLD_PUBLIC212_historical_public_T_corridor_floor'];assert old.name in bpy.data.collections['OLD_MAIN_FOYER174'].all_objects and old.name in bpy.data.collections['OLD_EXTERIOR'].all_objects
record=dict(sourceModelSha256=hashlib.sha256(CURRENT.read_bytes()).hexdigest(),completeModelReopened=True,originalMaterialsVerified=len(materials),
 courtWalkingProbes=len(rays),courtProbes=rays,churchTowerMappedPosition=tower,churchTowerTopZ=apex,churchTowerCentreFirstHitZ=top.z,churchNaveTopZ=nave.z,churchGroundFaces=floor_faces,
 churchFootprintExpectedM2=plan['footprintAreaM2'],oldCorridorSharedWithExterior=True)
(STAGE/'public-realm-verification.json').write_text(json.dumps(record,indent=2)+'\n');print('PUBLIC_REALM212_SAVED',len(rays),len(materials),flush=True)
