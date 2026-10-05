"""Apply source-supported building details to the latest complete native model.

Run in Blender's Text Editor. Each building owns a callable refiner; the shared
assembly verifies every unrelated mesh and saves one complete editable source.
"""
from pathlib import Path
import hashlib
import json
import sys
import bpy
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'web/tools'))
from refine_rooms import geometry_signatures
from refine_connaught_room_glazing import apply_connaught_room_glazing
BASE = ROOT / 'result/blender/LSE_campus_detailed_v161.blend'
TARGET = ROOT / 'result/blender/LSE_campus_detailed_v162.blend'
REPORT = ROOT / 'result/blender/stage162'


def refine_building_details():
    report_path = REPORT / 'building-refinement.json'
    if TARGET.exists() and report_path.exists():
        proof = json.loads(report_path.read_text())
        assert hashlib.sha256(TARGET.read_bytes()).hexdigest() == proof['sourceModelSha256']
        print('BUILDINGS162_ALREADY_CURRENT')
        return
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    for scene in bpy.data.scenes:
        for layer in scene.view_layers:
            layer.update()
    before = geometry_signatures()
    changes = [apply_connaught_room_glazing()]
    allowed = {name for record in changes for name in record.get('changedObjects', [])}
    assert allowed == {'CON_NEXT_con_methodology_rear_wall_white', 'CON_NEXT_con_methodology_rear_glazed_partition_glass', 'CON_NEXT_con_tea_point_rear_wall_white', 'CON_NEXT_con_tea_point_rear_window_glass'}
    after = geometry_signatures()
    assert all(after.get(name) == digest for name, digest in before.items() if name not in allowed)
    added = set(after) - set(before)
    assert added == {name for record in changes for name in record.get('addedObjects', [])}
    assert not bpy.data.libraries
    assert not any(image.source == 'FILE' and not image.packed_file for image in bpy.data.images)
    bpy.context.window.scene = bpy.data.scenes['00_CAMPUS_COMPLETE']
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(TARGET))
    proof = {'version': 162, 'baselineSha256': hashlib.sha256(BASE.read_bytes()).hexdigest(),
             'sourceModelSha256': hashlib.sha256(TARGET.read_bytes()).hexdigest(),
             'allUnrelatedMeshesPreserved': True, 'changes': changes,
             'objects': len(bpy.data.objects), 'geometrySignatures': after}
    report_path.write_text(json.dumps(proof, indent=2) + '\n')
    print('BUILDINGS162_SAVED', len(bpy.data.objects), len(added))


if __name__ == '__main__':
    refine_building_details()
