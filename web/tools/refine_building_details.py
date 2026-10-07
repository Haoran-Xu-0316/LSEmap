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
from refine_architectural_glass import shape_signature
from refine_old_foyer174 import apply_old_foyer174
from refine_mar_exterior174 import apply_mar_exterior174
from refine_lrb_facade174 import apply_lrb_facade174
from refine_public_realm174 import apply_public_realm174
BASE = ROOT / 'result/blender/LSE_campus_detailed_v173.blend'
TARGET = ROOT / 'result/blender/LSE_campus_detailed_v174.blend'
REPORT = ROOT / 'result/blender/stage174'


def refine_building_details():
    report_path = REPORT / 'building-refinement.json'
    if TARGET.exists() and report_path.exists():
        proof = json.loads(report_path.read_text())
        assert hashlib.sha256(TARGET.read_bytes()).hexdigest() == proof['sourceModelSha256']
        print('BUILDINGS174_ALREADY_CURRENT')
        return
    REPORT.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    for scene in bpy.data.scenes:
        for layer in scene.view_layers:
            layer.update()
    before_objects = set(bpy.data.objects.keys())
    before = geometry_signatures()
    shapes = {o.name:shape_signature(o) for o in bpy.data.objects if o.type=='MESH'}
    visibility = {o.name: o.hide_render for o in bpy.data.objects}
    changes = [apply_old_foyer174(), apply_mar_exterior174(), apply_lrb_facade174(), apply_public_realm174()]
    for scene in bpy.data.scenes:
        for layer in scene.view_layers:
            layer.update()
    archived = {name for record in changes for name in record.get('archivedObjects', [])}
    assert all(o.hide_render == visibility[o.name] for o in bpy.data.objects if o.name in visibility and o.name not in archived)
    assert all(bpy.data.objects[name].hide_render for name in archived)
    allowed = {name for record in changes for name in record.get('changedObjects', [])}
    after = geometry_signatures()
    assert all(shape_signature(bpy.data.objects[name])==digest for name,digest in shapes.items())
    assert all(after.get(name) == digest for name, digest in before.items() if name not in allowed)
    added = set(bpy.data.objects.keys()) - before_objects
    assert added == {name for record in changes for name in record.get('addedObjects', [])}
    assert not bpy.data.libraries
    assert not any(image.source == 'FILE' and not image.packed_file for image in bpy.data.images)
    bpy.context.window.scene = bpy.data.scenes['00_CAMPUS_COMPLETE']
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(TARGET))
    proof = {'version': 174, 'baselineSha256': hashlib.sha256(BASE.read_bytes()).hexdigest(),
             'sourceModelSha256': hashlib.sha256(TARGET.read_bytes()).hexdigest(),
             'allUnrelatedMeshesPreserved': True, 'changes': changes,
             'objects': len(bpy.data.objects), 'geometrySignatures': after, 'originalShapesAndUVs': shapes, 'archivedObjects': sorted(archived),
             'visibility': {o.name:o.hide_render for o in bpy.data.objects}}
    report_path.write_text(json.dumps(proof, indent=2) + '\n')
    print('BUILDINGS174_SAVED', len(bpy.data.objects), len(added))


if __name__ == '__main__':
    refine_building_details()
