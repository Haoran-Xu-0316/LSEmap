"""Refine SAR's four photographed street windows and visible vertical blinds.

The estate photograph and 2018 street photograph show pale vertical shading
behind the dark curved-head frames. Slat spacing, setback and optical values are
estimates. This window treatment does not reconstruct the rooms behind it.
"""
from pathlib import Path
import json
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
SOURCE = 'GLASS181_SAR_D5_front119_glass'
TARGET = 'SAR186_street_glazing'
SHADING = 'SAR186_street_blinds'
BACKING = 'SAR186_window_shadow'


def facade_registration():
    record = json.loads((ROOT / 'result/blender/stage119/sardinia-frontage-audit.json').read_text())
    return record, *(Vector(record[key]) for key in ('origin', 'axis', 'normal'))


def material(name, colour, roughness):
    result = bpy.data.materials.new(name)
    result.use_nodes = True
    result.diffuse_color = (*colour, 1)
    shader = result.node_tree.nodes['Principled BSDF']
    shader.inputs['Base Color'].default_value = result.diffuse_color
    shader.inputs['Roughness'].default_value = roughness
    shader.inputs['Metallic'].default_value = 0
    return result


def mesh_parts(mesh):
    neighbours = [set() for _ in mesh.vertices]
    for edge in mesh.edges:
        a, b = edge.vertices
        neighbours[a].add(b)
        neighbours[b].add(a)
    visited = set()
    for seed in range(len(mesh.vertices)):
        if seed in visited:
            continue
        pending, part = [seed], set()
        while pending:
            index = pending.pop()
            if index in visited:
                continue
            visited.add(index)
            part.add(index)
            pending.extend(neighbours[index] - visited)
        yield part


def apply_sar_glazing186():
    names = [TARGET, SHADING, BACKING]
    if any(name in bpy.data.objects for name in names):
        assert all(name in bpy.data.objects for name in names)
        return {'alreadyApplied': True, 'addedObjects': [], 'archivedObjects': [], 'changedObjects': []}
    registration, origin, axis, normal = facade_registration()
    windows = [item for item in registration['openings'] if item['kind'] == 'ground-arch']
    assert len(windows) == 4
    collection = bpy.data.collections['SAR_EXTERIOR']
    source = bpy.data.objects[SOURCE]
    assert not source.hide_render
    copy = source.copy()
    copy.data = source.data.copy()
    copy.name = TARGET
    copy.data.name = TARGET
    collection.objects.link(copy)

    glazing = material('SAR186_clear_street_glass', (.18, .22, .205), .16)
    glazing.node_tree.nodes['Principled BSDF'].inputs['Transmission Weight'].default_value = .65
    glazing['webOpacity'] = .38
    glazing['webClosedGlazing'] = True
    slot = len(copy.data.materials)
    copy.data.materials.append(glazing)
    selected = []
    for part in mesh_parts(copy.data):
        centre = sum((copy.matrix_world @ copy.data.vertices[i].co for i in part), Vector()) / len(part)
        x = (centre - origin).dot(axis)
        window = next((item for item in windows if abs(x - item['x']) < .001 and
                       abs(centre.z - (item['low'] + item['high']) / 2) < .001), None)
        if not window:
            continue
        assert len(part) == 8
        for face in copy.data.polygons:
            if set(face.vertices) <= part:
                face.material_index = slot
        selected.append({'bay': window['bay'], 'vertices': sorted(part)})
    assert len(selected) == 4
    source.hide_render = True
    source.hide_set(True)
    copy.hide_render = False
    copy.hide_set(False)

    blind_vertices, blind_faces, back_vertices, back_faces = [], [], [], []
    def point(x, depth, z):
        return origin + axis * x + normal * depth + Vector((0, 0, z))
    def box(x, depth, z, width, thickness, height):
        start = len(blind_vertices)
        blind_vertices.extend(point(x + dx * width / 2, depth + dy * thickness / 2, z + dz * height / 2)
                              for dx, dy, dz in [(-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),
                                                 (-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1)])
        blind_faces.extend(tuple(start + i for i in face) for face in
                           [(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)])
    for window in windows:
        width = window['width'] - .08
        left = window['x'] - width / 2
        low, high = window['low'] + .06, 2.43
        pitch = width / 20
        for index in range(20):
            box(left + (index + .5) * pitch, -.245, (low + high) / 2,
                pitch * .94, .008, high - low)
        box(window['x'], -.245, high + .025, width, .035, .04)
        start = len(back_vertices)
        # A recessed dark field closes only the treated opening, not a new room.
        back_vertices.extend(point(x, -.38, z) for x, z in
                             [(left,window['low']+.04),(left,window['high']-.04),
                              (left+width,window['high']-.04),(left+width,window['low']+.04)])
        back_faces.append(tuple(start + i for i in range(4)))
    for name, vertices, faces, finish in [
        (SHADING, blind_vertices, blind_faces, material('SAR186_pale_blind_fabric', (.62,.63,.59), .91)),
        (BACKING, back_vertices, back_faces, material('SAR186_recess_shadow', (.095,.105,.10), 1.0)),
    ]:
        mesh = bpy.data.meshes.new(name)
        mesh.from_pydata(vertices, [], faces)
        mesh.update()
        mesh.materials.append(finish)
        obj = bpy.data.objects.new(name, mesh)
        collection.objects.link(obj)
    return {
        'version': 186, 'code': 'SAR', 'alreadyApplied': False,
        'addedObjects': names, 'archivedObjects': [SOURCE], 'changedObjects': [],
        'selectedPanes': selected, 'windows': windows, 'blindSlats': 80,
        'sources': [
            'data/建筑图片/SAR_Sardinia House/01_建筑实拍/exteriors_lse_estate_025.jpg',
            'data/建筑图片/SAR_Sardinia House/01_建筑实拍/campus_photos_round2_SAR_geograph_5974706_01.jpg',
        ],
        'limitations': 'Estate photograph undated; Geograph photo taken2018-08-07. '
                       'Blind spacing, setback, coverage and glass optics estimated. '
                       'Upper windows, entrance doors, facade shapes and complete rooms unchanged.',
    }
