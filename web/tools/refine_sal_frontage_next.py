"""Audit SAL's side-alley frontage against the architect's photographs.

Run in Blender's Text Editor. This audit deliberately produces no replacement
geometry until the two photographed blocks can be registered to native bays.
"""
from pathlib import Path
import array
import hashlib
import json
import math
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'result/blender/sal_frontage_next'
OUT.mkdir(parents=True, exist_ok=True)
BASE = ROOT / 'result/blender/LSE_campus_detailed_v124.blend'
if not BASE.exists():
    BASE = max((ROOT / 'result/blender').glob('LSE_campus_detailed_v[0-9]*.blend'),
               key=lambda path: int(path.stem.rsplit('v', 1)[1]))


def fingerprint(obj):
    digest = hashlib.sha256(str([list(row) for row in obj.matrix_world]).encode())
    if obj.type == 'MESH':
        for data, field, kind, count in ((obj.data.vertices, 'co', 'f', 3),
                                        (obj.data.loops, 'vertex_index', 'i', 1),
                                        (obj.data.polygons, 'material_index', 'i', 1)):
            values = array.array(kind, [0]) * (len(data) * count)
            data.foreach_get(field, values)
            digest.update(values.tobytes())
        for layer in obj.data.uv_layers:
            values = array.array('f', [0]) * (len(layer.data) * 2)
            layer.data.foreach_get('uv', values)
            digest.update(values.tobytes())
    digest.update(str([material.name if material else None
                       for material in getattr(obj.data, 'materials', [])]).encode())
    return digest.hexdigest()


bpy.ops.wm.open_mainfile(filepath=str(BASE))
scene = bpy.data.scenes['00_CAMPUS_COMPLETE']
bpy.context.window.scene = scene
originals = {obj.name: fingerprint(obj) for obj in bpy.data.objects}
collection = bpy.data.collections['SAL_EXTERIOR']
angle = math.radians(24.35)
right = Vector((-math.cos(angle), -math.sin(angle), 0))
outward = Vector((-math.sin(angle), math.cos(angle), 0))
rows = []
for name in ('SAL_Window_sash_frames', 'SAL_Window_sash_bars'):
    obj = bpy.data.objects[name]
    vertices = [obj.matrix_world @ vertex.co for vertex in obj.data.vertices]
    rows.append({'name': name,
                 'materials': [material.name for material in obj.data.materials],
                 'vertices': len(vertices),
                 'localRightBounds': [min(v.dot(right) for v in vertices),
                                      max(v.dot(right) for v in vertices)],
                 'localOutwardBounds': [min(v.dot(outward) for v in vertices),
                                        max(v.dot(outward) for v in vertices)]})
index = json.loads((ROOT / 'data/建筑图片/SAL_Sir Arthur Lewis Building/图片索引.json').read_text())
references = []
for suffix in ('SAL_5b39324ea103.jpg', 'SAL_d0d696021ed0.jpg'):
    record = next(item for item in index['images'] if item['file'].endswith(suffix))
    photograph = ROOT / 'data/建筑图片/SAL_Sir Arthur Lewis Building' / record['file']
    assert hashlib.sha256(photograph.read_bytes()).hexdigest() == record['sha256']
    references.append({'file': str(photograph.relative_to(ROOT)),
                       'sha256': record['sha256'], 'sources': record['sources']})

# Inspect the saved native flank; review visibility is temporary, never saved.
visible = {obj.name for obj in collection.all_objects}
for obj in scene.objects:
    if obj.type == 'MESH' and obj.name not in visible:
        obj.hide_render = True
focus = right * -135.5 + outward * 43 + Vector((0, 0, 12))
camera_data = bpy.data.cameras.new('SAL_FRONTAGE_REVIEW_CAMERA')
camera = bpy.data.objects.new(camera_data.name, camera_data)
scene.collection.objects.link(camera)
camera.location = focus + right * 60 - outward * 12 + Vector((0, 0, 3))
camera.rotation_euler = (focus - camera.location).to_track_quat('-Z', 'Y').to_euler()
camera_data.type = 'ORTHO'
camera_data.ortho_scale = 44
scene.camera = camera
scene.render.engine = 'BLENDER_EEVEE'
scene.render.resolution_x = 1400
scene.render.resolution_y = 1100
scene.render.resolution_percentage = 100
scene.render.filepath = str(OUT / 'native-flank-review.png')
bpy.ops.render.render(write_still=True)
assert all(fingerprint(bpy.data.objects[name]) == value for name, value in originals.items())
audit = {'baseline': str(BASE.relative_to(ROOT)),
         'baselineSha256': hashlib.sha256(BASE.read_bytes()).hexdigest(),
         'originalObjectCount': len(originals), 'originalGeometryPreserved': True,
         'ownedObjects': [], 'archivedObjects': [], 'references': references,
         'nativeWindowGroups': rows,
         'decision': 'No geometry or palette replacement: block registration remains unproven.',
         'observations': [
             'Architect front photograph shows blue sash paint on the historic principal elevation.',
             'Side-alley photograph shows a near brick block with charcoal sash and a recessed taller pale-trimmed middle block.',
             'Current native flank uses shared blue sash groups and a repeated four-storey sequence without the photographed taller middle-block silhouette.'
         ],
         'unresolved': [
             'Photographs do not establish native-depth coordinates of the near-block/middle-block junction.',
             'A uniform charcoal repaint would incorrectly remove the lighter sash visible on the middle block.',
             'Window repetition and block heights require a registered side elevation or site footprint before assigning exact bays.',
             'Photograph capture dates are unknown; these images are not evidence of a current complete survey.'
         ],
         'nativeReview': 'result/blender/sal_frontage_next/native-flank-review.png'}
(OUT / 'audit.json').write_text(json.dumps(audit, ensure_ascii=False, indent=2) + '\n')
(OUT / 'verification.json').write_text(json.dumps({
    'baselineSha256': audit['baselineSha256'],
    'originalObjectCount': len(originals), 'originalGeometryPreserved': True,
    'fullModelSaved': False, 'componentCreated': False, 'nativeReopenedAndRendered': True,
    'decision': audit['decision']}, indent=2) + '\n')
print('SAL_FRONTAGE_AUDIT_UNCHANGED', len(originals), flush=True)
bpy.ops.wm.quit_blender()
