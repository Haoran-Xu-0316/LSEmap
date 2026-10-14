"""Verify Fawcett House without transferring PAN entrance evidence upstairs.

Run in Blender's Text Editor. This bounded review is intentionally read-only:
no independent full-height FAW photograph establishes a reliable new correction.
"""
from pathlib import Path
import hashlib
import json
import sys

import bpy

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'web/tools'))
from integrate_exterior_round194 import object_fingerprint

BASE = ROOT / 'result/blender/LSE_campus_detailed_v196.blend'
BASE_SHA = '1c1185738e796221c6d30f06aec906b99829cad4867fbb2bced77d657afc298b'
OUT = ROOT / 'result/blender/faw-exterior197'
SOURCES = [
    ('result/blender/faw_exterior156/sources/plb-entrance.jpg',
     'https://www.architectureplb.com/sectors/universities-and-colleges/lse-towers',
     'Shared PAN/FAW entrance only; not independent FAW tower elevation or crown'),
    ('data/建筑图片/FAW_Fawcett House/01_建筑实拍/exteriors_lse_estate_007.jpg',
     'https://info.lse.ac.uk/staff/divisions/estates-division/lse-estate/LSE-Estate',
     'Existing official shared-entry photograph; cannot register independent upper FAW bays'),
]


def review():
    assert hashlib.sha256(BASE.read_bytes()).hexdigest() == BASE_SHA
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    bpy.context.window.scene = bpy.data.scenes['00_CAMPUS_COMPLETE']
    for scene in bpy.data.scenes:
        for layer in scene.view_layers:
            layer.update()
    originals = {o.name: object_fingerprint(o) for o in bpy.data.objects}
    visibility = {o.name: [o.hide_render, o.hide_viewport, o.hide_get()] for o in bpy.data.objects}
    materials, geometry = {}, []
    for obj in bpy.data.collections['FAW_EXTERIOR'].all_objects:
        if obj.type != 'MESH' or obj.hide_render or not obj.data.vertices:
            continue
        positions = [obj.matrix_world @ vertex.co for vertex in obj.data.vertices]
        geometry.append({
            'object': obj.name, 'fingerprint': originals[obj.name],
            'vertices': len(obj.data.vertices), 'polygons': len(obj.data.polygons),
            'bounds': [[min(p[i] for p in positions) for i in range(3)],
                       [max(p[i] for p in positions) for i in range(3)]],
            'materialSlots': [m.name if m else None for m in obj.data.materials],
        })
        for material in obj.data.materials:
            if not material or material.name in materials or not material.use_nodes:
                continue
            node = next((n for n in material.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
            if node is None:
                continue
            materials[material.name] = {
                'baseColor': list(node.inputs['Base Color'].default_value),
                'baseColorLinked': node.inputs['Base Color'].is_linked,
                'metallic': node.inputs['Metallic'].default_value,
                'roughness': node.inputs['Roughness'].default_value,
                'transmission': node.inputs['Transmission Weight'].default_value,
                'alpha': node.inputs['Alpha'].default_value,
                'webOpacity': material.get('webOpacity'),
            }
    assert geometry
    glass = {name: state for name, state in materials.items() if 'glass' in name.lower()}
    assert glass and all(state['metallic'] == 0 for state in glass.values())
    report = {
        'version': 197, 'baseline': str(BASE.relative_to(ROOT)), 'baselineSha256': BASE_SHA,
        'status': 'review-only-no-new-independent-elevation-evidence',
        'targetCollection': 'FAW_EXTERIOR', 'componentPath': None, 'componentSha256': None,
        'addedObjects': [], 'archivedObjects': [], 'changedObjects': [], 'replacements': [],
        'geometry': geometry, 'materials': materials,
        'references': [{'path': path, 'url': url, 'scope': scope,
                        'sha256': hashlib.sha256((ROOT / path).read_bytes()).hexdigest(),
                        'photographCaptureDate': 'Unknown'} for path, url, scope in SOURCES],
        'boundedLookup': {
            'date': '2026-10-14', 'query': 'Fawcett House LSE Tower Two building exterior facade photograph',
            'result': 'One query returned existing LSE Estate, property handbook, AccessAble and public realm sources; no new attributable independent full-height FAW elevation.',
            'newReferencePhotosDownloaded': 0,
        },
        'findings': [
            'Current glazing already has dielectric metallic0 response; no inherited bare-metal glass defect remains.',
            'Existing reflective upper glass, opaque curtains and pale metal frames are retained; changing opacity from a shared PAN entrance photograph would overstate evidence.',
            'Available architect and official images establish the shared ground-level entrance, which belongs to PAN and is retained unchanged.',
            'Independent complete upper elevations and roof remain unverified; no speculative window-count, height, rooftop or material recolouring is introduced.',
        ],
        'verification': {'originalObjectCount': len(originals), 'visibleFAWMeshCount': len(geometry),
                         'originalGeometryUVsAndBindingsPreserved': True,
                         'allVisibilityPreserved': True, 'baselineUnchanged': True,
                         'componentCreated': False, 'savedComponentReopened': False,
                         'previewsCreated': False, 'previewReason': 'No geometry or finish changed; duplicate before/after renders would add no comparison evidence.'},
        'limitations': [
            'Read-only model checks verify preservation, not the inherited architectural accuracy of all FAW faces.',
            'No newly measured dimensions, calibrated optical coefficients or current complete interiors are claimed.',
            '2018 project completion is not an individual photograph capture date.',
        ],
    }
    assert all(object_fingerprint(bpy.data.objects[name]) == value for name, value in originals.items())
    assert all([bpy.data.objects[name].hide_render, bpy.data.objects[name].hide_viewport,
                bpy.data.objects[name].hide_get()] == value for name, value in visibility.items())
    assert hashlib.sha256(BASE.read_bytes()).hexdigest() == BASE_SHA
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'audit.json').write_text(json.dumps(report, indent=2) + '\n')
    print('FAW197_REVIEW_ONLY', len(geometry), len(materials), flush=True)


if __name__ == '__main__':
    review()
