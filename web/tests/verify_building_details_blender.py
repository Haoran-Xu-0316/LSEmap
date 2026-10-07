"""Reopen the integrated scene and verify scoped geometry, room separation and idempotence."""
from pathlib import Path
import hashlib, json, sys
import bpy
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'web/tools'))
from refine_rooms import geometry_signatures
from refine_architectural_glass import shape_signature
from refine_old_foyer174 import apply_old_foyer174, COLLECTION
from refine_kgs_exterior176 import apply_kgs_exterior176
from refine_portugal_environment176 import apply_portugal_environment176
from refine_saw_lower_structure173 import OLD_STAIR_NAMES, OLD_FLOORS, FLOOR_NAMES
from refine_street_fixtures173 import OWNED
REPORT = ROOT / 'result/blender/stage176'
MODEL = ROOT / 'result/blender/LSE_campus_detailed_v176.blend'
proof = json.loads((REPORT / 'building-refinement.json').read_text())
assert hashlib.sha256(MODEL.read_bytes()).hexdigest() == proof['sourceModelSha256']
bpy.ops.wm.open_mainfile(filepath=str(MODEL))
for scene in bpy.data.scenes:
    for layer in scene.view_layers:
        layer.update()
assert geometry_signatures() == proof['geometrySignatures']
for refiner in (apply_kgs_exterior176, apply_portugal_environment176):
    assert refiner()['alreadyApplied']
assert geometry_signatures() == proof['geometrySignatures']
assert {o.name:o.hide_render for o in bpy.data.objects} == proof['visibility']
for name, digest in proof['originalShapesAndUVs'].items():
    assert shape_signature(bpy.data.objects[name]) == digest
attic = bpy.data.collections['KGS176_PORTUGAL_ATTIC']
assert attic['windowAxes'] == 5 and attic['paneFacets'] == 9
assert len(bpy.data.objects['KGS176_attic_single_glass'].data.polygons) == 9
assert all(len(o.users_collection) == 1 and o.users_collection[0].name == '00_SITE'
           for o in (bpy.data.objects['SITE176_PEA_Portugal_frontage_bollards'],
                     bpy.data.objects['SITE176_PEA_Portugal_double_yellow_lines']))
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
panes = bpy.data.objects['CKK_EXTERIOR173_D5_pavilion80_glazing_glass']
assert len(panes.data.polygons) == 18
shader = panes.data.materials[0].node_tree.nodes['Principled BSDF']
assert shader.inputs['Metallic'].default_value == 0
assert shader.inputs['Transmission Weight'].default_value > .1
assert abs(panes.data.materials[0]['webOpacity'] - .55) < 1e-6
assert all(bpy.data.objects[name].hide_render for name in OLD_STAIR_NAMES + OLD_FLOORS)
assert all(not bpy.data.objects[name].hide_render for name in FLOOR_NAMES)
assert OWNED in campus
foyer = bpy.data.collections[COLLECTION]
assert all(o.name in campus for o in foyer.all_objects)
assert all(bpy.data.objects[n].hide_render for n in proof['archivedObjects'])
assert not bpy.data.libraries
assert not any(i.source == 'FILE' and not i.packed_file for i in bpy.data.images)
result = dict(version=176, sourceModelSha256=proof['sourceModelSha256'],
              savedSceneReopened=True, atticWindowAxes=5, atticPaneFacets=9, streetMeshesSingleSiteMembership=True, allMeshSignaturesVerified=True,
              allOriginalShapesAndUVsPreserved=True, idempotent=True,
              independentRoomsOutsideCampus=True, entranceFoyerRegisteredToCampus=True, externalDependencies=False,
              archivedObjects=proof['archivedObjects'])
(REPORT / 'reopened-verification.json').write_text(json.dumps(result, indent=2) + '\n')
print('BUILDINGS176_REOPENED_VERIFIED')
