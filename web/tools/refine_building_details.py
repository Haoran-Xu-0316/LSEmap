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
from refine_houghton_bollard import apply_houghton_bollard
from refine_old_planter_coping import apply_old_planter_coping
from refine_mar_building_lettering import apply_mar_building_lettering
BASE = ROOT / 'result/blender/LSE_campus_detailed_v164.blend'
TARGET = ROOT / 'result/blender/LSE_campus_detailed_v165.blend'
REPORT = ROOT / 'result/blender/stage165'


def refine_building_details():
    report_path = REPORT / 'building-refinement.json'
    if TARGET.exists() and report_path.exists():
        proof = json.loads(report_path.read_text())
        assert hashlib.sha256(TARGET.read_bytes()).hexdigest() == proof['sourceModelSha256']
        print('BUILDINGS165_ALREADY_CURRENT')
        return
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    for scene in bpy.data.scenes:
        for layer in scene.view_layers:
            layer.update()
    before = geometry_signatures()
    visibility = {o.name: o.hide_render for o in bpy.data.objects}
    furniture = bpy.data.objects['SITE_V47_Mapped_street_furniture']
    assert not furniture.data.uv_layers, 'Retain source UVs before furniture rebuild'
    changes = [apply_houghton_bollard(), apply_old_planter_coping(), apply_mar_building_lettering()]
    archived = {name for record in changes for name in record.get('archivedObjects', [])}
    assert all(o.hide_render == visibility[o.name] for o in bpy.data.objects if o.name in visibility and o.name not in archived)
    assert all(bpy.data.objects[name].hide_render for name in archived)
    allowed = {name for record in changes for name in record.get('changedObjects', [])}
    assert allowed == {'SITE_V47_Mapped_street_furniture'}
    after = geometry_signatures()
    assert all(after.get(name) == digest for name, digest in before.items() if name not in allowed)
    added = set(after) - set(before)
    assert added == {name for record in changes for name in record.get('addedObjects', [])}
    assert not bpy.data.libraries
    assert not any(image.source == 'FILE' and not image.packed_file for image in bpy.data.images)
    bpy.context.window.scene = bpy.data.scenes['00_CAMPUS_COMPLETE']
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(TARGET))
    proof = {'version': 165, 'baselineSha256': hashlib.sha256(BASE.read_bytes()).hexdigest(),
             'sourceModelSha256': hashlib.sha256(TARGET.read_bytes()).hexdigest(),
             'allUnrelatedMeshesPreserved': True, 'changes': changes,
             'objects': len(bpy.data.objects), 'geometrySignatures': after, 'archivedObjects': sorted(archived),
             'visibility': {o.name:o.hide_render for o in bpy.data.objects}}
    report_path.write_text(json.dumps(proof, indent=2) + '\n')
    print('BUILDINGS165_SAVED', len(bpy.data.objects), len(added))


if __name__ == '__main__':
    refine_building_details()
