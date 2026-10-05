"""Correct the CON.7.04 window wall using its paired archived plan and photograph.

Call apply_connaught_interiors() from Blender's Text Editor with the full campus
already loaded. This module never opens or saves a blend file. Room dimensions
are inherited estimates; the plan supports window orientation, not a measured
survey or a current whole-floor layout.
"""
import array
import hashlib
import bpy

PHOTO = 'data/collections/interiors/images/73b7be2bc2de_CON.7.04.jpg'
PLAN = 'data/collections/interiors/images/11f7e4c56390_CON.7.04.GIF'
PREFIX = 'CON_D5_ROOM18_'


def _fingerprint(obj):
    digest = hashlib.sha256(str([list(row) for row in obj.matrix_world]).encode())
    if obj.type == 'MESH':
        for data, field, kind, width in ((obj.data.vertices, 'co', 'f', 3),
                                         (obj.data.loops, 'vertex_index', 'i', 1),
                                         (obj.data.polygons, 'material_index', 'i', 1)):
            values = array.array(kind, [0]) * (len(data) * width)
            data.foreach_get(field, values)
            digest.update(values.tobytes())
        digest.update(str([m.name if m else None for m in obj.data.materials]).encode())
    return digest.hexdigest()


def _bounds(objects):
    points = [obj.matrix_world @ vertex.co for obj in objects for vertex in obj.data.vertices]
    return [[min(p[i] for p in points), max(p[i] for p in points)] for i in range(3)]


def _box_object(collection, name, material, center, size):
    points = [tuple(center[i] + sign[i] * size[i] / 2 for i in range(3))
              for sign in [(-1,-1,-1), (1,-1,-1), (1,1,-1), (-1,1,-1),
                           (-1,-1,1), (1,-1,1), (1,1,1), (-1,1,1)]]
    mesh = bpy.data.meshes.new(name + '_mesh')
    mesh.from_pydata(points, [], [(0,3,2,1), (4,5,6,7), (0,1,5,4),
                                    (1,2,6,5), (2,3,7,6), (3,0,4,7)])
    mesh.materials.append(material)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    obj['sourcePhoto'], obj['sourcePlan'] = PHOTO, PLAN
    obj['scope'] = 'Historical CON.7.04 window/endwall correction; inherited estimated dimensions'
    return obj


def apply_connaught_interiors():
    """Move the photographed window to the table's endwall; preserve furniture."""
    marker = bpy.data.objects.get('CON_ROOM160_rear_wood_wall')
    if marker:
        return {'alreadyApplied': True, 'changedObjects': [], 'addedObjects': []}
    collection = bpy.data.collections['CON_PUBLIC_INTERIOR_study']
    room_objects = list(collection.all_objects)
    before_bounds = _bounds(room_objects)
    affected = [PREFIX + suffix for suffix in [
        'wood_wall_wood', 'panel_rail_oak', 'panel_stile_oak', 'panel_moulding_oak',
        'window_header_wood', 'side_window_panel_wood', 'window_glass_glass',
        'window_mullion_white', 'window_rail_white', 'window_sill_white',
        'window_stile_white', 'roller_blind_plaster', 'display_black',
        'display_stand_steel']]
    assert all(bpy.data.objects.get(name) for name in affected)
    protected = {obj.name: _fingerprint(obj) for obj in bpy.data.objects if obj.name not in affected}
    # The window/header had been built across the long Y wall. Its entire
    # assembly moves to the short X endwall. Width adapts from 6.4 to 4.2m;
    # height, frame depth, room floor and table/chair positions are retained.
    endwall_offset = before_bounds[0][1] - before_bounds[1][1]
    width_ratio = -before_bounds[1][0] / before_bounds[0][1]
    for name in affected:
        obj = bpy.data.objects[name]
        mesh = obj.data.copy()
        obj.data = mesh
        for vertex in mesh.vertices:
            x, y, z = vertex.co
            if name.endswith('panel_moulding_oak'):
                # Existing short-endwall mouldings extended beyond its cutaway
                # edge. Clip their three horizontal ends to the actual wall.
                vertex.co.y = max(y, -1.0)
                continue
            if name.endswith('panel_stile_oak') and vertex.index >= 72:
                # Last four stile boxes belong to the unchanged left wood wall.
                continue
            if name.endswith(('display_black', 'display_stand_steel')):
                # Display width remains unchanged. Only its center and facing
                # follow the photographed window, avoiding stretched AV units.
                vertex.co = (endwall_offset + y, -(x + 1.7) + 1.7 * width_ratio, z)
            else:
                vertex.co = (endwall_offset + y, -x * width_ratio, z)
        mesh.update()
        obj['sourcePhoto'], obj['sourcePlan'] = PHOTO, PLAN
        obj['windowWallReview'] = 'Table long-axis endwall, historical paired plan/photo'
    wood = bpy.data.objects[PREFIX + 'wood_wall_wood'].data.materials[0]
    # The old window wall is now closed timber. The cutaway front remains open;
    # no door/corridor connection is guessed. Back thickness retains the sample's
    # former outer extent.
    wall = _box_object(collection, 'CON_ROOM160_rear_wood_wall', wood,
                       (0, 2.1, 1.5), (6.4, .16, 3.0))
    oak = bpy.data.objects[PREFIX + 'panel_moulding_oak'].data.materials[0]
    mouldings = []
    for z in [.13, .84, 2.75]:
        mouldings.append(_box_object(collection, 'CON_ROOM160_rear_panel_rail_' + str(z),
                                    oak, (0, 1.995, z), (6.4, .055, .055)))
    for index in range(9):
        x = -3.18 + index * 6.36 / 8
        mouldings.append(_box_object(collection, 'CON_ROOM160_rear_panel_stile_' + str(index),
                                    oak, (x, 1.995, 1.45), (.042, .055, 2.7)))
    # Consolidate matching timber mouldings into one draw group.
    vertices, faces = [], []
    for obj in mouldings:
        offset = len(vertices)
        vertices.extend(tuple(vertex.co) for vertex in obj.data.vertices)
        faces.extend(tuple(offset + i for i in polygon.vertices) for polygon in obj.data.polygons)
        mesh = obj.data
        bpy.data.objects.remove(obj, do_unlink=True)
        if not mesh.users:
            bpy.data.meshes.remove(mesh)
    mesh = bpy.data.meshes.new('CON_ROOM160_rear_panel_mouldings_mesh')
    mesh.from_pydata(vertices, [], faces)
    mesh.materials.append(oak)
    trim = bpy.data.objects.new('CON_ROOM160_rear_panel_mouldings', mesh)
    collection.objects.link(trim)
    trim['scope'] = 'Photo-supported long timber wall; inherited panel rhythm remains estimated'
    trim['sourcePhoto'] = PHOTO
    assert all(_fingerprint(bpy.data.objects[name]) == fingerprint
               for name, fingerprint in protected.items()), 'Protected campus objects changed'
    after_bounds = _bounds(collection.all_objects)
    assert all(abs(a - b) < .00001 for old, new in zip(before_bounds, after_bounds)
               for a, b in zip(old, new)), (before_bounds, after_bounds)
    return {'changedObjects': affected, 'addedObjects': [wall.name, trim.name],
            'protectedObjectsVerified': len(protected),
            'roomBoundsBefore': before_bounds, 'roomBoundsAfter': after_bounds,
            'sources': [PHOTO, PLAN],
            'limitations': ['Historical paired sources, not verified current layout',
                            'Room dimensions and window width remain estimates',
                            'No complete floor connection inferred'],
            'furnitureUnchanged': True, 'oppositeEndwallGeometryUnchanged': True,
            'oppositeEndwallMouldingsClippedToWall': True,
            'recommendedInteriorView': {'position': [-7, 5.7, 6],
                                        'target': [0, .75, 0], 'fov': 50}}
