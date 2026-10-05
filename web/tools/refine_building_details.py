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
from refine_garrick_chairs import apply_garrick_chairs
from refine_connaught_interiors import apply_connaught_interiors
from refine_salisbury_projector import apply_salisbury_projector
BASE = ROOT / 'result/blender/LSE_campus_detailed_v159.blend'
TARGET = ROOT / 'result/blender/LSE_campus_detailed_v160.blend'
REPORT = ROOT / 'result/blender/stage160'


def refine_building_details():
    report_path = REPORT / 'building-refinement.json'
    if TARGET.exists() and report_path.exists():
        proof = json.loads(report_path.read_text())
        assert hashlib.sha256(TARGET.read_bytes()).hexdigest() == proof['sourceModelSha256']
        print('BUILDINGS160_ALREADY_CURRENT')
        return
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    for scene in bpy.data.scenes:
        for layer in scene.view_layers:
            layer.update()
    before = geometry_signatures()
    changes = [apply_garrick_chairs(), apply_connaught_interiors(), apply_salisbury_projector()]
    allowed = {name for record in changes for name in record.get('changedObjects', [])}
    assert {'COL_V20_INTA_chair_back_oak', 'SAL_V20_INTA_projector_body_white'} <= allowed
    assert all(name.startswith(('COL_V20_INTA_chair_back_oak', 'SAL_V20_INTA_projector_body_white', 'CON_D5_ROOM18_')) for name in allowed), allowed
    after = geometry_signatures()
    assert all(after.get(name) == digest for name, digest in before.items() if name not in allowed)
    added = set(after) - set(before)
    assert added == {name for record in changes for name in record.get('addedObjects', [])}
    assert not bpy.data.libraries
    assert not any(image.source == 'FILE' and not image.packed_file for image in bpy.data.images)
    bpy.context.window.scene = bpy.data.scenes['00_CAMPUS_COMPLETE']
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(TARGET))
    proof = {'version': 160, 'baselineSha256': hashlib.sha256(BASE.read_bytes()).hexdigest(),
             'sourceModelSha256': hashlib.sha256(TARGET.read_bytes()).hexdigest(),
             'allUnrelatedMeshesPreserved': True, 'changes': changes,
             'objects': len(bpy.data.objects), 'geometrySignatures': after}
    report_path.write_text(json.dumps(proof, indent=2) + '\n')
    print('BUILDINGS160_SAVED', len(bpy.data.objects), len(added))


if __name__ == '__main__':
    refine_building_details()
