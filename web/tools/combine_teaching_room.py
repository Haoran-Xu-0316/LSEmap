"""Append reviewed teaching-room studies without replacing public interiors."""
from pathlib import Path
import hashlib, json, math
import bpy
from mathutils import Vector
ROOT = Path(__file__).resolve().parents[2]
STAGE = ROOT / 'result/blender/stage24'
BASE = ROOT / 'result/blender/LSE_campus_detailed_v23.blend'
MODEL = ROOT / 'result/blender/LSE_campus_detailed_v24.blend'
bpy.ops.wm.open_mainfile(filepath=str(BASE))
original = set(bpy.data.objects.keys())
review = json.loads((ROOT / 'result/blender/stage23/building-review.json').read_text())
for record in review['buildings']:
    record.update(addedObjects=[], replacedObjects=[], changes=[], status='reviewed-no-change')
spaces = json.loads((ROOT / 'result/blender/stage23/room-spaces.json').read_text())['spaces']
rooms = json.loads((ROOT / 'result/blender/stage23/room-studies.json').read_text())
records = []
for group in ['saw','61a']:
    for record in json.loads((STAGE / group / 'manifest.json').read_text())['buildings']:
        records.append((group, record))
for group, record in records:
    study = record['roomStudy']
    existing = bpy.data.collections.get(study['collection'])
    if existing:
        assert not existing.all_objects, 'Only empty placeholders may be replaced'
        bpy.data.collections.remove(existing)
    collection = bpy.data.collections.new(study['collection'])
    collection['roomSample'] = True
    collection['roomLabel'] = study['label']
    scene = bpy.data.scenes.new('ROOM24_'+record['code']+'_TEACHING')
    scene.collection.children.link(collection)
    names = [item['name'] for item in record['addedObjects']]
    assert len(names) == len(set(names)) and not set(names) & original
    with bpy.data.libraries.load(str(STAGE / group / 'refined.blend'), link=False) as (available, imported):
        assert set(names) <= set(available.objects)
        imported.objects = names
    for obj in imported.objects:
        assert obj.type == 'MESH' and not obj.hide_render
        assert all(math.isfinite(x) for vertex in obj.data.vertices for x in vertex.co)
        collection.objects.link(obj)
    camera_name = record['code']+'_ROOM24_camera'
    camera = bpy.data.objects.new(camera_name, bpy.data.cameras.new(camera_name))
    scene.collection.objects.link(camera)
    camera.location = study['camera']
    camera.rotation_euler = (Vector(study['target']) - camera.location).to_track_quat('-Z', 'Y').to_euler()
    scene.camera = camera
    current = next(item for item in review['buildings'] if item['code'] == record['code'])
    current.update(status='refined', addedObjects=record['addedObjects'], changes=record.get('changes', []))
    current.setdefault('sources', []).extend(record.get('sources', []))
    destination = rooms['buildings'] if study['collection'] == record['code']+'_PUBLIC_INTERIOR_study' else spaces
    destination.append({'code':record['code'], **study, 'sources':record.get('sources', [])})
assert original <= set(bpy.data.objects.keys())
campus = bpy.data.scenes['00_CAMPUS_COMPLETE']
for space in spaces:
    assert not any(obj.name in campus.objects for obj in bpy.data.collections[space['collection']].all_objects)
bpy.context.window.scene = campus
bpy.ops.wm.save_as_mainfile(filepath=str(MODEL))
review.update(version=24, sourceModelSha256=hashlib.sha256(MODEL.read_bytes()).hexdigest(), baselineSha256=hashlib.sha256(BASE.read_bytes()).hexdigest())
(STAGE / 'building-review.json').write_text(json.dumps(review, ensure_ascii=False, indent=2)+'\n')
rooms['version'] = 24
(STAGE / 'room-studies.json').write_text(json.dumps(rooms, ensure_ascii=False, indent=2)+'\n')
(STAGE / 'room-spaces.json').write_text(json.dumps({'version':24, 'spaces':spaces}, ensure_ascii=False, indent=2)+'\n')
print('EDITION24_COMBINED', len(spaces), 'additional spaces', flush=True)
