"""Merge explicit exterior replacements and independently reviewed interiors.

Run in Blender. The edition-19 native file is never overwritten. Every removed
object must appear in a replacement manifest; new room cutaways stay off the map.
"""
from pathlib import Path
import hashlib
import json
import math
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
STAGE = ROOT / 'result/blender/stage20'
BASELINE = ROOT / 'result/blender/LSE_campus_detailed_v19.blend'
MODEL = ROOT / 'result/blender/LSE_campus_detailed_v20.blend'
bpy.ops.wm.open_mainfile(filepath=str(BASELINE))
original_names = set(bpy.data.objects.keys())
removed_names = set()
review = {item['code']: {'code': item['code'], 'changes': [], 'sources': [], 'limitations': [],
                         'addedObjects': [], 'replacedObjects': []}
          for item in json.loads((ROOT / 'data/buildings.json').read_text())['buildings']}
rooms = json.loads((ROOT / 'result/blender/stage18/room-studies.json').read_text())['buildings']
for room in rooms:
    room['scope'] = '历史资料中的局部房间，尺寸估算，不代表整栋内部或当前布局。'

def entries(value):
    return value if isinstance(value, list) else [value] if value else []

for group in ['exteriors', 'interiors-a', 'interiors-b']:
    folder = STAGE / group
    records = json.loads((folder / 'manifest.json').read_text())['buildings']
    objects = [obj for record in records for obj in record.get('addedObjects', [])]
    names = [obj['name'] for obj in objects]
    assert len(names) == len(set(names))
    assert not set(names).intersection(bpy.data.objects.keys()), f'Duplicate objects in {group}'
    replacements = [name for record in records for name in record.get('replacedObjects', [])]
    assert not set(replacements).intersection(removed_names)
    for name in replacements:
        assert name in original_names and name in bpy.data.objects
        bpy.data.objects.remove(bpy.data.objects[name], do_unlink=True)
        removed_names.add(name)
    for record in records:
        code = record['code']
        current = review[code]
        for field in ['changes', 'sources', 'limitations', 'addedObjects', 'replacedObjects']:
            current[field].extend(entries(record.get(field)))
        if record.get('detailView'):
            current['detailView'] = record['detailView']
        study = record.get('roomStudy')
        if not study:
            continue
        name = code + '_PUBLIC_INTERIOR_study'
        existing = bpy.data.collections.get(name)
        if existing:
            assert not existing.all_objects, f'Do not replace an existing interior: {code}'
            bpy.data.collections.remove(existing)
        collection = bpy.data.collections.new(name)
        collection['roomSample'] = True
        collection['roomLabel'] = study['label']
        collection['roomScope'] = study['scope']
        scene = bpy.data.scenes.new('ROOM20_' + code)
        scene.collection.children.link(collection)
        camera = bpy.data.objects.new('ROOM20_' + code + '_camera', bpy.data.cameras.new('ROOM20_' + code + '_camera'))
        scene.collection.objects.link(camera)
        camera.location = study['camera']
        camera.rotation_euler = (Vector(study['target']) - camera.location).to_track_quat('-Z', 'Y').to_euler()
        camera.data.lens = 36
        scene.camera = camera
        rooms.append({'code': code, **study, 'sources': record.get('sources', [])})
    with bpy.data.libraries.load(str(folder / 'refined.blend'), link=False) as (available, imported):
        assert set(names).issubset(available.objects)
        imported.objects = names
    imported_objects = {obj.name: obj for obj in imported.objects}
    for specification in objects:
        obj = imported_objects[specification['name']]
        bpy.data.collections[specification['collection']].objects.link(obj)
        assert not obj.hide_render
        if obj.type == 'MESH':
            assert obj.data.vertices
            assert all(math.isfinite(value) for vertex in obj.data.vertices for value in vertex.co)

assert original_names - removed_names <= set(bpy.data.objects.keys())
assert len({room['code'] for room in rooms}) == len(rooms)
campus = bpy.data.scenes['00_CAMPUS_COMPLETE']
for room in rooms:
    collection = bpy.data.collections[room['code'] + '_PUBLIC_INTERIOR_study']
    assert len(collection.all_objects) > 0
    assert all(obj.name not in campus.objects for obj in collection.all_objects)
for record in review.values():
    record['status'] = 'refined' if record['addedObjects'] else 'reviewed-no-change'
    for field in ['changes', 'sources', 'limitations', 'replacedObjects']:
        record[field] = list({json.dumps(value, sort_keys=True): value for value in record[field]}.values())
bpy.context.window.scene = campus
bpy.ops.wm.save_as_mainfile(filepath=str(MODEL))
report = {'version': 20, 'baselineSha256': hashlib.sha256(BASELINE.read_bytes()).hexdigest(),
          'sourceModelSha256': hashlib.sha256(MODEL.read_bytes()).hexdigest(), 'buildings': list(review.values())}
(STAGE / 'building-review.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
(STAGE / 'room-studies.json').write_text(json.dumps({'version': 20, 'buildings': rooms}, ensure_ascii=False, indent=2)+'\n')
print('EDITION20_COMBINED', len(rooms), 'room samples;', len(removed_names), 'explicit replacements', flush=True)
