"""Reopen edition217 and check it against the independently accepted216 source.

Run as a fixed-config Blender validation file. No model is saved or altered.
"""
from pathlib import Path
import hashlib
import json
import sys
import bpy

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'web/tools'))
from integrate_exterior_round194 import accepted_fingerprints, object_fingerprint, update_scene
from refine_portsmouth_exterior207 import material_fingerprint
from public_interior_objects import public_interior_objects

OUT = ROOT / 'result/blender/stage217'
BASE = ROOT / 'result/blender/LSE_campus_detailed_v216.blend'
FINAL = ROOT / 'result/blender/LSE_campus_detailed_v217.blend'
BASE_SHA = '12376d6365bbc57fa9eec97617453dbbfcf9235a8200bb90726f80c2147c1a60'
material_state = OUT / 'source-material-state.json'
expected = accepted_fingerprints(ROOT / 'result/blender/stage216', BASE_SHA)
if BASE.exists():
    assert hashlib.sha256(BASE.read_bytes()).hexdigest() == BASE_SHA
    bpy.ops.wm.open_mainfile(filepath=str(BASE)); update_scene()
    assert {obj.name: object_fingerprint(obj) for obj in bpy.data.objects} == expected
    original_materials = {mat.name: material_fingerprint(mat) for mat in bpy.data.materials}
    metadata = json.loads((ROOT / 'web/tools/building-metadata.json').read_text())
    room_visibility = {obj.name: obj.hide_render for room in metadata['spaces']
                       for obj in bpy.data.collections[room['collection']].all_objects}
    (OUT / 'room-visibility-before.json').write_text(json.dumps(room_visibility, indent=2) + '\n')
    material_state.write_text(json.dumps(dict(baselineSha256=BASE_SHA, materials=original_materials), indent=2) + '\n')
else:
    stored = json.loads(material_state.read_text())
    assert stored['baselineSha256'] == BASE_SHA
    original_materials = stored['materials']
room_visibility = json.loads((OUT / 'room-visibility-before.json').read_text())
record = json.loads((OUT / 'building-refinement.json').read_text())
assert record['baselineSha256'] == BASE_SHA
assert hashlib.sha256(FINAL.read_bytes()).hexdigest() == record['sourceModelSha256']
bpy.ops.wm.open_mainfile(filepath=str(FINAL)); update_scene()
assert json.loads((OUT / 'baseline-state.json').read_text())['fingerprints'] == expected
assert all(object_fingerprint(bpy.data.objects[name]) == value for name, value in expected.items())
assert all(material_fingerprint(bpy.data.materials[name]) == value for name, value in original_materials.items())
assert all(object_fingerprint(bpy.data.objects[name]) == value for name, value in record['addedFingerprints'].items())
assert set(bpy.data.objects.keys()) == set(expected) | set(record['addedObjects'])
assert all(bpy.data.objects[name].hide_render == hidden for name, hidden in room_visibility.items()), 'Independent room visibility changed'
assert all(bpy.data.objects[name].hide_render for name in record['archivedObjects'])
assert all(not bpy.data.objects[name].hide_render for name in record['addedObjects'])

# Optical replacements must retain the source mesh, transform and every UV.
finish_objects = []
for change in record['changes']:
    if change['code'] not in {'COW', 'OLD'}:
        continue
    for name in change['addedObjects']:
        obj = bpy.data.objects[name]
        source = bpy.data.objects[obj['originalObject']]
        assert obj.matrix_world == source.matrix_world, name
        assert [tuple(v.co) for v in obj.data.vertices] == [tuple(v.co) for v in source.data.vertices], name
        assert [tuple(p.vertices) for p in obj.data.polygons] == [tuple(p.vertices) for p in source.data.polygons], name
        assert len(obj.data.uv_layers) == len(source.data.uv_layers), name
        for new_uv, old_uv in zip(obj.data.uv_layers, source.data.uv_layers):
            assert new_uv.name == old_uv.name
            assert [tuple(v.uv) for v in new_uv.data] == [tuple(v.uv) for v in old_uv.data], name
        finish_objects.append(name)

metadata = json.loads((ROOT / 'web/tools/building-metadata.json').read_text())
mar = next(row for row in metadata['buildings'] if row['code'] == 'MAR')
public = {obj.name for obj in public_interior_objects(mar) if not obj.hide_render}
ground = [obj for obj in bpy.data.collections['MAR_EXTERIOR'].all_objects
          if not obj.hide_render and obj.get('publicInteriorComponent')]
assert ground, 'Registered ground envelope must be available in the public interior'
assert all(obj.name in public for obj in ground)
rooms = [row['collection'] for row in metadata['spaces'] if 'collection' in row]
for name in rooms:
    assert not set(obj.name for obj in bpy.data.collections[name].all_objects) & public
result = dict(sourceModelSha256=record['sourceModelSha256'], baselineSha256=BASE_SHA,
              originalObjectsVerified=len(expected), originalMaterialNodesVerified=len(original_materials),
              newObjectsVerified=len(record['addedObjects']), opticalReplacementGeometryAndUVsVerified=len(finish_objects),
              marGroundEnvelopeIncludedInPublicStudy=[obj.name for obj in ground],
              independentRoomObjectVisibilityVerified=len(room_visibility), completeModelReopened=True)
(OUT / 'native-verification.json').write_text(json.dumps(result, indent=2) + '\n')
print('CAMPUS217_NATIVE', result, flush=True)
