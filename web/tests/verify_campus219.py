"""Verify edition219 against the independently accepted218 campus.

Fixed Blender validation, without model writes. Check all original geometry,
UVs, material nodes, visibility and detached room ownership after integration.
Component-specific physical checks remain in their own source audit records.
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

OUT = ROOT / 'result/blender/stage219'
PRIOR = ROOT / 'result/blender/stage218'
BASE = ROOT / 'result/blender/LSE_campus_detailed_v218.blend'
FINAL = ROOT / 'result/blender/LSE_campus_detailed_v219.blend'
BASE_SHA = 'd57142ea7dce27ea052bbd508f63dcd8c15136faccc132ac4f5915dff64fe27d'
PREFIXES = ('CKK219_', 'KSW219_')


def read(path):
    return json.loads(path.read_text())


def write(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


expected = accepted_fingerprints(PRIOR, BASE_SHA)
previous = read(PRIOR / 'building-refinement.json')
visibility = read(PRIOR / 'baseline-state.json')['visibility']
visibility.update({name: True for name in previous['archivedObjects']})
visibility.update({name: False for name in previous['addedObjects']})
metadata = read(ROOT / 'web/tools/building-metadata.json')
source_state = OUT / 'protected-source-state.json'
if BASE.exists():
    assert hashlib.sha256(BASE.read_bytes()).hexdigest() == BASE_SHA
    bpy.ops.wm.open_mainfile(filepath=str(BASE)); update_scene()
    assert {o.name: object_fingerprint(o) for o in bpy.data.objects} == expected
    assert {o.name: o.hide_render for o in bpy.data.objects} == visibility
    protected = dict(
        baselineSha256=BASE_SHA,
        materials={m.name: material_fingerprint(m) for m in bpy.data.materials},
        rooms={r['collection']: sorted(o.name for o in bpy.data.collections[r['collection']].all_objects)
               for r in metadata['spaces']},
        roomCampusObjects={r['collection']: sorted(o.name for o in bpy.data.collections[r['collection']].all_objects
                           if o.name in bpy.data.scenes['00_CAMPUS_COMPLETE'].objects)
                           for r in metadata['spaces']},
    )
    if source_state.exists():
        assert all(protected[k] == value for k, value in read(source_state).items()), 'Saved source identity must remain stable'
    write(source_state, protected)
else:
    protected = read(source_state)
    assert protected['baselineSha256'] == BASE_SHA

record = read(OUT / 'building-refinement.json')
assert record['version'] == 219 and record['baselineSha256'] == BASE_SHA
assert hashlib.sha256(FINAL.read_bytes()).hexdigest() == record['sourceModelSha256']
assert read(OUT / 'baseline-state.json') == dict(fingerprints=expected, visibility=visibility)
bpy.ops.wm.open_mainfile(filepath=str(FINAL)); update_scene()
assert set(bpy.data.objects.keys()) == set(expected) | set(record['addedObjects'])
assert all(object_fingerprint(bpy.data.objects[n]) == value for n, value in expected.items())
assert all(material_fingerprint(bpy.data.materials[n]) == value for n, value in protected['materials'].items())
assert all(object_fingerprint(bpy.data.objects[n]) == value for n, value in record['addedFingerprints'].items())
assert all(n.startswith(PREFIXES) for n in record['addedObjects'])
archived = set(record['archivedObjects'])
assert all(bpy.data.objects[n].hide_render == (True if n in archived else hidden)
           for n, hidden in visibility.items())
assert all(not bpy.data.objects[n].hide_render for n in record['addedObjects'])
assert not record['changedObjects']
component_names, component_archives = [], []
for change in record['changes']:
    audit = read(ROOT / change['report'])
    path = ROOT / audit.get('componentPath', audit.get('component', ''))
    assert hashlib.sha256(path.read_bytes()).hexdigest() == change['componentSha256'] == audit['componentSha256']
    assert audit['baselineSha256'] == BASE_SHA
    assert change['addedObjects'] == audit['addedObjects']
    assert change['archivedObjects'] == audit['archivedObjects']
    component_names.extend(audit['addedObjects']); component_archives.extend(audit['archivedObjects'])
assert len(component_names) == len(set(component_names))
assert len(component_archives) == len(set(component_archives))
assert set(component_names) == set(record['addedObjects'])
assert set(component_archives) == archived
room_names = set()
for collection, names in protected['rooms'].items():
    assert sorted(o.name for o in bpy.data.collections[collection].all_objects) == names
    assert not set(names) & (archived | set(record['addedObjects']))
    assert all(bpy.data.objects[n].hide_render == visibility[n] for n in names)
    assert sorted(n for n in names if n in bpy.data.scenes['00_CAMPUS_COMPLETE'].objects) == protected['roomCampusObjects'][collection]
    room_names.update(names)
# Optical corrections must preserve every source vertex, face, UV and transform.
for name in record['addedObjects']:
    obj = bpy.data.objects[name]
    source = bpy.data.objects[obj['originalObject']]
    assert obj.matrix_world == source.matrix_world, name
    assert [tuple(v.co) for v in obj.data.vertices] == [tuple(v.co) for v in source.data.vertices], name
    assert [tuple(p.vertices) for p in obj.data.polygons] == [tuple(p.vertices) for p in source.data.polygons], name
    assert len(obj.data.uv_layers) == len(source.data.uv_layers), name
    for new_uv, old_uv in zip(obj.data.uv_layers, source.data.uv_layers):
        assert new_uv.name == old_uv.name
        assert [tuple(v.uv) for v in new_uv.data] == [tuple(v.uv) for v in old_uv.data], name
result = dict(sourceModelSha256=record['sourceModelSha256'], baselineSha256=BASE_SHA,
              originalObjectsVerified=len(expected), originalMaterialNodesVerified=len(protected['materials']),
              newObjectsVerified=len(record['addedObjects']), archivedObjectsVerified=len(archived),
              independentRoomsVerified=len(protected['rooms']), independentRoomObjectsVerified=len(room_names),
              unchangedOriginalGeometryUVsMaterialBindingsAndVisibility=True, completeModelReopened=True)
write(OUT / 'native-verification.json', result)
print('CAMPUS219_NATIVE', result, flush=True)
