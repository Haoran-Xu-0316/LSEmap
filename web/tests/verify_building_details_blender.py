"""Reopen the saved building update and compare every native mesh signature."""
from pathlib import Path
import hashlib
import json
import sys
import bpy
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'web/tools'))
from refine_rooms import geometry_signatures
REPORT=ROOT/'result/blender/stage162'
MODEL=ROOT/'result/blender/LSE_campus_detailed_v162.blend'
proof=json.loads((REPORT/'building-refinement.json').read_text())
assert hashlib.sha256(MODEL.read_bytes()).hexdigest()==proof['sourceModelSha256']
bpy.ops.wm.open_mainfile(filepath=str(MODEL))
for scene in bpy.data.scenes:
 for layer in scene.view_layers:layer.update()
assert geometry_signatures()==proof['geometrySignatures']
from mathutils import Vector
from mathutils.bvhtree import BVHTree
aperture_probes=[]
for room, suffix in [('con_methodology','rear_glazed_partition_glass'),('con_tea_point','rear_window_glass')]:
 wall=bpy.data.objects['CON_NEXT_'+room+'_rear_wall_white']
 glass=bpy.data.objects['CON_NEXT_'+room+'_'+suffix]
 wall_points=[wall.matrix_world@v.co for v in wall.data.vertices]
 glass_points=[glass.matrix_world@v.co for v in glass.data.vertices]
 trees=[BVHTree.FromPolygons(points,[tuple(p.vertices) for p in obj.data.polygons]) for points,obj in [(wall_points,wall),(glass_points,glass)]]
 lo=[min(v[i] for v in glass_points) for i in range(3)];hi=[max(v[i] for v in glass_points) for i in range(3)]
 for u in [.1,.5,.9]:
  for v in [.1,.5,.9]:
   ray=Vector((lo[0]+u*(hi[0]-lo[0]),min(p.y for p in wall_points)-1,lo[2]+v*(hi[2]-lo[2])))
   assert trees[0].ray_cast(ray,Vector((0,1,0)))[0] is None
   assert trees[1].ray_cast(ray,Vector((0,1,0)))[0] is not None
 aperture_probes.append({'room':room,'clearSamples':9,'glassSamples':9})
from refine_connaught_room_glazing import apply_connaught_room_glazing
assert apply_connaught_room_glazing()['alreadyApplied']
assert geometry_signatures()==proof['geometrySignatures']
assert not bpy.data.libraries
assert not any(i.source=='FILE' and not i.packed_file for i in bpy.data.images)
(REPORT/'reopened-verification.json').write_text(json.dumps({'version':162,'savedSceneReopened':True,'allMeshSignaturesVerified':True,'sourceModelSha256':proof['sourceModelSha256'],'externalDependencies':False,'apertureProbes':aperture_probes},indent=2)+'\n')
print('BUILDINGS162_REOPENED_VERIFIED')
