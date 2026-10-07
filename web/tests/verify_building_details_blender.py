"""Reopen the integrated scene and verify scoped geometry, room separation and idempotence."""
from pathlib import Path
import hashlib, json, sys
import bpy
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'web/tools'))
from refine_rooms import geometry_signatures
from refine_architectural_glass import shape_signature
from refine_saw_structure172 import apply_saw_structure172
from refine_lrb_exterior172 import apply_lrb_exterior172
from refine_street_surface172 import apply_street_surface172
from refine_old_glass172 import apply_old_glass172
REPORT = ROOT / 'result/blender/stage172'
MODEL = ROOT / 'result/blender/LSE_campus_detailed_v172.blend'
proof = json.loads((REPORT / 'building-refinement.json').read_text())
assert hashlib.sha256(MODEL.read_bytes()).hexdigest() == proof['sourceModelSha256']
bpy.ops.wm.open_mainfile(filepath=str(MODEL))
for scene in bpy.data.scenes:
    for layer in scene.view_layers:
        layer.update()
assert geometry_signatures() == proof['geometrySignatures']
for refiner in (apply_saw_structure172, apply_lrb_exterior172, apply_street_surface172, apply_old_glass172):
    assert refiner()['alreadyApplied']
assert geometry_signatures() == proof['geometrySignatures']
assert {o.name:o.hide_render for o in bpy.data.objects} == proof['visibility']
for name, digest in proof['originalShapesAndUVs'].items():
    assert shape_signature(bpy.data.objects[name]) == digest
campus = set(bpy.data.scenes['00_CAMPUS_COMPLETE'].objects.keys())
room = bpy.data.collections['LRB_PUBLIC_INTERIOR168_study']
assert room.all_objects and all(obj.name not in campus for obj in room.all_objects)
assert len(room.all_objects) == 109
room171 = bpy.data.collections['CBG205_ROOM171_study']
assert room171['studentSeatCount'] == 42
assert all(o.name not in campus for o in room171.all_objects)
assert len(room171.all_objects) == 24
glass = bpy.data.objects['OLD_NEXT_GLAZING172_single_door_panes']
assert len(glass.data.vertices) == 32 and len(glass.data.polygons) == 8
assert glass.data.materials[0].node_tree.nodes['Principled BSDF'].inputs['Metallic'].default_value == 0
assert bpy.data.objects['OLD_NEXT_EXTERIOR154_door_glass'].hide_render
assert not bpy.data.libraries
assert not any(i.source == 'FILE' and not i.packed_file for i in bpy.data.images)
result = dict(version=172, sourceModelSha256=proof['sourceModelSha256'],
              savedSceneReopened=True, allMeshSignaturesVerified=True,
              allOriginalShapesAndUVsPreserved=True, idempotent=True,
              roomsOutsideCampus=True, externalDependencies=False,
              archivedObjects=proof['archivedObjects'])
(REPORT / 'reopened-verification.json').write_text(json.dumps(result, indent=2) + '\n')
print('BUILDINGS172_REOPENED_VERIFIED')
