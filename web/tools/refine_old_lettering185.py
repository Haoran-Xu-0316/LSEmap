"""Register OLD's lettering with the same geometry as its supporting masonry.

Run through the complete-scene assembler in Blender. Native text remains editable.
The existing plaque and arch meshes supply the registration. Names fit within
the retained stone piers; lettering scale and mounting clearance are estimates.
Colours, fonts, window openings and sculpture shapes remain unchanged.
"""
import hashlib
import json

import bpy
import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

PREFIX = 'OLD185_'
REGISTRATIONS = (
    {
        'originalSupport': 'OLD_V97_LSE_entrance_signs',
        'currentSupport': 'OLD_V112_entry_V97_LSE_entrance_signs',
        'labels': (
            ('OLD_V97_Old_Building_name', 'OLD_V112_entry_V97_Old_Building_name', 'left_name'),
            ('OLD_V97_Old_Building_name.001', 'OLD_V112_entry_V97_Old_Building_name.001', 'right_name'),
        ),
    },
    {
        'originalSupport': 'OLD_V103_curved_limestone_arch',
        'currentSupport': 'OLD_V112_entry_V103_curved_limestone_arch',
        'labels': (('OLD_V69_scroll_motto', 'OLD_V69_scroll_motto', 'scroll_motto'),),
    },
)


def font_signature(obj):
    """Include transforms and editable text properties omitted by mesh hashing."""
    curve = obj.data
    values = {
        'matrix': [list(row) for row in obj.matrix_world],
        'body': curve.body,
        'font': curve.font.name,
        'size': curve.size,
        'align': [curve.align_x, curve.align_y],
        'spacing': [curve.space_character, curve.space_word, curve.space_line],
        'extrude': curve.extrude,
        'bevel': [curve.bevel_depth, curve.bevel_resolution],
        'resolution': curve.resolution_u,
        'materials': [material.name if material else None for material in curve.materials],
    }
    return hashlib.sha256(json.dumps(values, sort_keys=True).encode()).hexdigest()


def fit_support_transform(original, current):
    """Recover and validate the complete affine transform from matched vertices."""
    assert original.type == current.type == 'MESH'
    assert len(original.data.vertices) == len(current.data.vertices)
    assert [tuple(face.vertices) for face in original.data.polygons] == [
        tuple(face.vertices) for face in current.data.polygons
    ]
    source = np.array([list(original.matrix_world @ vertex.co) + [1]
                       for vertex in original.data.vertices])
    target = np.array([list(current.matrix_world @ vertex.co)
                       for vertex in current.data.vertices])
    coefficients, _, rank, _ = np.linalg.lstsq(source, target, rcond=None)
    error = float(np.max(np.abs(source @ coefficients - target)))
    assert rank == 4 and error < .00002, (rank, error)
    transform = Matrix(np.vstack([coefficients.T, [0, 0, 0, 1]]).tolist())
    assert transform.to_3x3().determinant() > 0
    return transform, error


def seat_lettering(records):
    """Fit lettering to existing stone without crossing an adjacent window.

    Fit the names within their existing stone piers, then seat the
    back of the lettering 4mm from the nearest supporting stone surface.
    The clearance is a modelling tolerance, not a surveyed dimension.
    """
    bpy.context.view_layer.update()
    vertices, faces, stone = [], [], []
    for obj in bpy.data.collections['OLD_EXTERIOR'].all_objects:
        if obj.type != 'MESH' or obj.hide_render:
            continue
        offset = len(vertices)
        vertices.extend(obj.matrix_world @ vertex.co for vertex in obj.data.vertices)
        obj.data.calc_loop_triangles()
        for triangle in obj.data.loop_triangles:
            faces.append(tuple(offset + index for index in triangle.vertices))
            material = obj.data.materials[obj.data.polygons[triangle.polygon_index].material_index]
            stone.append(any(word in material.name.lower() for word in ('stone', 'ashlar')))
    facade = BVHTree.FromPolygons(vertices, faces, all_triangles=True)
    for record in records:
        target = bpy.data.objects[record['target']]
        matrix = target.matrix_world.copy()
        normal = (matrix.to_3x3().inverted().transposed() @ Vector((0, 0, 1))).normalized()
        tangent = matrix.to_3x3().col[0].normalized()
        scale = 1.0
        lateral = Vector((0, 0, 0))
        if record['target'].endswith(('left_name', 'right_name')):
            # Each pier is a separate closed cube within this support mesh.
            # Fit the name to that stone bay, never to the adjacent glazing.
            pier = bpy.data.objects['OLD_V112_entry_V97_entry_pier_backing']
            positions = [(pier.matrix_world @ vertex.co).dot(tangent) for vertex in pier.data.vertices]
            midpoint = (min(positions) + max(positions)) / 2
            side = matrix.translation.dot(tangent) > midpoint
            positions = [value for value in positions if (value > midpoint) == side]
            low, high = min(positions), max(positions)
            corners = [matrix @ Vector(point) for point in target.bound_box]
            text_low = min(point.dot(tangent) for point in corners)
            text_high = max(point.dot(tangent) for point in corners)
            scale = min(1.0, (high - low - .06) / (text_high - text_low))
            text_centre = (text_low + text_high) / 2
            pivot = matrix.translation.dot(tangent)
            lateral = tangent * ((low + high) / 2 - (pivot + (text_centre - pivot) * scale))
            matrix = matrix @ Matrix.Diagonal((scale, scale, 1, 1))
            matrix.translation += lateral
            target.matrix_parent_inverse = target.parent.matrix_world.inverted() @ matrix
            bpy.context.view_layer.update()
        evaluated = target.evaluated_get(bpy.context.evaluated_depsgraph_get())
        mesh = evaluated.to_mesh()
        points = [matrix @ vertex.co for vertex in mesh.vertices]
        rear = min(point.dot(normal) for point in points)
        backs = [point for point in points if point.dot(normal) - rear < .00002]
        evaluated.to_mesh_clear()
        hits = [facade.ray_cast(point + normal * .3, -normal, .6) for point in backs]
        assert all(hit[2] is not None and stone[hit[2]] for hit in hits), target.name
        # Cast from outside the facade: a rear-only ray misses stone in front.
        normal_shift = min(hit[3] for hit in hits) - .304
        translation = -normal * normal_shift
        matrix.translation += translation
        target.matrix_parent_inverse = target.parent.matrix_world.inverted() @ matrix
        record['seatingTranslation'] = list(lateral + translation)
        record['glyphScale'] = scale
        record['backVertexContactCount'] = len(backs)
    bpy.context.view_layer.update()


def apply_old_lettering185():
    targets = [PREFIX + label for item in REGISTRATIONS for _, _, label in item['labels']]
    if any(name in bpy.data.objects for name in targets):
        assert all(name in bpy.data.objects for name in targets)
        return {'alreadyApplied': True, 'addedObjects': [], 'archivedObjects': [], 'changedObjects': []}

    records = []
    archives = []
    for item in REGISTRATIONS:
        original_support = bpy.data.objects[item['originalSupport']]
        current_support = bpy.data.objects[item['currentSupport']]
        assert not current_support.hide_render
        transform, error = fit_support_transform(original_support, current_support)
        for original_name, obsolete_name, label in item['labels']:
            original = bpy.data.objects[original_name]
            obsolete = bpy.data.objects[obsolete_name]
            assert original.type == obsolete.type == 'FONT' and not obsolete.hide_render
            replacement = original.copy()
            replacement.data = original.data.copy()
            replacement.name = PREFIX + label
            replacement.data.name = replacement.name
            # Object location/rotation/scale cannot retain affine shear. Store
            # the registration in the parent inverse instead so editable text
            # follows its actual support without decomposition on save/reload.
            replacement.parent = current_support
            replacement.matrix_parent_inverse = (
                current_support.matrix_world.inverted() @ transform @ original.matrix_world
            )
            replacement.matrix_basis = Matrix.Identity(4)
            for collection in obsolete.users_collection:
                collection.objects.link(replacement)
            replacement.hide_render = False
            replacement.hide_set(False)
            obsolete.hide_render = True
            obsolete.hide_set(True)
            archives.append(obsolete.name)
            records.append({
                'source': original_name,
                'archived': obsolete_name,
                'target': replacement.name,
                'originalSupport': original_support.name,
                'currentSupport': current_support.name,
                'registrationMaximumError': error,
                'registration': [list(row) for row in transform],
                'body': original.data.body,
            })

    seat_lettering(records)
    return {
        'version': 185,
        'code': 'OLD',
        'alreadyApplied': False,
        'addedObjects': targets,
        'archivedObjects': archives,
        'changedObjects': [],
        'records': records,
        'sources': ['data/collections/old-user-reference/houghton-entrance-user-20261002.png'],
        'scope': 'Register the two building names and scroll motto with their existing supports. '
                 'Retain editable lettering, text, font, font and material. Fit names to their existing stone piers and seat every rear glyph vertex; lettering scale and clearance estimated.',
    }
