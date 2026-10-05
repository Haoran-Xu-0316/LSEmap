"""Reopen the saved room update and verify every protected mesh signature."""
from pathlib import Path
import hashlib
import json
import sys
import bpy
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'web/tools'))
from refine_rooms import geometry_signatures
REPORT = ROOT/'result/blender/stage158'
MODEL = ROOT/'result/blender/LSE_campus_detailed_v158.blend'
proof = json.loads((REPORT/'room-refinement.json').read_text())
assert hashlib.sha256(MODEL.read_bytes()).hexdigest() == proof['sourceModelSha256']
bpy.ops.wm.open_mainfile(filepath=str(MODEL))
for scene in bpy.data.scenes:
    for layer in scene.view_layers:
        layer.update()
assert geometry_signatures() == proof['geometrySignatures']
assert 'MAR_V22_TEACH_front_acoustic_slats_oak' not in bpy.data.objects
assert 'MAR_V22_TEACH_front_wall_plaster' in bpy.data.objects
room = bpy.data.collections[proof['newRoomCollection']]
assert len(room.all_objects) == proof['newRoomObjects']
assert all(o.name not in bpy.data.scenes['00_CAMPUS_COMPLETE'].objects for o in room.all_objects)
assert not bpy.data.libraries
assert not any(i.source == 'FILE' and not i.packed_file for i in bpy.data.images)
(REPORT/'reopened-verification.json').write_text(json.dumps({'version':158,'sourceModelSha256':proof['sourceModelSha256'],'savedSceneReopened':True,'allMeshSignaturesVerified':True,'roomExcludedFromCampus':True,'externalDependencies':False},indent=2)+'\n')
print('ROOMS158_REOPENED_VERIFIED')
