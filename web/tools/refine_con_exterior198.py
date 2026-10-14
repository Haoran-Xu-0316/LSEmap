"""Audit Connaught House without extrapolating an entrance crop into a full facade.

Run in Blender's Text Editor. This read-only review preserves the current campus,
including every room, glazing policy and original object. A single bounded
primary-source lookup provides no new registered full-height facade photograph.
"""
from pathlib import Path
import hashlib
import json
import sys

import bpy

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'web/tools'))
from integrate_exterior_round194 import object_fingerprint

BASE = ROOT / 'result/blender/LSE_campus_detailed_v197.blend'
BASE_SHA = '5a225f1d5227e0b173bc93d9ba4aa5da1e539ec73b003f31ea575ccea807d854'
OUT = ROOT / 'result/blender/con-exterior198'
PHOTO = 'data/建筑图片/CON_Connaught House/01_建筑实拍/exteriors_lse_estate_005.jpg'
ESTATE = 'https://info.lse.ac.uk/staff/divisions/estates-division/lse-estate/LSE-Estate'


def material_state(material):
    """Record optical properties without modifying nodes or enclosure policy."""
    if not material.use_nodes:
        return {'diffuseColor': list(material.diffuse_color)}
    node = next((n for n in material.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
    if node is None:
        return {'principledShader': False}
    return {'baseColor': list(node.inputs['Base Color'].default_value),
            'baseColorLinked': node.inputs['Base Color'].is_linked,
            'roughness': node.inputs['Roughness'].default_value,
            'metallic': node.inputs['Metallic'].default_value,
            'alpha': node.inputs['Alpha'].default_value,
            'transmission': node.inputs['Transmission Weight'].default_value,
            'webOpacity': material.get('webOpacity'),
            'webClosedGlazing': material.get('webClosedGlazing')}


def review():
    """Write a finite evidence and preservation report; save no native file."""
    assert hashlib.sha256(BASE.read_bytes()).hexdigest() == BASE_SHA
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    bpy.context.window.scene = bpy.data.scenes['00_CAMPUS_COMPLETE']
    for scene in bpy.data.scenes:
        for layer in scene.view_layers:
            layer.update()
    originals = {obj.name: object_fingerprint(obj) for obj in bpy.data.objects}
    visibility = {obj.name: [obj.hide_render, obj.hide_viewport, obj.hide_get()] for obj in bpy.data.objects}
    original_materials = {mat.name: material_state(mat) for mat in bpy.data.materials}
    inventory, materials = [], {}
    for obj in bpy.data.collections['CON_EXTERIOR'].all_objects:
        if obj.type != 'MESH' or obj.hide_render or not obj.data.vertices:
            continue
        points = [obj.matrix_world @ vertex.co for vertex in obj.data.vertices]
        inventory.append({'object': obj.name, 'fingerprint': originals[obj.name],
                          'vertices': len(obj.data.vertices), 'faces': len(obj.data.polygons),
                          'bounds': [[min(p[i] for p in points) for i in range(3)],
                                     [max(p[i] for p in points) for i in range(3)]],
                          'materials': [mat.name if mat else None for mat in obj.data.materials]})
        for material in obj.data.materials:
            if material:
                materials[material.name] = material_state(material)
    assert inventory
    report = {
        'version': 198, 'targetCollection': 'CON_EXTERIOR',
        'baseline': str(BASE.relative_to(ROOT)), 'baselineSha256': BASE_SHA,
        'status': 'review-only-no-new-registered-whole-building-evidence',
        'componentPath': None, 'componentSha256': None,
        'addedObjects': [], 'archivedObjects': [], 'changedObjects': [], 'replacements': [],
        'inventory': inventory, 'materials': materials,
        'references': [{'path': PHOTO, 'url': ESTATE,
                        'sha256': hashlib.sha256((ROOT / PHOTO).read_bytes()).hexdigest(),
                        'resolution': [300, 400], 'photographCaptureDate': 'Unknown',
                        'coverage': 'Ground-floor entrance and one small four-light window only; no full height or roof'}],
        'boundedLookup': {
            'date': '2026-10-14', 'query': '"Connaught House" LSE facade Aldwych exterior photograph',
            'domains': ['lse.ac.uk'], 'searchCount': 1, 'newPhotosDownloaded': 0,
            'primarySources': [
                {'url': 'https://info.lse.ac.uk/staff/divisions/estates-division/Assets/Documents/Property-and-Space/LSE-Property-Handbook.pdf',
                 'finding': 'Repeats the known entrance crop; publication freshness is not capture-date evidence'},
                {'url': 'https://info.lse.ac.uk/staff/divisions/estates-division/Assets/Documents/Cap-Dev/23-0079-Campus-map-Long-term-maintenance-V5-FINAL.pdf',
                 'finding': 'Programme2022-23 lists stone modification works to Connaught facade; no complete elevation or finished-condition measurements'},
                {'url': 'https://www.lse.ac.uk/PBS/Study/Student-life-in-the-Department',
                 'finding': 'Departmental occupancy and common-room information; no registered whole-building exterior reference'},
            ],
            'conclusion': 'No evidence justifies replacing upper-storey rows, roof or complete envelope geometry this round',
        },
        'findings': [
            'Existing photographed entrance already distinguishes pale limestone upper casing, gray granite lower jambs, recessed vestibule and compact four-light overdoor window.',
            'Eight previously registered entrance panes retain single-surface geometry and inherited enclosure policy; no unsupported transparency increase.',
            'Full-height facade, roofline and side elevations remain architectural estimates, not verified current conditions.',
            'The2018 and2023 complete facade photographs previously attributed to CON belong to CLM; they are excluded.',
            'No minor roughness-only change is manufactured to stand in for unresolved whole-building accuracy.',
        ],
        'verification': {'baselineUnchanged': True, 'allOriginalObjectsPreserved': True,
                         'allGeometryUVTransformsAndBindingsPreserved': True,
                         'allMaterialValuesPreserved': True, 'allVisibilityPreserved': True,
                         'originalObjectCount': len(originals), 'visibleExteriorMeshCount': len(inventory),
                         'componentCreated': False, 'completeNativeSaved': False,
                         'previewsCreated': False,
                         'previewReason': 'Read-only review; duplicate unchanged renders add no evidence'},
        'limitations': [
            'Model preservation does not certify inherited geometric accuracy.',
            'The single source photograph cannot establish whole facade storey counts, spacing or calibrated color.',
            'No native or room geometry has been changed; unseen current layout is unresolved.',
        ],
    }
    assert set(originals) == {obj.name for obj in bpy.data.objects}
    assert all(object_fingerprint(bpy.data.objects[name]) == expected for name, expected in originals.items())
    assert all([bpy.data.objects[name].hide_render, bpy.data.objects[name].hide_viewport,
                bpy.data.objects[name].hide_get()] == expected for name, expected in visibility.items())
    assert all(material_state(bpy.data.materials[name]) == expected for name, expected in original_materials.items())
    assert hashlib.sha256(BASE.read_bytes()).hexdigest() == BASE_SHA
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'audit.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print('CON198_REVIEW_ONLY', len(inventory), len(materials), len(originals), flush=True)


if __name__ == '__main__':
    review()
