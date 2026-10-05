"""Assemble independently verified classroom corrections in the latest campus.

Run in Blender's Text Editor. Room samples remain outside the campus scene;
all existing mesh geometry and material bindings are verified before saving.
"""
from pathlib import Path
from array import array
import hashlib
import json
import sys
import bpy

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'web/tools'))
from refine_room_finishes import apply_room_finishes
BASE = ROOT / 'result/blender/LSE_campus_detailed_v157.blend'
TARGET = ROOT / 'result/blender/LSE_campus_detailed_v158.blend'
REPORT = ROOT / 'result/blender/stage158'
COMPONENT = REPORT / 'cbg103-component.blend'


def geometry_signatures():
    result = {}
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
        digest.update(str([m.name if m else None for m in obj.data.materials]).encode())
        result[obj.name] = digest.hexdigest()
    return result


def assemble_rooms():
    existing_proof = REPORT / 'room-refinement.json'
    if TARGET.exists() and existing_proof.exists():
        proof = json.loads(existing_proof.read_text())
        assert hashlib.sha256(TARGET.read_bytes()).hexdigest() == proof['sourceModelSha256']
        print('ROOMS158_ALREADY_CURRENT')
        return
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    for scene in bpy.data.scenes:
        for layer in scene.view_layers:
            layer.update()
    before = geometry_signatures()
    campus_names = set(bpy.data.scenes['00_CAMPUS_COMPLETE'].objects.keys())
    changes = apply_room_finishes()
    with bpy.data.libraries.load(str(COMPONENT), link=False) as (available, imported):
        names = [name for name in available.collections if name == 'CBG103_TEACHING_ROOM_study']
        assert len(names) == 1, available.collections
        imported.collections = names
    room = imported.collections[0]
    assert room is not None and room.all_objects
    scene = bpy.data.scenes.new('ROOM158_CBG103_TEACHING')
    scene.collection.children.link(room)
    after = geometry_signatures()
    deleted = set(changes['deletedObjects'])
    changed = set(changes['changedObjects'])
    assert changed == {'OLD_D5_ROOM18_door_vision_black'}
    assert deleted == {'MAR_V22_TEACH_front_acoustic_slats_oak'}
    assert all(after.get(name) == signature for name, signature in before.items() if name not in deleted | changed)
    assert campus_names == set(bpy.data.scenes['00_CAMPUS_COMPLETE'].objects.keys())
    assert all(obj.name not in campus_names for obj in room.all_objects)
    # Append retains an unused library provenance datablock in Blender 5.2.
    # Require every imported ID to be local before removing that provenance.
    assert not any(block.library for block in bpy.data.objects)
    assert not any(block.library for block in bpy.data.meshes)
    assert not any(block.library for block in bpy.data.materials)
    for library in list(bpy.data.libraries):
        assert not any(block.library == library for block in bpy.data.user_map()), 'Unexpected linked component dependency'
        bpy.data.libraries.remove(library)
    assert not bpy.data.libraries
    assert not any(i.source == 'FILE' and not i.packed_file for i in bpy.data.images)
    bpy.context.window.scene = bpy.data.scenes['00_CAMPUS_COMPLETE']
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(TARGET))
    proof = {'version': 158, 'baselineSha256': hashlib.sha256(BASE.read_bytes()).hexdigest(),
             'sourceModelSha256': hashlib.sha256(TARGET.read_bytes()).hexdigest(),
             'allUnrelatedMeshesPreserved': True, 'campusSceneUnchanged': True,
             'changes': changes, 'newRoomCollection': room.name,
             'newRoomObjects': len(room.all_objects), 'objects': len(bpy.data.objects),
             'geometrySignatures': after}
    (REPORT / 'room-refinement.json').write_text(json.dumps(proof, indent=2) + '\n')
    print('ROOMS158_SAVED', len(bpy.data.objects), len(room.all_objects))


if __name__ == '__main__':
    assemble_rooms()
