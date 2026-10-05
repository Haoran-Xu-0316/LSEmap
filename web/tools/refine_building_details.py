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
from refine_ckk_rainwater import apply_ckk_rainwater
from refine_saw_stairs import apply_saw_stairs
from refine_lrb_handrails import apply_lrb_handrails
BASE = ROOT / 'result/blender/LSE_campus_detailed_v158.blend'
TARGET = ROOT / 'result/blender/LSE_campus_detailed_v159.blend'
REPORT = ROOT / 'result/blender/stage159'


def refine_building_details():
    report_path = REPORT / 'building-refinement.json'
    if TARGET.exists() and report_path.exists():
        proof = json.loads(report_path.read_text())
        assert hashlib.sha256(TARGET.read_bytes()).hexdigest() == proof['sourceModelSha256']
        print('BUILDINGS159_ALREADY_CURRENT')
        return
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    for scene in bpy.data.scenes:
        for layer in scene.view_layers:
            layer.update()
    before = geometry_signatures()
    changes = [apply_ckk_rainwater(), apply_saw_stairs(), apply_lrb_handrails()]
    allowed = {name for record in changes for name in record.get('changedObjects', [])}
    assert allowed == {'SAW_spiral_anti_slip_nosings', 'LRB_gallery_circular_handrail', 'LRB_spiral_continuous_handrail', 'LRB_landing_handrail.001'}, allowed
    after = geometry_signatures()
    assert all(after.get(name) == digest for name, digest in before.items() if name not in allowed)
    added = set(after) - set(before)
    assert added == {name for record in changes for name in record.get('addedObjects', [])}
    assert not bpy.data.libraries
    assert not any(image.source == 'FILE' and not image.packed_file for image in bpy.data.images)
    bpy.context.window.scene = bpy.data.scenes['00_CAMPUS_COMPLETE']
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(TARGET))
    proof = {'version': 159, 'baselineSha256': hashlib.sha256(BASE.read_bytes()).hexdigest(),
             'sourceModelSha256': hashlib.sha256(TARGET.read_bytes()).hexdigest(),
             'allUnrelatedMeshesPreserved': True, 'changes': changes,
             'objects': len(bpy.data.objects), 'geometrySignatures': after}
    report_path.write_text(json.dumps(proof, indent=2) + '\n')
    print('BUILDINGS159_SAVED', len(bpy.data.objects), len(added))


if __name__ == '__main__':
    refine_building_details()
