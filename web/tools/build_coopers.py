"""Correct 49L/50L street envelopes using Rock Townsend's 2022 block plan.

Run inside Blender. Plan registration is an architectural-study approximation,
not a measured boundary or a claim of exclusive occupancy of the 50/50A building.
"""
from pathlib import Path
import array
import hashlib
import json
import math
import sys
import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from facade_geometry import Geometry, Facade, materials

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'result/blender/stage08'
evidence = json.loads((OUT / 'coopers-geometry.json').read_text())
bpy.ops.wm.open_mainfile(filepath=str(ROOT / 'result/blender/LSE_campus_detailed_v07.blend'))
bpy.context.window.scene = bpy.data.scenes['00_CAMPUS_COMPLETE']
roots = {code: next(c for c in bpy.data.collections['02_LSE_BUILDINGS'].children if c.name.startswith(code + '_')) for code in ['49L', '50L']}


def protected_geometry():
    excluded = {obj for root in roots.values() for obj in root.all_objects}
    digest = hashlib.sha256()
    for obj in sorted(bpy.data.objects, key=lambda item: item.name):
        if obj.type != 'MESH' or obj in excluded or obj.name.startswith('Context_way/181939042'):
            continue
        digest.update(obj.name.encode())
        digest.update(array.array('f', [v for row in obj.matrix_world for v in row]).tobytes())
        coordinates = array.array('f', [0]) * (len(obj.data.vertices) * 3)
        obj.data.vertices.foreach_get('co', coordinates)
        digest.update(coordinates.tobytes())
    return digest.hexdigest()


before = protected_geometry()
removed = []
for obj in list(bpy.data.objects):
    if obj.name.startswith('Context_way/181939042'):
        removed.append(obj.name)
        bpy.data.objects.remove(obj, do_unlink=True)
assert removed, 'Expected adjoining 50/50A context shell was absent'
materials.clear()
colors = {'cream': (.72, .69, .59), 'blue': (.27, .43, .56), 'white': (.83, .82, .76),
          'glass': (.075, .13, .15), 'shutter': (.26, .29, .27), 'black': (.025, .03, .025),
          'brick': (.43, .20, .12), 'stone': (.56, .43, .27), 'wood': (.18, .095, .045),
          'slate': (.14, .15, .14), 'green': (.15, .29, .27)}
for name, color in colors.items():
    material = bpy.data.materials.new('COOPERS_' + name)
    material.use_nodes = True
    material.diffuse_color = (*color, 1)
    shader = material.node_tree.nodes['Principled BSDF']
    shader.inputs['Base Color'].default_value = material.diffuse_color
    shader.inputs['Roughness'].default_value = .28 if name == 'glass' else .8
    if name == 'brick':
        nodes, links = material.node_tree.nodes, material.node_tree.links
        uv = nodes.new('ShaderNodeTexCoord')
        brick = nodes.new('ShaderNodeTexBrick')
        brick.inputs['Scale'].default_value = 1
        brick.inputs['Brick Width'].default_value = .225
        brick.inputs['Row Height'].default_value = .078
        brick.inputs['Mortar Size'].default_value = .005
        brick.inputs['Color1'].default_value = (*color, 1)
        brick.inputs['Color2'].default_value = (.34, .13, .075, 1)
        brick.inputs['Mortar'].default_value = (.30, .27, .21, 1)
        links.new(uv.outputs['UV'], brick.inputs['Vector'])
        links.new(brick.outputs['Color'], shader.inputs['Base Color'])
    materials[name] = material

records = []
for profile in evidence['profiles']:
    code, height = profile['code'], profile['height']
    for obj in list(roots[code].all_objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for child in list(roots[code].children):
        bpy.data.collections.remove(child)
    exterior = bpy.data.collections.new(code + '_EXTERIOR')
    roots[code].children.link(exterior)
    groups = {}
    ring = profile['ring']
    for edge, (p, q) in enumerate(zip(ring, ring[1:] + ring[:1])):
        length = math.dist(p, q)
        normal = Vector(((q[1] - p[1]) / length, -(q[0] - p[0]) / length))
        if normal.dot((Vector(p) + Vector(q)) / 2 - Vector(profile['center'])) < 0:
            normal = -normal
        facade = Facade(profile, {'p': p, 'q': q, 'length': length, 'outward': list(normal)}, groups)
        street = edge in ([0, 5, 6] if code == '49L' else [5])
        material = 'cream' if code == '49L' else 'brick'
        if not street:
            facade.box('unobserved_wall', material, length / 2, height / 2, length, height)
            continue
        corner = code == '49L' and edge == 6
        if (code == '49L' and edge == 0) or code == '50L':
            front = facade
        floors = [0, 3.8, 7.25, height] if code == '49L' else [0, 3.8, 6.7, 9.6, height]
        count = 1 if corner else 2 if code == '49L' and edge == 0 else max(2, round(length / 2.8))
        pitch = length / count
        ground_openings = []
        for floor, (bottom, top) in enumerate(zip(floors, floors[1:])):
            wall_material = 'blue' if code == '49L' and floor == 0 else material
            for bay in range(count):
                x = (bay + .5) * pitch
                low, high = bottom + .50, top - .38
                width = min(1.65, pitch * .58)
                doorway = floor == 0 and (corner or code == '50L' and bay == count - 1)
                if corner and floor > 0:
                    facade.box('corner_pier', 'cream', x, (bottom + top) / 2, pitch, top - bottom, .35)
                    continue
                if doorway:
                    low, high, width = .08, 2.8, min(1.55, pitch * .72)
                if floor == 0:
                    ground_openings.append((x - width / 2, x + width / 2, low, high))
                for side in [-1, 1]:
                    facade.box('masonry_piers', wall_material, x + side * (pitch + width) / 4,
                               (low + high) / 2, (pitch - width) / 2, high - low)
                facade.box('masonry_below', wall_material, x, (bottom + low) / 2, pitch, low - bottom)
                facade.box('masonry_above', wall_material, x, (high + top) / 2, pitch, top - high)
                facade.box('door' if doorway else 'window', ('black' if code == '49L' else 'wood') if doorway else 'glass',
                           x, (low + high) / 2, width, high - low, .04, -.17)
                for side in [-1, 1]:
                    facade.box('window_frame', 'stone' if doorway else 'white', x + side * width / 2,
                               (low + high) / 2, .085, high - low, .16, -.01)
                for z in [low, high, low + (high - low) * .5]:
                    facade.box('sash_rail', 'white' if not doorway else 'wood', x, z, width, .06, .13, -.01)
                if code == '50L' and not doorway:
                    facade.box('vertical_mullion', 'white', x, (low + high) / 2, .055, high - low, .13, -.01)
                if code == '49L' and floor > 0:
                    for side in [-1, 1]:
                        xx = x + side * (width / 2 + .32)
                        facade.box('shutter_frame', 'white', xx, (low + high) / 2, .56, high - low, .10, .015)
                        for index in range(22):
                            facade.box('shutter_louvre', 'shutter', xx, low + .06 + index * (high - low - .12) / 21,
                                       .46, .045, .035, .077)
                if code == '50L' and doorway:
                    facade.arch('arched_entry', 'stone', x, 2.7, width / 2, .23, .28)
                    facade.box('entry_header', 'stone', x, 3.65, width + .70, .20, .50, .14)
                    facade.label('50', x, 2.48, .20, 'white', .04)
                if corner and doorway:
                    canopy = facade.group('curved_canopy', 'black')
                    for index in range(24):
                        a, b = index * math.pi / 24, (index + 1) * math.pi / 24
                        canopy.add([facade.point(x + .98 * math.cos(angle), 2.75 + .55 * math.sin(angle), depth)
                                    for depth in [.15, 1.0] for angle in [a, b]], [(0, 1, 3, 2)])
        for z in [3.8, height - .15, height + .10]:
            facade.box('cornice', 'white' if code == '49L' else 'stone', length / 2, z, length, .17, .42, .04)
        for x in [0.1, length - .1]:
            facade.box('upper_pilaster', 'white' if code == '49L' else 'stone', x, (3.8 + height) / 2,
                       .18, height - 3.8, .33, .01)
        if code == '49L':
            for z in [.4, .9, 1.4, 1.9, 2.4, 2.9, 3.4]:
                cursor = 0
                for left, right, low, high in sorted(ground_openings):
                    if not low < z < high:
                        continue
                    facade.box('blue_rustication', 'shutter', (cursor + left) / 2, z,
                               left - cursor, .014, .012, .011)
                    cursor = right
                facade.box('blue_rustication', 'shutter', (cursor + length) / 2, z,
                           length - cursor, .014, .012, .011)
        if corner:
            facade.box('corner_parapet', 'cream', length / 2, height + .45, length * .74, .9, .50, -.05)
            facade.box('parapet_cap', 'white', length / 2, height + .95, length * .85, .13, .65, -.04)
            oculus = facade.group('round_corner_window', 'glass')
            trim = facade.group('oculus_frame', 'white')
            for index in range(32):
                a, b = index * math.tau / 32, (index + 1) * math.tau / 32
                z = height - 1.3
                oculus.add([facade.point(length / 2, z, .10),
                            facade.point(length / 2 + .29 * math.cos(a), z + .29 * math.sin(a), .10),
                            facade.point(length / 2 + .29 * math.cos(b), z + .29 * math.sin(b), .10)], [(0, 1, 2)])
                trim.add([facade.point(length / 2 + radius * math.cos(angle), z + radius * math.sin(angle), .13)
                          for radius, angle in [(.29, a), (.29, b), (.39, b), (.39, a)]], [(0, 1, 2, 3)])
    if code == '49L':
        front.box('restaurant_name_board', 'green', front.length / 2, 2.1, .8, 1.05, .08, .09)
        front.label('COOPERS', front.length / 2, 2.09, .105, 'white', .14)
    roof = Geometry(code, 'roof', 'slate')
    for triangle in profile['triangles']:
        roof.add([(x, y, height) for x, y in triangle], [(0, 1, 2)])
    groups['roof'] = roof
    for geometry in groups.values():
        geometry.finish()
    records.append({'code': code, 'exteriorDirection': [front.n.x - .45, .55, -front.n.y],
                    'scope': profile['scope'], 'sourceDrawing': evidence['drawing'],
                    'sourcePage': evidence['sourceUrl'], 'components': sum(g.parts for g in groups.values())})

bpy.context.view_layer.update()
assert protected_geometry() == before, 'An unrelated building changed'
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / 'result/blender/LSE_campus_detailed_v08.blend'))
(OUT / 'coopers-manifest.json').write_text(json.dumps({'buildings': records, 'protectedGeometrySha256': before,
                                                    'removedContextObjects': removed}, indent=2) + '\n')
print('COOPERS_COMPLETE', records, flush=True)
