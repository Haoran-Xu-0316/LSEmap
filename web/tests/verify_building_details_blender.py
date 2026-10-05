"""Reopen the saved building update and compare every native mesh signature."""
from pathlib import Path
import hashlib
import json
import sys
import bpy
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'web/tools'))
from refine_rooms import geometry_signatures
REPORT=ROOT/'result/blender/stage159'
MODEL=ROOT/'result/blender/LSE_campus_detailed_v159.blend'
proof=json.loads((REPORT/'building-refinement.json').read_text())
assert hashlib.sha256(MODEL.read_bytes()).hexdigest()==proof['sourceModelSha256']
bpy.ops.wm.open_mainfile(filepath=str(MODEL))
for scene in bpy.data.scenes:
 for layer in scene.view_layers:layer.update()
assert geometry_signatures()==proof['geometrySignatures']
assert not bpy.data.libraries
assert not any(i.source=='FILE' and not i.packed_file for i in bpy.data.images)
(REPORT/'reopened-verification.json').write_text(json.dumps({'version':159,'savedSceneReopened':True,'allMeshSignaturesVerified':True,'sourceModelSha256':proof['sourceModelSha256'],'externalDependencies':False},indent=2)+'\n')
print('BUILDINGS159_REOPENED_VERIFIED')
