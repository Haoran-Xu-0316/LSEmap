"""Reopen the integrated220 campus and protect its accepted219 source.

The new theatre is a separate scene. Existing source geometry, materials,
visibility, modifiers and room memberships must remain unchanged.
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
from refine_ksw_exterior219 import modifier_state
OUT = ROOT / 'result/blender/stage220'
PRIOR = ROOT / 'result/blender/stage219'
BASE = ROOT / 'result/blender/LSE_campus_detailed_v219.blend'
FINAL = ROOT / 'result/blender/LSE_campus_detailed_v220.blend'
BASE_SHA = '62d7882be80b3f383a1e8b40139cd5168baf2b0b9f42cb9806fd9417e104d3b9'
ROOM_ID = 'clm-hongkong'


def read(path):
    return json.loads(path.read_text())


def write(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


expected = accepted_fingerprints(PRIOR, BASE_SHA)
previous = read(PRIOR / 'building-refinement.json')
visibility = read(PRIOR / 'baseline-state.json')['visibility']
visibility.update({n: True for n in previous['archivedObjects']})
visibility.update({n: False for n in previous['addedObjects']})
metadata = read(ROOT / 'web/tools/building-metadata.json')
existing_rooms = [r for r in metadata['spaces'] if r['id'] != ROOM_ID]
new_room = next(r for r in metadata['spaces'] if r['id'] == ROOM_ID)
assert len(existing_rooms) == 18
snapshot = OUT / 'protected-source-state.json'
if BASE.exists():
    assert hashlib.sha256(BASE.read_bytes()).hexdigest() == BASE_SHA
    bpy.ops.wm.open_mainfile(filepath=str(BASE)); update_scene()
    assert {o.name: object_fingerprint(o) for o in bpy.data.objects} == expected
    assert {o.name: o.hide_render for o in bpy.data.objects} == visibility
    assert new_room['collection'] not in bpy.data.collections
    protected = dict(baselineSha256=BASE_SHA,
        materials={m.name: material_fingerprint(m) for m in bpy.data.materials},
        modifiers={o.name: json.loads(json.dumps(modifier_state(o))) for o in bpy.data.objects},
        rooms={r['collection']: sorted(o.name for o in bpy.data.collections[r['collection']].all_objects)
               for r in existing_rooms},
        roomCampusObjects={r['collection']: sorted(o.name for o in bpy.data.collections[r['collection']].all_objects
                           if o.name in bpy.data.scenes['00_CAMPUS_COMPLETE'].objects)
                           for r in existing_rooms})
    if snapshot.exists():
        assert read(snapshot) == protected
    else:
        write(snapshot, protected)
else:
    protected = read(snapshot)
    assert protected['baselineSha256'] == BASE_SHA

record = read(OUT / 'building-refinement.json')
assert record['version'] == 220 and record['baselineSha256'] == BASE_SHA
assert hashlib.sha256(FINAL.read_bytes()).hexdigest() == record['sourceModelSha256']
assert read(OUT / 'baseline-state.json') == dict(fingerprints=expected, visibility=visibility)
assert record['archivedObjects'] == record['changedObjects'] == []
assert len(record['changes']) == len(record['independentRooms']) == 1
bpy.ops.wm.open_mainfile(filepath=str(FINAL)); update_scene()
assert set(bpy.data.objects.keys()) == set(expected) | set(record['addedObjects'])
assert all(object_fingerprint(bpy.data.objects[n]) == v for n, v in expected.items())
assert all(material_fingerprint(bpy.data.materials[n]) == v for n, v in protected['materials'].items())
assert all(bpy.data.objects[n].hide_render == v for n, v in visibility.items())
assert all(json.loads(json.dumps(modifier_state(bpy.data.objects[n]))) == v for n, v in protected['modifiers'].items())
assert all(object_fingerprint(bpy.data.objects[n]) == v for n, v in record['addedFingerprints'].items())
room_count = 0
for collection, names in protected['rooms'].items():
    assert sorted(o.name for o in bpy.data.collections[collection].all_objects) == names
    assert sorted(n for n in names if n in bpy.data.scenes['00_CAMPUS_COMPLETE'].objects) == protected['roomCampusObjects'][collection]
    room_count += len(names)
assert room_count == 623
change = record['changes'][0]
audit = read(ROOT / change['report'])
assert audit['baselineSha256'] == BASE_SHA
component = ROOT / audit.get('componentPath', audit.get('component', ''))
assert hashlib.sha256(component.read_bytes()).hexdigest() == audit['componentSha256'] == change['componentSha256']
assert audit['space'] == new_room
assert set(audit['addedObjects']) == set(record['addedObjects'])
collection = bpy.data.collections[new_room['collection']]
assert set(o.name for o in collection.all_objects) == set(record['addedObjects'])
assert not any(n in bpy.data.scenes['00_CAMPUS_COMPLETE'].objects for n in record['addedObjects'])
assert all(n.startswith('CLMG02_R220_') for n in record['addedObjects'])
assert collection.name in bpy.data.scenes[audit['collectionSpec']['scene']].collection.children
assert all(not bpy.data.objects[n].hide_render for n in record['addedObjects'])
layout = read(ROOT / 'result/blender/clm-hongkong220/plan-layout.json')
assert len(layout['seats']) == 260
assert len(set(s['id'] for s in layout['seats'])) == 260
result = dict(sourceModelSha256=record['sourceModelSha256'], baselineSha256=BASE_SHA,
              originalObjectsVerified=len(expected), originalMaterialNodesVerified=len(protected['materials']),
              sourceRoomObjectsVerified=room_count, sourceRoomsVerified=18, newRoomObjects=len(record['addedObjects']),
              newRoomIsolatedFromCampus=True, totalSelectableRooms=19, historicPlanSymbols=260,
              currentCapacityClaimed=False, completeModelReopened=True)
write(OUT / 'native-verification.json', result)
print('CAMPUS220_NATIVE', result, flush=True)
