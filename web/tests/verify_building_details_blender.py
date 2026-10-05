"""Reopen the saved building update and compare every native mesh signature."""
from pathlib import Path
import hashlib
import json
import sys
import bpy
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'web/tools'))
from refine_rooms import geometry_signatures
REPORT=ROOT/'result/blender/stage163'
MODEL=ROOT/'result/blender/LSE_campus_detailed_v163.blend'
proof=json.loads((REPORT/'building-refinement.json').read_text())
assert hashlib.sha256(MODEL.read_bytes()).hexdigest()==proof['sourceModelSha256']
bpy.ops.wm.open_mainfile(filepath=str(MODEL))
for scene in bpy.data.scenes:
 for layer in scene.view_layers:layer.update()
assert geometry_signatures()==proof['geometrySignatures']
from mathutils import Vector
from refine_old_wall_lantern import apply_old_wall_lantern
assert apply_old_wall_lantern()['alreadyApplied']
assert geometry_signatures()==proof['geometrySignatures']
lamp_proof=proof['changes'][0]
origin,normal=Vector(lamp_proof['wallPlaneOrigin']),Vector(lamp_proof['wallPlaneOutward'])
lamp=[bpy.data.objects[name]for name in ['OLD_LANTERN163_blue_frame','OLD_LANTERN163_opal_shade']]
depths=[(obj.matrix_world@v.co-origin).dot(normal)for obj in lamp for v in obj.data.vertices]
assert min(depths)>-.0001 and abs(min(depths))<.0001
assert all(obj.name in bpy.data.collections['OLD_EXTERIOR'].objects for obj in lamp)
assert not bpy.data.libraries
assert not any(i.source=='FILE' and not i.packed_file for i in bpy.data.images)
(REPORT/'reopened-verification.json').write_text(json.dumps({'version':163,'savedSceneReopened':True,'allMeshSignaturesVerified':True,'sourceModelSha256':proof['sourceModelSha256'],'externalDependencies':False,'lampBackFaceMeetsRegisteredWall':True,'lampVertices':sum(len(o.data.vertices)for o in lamp)},indent=2)+'\n')
print('BUILDINGS163_REOPENED_VERIFIED')
