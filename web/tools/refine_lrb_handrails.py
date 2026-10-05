"""Correct the photographed LRB top-rail finish without changing its geometry.

Run apply_lrb_handrails() from Blender's Text Editor on an already loaded
campus. The callable never opens or saves a .blend. Supplier photographs have
unknown capture dates; this is a photographic finish correction, not a survey
of the current library or a measured optical material specification.
"""
from pathlib import Path
import array
import hashlib
import json
import bpy

ROOT = Path(__file__).resolve().parents[2]
HANDRAILS = (
    'LRB_gallery_circular_handrail',
    'LRB_spiral_continuous_handrail',
    'LRB_landing_handrail.001',
)
MATERIAL_NAME = 'LRB_brushed_silver_top_handrails'
REFERENCES = (
    'data/建筑图片/LRB_Lionel Robbins Building_Library/01_建筑实拍/library_photos_round2_library-r2-1b1d22ec09ce.jpg',
    'data/建筑图片/LRB_Lionel Robbins Building_Library/01_建筑实拍/library_photos_round2_library-r2-f73ef0243deb.jpg',
)


def geometry_fingerprint(obj):
    """Include transforms, topology, UVs and face assignments, but not slots."""
    digest = hashlib.sha256()
    digest.update(array.array('f', [value for row in obj.matrix_world for value in row]).tobytes())
    if obj.type == 'MESH':
        for data, field, kind, count in (
            (obj.data.vertices, 'co', 'f', 3),
            (obj.data.loops, 'vertex_index', 'i', 1),
            (obj.data.polygons, 'material_index', 'i', 1),
        ):
            values = array.array(kind, [0]) * (len(data) * count)
            data.foreach_get(field, values)
            digest.update(values.tobytes())
        for layer in obj.data.uv_layers:
            values = array.array('f', [0]) * (len(layer.data) * 2)
            layer.data.foreach_get('uv', values)
            digest.update(values.tobytes())
    return digest.hexdigest()


def material_bindings(obj):
    return tuple(slot.material.name if slot.material else None for slot in obj.material_slots)


def material_parameters(material):
    shader = material.node_tree.nodes.get('Principled BSDF')
    return {
        'name': material.name,
        'diffuseColor': list(material.diffuse_color),
        'baseColor': list(shader.inputs['Base Color'].default_value),
        'metallic': shader.inputs['Metallic'].default_value,
        'roughness': shader.inputs['Roughness'].default_value,
    }


def apply_lrb_handrails():
    """Return the audited change; only three existing material bindings change."""
    objects = [bpy.data.objects[name] for name in HANDRAILS]
    assert all(obj.type == 'MESH' and len(obj.material_slots) == 1 for obj in objects)
    current = {obj.material_slots[0].material.name for obj in objects}
    assert current in ({'ATRIA_dark_rail'}, {MATERIAL_NAME}), current
    original = bpy.data.materials['ATRIA_dark_rail']
    original_parameters = material_parameters(original)
    before_geometry = {obj.name: geometry_fingerprint(obj) for obj in bpy.data.objects}
    before_bindings = {obj.name: material_bindings(obj) for obj in bpy.data.objects}
    before_objects = set(before_geometry)

    material = bpy.data.materials.get(MATERIAL_NAME)
    if material is None:
        material = original.copy()
        material.name = MATERIAL_NAME
    material.diffuse_color = (.46, .49, .50, 1)
    shader = material.node_tree.nodes.get('Principled BSDF')
    assert not shader.inputs['Base Color'].is_linked
    shader.inputs['Base Color'].default_value = material.diffuse_color
    shader.inputs['Metallic'].default_value = .90
    shader.inputs['Roughness'].default_value = .32
    material['sourceScope'] = 'Supplier photos: silver top rails; capture dates unknown. Optical values are visual estimates.'
    for obj in objects:
        obj.material_slots[0].material = material

    assert set(bpy.data.objects.keys()) == before_objects
    assert all(geometry_fingerprint(obj) == before_geometry[obj.name] for obj in bpy.data.objects)
    assert all(material_bindings(obj) == before_bindings[obj.name]
               for obj in bpy.data.objects if obj.name not in HANDRAILS)
    assert material_parameters(original) == original_parameters
    changed = [name for name in HANDRAILS if material_bindings(bpy.data.objects[name]) != before_bindings[name]]
    audit = {
        'changedObjects': changed,
        'targetObjects': list(HANDRAILS),
        'addedObjects': [],
        'geometryAndTransformsPreserved': True,
        'otherMaterialBindingsPreserved': True,
        'sharedOriginalMaterialPreserved': True,
        'beforeFinish': original_parameters,
        'afterFinish': material_parameters(material),
        'sources': [{'path': path, 'sha256': hashlib.sha256((ROOT / path).read_bytes()).hexdigest()}
                    for path in REFERENCES],
        'sourceUrl': 'https://rainbowdesign.co.uk/project/london-school-of-economics/',
        'photographDate': 'unknown; one asset URL contains 2021/12',
        'limitations': ['Silver appearance supported by photographs; metal grade and optical values are estimated.',
                        'Historical photographs do not establish 2026 furnishing or finish condition.'],
        'nativeFileSaved': False,
    }
    out = ROOT / 'result/blender/stage159/lrb'
    out.mkdir(parents=True, exist_ok=True)
    (out / 'handrail-audit.json').write_text(json.dumps(audit, indent=2) + '\n')
    return audit
