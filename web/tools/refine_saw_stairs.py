"""Correct SAW stair nosings from round rods to photographed flat strips.

Call apply_saw_stairs() in Blender after loading the current campus model.
No file is opened or saved. The source photograph dates from an unverified
capture date; its 2017 upload path does not establish the current condition.
"""
import hashlib
import math
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
STRIPS_NAME = 'SAW_spiral_anti_slip_nosings'
TREADS_NAME = 'SAW_spiral_stair_treads'
REFERENCE = ROOT / 'data/collections/architecture_round5/images/SAW/SAW_saw_909_07.jpg'
# These finish dimensions are photographic estimates, not surveyed values.
STRIP_WIDTH = 0.055
EDGE_SETBACK = 0.060
STRIP_THICKNESS = 0.002
SURFACE_CLEARANCE = 0.0007
STEP_COUNT = 128


def apply_saw_stairs():
    """Replace one mesh in place, preserving its object, matrix and materials."""
    strips = bpy.data.objects[STRIPS_NAME]
    treads = bpy.data.objects[TREADS_NAME]
    old_mesh = strips.data
    assert len(old_mesh.vertices) == STEP_COUNT * 12, 'Expected original six-sided rods'
    assert len(treads.data.vertices) == STEP_COUNT * 8, 'Expected existing 128 treads'
    assert old_mesh.users == 1, 'Strip mesh must not be shared'
    matrix_before = strips.matrix_world.copy()
    material_names = [material.name for material in old_mesh.materials]
    inverse = strips.matrix_world.inverted()
    vertices, faces = [], []
    bottom_clearances = []
    for step in range(STEP_COUNT):
        rod = [strips.matrix_world @ vertex.co for vertex in old_mesh.vertices[step * 12:step * 12 + 12]]
        start = sum(rod[:6], Vector()) / 6
        end = sum(rod[6:], Vector()) / 6
        radial = (end - start).normalized()
        tread = [treads.matrix_world @ vertex.co for vertex in treads.data.vertices[step * 8:step * 8 + 8]]
        # The old wedge's next-angle edge establishes which side is inside.
        tangent = Vector((-radial.y, radial.x, 0)).normalized()
        if tangent.dot(tread[1] - tread[2]) > 0:
            tangent.negate()
        top = max(point.z for point in tread)
        bottom = top + SURFACE_CLEARANCE
        offset = len(vertices)
        for height in (bottom, bottom + STRIP_THICKNESS):
            for endpoint, lateral in ((start, -1), (end, -1), (end, 1), (start, 1)):
                point = endpoint + tangent * (EDGE_SETBACK + lateral * STRIP_WIDTH / 2)
                point.z = height
                vertices.append(inverse @ point)
        faces.extend(tuple(offset + index for index in face) for face in (
            (0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4),
            (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)))
        bottom_clearances.append(bottom - top)
    assert all(math.isfinite(value) for point in vertices for value in point)
    mesh = bpy.data.meshes.new(STRIPS_NAME + '_flat_strips')
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    for material in old_mesh.materials:
        mesh.materials.append(material)
    uv = mesh.uv_layers.new(name='MetricUV')
    for polygon in mesh.polygons:
        for loop_index in polygon.loop_indices:
            vertex = mesh.vertices[mesh.loops[loop_index].vertex_index].co
            uv.data[loop_index].uv = (vertex.x, vertex.y)
    assert len(mesh.vertices) == STEP_COUNT * 8
    assert len(mesh.polygons) == STEP_COUNT * 6
    strips.data = mesh
    bpy.data.meshes.remove(old_mesh)
    assert strips.matrix_world == matrix_before
    assert [material.name for material in mesh.materials] == material_names
    return {
        'changedObjects': [STRIPS_NAME], 'addedObjects': [],
        'stripCount': STEP_COUNT, 'vertices': len(mesh.vertices),
        'faces': len(mesh.polygons), 'materialNames': material_names,
        'stripWidthEstimate': STRIP_WIDTH, 'edgeSetbackEstimate': EDGE_SETBACK,
        'thicknessEstimate': STRIP_THICKNESS,
        'minimumSurfaceClearance': min(bottom_clearances),
        'reference': str(REFERENCE.relative_to(ROOT)),
        'referenceSha256': hashlib.sha256(REFERENCE.read_bytes()).hexdigest(),
        'source': 'https://www.photography909.co.uk/saw-swee-hocklse-gallery',
        'limitations': [
            'Capture date unknown; 2017 upload path does not establish 2026 condition.',
            'Strip finish dimensions are photographic estimates.',
            'Existing 128-step study arrangement retained; whole stair is not a measured reconstruction.',
        ],
    }
