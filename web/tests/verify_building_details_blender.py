"""Reopen the integrated scene and verify scoped geometry, room separation and idempotence."""
from pathlib import Path
import hashlib, json, sys
import bpy
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'web/tools'))
from refine_rooms import geometry_signatures
from refine_architectural_glass import shape_signature
from refine_col_exterior167 import apply_col_exterior167
from refine_streets167 import apply_streets167
from build_room_samples167 import apply_room_samples167
REPORT = ROOT / 'result/blender/stage167'
MODEL = ROOT / 'result/blender/LSE_campus_detailed_v167.blend'
proof = json.loads((REPORT / 'building-refinement.json').read_text())
assert hashlib.sha256(MODEL.read_bytes()).hexdigest() == proof['sourceModelSha256']
bpy.ops.wm.open_mainfile(filepath=str(MODEL))
for scene in bpy.data.scenes:
    for layer in scene.view_layers:
        layer.update()
assert geometry_signatures() == proof['geometrySignatures']
for refiner in (apply_col_exterior167, apply_streets167, apply_room_samples167):
    assert refiner()['alreadyApplied']
assert geometry_signatures() == proof['geometrySignatures']
assert {o.name:o.hide_render for o in bpy.data.objects} == proof['visibility']
for name, digest in proof['originalShapesAndUVs'].items():
    assert shape_signature(bpy.data.objects[name]) == digest
campus = set(bpy.data.scenes['00_CAMPUS_COMPLETE'].objects.keys())
for space in proof['changes'][2]['spaces']:
    room = bpy.data.collections[space['collection']]
    assert room.all_objects and all(obj.name not in campus for obj in room.all_objects)
assert not bpy.data.libraries
assert not any(i.source == 'FILE' and not i.packed_file for i in bpy.data.images)
result = dict(version=167, sourceModelSha256=proof['sourceModelSha256'],
              savedSceneReopened=True, allMeshSignaturesVerified=True,
              allOriginalShapesAndUVsPreserved=True, idempotent=True,
              roomsOutsideCampus=True, externalDependencies=False,
              archivedObjects=proof['archivedObjects'])
(REPORT / 'reopened-verification.json').write_text(json.dumps(result, indent=2) + '\n')
print('BUILDINGS167_REOPENED_VERIFIED')
