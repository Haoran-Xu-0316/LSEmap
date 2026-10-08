"""Place the existing Final Sale protective pane in front of the artwork.

The user's entrance photograph and archived front/side photographs show reflected
architecture across the mesh figures. Keep their geometry and the original pane
outline. The mounting clearance is estimated, not a measured installation depth.
This callable neither opens nor saves the campus source.
"""
from pathlib import Path
import hashlib
import json

import bpy
from mathutils import Vector
from refine_old_lettering185 import fit_support_transform

ROOT = Path(__file__).resolve().parents[2]
SOURCE = 'OLD_NEXT_EXTERIOR154_artwork_straight_lower_field'
TARGET = 'OLD_NEXT_ARTWORK_front_glazing'
ARTWORK = (
    'OLD_NEXT_EXTERIOR154_D5_finalsale84_containers',
    'OLD_NEXT_EXTERIOR154_D5_finalsale84_display_frame',
    'OLD_NEXT_EXTERIOR154_V111_lattice_products',
    'OLD_NEXT_EXTERIOR154_V111_lattice_figures',
)
MOUNTING_CLEARANCE = .035


def apply_old_artwork_glazing():
    if TARGET in bpy.data.objects:
        assert bpy.data.objects[SOURCE].hide_render
        assert not bpy.data.objects[TARGET].hide_render
        return {'alreadyApplied': True, 'addedObjects': [], 'archivedObjects': [], 'changedObjects': []}
    source = bpy.data.objects[SOURCE]
    assert not source.hide_render
    transform, error = fit_support_transform(
        bpy.data.objects['OLD_V103_curved_limestone_arch'],
        bpy.data.objects['OLD_V112_entry_V103_curved_limestone_arch'])
    frame = json.loads((ROOT / 'result/blender/stage52/old-houghton-audit.json').read_text())
    normal = (transform.to_3x3().inverted().transposed() @ Vector(frame['outward'])).normalized()
    artwork = [bpy.data.objects[name] for name in ARTWORK]
    assert all(not obj.hide_render for obj in artwork)
    nearest_art = max((obj.matrix_world @ vertex.co).dot(normal)
                      for obj in artwork for vertex in obj.data.vertices)
    depths = [(source.matrix_world @ vertex.co).dot(normal) for vertex in source.data.vertices]
    assert max(depths) - min(depths) < .00003, 'Protective pane must be planar'
    displacement = nearest_art + MOUNTING_CLEARANCE - min(depths)
    assert .1 < displacement < 1, 'Unexpected registration: inspect rather than guessing'
    pane = source.copy()
    pane.data = source.data.copy()
    pane.name = TARGET
    material = source.data.materials[0].copy()
    material.name = 'OLD_ARTWORK_clear_protective_glass'
    shader = material.node_tree.nodes['Principled BSDF']
    shader.inputs['Metallic'].default_value = 0
    shader.inputs['Roughness'].default_value = .14
    shader.inputs['Alpha'].default_value = .22
    shader.inputs['Transmission Weight'].default_value = .12
    material['webOpacity'] = .22
    material['opticalEvidence'] = 'Visual estimate: preserve clear mesh silhouettes behind protective glazing'
    pane.data.materials.clear()
    pane.data.materials.append(material)
    for collection in source.users_collection:
        collection.objects.link(pane)
    matrix = source.matrix_world.copy()
    matrix.translation += normal * displacement
    if pane.parent:
        pane.matrix_parent_inverse = pane.parent.matrix_world.inverted() @ matrix @ pane.matrix_basis.inverted()
    else:
        pane.matrix_world = matrix
    pane['originalObject'] = SOURCE
    pane['photographicEstimate'] = True
    pane['scope'] = 'Existing protective glazing moved ahead of the mesh artwork; no second transparent layer'
    source.hide_render = True
    source.hide_set(True)
    bpy.context.view_layer.update()
    paths = ['data/collections/old-user-reference/final-sale-front.jpg',
             'data/collections/old-user-reference/final-sale-side.jpg',
             'data/collections/old-exterior-2026/user-references/houghton-arch-masonry.png']
    return {
        'addedObjects': [TARGET], 'archivedObjects': [SOURCE], 'changedObjects': [],
        'normal': list(normal), 'translationMetres': displacement,
        'estimatedMountingClearanceMetres': MOUNTING_CLEARANCE,
        'registrationResidual': error,
        'references': [{'path': path, 'sha256': hashlib.sha256((ROOT / path).read_bytes()).hexdigest(),
                        'captureDate': 'unknown'} for path in paths],
        'limitations': ['Reference photos establish glass in front of the sculpture, not the precise setback.',
                       'Existing sculpture, stone arch and pane outline retained; glass opacity0.22 is a visual estimate.',
                       'Photographic approximation; complete OLD exterior and interior are not established by this correction.'],
    }
