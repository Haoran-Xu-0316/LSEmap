"""Combine the reviewed, non-overlapping building groups into edition 19.

Run in Blender. Only explicitly listed new objects are appended to the edition-18
baseline; existing meshes, cameras and historical room studies are retained.
"""
from pathlib import Path
import hashlib
import json
import math
import bpy

ROOT = Path(__file__).resolve().parents[2]
STAGE = ROOT / 'result/blender/stage19'
BASELINE = ROOT / 'result/blender/LSE_campus_detailed_v18.blend'
MODEL = ROOT / 'result/blender/LSE_campus_detailed_v19.blend'
bpy.ops.wm.open_mainfile(filepath=str(BASELINE))
original_names = {obj.name for obj in bpy.data.objects}
records = []

for group in ['historic', 'modern', 'remaining']:
    folder = STAGE / group
    manifest = json.loads((folder / 'manifest.json').read_text())
    specifications = [obj for building in manifest['buildings'] for obj in building['addedObjects']]
    names = [obj['name'] for obj in specifications]
    assert len(set(names)) == len(names), f'Duplicate names in {group}'
    assert not (set(names) & original_names), f'Existing geometry would be replaced by {group}'
    with bpy.data.libraries.load(str(folder / 'refined.blend'), link=False) as (available, imported):
        assert set(names) <= set(available.objects), f'Missing authored objects in {group}'
        imported.objects = names
    by_name = {obj.name: obj for obj in imported.objects}
    for specification in specifications:
        obj = by_name[specification['name']]
        collection = bpy.data.collections[specification['collection']]
        collection.objects.link(obj)
        assert not obj.hide_render, f'Invisible addition: {obj.name}'
        if obj.type == 'MESH':
            assert len(obj.data.vertices), f'Empty addition: {obj.name}'
            assert all(math.isfinite(value) for vertex in obj.data.vertices for value in vertex.co)
    records.extend(manifest['buildings'])

expected_codes = {item['code'] for item in json.loads((ROOT / 'data/buildings.json').read_text())['buildings']}
assert len(records) == len(expected_codes) == 31
assert {item['code'] for item in records} == expected_codes
assert original_names <= {obj.name for obj in bpy.data.objects}
for code in ['OLD', 'CLM', 'CON']:
    collection = bpy.data.collections[code + '_PUBLIC_INTERIOR_study']
    assert collection.get('roomSample') and len(collection.all_objects) > 20
    assert collection.name not in bpy.data.scenes['00_CAMPUS_COMPLETE'].collection.children
bpy.context.window.scene = bpy.data.scenes['00_CAMPUS_COMPLETE']
bpy.ops.wm.save_as_mainfile(filepath=str(MODEL))
report = {
    'version': 19,
    'baselineSha256': hashlib.sha256(BASELINE.read_bytes()).hexdigest(),
    'sourceModelSha256': hashlib.sha256(MODEL.read_bytes()).hexdigest(),
    'buildings': records,
}
(STAGE / 'building-review.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
print('EDITION19_COMBINED', len(records), 'reviewed buildings;', sum(len(r['addedObjects']) for r in records), 'new objects', flush=True)
