"""Correct the historical SAL.G.01 projector without replacing its room layout.

Call apply_salisbury_projector() after loading the campus in Blender. No file is
opened or saved. The archived official photograph supports a charcoal projector
and black ceiling mount; colour and mount dimensions are visual estimates. The
cutaway has no ceiling slab, so the plate terminates on the existing wall-top
ceiling datum rather than inventing a surveyed ceiling or a taller room.
"""
import bpy
from mathutils import Vector

PHOTO = 'data/collections/interiors/images/32195c447bd2_SAL.G.01.jpg'
BODY = 'SAL_V20_INTA_projector_body_white'
MOUNT = 'SAL_ROOM160_projector_mount'
MATERIAL = 'SAL_ROOM160_projector_charcoal'


def _bounds(obj):
    points = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    return ([min(point[i] for point in points) for i in range(3)],
            [max(point[i] for point in points) for i in range(3)])


def _box(vertices, faces, center, size):
    start = len(vertices)
    vertices.extend(tuple(center[i] + sign[i] * size[i] / 2 for i in range(3))
                    for sign in [(-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),
                                 (-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1)])
    faces.extend(tuple(start + i for i in face) for face in
                 [(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)])


def apply_salisbury_projector():
    """Return the exact bounded changes for the shared campus assembler."""
    report = {'changedObjects': [], 'addedObjects': [], 'sources': [PHOTO],
              'limitations': ['Historical room photo; capture date unknown',
                              'Mount width and colour estimated',
                              'Ceiling slab omitted in retained cutaway; mounting datum follows wall tops']}
    body = bpy.data.objects.get(BODY)
    collection = bpy.data.collections.get('SAL_PUBLIC_INTERIOR_study')
    assert body is not None and collection is not None
    assert body.name in collection.all_objects and len(body.data.vertices) == 8
    if bpy.data.objects.get(MOUNT):
        assert [mat.name for mat in body.data.materials] == [MATERIAL]
        report['alreadyApplied'] = True
        return report
    wall_names = ['SAL_V20_INTA_back_wall_plaster', 'SAL_V20_INTA_left_wall_plaster']
    ceiling_levels = [_bounds(bpy.data.objects[name])[1][2] for name in wall_names]
    assert max(ceiling_levels) - min(ceiling_levels) < .001
    ceiling = sum(ceiling_levels) / len(ceiling_levels)
    low, high = _bounds(body)
    assert ceiling > high[2] + .05
    center_x, center_y = [(low[i] + high[i]) / 2 for i in range(2)]
    material = bpy.data.materials.new(MATERIAL)
    material.use_nodes = True
    material.diffuse_color = (.055, .058, .055, 1)
    shader = material.node_tree.nodes['Principled BSDF']
    shader.inputs['Base Color'].default_value = material.diffuse_color
    shader.inputs['Roughness'].default_value = .64
    shader.inputs['Metallic'].default_value = 0
    # An owned mesh binding prevents shared pale furniture material mutation.
    mesh = body.data.copy()
    mesh.name = 'SAL_ROOM160_projector_body_mesh'
    mesh.materials.clear()
    mesh.materials.append(material)
    body.data = mesh
    body['sourcePhoto'] = PHOTO
    vertices, faces = [], []
    plate_depth = .018
    plate_bottom = ceiling - plate_depth
    _box(vertices, faces, (center_x, center_y, (high[2] + plate_bottom) / 2),
         (.032, .032, plate_bottom - high[2]))
    _box(vertices, faces, (center_x, center_y, ceiling - plate_depth / 2),
         (.14, .11, plate_depth))
    mount_mesh = bpy.data.meshes.new(MOUNT + '_mesh')
    mount_mesh.from_pydata(vertices, [], faces)
    mount_mesh.materials.append(material)
    mount_mesh.update()
    mount = bpy.data.objects.new(MOUNT, mount_mesh)
    collection.objects.link(mount)
    mount['sourcePhoto'] = PHOTO
    mount['ceilingDatumSource'] = ','.join(wall_names)
    mount['ceilingDatumEstimated'] = ceiling
    mount['scope'] = 'Photo-informed mount on retained wall-top ceiling datum; not surveyed'
    mount_low, mount_high = _bounds(mount)
    assert abs(mount_low[2] - high[2]) < .00001
    assert abs(mount_high[2] - ceiling) < .00001
    report.update(changedObjects=[BODY], addedObjects=[MOUNT],
                  ceilingDatum=ceiling, projectorBounds=[low, high],
                  mountBounds=[mount_low, mount_high])
    return report
