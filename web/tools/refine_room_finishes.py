"""Apply two room-specific corrections to an already loaded Blender scene.

No files are opened or saved here. The archived official room photographs show
MAR.1.04's plain projection wall and OLD.4.10's pale, dark-framed door with a
long wine-coloured vision insert. Dimensions of the OLD insert remain estimated;
the existing room, door position, teaching equipment and seating are preserved.
"""
import bpy
from mathutils import Vector


MAR_PHOTO = 'data/collections/interiors/images/2f04d6322e38_MAR.1.04.jpg'
OLD_PHOTO = 'data/collections/interiors/images/8608c74c666d_OLD.4.10.jpg'


def _material(name, colour, roughness):
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    material.diffuse_color = (*colour, 1)
    shader = material.node_tree.nodes['Principled BSDF']
    shader.inputs['Base Color'].default_value = material.diffuse_color
    shader.inputs['Roughness'].default_value = roughness
    return material


def _frame_mesh(collection, material, door):
    vertices, faces = [], []

    def box(center, size):
        start = len(vertices)
        vertices.extend(tuple(center[i] + sign[i] * size[i] / 2 for i in range(3))
                        for sign in [(-1,-1,-1), (1,-1,-1), (1,1,-1), (-1,1,-1),
                                     (-1,-1,1), (1,-1,1), (1,1,1), (-1,1,1)])
        faces.extend(tuple(start + i for i in face) for face in
                     [(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)])

    points = [vertex.co for vertex in door.data.vertices]
    low = Vector(tuple(min(point[i] for point in points) for i in range(3)))
    high = Vector(tuple(max(point[i] for point in points) for i in range(3)))
    middle = (low + high) / 2
    # Three perimeter members avoid inventing a raised threshold. The face is
    # offset from the pale door surface, so no coplanar flicker is introduced.
    frame_width, frame_depth = .055, .055
    face_y = high.y + .016
    for x in [low.x - frame_width / 2, high.x + frame_width / 2]:
        box((x, face_y, middle.z), (frame_width, frame_depth, high.z - low.z))
    box((middle.x, face_y, high.z + frame_width / 2),
        (high.x - low.x + 2 * frame_width, frame_depth, frame_width))
    mesh = bpy.data.meshes.new('OLD_ROOM158_door_perimeter_mesh')
    mesh.from_pydata(vertices, [], faces)
    mesh.materials.append(material)
    mesh.update()
    obj = bpy.data.objects.new('OLD_ROOM158_door_perimeter', mesh)
    collection.objects.link(obj)
    obj.matrix_world = door.matrix_world.copy()
    obj['scope'] = 'OLD.4.10 photo-supported dark door perimeter; thickness estimated'
    obj['sourcePhoto'] = OLD_PHOTO
    return obj


def apply_room_finishes():
    """Return exactly the names and evidence for the two bounded corrections."""
    report = {'changedObjects': [], 'deletedObjects': [], 'addedObjects': [],
              'sources': [MAR_PHOTO, OLD_PHOTO],
              'limitations': ['Archived room photographs, not verified current layouts',
                              'OLD vision-insert dimensions and frame thickness estimated']}
    slats = bpy.data.objects.get('MAR_V22_TEACH_front_acoustic_slats_oak')
    wall = bpy.data.objects.get('MAR_V22_TEACH_front_wall_plaster')
    assert wall is not None, 'MAR plain projection wall is missing'
    if slats is not None:
        assert len(slats.data.vertices) == 456, 'Unexpected MAR projection-wall strip geometry'
        report['deletedObjects'].append(slats.name)
        bpy.data.objects.remove(slats, do_unlink=True)

    if bpy.data.objects.get('OLD_ROOM158_door_perimeter'):
        report['alreadyApplied'] = True
        return report
    door = bpy.data.objects.get('OLD_D5_ROOM18_door_white')
    vision = bpy.data.objects.get('OLD_D5_ROOM18_door_vision_black')
    assert door is not None and vision is not None, 'Expected OLD.4.10 door geometry is missing'
    assert len(door.data.vertices) == len(vision.data.vertices) == 8
    collection = bpy.data.collections['OLD_PUBLIC_INTERIOR_study']
    assert door in collection.all_objects.values() and vision in collection.all_objects.values()

    # Replace only this object's data/material, leaving shared ROOM18_black and
    # the pale leaf untouched. The official photo shows the inset almost the
    # full leaf height, whereas the previous model used a short black slot.
    source_points = [vertex.co.copy() for vertex in vision.data.vertices]
    low = Vector(tuple(min(point[i] for point in source_points) for i in range(3)))
    high = Vector(tuple(max(point[i] for point in source_points) for i in range(3)))
    middle = (low + high) / 2
    replacement = vision.data.copy()
    replacement.name = 'OLD_ROOM158_wine_vision_mesh'
    for vertex in replacement.vertices:
        vertex.co.x = middle.x + (vertex.co.x - middle.x) * (.18 / (high.x - low.x))
        vertex.co.z = 1.09 + (vertex.co.z - middle.z) * (1.72 / (high.z - low.z))
    wine = _material('OLD_ROOM158_wine_vision', (.105,.010,.014), .32)
    replacement.materials.clear()
    replacement.materials.append(wine)
    vision.data = replacement
    vision['sourcePhoto'] = OLD_PHOTO
    vision['scope'] = 'OLD.4.10 long wine-coloured vision insert; dimensions photo-estimated'
    report['changedObjects'].append(vision.name)
    dark = _material('OLD_ROOM158_dark_frame', (.012,.014,.015), .48)
    frame = _frame_mesh(collection, dark, door)
    report['addedObjects'].append(frame.name)
    return report
