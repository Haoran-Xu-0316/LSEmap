"""Read-only whole-building MAR195 review of the accepted v194 campus.

Open in Blender's Text Editor. The earlier exterior-only roof impression is
explicitly rejected: MAR_PUBLIC_INTERIOR_study owns visible 39.4m top slabs,
and the production exporter includes them in both overview and exterior.
No roof, upper floor, footprint, backup or new whole-campus model is created.
"""
from pathlib import Path
import array
import hashlib
import json
import sys

import bpy

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'result/blender/mar-exterior195'
BASE = ROOT / 'result/blender/LSE_campus_detailed_v194.blend'
BASE_SHA = 'bcd7292cfda4c43ed4fd7622f564a5d3ce7ef8ac0360ba00d68b4081bd363c8e'
sys.path.insert(0, str(Path(__file__).parent))
from refine_mar_exterior174 import local, world


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fingerprint(obj):
    digest = hashlib.sha256(str([list(row) for row in obj.matrix_world]).encode())
    if obj.type == 'MESH':
        for values, field, kind, size in [
            (obj.data.vertices, 'co', 'f', 3),
            (obj.data.loops, 'vertex_index', 'i', 1),
            (obj.data.polygons, 'material_index', 'i', 1),
        ]:
            packed = array.array(kind, [0]) * (len(values) * size)
            values.foreach_get(field, packed)
            digest.update(packed.tobytes())
        for layer in obj.data.uv_layers:
            packed = array.array('f', [0]) * (len(layer.data) * 2)
            layer.data.foreach_get('uv', packed)
            digest.update(layer.name.encode() + packed.tobytes())
        for material in obj.data.materials:
            if material:
                digest.update(material.name.encode())
                digest.update(str(list(material.diffuse_color)).encode())
    return digest.hexdigest()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    assert sha(BASE) == BASE_SHA
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    scene = bpy.data.scenes['00_CAMPUS_COMPLETE']
    bpy.context.window.scene = scene
    bpy.context.view_layer.update()
    originals = {o.name: fingerprint(o) for o in bpy.data.objects}
    visibility = {o.name: (o.hide_render, o.hide_viewport, o.hide_get()) for o in bpy.data.objects}
    building = {o for name in ['MAR_EXTERIOR', 'MAR_PUBLIC_INTERIOR_study'] for o in bpy.data.collections[name].all_objects}
    inventory = []
    roof_records = []
    for obj in sorted(building, key=lambda o: o.name):
        if obj.type != 'MESH' or obj.hide_render:
            continue
        points = [local(obj.matrix_world @ v.co) for v in obj.data.vertices]
        if not points:
            continue
        row = dict(name=obj.name, localBounds=[[min(p[i] for p in points), max(p[i] for p in points)] for i in range(3)],
                   faceCount=len(obj.data.polygons), vertexCount=len(points),
                   collections=[c.name for c in obj.users_collection],
                   materials=[m.name if m else None for m in obj.data.materials])
        inventory.append(row)
        if obj.name in ['MAR_MAR_floor_way/1376078545_39.4', 'MAR_V115_retained_MAR_floor_way/1376078544_39.4', 'MAR_NEXT_ROOF154_8546_bounded_roof']:
            roof_records.append(row)
    assert len(roof_records) == 3
    exporter = ROOT/'web/tools/export_scene.py'
    exporter_lines = exporter.read_text().splitlines()
    start = next(i for i, line in enumerate(exporter_lines) if line.startswith('def exterior_objects('))
    end = next(i for i in range(start+1, len(exporter_lines)) if exporter_lines[i].startswith('campus_root ='))
    selection = '\n'.join(exporter_lines[start:end])
    assert "objects += list(bpy.data.collections[code + '_PUBLIC_INTERIOR_study'].all_objects)" in selection
    (OUT/'inventory.json').write_text(json.dumps(inventory, indent=2)+'\n')
    for obj in scene.objects:
        if obj.type in ['MESH', 'FONT', 'CURVE'] and obj not in building:
            obj.hide_render = True
    camera = bpy.data.objects.new('MAR195_readonly_review', bpy.data.cameras.new('MAR195_readonly_review'))
    scene.collection.objects.link(camera)
    scene.camera = camera
    camera.data.type = 'ORTHO'
    camera.data.ortho_scale = 75
    scene.render.engine = 'BLENDER_WORKBENCH'
    scene.display.shading.color_type = 'MATERIAL'
    scene.display.shading.light = 'STUDIO'
    scene.display.shading.show_cavity = True
    scene.display.shading.show_shadows = True
    scene.render.resolution_x = 1100
    scene.render.resolution_y = 950
    scene.render.resolution_percentage = 100
    views = [('south', (-70, -95, 82)), ('north', (-65, 105, 80)), ('south-east', (85, -95, 78))]
    for name, position in views:
        camera.location = world(*position)
        camera.rotation_euler = (world(-3, -1, 22)-camera.location).to_track_quat('-Z', 'Y').to_euler()
        scene.render.filepath = str(OUT/f'complete-before-{name}.png')
        bpy.ops.render.render(write_still=True)
    for name, values in visibility.items():
        obj = bpy.data.objects[name]
        obj.hide_render, obj.hide_viewport = values[:2]
        obj.hide_set(values[2])
    assert all(fingerprint(bpy.data.objects[name]) == value for name, value in originals.items())
    assert all((bpy.data.objects[name].hide_render, bpy.data.objects[name].hide_viewport, bpy.data.objects[name].hide_get()) == value for name, value in visibility.items())
    report = dict(
        readOnly=True, status='no-evidence-supported-new-envelope-correction',
        addedObjects=[], archivedObjects=[], replacements=[], targetCollection='MAR_EXTERIOR',
        componentPath=None, componentSha256=None, baselineSha256=BASE_SHA,
        originalObjectCount=len(originals), visibleWholeBuildingMeshCount=len(inventory),
        allOriginalGeometryUVMaterialsPreserved=True, allOriginalVisibilityRestored=True,
        baselineFileUnchanged=sha(BASE) == BASE_SHA, wholeCampusSaved=False,
        roofRecords=roof_records,
        rejectedDiagnosis=dict(issue='39.4m roof appears missing in exterior-only collection render',
                               finding='Roof already present in public-interior collection; production exterior_objects includes that collection.',
                               repeatedRoofNotCreated=True, exporterPath=str(exporter.relative_to(ROOT)),
                               exporterSelectionLines=[start+1, end], exporterSha256=sha(exporter)),
        references=[dict(path=f'data/collections/architecture_round5/images/MAR/MAR_mar_kane_{number}.jpg',
                         sha256=sha(ROOT/f'data/collections/architecture_round5/images/MAR/MAR_mar_kane_{number}.jpg'),
                         sourceUrl='https://nickkane.co.uk/portfolio_page/marshall-building-lse-london-grafton-architects/',
                         captureDate=None, uploadYear=2022) for number in ['02', '03', '05', '07', '08']],
        examinedScope=['Whole north front with retained188court and two middle wall rows.',
                       'South and south-east academic wings including existing39.4m/42.8m roofs.',
                       'North roof terraces, rear window walls and shared public-interior top plates.'],
        limitations=['Upper-wing footprints and blank gable attribution remain inherited estimates; no uniquely registered upper04–09or roof plan obtained.',
                     'No change to188north recess, podium, glass or room studies; internal offices and room-by-room detail remain incomplete.',
                     'A roof-only or cropped exterior preview cannot prove an open roof: all render-visible building collections must be inspected together.',
                     'Workbench preview proves shape and collection inclusion, not final browser glass/reflection appearance.',
                     '2022publication/upload does not establish a current photograph capture date.'],
        previewFiles=[f'complete-before-{name}.png' for name, position in views],
        newWholeCampusModels=0,
    )
    (OUT/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    print('MAR195_READONLY_REVIEW_VERIFIED', json.dumps({key: report[key] for key in ['status', 'visibleWholeBuildingMeshCount', 'baselineFileUnchanged', 'previewFiles']}), flush=True)
    bpy.ops.wm.quit_blender()


if __name__ == '__main__':
    main()
