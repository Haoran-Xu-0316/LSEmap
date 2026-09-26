"""Reopen edition 19 and independently verify additive geometry and room scope."""
from array import array
from pathlib import Path
import hashlib
import json
import math
import bpy

ROOT = Path(__file__).resolve().parents[2]

def existing_geometry():
    signatures = {}
    for obj in bpy.data.objects:
        if obj.type != 'MESH':
            continue
        digest = hashlib.sha256()
        for elements, attribute, width, kind in [
            (obj.data.vertices, 'co', 3, 'f'),
            (obj.data.loops, 'vertex_index', 1, 'i'),
            (obj.data.polygons, 'material_index', 1, 'i'),
        ]:
            buffer = array(kind, [0]) * (len(elements) * width)
            elements.foreach_get(attribute, buffer)
            digest.update(buffer.tobytes())
        digest.update(str([list(row) for row in obj.matrix_world]).encode())
        digest.update(str([material.name if material else None for material in obj.data.materials]).encode())
        signatures[obj.name] = digest.hexdigest()
    return signatures

bpy.ops.wm.open_mainfile(filepath=str(ROOT / 'result/blender/LSE_campus_detailed_v17.blend'))
before = existing_geometry()
bpy.ops.wm.open_mainfile(filepath=str(ROOT / 'result/blender/LSE_campus_detailed_v19.blend'))
after = existing_geometry()
review = json.loads((ROOT / 'result/blender/stage19/building-review.json').read_text())
rooms = json.loads((ROOT / 'result/blender/stage18/room-studies.json').read_text())['buildings']
campus = bpy.data.scenes['00_CAMPUS_COMPLETE']
checks = {
    'existing_mesh_geometry_and_material_slots_preserved': all(after.get(name) == digest for name, digest in before.items()),
    'all_31_buildings_reviewed': len(review['buildings']) == len({record['code'] for record in review['buildings']}) == 31,
    'three_unique_room_samples': len(rooms) == 3 and {room['code'] for room in rooms} == {'OLD', 'CLM', 'CON'},
    'room_meshes_are_finite': True,
    'room_samples_excluded_from_campus': True,
    'eight_nonempty_interiors': sum(bool(collection.all_objects) for collection in bpy.data.collections if collection.name.endswith('_PUBLIC_INTERIOR_study')) == 8,
}
for room in rooms:
    collection = bpy.data.collections[room['code'] + '_PUBLIC_INTERIOR_study']
    assert collection.get('roomLabel') == room['label']
    assert len(collection.all_objects) == room['meshFamilies']
    for obj in collection.all_objects:
        checks['room_meshes_are_finite'] &= all(math.isfinite(value) for vertex in obj.data.vertices for value in vertex.co)
        checks['room_samples_excluded_from_campus'] &= obj.name not in campus.objects
report = {'checks': checks, 'preservedMeshes': len(before), 'roomSeats': {room['code']: room['seats'] for room in rooms}}
(ROOT / 'result/blender/stage19/native-audit.json').write_text(json.dumps(report, indent=2) + '\n')
assert all(checks.values()), checks
print('EDITION19_NATIVE_AUDIT_PASS', json.dumps(report), flush=True)
