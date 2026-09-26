"""Audit explicit replacements, untouched source geometry and isolated interiors."""
from pathlib import Path
from array import array
import hashlib
import json
import math
import bpy
ROOT = Path(__file__).resolve().parents[2]
STAGE = ROOT / 'result/blender/stage24'

def geometry():
    output = {}
    for obj in bpy.data.objects:
        if obj.type != 'MESH':
            continue
        digest = hashlib.sha256()
        for elements, name, width, kind in [(obj.data.vertices,'co',3,'f'),(obj.data.loops,'vertex_index',1,'i'),(obj.data.polygons,'material_index',1,'i')]:
            buffer = array(kind, [0]) * (len(elements) * width)
            elements.foreach_get(name, buffer)
            digest.update(buffer.tobytes())
        digest.update(str([list(row) for row in obj.matrix_world]).encode())
        digest.update(str([material.name if material else None for material in obj.data.materials]).encode())
        output[obj.name] = digest.hexdigest()
    return output

bpy.ops.wm.open_mainfile(filepath=str(ROOT / 'result/blender/LSE_campus_detailed_v23.blend'))
before = geometry()
bpy.ops.wm.open_mainfile(filepath=str(ROOT / 'result/blender/LSE_campus_detailed_v24.blend'))
after = geometry()
review = json.loads((STAGE / 'building-review.json').read_text())['buildings']
replaced = {name for item in review for name in item['replacedObjects']}
rooms = json.loads((STAGE / 'room-studies.json').read_text())['buildings']
campus = bpy.data.scenes['00_CAMPUS_COMPLETE']
checks = {
    'all_unreplaced_meshes_preserved': all(after.get(name) == digest for name, digest in before.items() if name not in replaced),
    'explicit_replacements_removed': all(name not in bpy.data.objects for name in replaced),
    'only_additive_geometry': not replaced,
    'library_has_six_sections': len(next(item for item in review if item['code']=='LRB')['interiorSections']) == 6,
    'all_31_buildings_recorded': len(review) == len({item['code'] for item in review}) == 31,
    'twenty_independent_samples': len(rooms) == len({item['code'] for item in rooms}) == 20,
    'twenty_five_interiors': sum(bool(collection.all_objects) for collection in bpy.data.collections if collection.name.endswith('_PUBLIC_INTERIOR_study')) == 25,
    'sample_geometry_finite_and_isolated': True,
}
for room in rooms:
    collection = bpy.data.collections[room['code'] + '_PUBLIC_INTERIOR_study']
    assert collection.get('roomSample') and collection.get('roomLabel') == room['label']
    assert collection.all_objects
    for obj in collection.all_objects:
        checks['sample_geometry_finite_and_isolated'] &= obj.name not in campus.objects
        checks['sample_geometry_finite_and_isolated'] &= all(math.isfinite(value) for vertex in obj.data.vertices for value in vertex.co)
spaces = [bpy.data.collections[record['collection']] for record in json.loads((STAGE/'room-spaces.json').read_text())['spaces']]
checks['additional_rooms_isolated'] = all(bool(space.all_objects) and all(o.name not in campus.objects for o in space.all_objects) for space in spaces)
checks['marshall_hall_retained'] = bool(bpy.data.collections['MAR_PUBLIC_INTERIOR_study'].all_objects)
report = {'checks': checks, 'preservedMeshes': len(before) - len(replaced.intersection(before)), 'replacedObjects': len(replaced)}
(STAGE / 'native-audit.json').write_text(json.dumps(report, indent=2)+'\n')
assert all(checks.values()), checks
print('EDITION24_NATIVE_AUDIT_PASS', json.dumps(report), flush=True)
