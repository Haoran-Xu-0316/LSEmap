"""Restore three real apertures in the photographed Garrick timber chair backs.

Call apply_garrick_chairs() in Blender's Text Editor on the loaded campus.
No .blend is opened or saved. Furniture count, layout, outer bounds and finish
are retained. Aperture dimensions are photo estimates; capture date is unknown.
"""
from pathlib import Path
import array
import hashlib
import json
import bpy
import bmesh
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
OBJECT_NAME = 'COL_V20_INTA_chair_back_oak'
REFERENCE = 'data/collections/campus_photos_round2/images/COL/COL_food_outlets_11.png'


def fingerprint(obj):
    digest = hashlib.sha256()
    digest.update(array.array('f', [v for row in obj.matrix_world for v in row]).tobytes())
    if obj.type == 'MESH':
        for records, field, kind, count in ((obj.data.vertices, 'co', 'f', 3),
                (obj.data.loops, 'vertex_index', 'i', 1),
                (obj.data.polygons, 'material_index', 'i', 1)):
            values = array.array(kind, [0]) * (len(records) * count)
            records.foreach_get(field, values)
            digest.update(values.tobytes())
        for layer in obj.data.uv_layers:
            values = array.array('f', [0]) * (len(layer.data) * 2)
            layer.data.foreach_get('uv', values)
            digest.update(values.tobytes())
    digest.update(str(tuple(slot.material.name if slot.material else None
                            for slot in obj.material_slots)).encode())
    return digest.hexdigest()


def perforated_back(corners):
    """Build one connected, closed shell with three through holes, no overlaps."""
    center = sum(corners, Vector()) / 8
    vertical = Vector((0, 0, 1))
    horizontal = [b - a for a in corners for b in corners
                  if abs((b-a).z) < 1e-6 and abs((b-a).length - .46) < 1e-5]
    assert horizontal, 'Expected retained 0.46m back width'
    axis = horizontal[0].normalized()
    if axis.x < -1e-6 or (abs(axis.x) < 1e-6 and axis.y < 0):
        axis.negate()
    depth_axis = vertical.cross(axis)
    width = max((p-center).dot(axis) for p in corners) * 2
    depth = max((p-center).dot(depth_axis) for p in corners) * 2
    height = max((p-center).z for p in corners) * 2
    assert abs(width-.46) < 1e-5 and abs(depth-.065) < 1e-5
    assert abs(height-.49) < 1e-5
    hole_width = .055
    hole_bottom, hole_top = .100, .155  # local height relative to retained centre
    xs = [-width/2]
    for x in (-.10, 0, .10):
        xs.extend((x-hole_width/2, x+hole_width/2))
    xs.append(width/2)
    zs = [-height/2, hole_bottom, hole_top, height/2]
    occupied = {(i, j) for i in range(7) for j in range(3)
                if not (j == 1 and i in (1, 3, 5))}
    vertices, faces, index = [], [], {}

    def vertex(i, j, side):
        key = (i, j, side)
        if key not in index:
            index[key] = len(vertices)
            vertices.append(tuple(center + axis*xs[i] + vertical*zs[j]
                                  + depth_axis*(depth/2 if side else -depth/2)))
        return index[key]

    for i, j in sorted(occupied):
        for side in (0, 1):
            faces.append(tuple(vertex(x, z, side) for x, z in
                              ((i,j), (i+1,j), (i+1,j+1), (i,j+1))))
        boundaries = [((i-1,j), (i,j), (i,j+1)),
                      ((i+1,j), (i+1,j), (i+1,j+1)),
                      ((i,j-1), (i,j), (i+1,j)),
                      ((i,j+1), (i,j+1), (i+1,j+1))]
        for neighbour, a, b in boundaries:
            if neighbour not in occupied:
                faces.append((vertex(*a,0), vertex(*b,0),
                              vertex(*b,1), vertex(*a,1)))
    return vertices, faces, {'center': list(center), 'widthAxis': list(axis),
                            'bounds': [width, depth, height]}


def topology(mesh):
    bm = bmesh.new()
    bm.from_mesh(mesh)
    assert all(edge.is_manifold for edge in bm.edges)
    pending = set(bm.verts)
    components = []
    while pending:
        reached = {pending.pop()}
        stack = list(reached)
        while stack:
            for edge in stack.pop().link_edges:
                for vertex in edge.verts:
                    if vertex in pending:
                        pending.remove(vertex)
                        reached.add(vertex)
                        stack.append(vertex)
        edges = {e for v in reached for e in v.link_edges}
        faces = {f for v in reached for f in v.link_faces}
        components.append(len(reached) - len(edges) + len(faces))
    bm.free()
    assert len(components) == 24 and set(components) == {-4}, components
    return {'backs': 24, 'throughApertures': 72, 'closedManifold': True,
            'componentEulerCharacteristic': -4}


def preview(out):
    """Private inspection render; remove all temporary preview datablocks."""
    previous = bpy.context.window.scene
    scene = bpy.data.scenes.new('GARRICK_CHAIRS_PRIVATE_PREVIEW')
    camera_data = bpy.data.cameras.new('GARRICK_CHAIRS_PRIVATE_CAMERA')
    camera = bpy.data.objects.new(camera_data.name, camera_data)
    try:
        for name in (OBJECT_NAME, 'COL_V20_INTA_chair_seat_oak',
                     'COL_V20_INTA_chair_legs_steel'):
            scene.collection.objects.link(bpy.data.objects[name])
        scene.collection.objects.link(camera)
        scene.camera = camera
        camera.location = (7, -12, 6)
        camera.rotation_euler = (Vector((0, -.4, .55))-camera.location).to_track_quat('-Z','Y').to_euler()
        camera_data.type = 'ORTHO'
        camera_data.ortho_scale = 11
        scene.render.engine = 'BLENDER_WORKBENCH'
        scene.display.shading.light = 'STUDIO'
        scene.display.shading.color_type = 'MATERIAL'
        scene.display.shading.show_shadows = True
        scene.display.shading.show_cavity = True
        scene.render.resolution_x = 1200
        scene.render.resolution_y = 850
        scene.render.resolution_percentage = 100
        scene.render.image_settings.file_format = 'PNG'
        scene.render.filepath = str(out/'chair-apertures.png')
        bpy.context.window.scene = scene
        bpy.ops.render.render(write_still=True)
    finally:
        bpy.context.window.scene = previous
        bpy.data.scenes.remove(scene)
        bpy.data.objects.remove(camera, do_unlink=True)
        bpy.data.cameras.remove(camera_data)


def apply_garrick_chairs():
    obj = bpy.data.objects[OBJECT_NAME]
    before = {o.name: fingerprint(o) for o in bpy.data.objects}
    if obj.get('garrickThreeApertures'):
        return {'changedObjects': [], 'addedObjects': [], 'verification': topology(obj.data)}
    old = obj.data
    assert len(old.vertices) == 192 and len(old.polygons) == 144
    assert old.users == 1
    materials = list(old.materials)
    old_bounds = [(min(v.co[k] for v in old.vertices), max(v.co[k] for v in old.vertices))
                  for k in range(3)]
    vertices, faces, records = [], [], []
    for start in range(0, 192, 8):
        corners = [v.co.copy() for v in old.vertices[start:start+8]]
        local, polygons, record = perforated_back(corners)
        for axis in range(3):
            assert abs(min(p[axis] for p in corners)-min(p[axis] for p in local)) < 1e-6
            assert abs(max(p[axis] for p in corners)-max(p[axis] for p in local)) < 1e-6
        offset = len(vertices)
        vertices.extend(local)
        faces.extend(tuple(offset+i for i in face) for face in polygons)
        records.append(record)
    mesh = bpy.data.meshes.new('COL_Garrick_chair_backs_three_apertures')
    mesh.from_pydata(vertices, [], faces)
    for material in materials:
        mesh.materials.append(material)
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(mesh)
    bm.free()
    obj.data = mesh
    bpy.data.meshes.remove(old)
    obj['garrickThreeApertures'] = True
    obj['apertureScope'] = 'Three square cutouts from undated official Garrick photo; sizes estimated, layout/count retained'
    verified = topology(mesh)
    new_bounds = [(min(v.co[k] for v in mesh.vertices), max(v.co[k] for v in mesh.vertices))
                  for k in range(3)]
    assert all(abs(a-b) < 1e-6 for pair, other in zip(old_bounds,new_bounds)
               for a,b in zip(pair,other))
    changed = [o.name for o in bpy.data.objects if fingerprint(o) != before[o.name]]
    assert changed == [OBJECT_NAME], changed
    out = ROOT/'result/blender/stage160/col'
    out.mkdir(parents=True, exist_ok=True)
    preview(out)
    assert set(before) == {o.name for o in bpy.data.objects}
    assert all(fingerprint(o) == before[o.name] for o in bpy.data.objects if o != obj)
    audit = {'changedObjects': changed, 'addedObjects': [], 'verification': verified,
             'retainedBounds': new_bounds, 'retainedBacks': records,
             'holeDimensionsMeters': [.055, .055], 'holeCentersLocalWidth': [-.1, 0, .1],
             'source': REFERENCE, 'sourceUrl': 'https://food.lse.ac.uk/outlets',
             'sourceSha256': hashlib.sha256((ROOT/REFERENCE).read_bytes()).hexdigest(),
             'retrievedDate': '2026-09-12', 'captureDate': 'unknown',
             'scope': 'Photographed chair detail only; 24 retained chairs are not a surveyed capacity; room layout and finish unchanged'}
    (out/'garrick-chairs-audit.json').write_text(json.dumps(audit, indent=2)+'\n')
    return audit
