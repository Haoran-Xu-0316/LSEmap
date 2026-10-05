"""Add photographed CKK frontage rainwater fittings to the loaded campus.

Call apply_ckk_rainwater() in Blender's Text Editor after opening the latest
campus. This module neither opens nor saves a model. Geometry covers visible
frontage runs only; pipe diameter, clamp spacing and registration are estimates.
"""
import math
import bpy
from mathutils import Vector

SOURCE_PHOTO = 'data/建筑图片/CKK_Cheng Kin Ku Building/01_建筑实拍/exteriors_ckk_grimshaw_010.jpg'
SOURCE_URL = 'https://grimshaw.global/projects/education-and-science/london-school-of-economics-new-academic-building/'
PREFIX = 'CKK_RAINWATER159_'


class RainwaterBatch:
    """Collect one component family in one mesh, with explicit smooth sides."""

    def __init__(self, suffix, material, collection):
        self.name = PREFIX + suffix
        self.material, self.collection = material, collection
        self.vertices, self.faces, self.smooth_faces = [], [], set()
        self.component_count = 0

    def add(self, vertices, faces, smooth=()):
        start, face_start = len(self.vertices), len(self.faces)
        self.vertices.extend(vertices)
        self.faces.extend(tuple(start + i for i in face) for face in faces)
        self.smooth_faces.update(face_start + i for i in smooth)
        self.component_count += 1

    def tube(self, start, end, radius, sides=12):
        direction = (end - start).normalized()
        first = direction.cross(Vector((1, 0, 0)))
        if first.length < .01:
            first = direction.cross(Vector((0, 1, 0)))
        first.normalize()
        second = direction.cross(first).normalized()
        vertices = [point + radius * (first * math.cos(i * math.tau / sides) +
                    second * math.sin(i * math.tau / sides))
                    for point in (start, end) for i in range(sides)]
        faces = [(i, (i + 1) % sides, (i + 1) % sides + sides, i + sides)
                 for i in range(sides)]
        faces.extend((tuple(reversed(range(sides))), tuple(range(sides, 2 * sides))))
        self.add(vertices, faces, range(sides))

    def finish(self):
        mesh = bpy.data.meshes.new(self.name)
        mesh.from_pydata(self.vertices, [], self.faces)
        mesh.materials.append(self.material)
        mesh.update()
        for i in self.smooth_faces:
            mesh.polygons[i].use_smooth = True
        obj = bpy.data.objects.new(self.name, mesh)
        self.collection.objects.link(obj)
        obj['component_count'] = self.component_count
        obj['source_photo'] = SOURCE_PHOTO
        obj['source_url'] = SOURCE_URL
        obj['capture_date'] = 'unknown'
        obj['scope'] = 'Two visible frontage rainwater runs; dimensions and clamp spacing photo-estimated. No underground, roof or unseen drainage routing.'
        return obj


def apply_ckk_rainwater():
    """Return an audit record; preserve every existing object and material."""
    names = [PREFIX + family for family in ('downpipes', 'hoppers', 'clamps')]
    assert not any(bpy.data.objects.get(name) for name in names), 'Rainwater fittings already applied'
    collection = bpy.data.collections['CKK_EXTERIOR']
    stone = bpy.data.objects['CKK_NEXT_ENVELOPE_masonry']
    normal = Vector((math.cos(math.radians(22)), math.sin(math.radians(22)), 0))
    axis = Vector((-normal.y, normal.x, 0))
    origin = Vector((-110.49102024587766, 77.56014819690478, 0))
    # Derive the central wall plane from its actual surviving mesh vertices,
    # excluding the projecting wings and the recessed window surfaces.
    front_points = [stone.matrix_world @ vertex.co for vertex in stone.data.vertices
                    if abs((stone.matrix_world @ vertex.co - origin).dot(axis)) < 8.85]
    front_plane = max((point - origin).dot(normal) for point in front_points)
    assert 22.8 < front_plane < 23.1, front_plane
    def point(depth, horizontal, height):
        return origin + normal * depth + axis * horizontal + Vector((0, 0, height))

    material = bpy.data.materials.new(PREFIX + 'painted_iron')
    material.use_nodes = True
    material.diffuse_color = (.026, .030, .031, 1)
    shader = material.node_tree.nodes['Principled BSDF']
    shader.inputs['Base Color'].default_value = material.diffuse_color
    shader.inputs['Metallic'].default_value = 0
    shader.inputs['Roughness'].default_value = .72
    batches = {family: RainwaterBatch(family, material, collection)
               for family in ('downpipes', 'hoppers', 'clamps')}
    # Both photographed upper fittings step slightly towards screen-right.
    # Terminate the visible runs above the ground; do not infer drain outlets.
    radius = .065
    for horizontal in (-8.9, 8.9):
        adjacent = [stone.matrix_world @ vertex.co for vertex in stone.data.vertices
                    if abs((stone.matrix_world @ vertex.co - origin).dot(axis) - horizontal) < .35]
        mounting_plane = max((vertex - origin).dot(normal) for vertex in adjacent)
        depth = mounting_plane + .14
        path = [point(depth, horizontal, .6), point(depth, horizontal, 18.9),
                point(depth, horizontal + .27, 19.28),
                point(depth, horizontal + .27, 19.66)]
        for start, end in zip(path, path[1:]):
            batches['downpipes'].tube(start, end, radius)
        # An open-topped tapered hopper expresses only its photographed shell.
        lower, upper = 19.60, 19.93
        vertices = [point(depth + dx, horizontal + .27 + dy, height)
                    for height, half_width, half_depth in ((lower, .065, .065), (upper, .17, .12))
                    for dx, dy in ((-half_depth, -half_width), (-half_depth, half_width),
                                  (half_depth, half_width), (half_depth, -half_width))]
        batches['hoppers'].add(vertices, [(0, 1, 5, 4), (1, 2, 6, 5),
                                          (2, 3, 7, 6), (3, 0, 4, 7)])
        # Four visible-height brackets per run; spacing is an explicit estimate.
        for height in (4.15, 8.65, 13.1, 17.6):
            batches['clamps'].tube(point(depth, horizontal, height - .028),
                                   point(depth, horizontal, height + .028), .078)
            batches['clamps'].tube(point(mounting_plane + .015, horizontal, height),
                                   point(depth - radius, horizontal, height), .024, 8)
    added = [batch.finish() for batch in batches.values()]
    for layer in bpy.context.scene.view_layers:
        layer.update()
    return {'addedObjects': [obj.name for obj in added], 'changedObjects': [],
            'sourcePhotos': [SOURCE_PHOTO], 'sourceUrl': SOURCE_URL,
            'frontPlaneDerivedFromNative': front_plane, 'downpipeRuns': 2,
            'upperOffsetRuns': 2, 'hoppers': 2, 'clamps': 8,
            'dimensionsArePhotoEstimates': True, 'unseenDrainRoutesAdded': False,
            'components': {obj.name: {'vertices': len(obj.data.vertices),
                                    'faces': len(obj.data.polygons),
                                    'pieces': obj['component_count']} for obj in added}}
