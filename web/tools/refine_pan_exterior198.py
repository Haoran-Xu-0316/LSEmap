"""Verify Pankhurst House without extrapolating a cropped lower facade.

Run in Blender's Text Editor. This bounded review is intentionally read-only:
cropped lower-front photos cannot establish a reliable new upper-facade correction.
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
OUT = ROOT / 'result/blender/pan-exterior198'
SOURCES = [
    ('result/blender/faw_exterior156/sources/plb-entrance.jpg',
     'https://www.architectureplb.com/sectors/universities-and-colleges/lse-towers',
     'Shared PAN/FAW entrance, canopy soffit and lower PAN windows only; 2018 completion is not photo date'),
    ('data/建筑图片/PAN_Pankhurst House/01_建筑实拍/exteriors_lse_estate_007.jpg',
     'https://info.lse.ac.uk/staff/divisions/estates-division/lse-estate/LSE-Estate',
     'Cropped lower-five-row main frontage: five broad independent window modules; top and roof absent'),
    ('data/documents/property_handbook.pdf',
     'https://info.lse.ac.uk/staff/divisions/estates-division/Assets/Documents/Property-and-Space/LSE-Property-Handbook.pdf',
     'Printed page31/PDF page33: PAN identification and lower frontage, no complete height or roof; capture date unknown'),
    ('data/collections/tower_photos_round4/images/PAN/realm_p47_0.jpg',
     'https://info.lse.ac.uk/staff/divisions/estates-division/Assets/Documents/2022-LSE-Public-Realm-Strategy.pdf',
     'Shared lower entry and court; 2022 document, photograph date unspecified'),
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
    for obj in bpy.data.collections['PAN_EXTERIOR'].all_objects:
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
    front = next(obj for obj in bpy.data.collections['PAN_EXTERIOR'].all_objects
                 if obj.type == 'MESH' and not obj.hide_render
                 and 'five_module_glass' in obj.name)
    # Each accepted pane is a disjoint closed eight-vertex box.
    adjacency = {vertex.index: set() for vertex in front.data.vertices}
    for edge in front.data.edges:
        a, b = edge.vertices
        adjacency[a].add(b)
        adjacency[b].add(a)
    groups, seen = [], set()
    for seed in adjacency:
        if seed in seen:
            continue
        pending, group = [seed], []
        seen.add(seed)
        while pending:
            index = pending.pop()
            group.append(index)
            for linked in adjacency[index] - seen:
                seen.add(linked)
                pending.append(linked)
        groups.append(group)
    assert len(groups) == 25 and all(len(group) == 8 for group in groups)
    rows = {}
    for group in groups:
        height = round(sum((front.matrix_world @ front.data.vertices[index].co).z for index in group) / len(group), 3)
        rows[height] = rows.get(height, 0) + 1
    assert len(rows) == 5 and set(rows.values()) == {5}
    glass = {name: state for name, state in materials.items() if 'glass' in name.lower()}
    assert glass and all(state['metallic'] == 0 for state in glass.values())
    report = {
        'version': 198, 'baseline': str(BASE.relative_to(ROOT)), 'baselineSha256': BASE_SHA,
        'status': 'review-only-no-new-independent-elevation-evidence',
        'targetCollection': 'PAN_EXTERIOR', 'componentPath': None, 'componentSha256': None,
        'addedObjects': [], 'archivedObjects': [], 'changedObjects': [], 'replacements': [],
        'geometry': geometry, 'materials': materials,
        'registeredLowerFrontage': {'object': front.name, 'closedPaneCount': len(groups), 'paneCountsByHeight': rows},
        'references': [{'path': path, 'url': url, 'scope': scope,
                        'sha256': hashlib.sha256((ROOT / path).read_bytes()).hexdigest(),
                        'photographCaptureDate': 'Unknown'} for path, url, scope in SOURCES],
        'boundedLookup': {
            'date': '2026-10-14', 'query': 'Pankhurst House LSE tower exterior Fawcett House architecture',
            'result': 'One bounded query returned the existing LSE Estate, official Property Handbook and public realm strategy. Handbook printed page31 was inspected locally: its photograph also clips the upper tower and roof.',
            'newReferencePhotosDownloaded': 0,
        },
        'findings': [
            'The five lower-front rows already contain25 independent broad glass modules, reflecting the official estate photograph rather than the former eight-light subdivision.',
            'Shared ground-level entry, two revolving doors, independent automatic door and yellow canopy underside are already represented and belong to PAN; FAW is served through that entrance.',
            'Available full-colour daylight and architect night photographs do not calibrate optical coefficients or justify changing already dielectric glass and inherited blinds.',
            'The official property handbook establishes PAN identity and1971construction, but its cropped photo does not prove total storey count, upper-window cadence, rooftop or hidden elevations.',
            'No facade or interior object is moved from FAW, and no unsupported upper geometry is added.',
        ],
        'verification': {'originalObjectCount': len(originals), 'visiblePANMeshCount': len(geometry),
                         'originalGeometryUVsAndBindingsPreserved': True,
                         'allVisibilityPreserved': True, 'baselineUnchanged': True,
                         'componentCreated': False, 'savedComponentReopened': False,
                         'previewsCreated': False, 'previewReason': 'No change: existing whole-building170 preview and source photographs inspected; identical before/after rerenders would add no evidence.'},
        'limitations': [
            'Read-only model checks verify preservation, not the inherited architectural accuracy of all PAN faces.',
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
    print('PAN198_REVIEW_ONLY', len(geometry), len(materials), flush=True)


if __name__ == '__main__':
    review()
