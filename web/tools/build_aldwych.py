"""Develop 61A's existing provisional envelope from its archived street photograph.

Run in Blender's Text Editor. Preserve edition 06 and all other building geometry.
No proposed redevelopment interiors or reference-image textures are published.
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
OUT = ROOT / 'result/blender/stage07'
profile = json.loads((OUT / 'aldwych-geometry.json').read_text())
bpy.ops.wm.open_mainfile(filepath=str(ROOT / 'result/blender/LSE_campus_detailed_v06.blend'))
bpy.context.window.scene = bpy.data.scenes['00_CAMPUS_COMPLETE']
root = next(c for c in bpy.data.collections['02_LSE_BUILDINGS'].children if c.name.startswith('61A_'))


def protected_geometry():
    """Check coordinates and transforms of every mesh outside this building."""
    excluded = set(root.all_objects)
    digest = hashlib.sha256()
    for obj in sorted(bpy.data.objects, key=lambda item: item.name):
        if obj.type != 'MESH' or obj in excluded:
            continue
        digest.update(obj.name.encode())
        digest.update(array.array('f', [v for row in obj.matrix_world for v in row]).tobytes())
        coordinates = array.array('f', [0]) * (len(obj.data.vertices) * 3)
        obj.data.vertices.foreach_get('co', coordinates)
        digest.update(coordinates.tobytes())
    return digest.hexdigest()


before = protected_geometry()
for obj in list(root.all_objects):
    bpy.data.objects.remove(obj, do_unlink=True)
for child in list(root.children):
    bpy.data.collections.remove(child)
exterior = bpy.data.collections.new('61A_EXTERIOR')
root.children.link(exterior)
materials.clear()
colors = {
    'stone': (.60, .565, .49),
    'trim': (.72, .69, .61),
    'shadow': (.36, .35, .32),
    'glass': (.10, .16, .18),
    'bronze': (.16, .125, .075),
    'slate': (.12, .15, .16),
    'metal': (.04, .045, .043),
}
for name, color in colors.items():
    material = bpy.data.materials.new('61A_' + name)
    material.use_nodes = True
    material.diffuse_color = (*color, 1)
    shader = material.node_tree.nodes['Principled BSDF']
    shader.inputs['Base Color'].default_value = material.diffuse_color
    shader.inputs['Roughness'].default_value = .28 if name == 'glass' else .75
    if name == 'bronze':
        shader.inputs['Metallic'].default_value = .4
    materials[name] = material

groups = {}
height = 29.4
levels = [0, 4.2, 7.8, 11.4, 15, 18.6, 22.2, 25.8, height]
front = Facade(profile, profile['front'], groups)
for wall in profile['walls']:
    facade = Facade(profile, wall, groups)
    length = wall['length']
    if not wall['street']:
        facade.box('unobserved_envelope', 'stone', length / 2, height / 2, length, height)
        continue
    count = max(1, round(length / 3.3))
    pitch = length / count
    is_entrance = wall == profile['front']
    for floor, (bottom, top) in enumerate(zip(levels, levels[1:])):
        for bay in range(count):
            x = (bay + .5) * pitch
            width = pitch * (.74 if 1 < floor < 5 else .58)
            low, high = bottom + .65, top - .48
            if floor == 0:
                low, high, width = .15, 3.5, pitch * .8
            if is_entrance and floor == 0:
                continue
            for side in [-1, 1]:
                facade.box('window_piers', 'stone', x + side * (pitch + width) / 4,
                           (low + high) / 2, (pitch - width) / 2, high - low, .46, -.15)
            facade.box('sill_wall', 'stone', x, (bottom + low) / 2, pitch, low - bottom, .46, -.15)
            facade.box('head_wall', 'stone', x, (high + top) / 2, pitch, top - high, .46, -.15)
            facade.box('glazing', 'glass', x, (low + high) / 2, width, high - low, .045, -.27)
            for side in [-1, 1]:
                facade.box('window_jamb', 'bronze', x + side * width / 2, (low + high) / 2,
                           .065, high - low, .12, -.12)
            for z in [low, high, low + (high - low) * .72]:
                facade.box('window_transom', 'bronze', x, z, width, .065, .12, -.12)
            facade.box('window_mullion', 'bronze', x, (low + high) / 2, .055, high - low, .12, -.12)
            facade.box('projecting_sill', 'trim', x, low - .06, width + .18, .12, .52, .07)
            if floor in [2, 3, 4]:
                # Three-storey vertical piers establish the photographed facade rhythm.
                facade.box('giant_pilaster', 'trim', bay * pitch, (bottom + top) / 2,
                           .40, top - bottom, .65, .08)
    for z, thickness in [(4.2, .3), (18.6, .42), (22.2, .28), (25.8, .42), (29.4, .32)]:
        facade.box('cornice', 'trim', length / 2, z, length + .06, thickness, .76, .10)
    for z in [5.7, 7.6, 19.5, 20.4, 21.3, 23.2, 24.2, 28.4]:
        facade.box('stone_joint', 'shadow', length / 2, z, length, .014, .018, .089)
    # Set-back roof windows and a slate apron replace the former flat roof edge.
    for bay in range(count):
        x = (bay + .5) * pitch
        facade.box('roof_dormer', 'stone', x, 30.7, 1.95, 2.45, 1.35, -1.25)
        facade.box('roof_window', 'glass', x, 30.7, 1.50, 1.65, .04, -.55)
        facade.box('roof_window_mullion', 'bronze', x, 30.7, .055, 1.65, .08, -.49)
        facade.box('dormer_coping', 'trim', x, 31.96, 2.05, .14, 1.48, -1.25)
    roof_edge = facade.group('slate_apron', 'slate')
    roof_edge.add([facade.point(0, 29.55, .1), facade.point(length, 29.55, .1),
                   facade.point(length, 32.1, -2.3), facade.point(0, 32.1, -2.3)], [(0, 1, 2, 3)])
    for bay in range(max(1, round(length / 1.1))):
        x = (bay + .5) * length / max(1, round(length / 1.1))
        facade.box('balcony_rail_post', 'metal', x, 26.38, .032, .9, .032, .57)
    facade.box('balcony_rail', 'metal', length / 2, 26.82, length, .04, .04, .57)

# Recessed corner portal, lintel and a modest stone entrance canopy.
x = front.length / 2
front.box('entrance_glass', 'glass', x, 1.85, front.length - 1.1, 3.7, .05, -.35)
for side in [-1, 1]:
    front.box('entrance_pier', 'trim', x + side * (front.length / 2 - .3), 2.05, .6, 4.1, .85, .12)
    front.box('entrance_door_frame', 'bronze', x + side * 1.05, 1.7, .10, 3.4, .16, -.12)
front.box('entrance_lintel', 'trim', x, 3.96, front.length, .36, 1.05, .18)
front.box('entrance_transom', 'bronze', x, 2.9, front.length - 1.1, .10, .15, -.12)
front.box('entrance_door_center', 'bronze', x, 1.45, .08, 2.9, .15, -.12)
front.box('entrance_step', 'shadow', x, .06, front.length, .12, 1.05, .45)
front.label('61 ALDWYCH', x, 3.73, .25, 'bronze', .73)

# The existing photographed corner roof pavilion, not the proposed LSE extension.
pavilion = Geometry('61A', 'corner_pavilion', 'stone')
roof = Geometry('61A', 'corner_roof', 'slate')
cx, cy = -37.6, -120.0
angle = math.atan2(front.u.y, front.u.x)

def pavilion_point(x, y, z):
    return (cx + math.cos(angle) * x - math.sin(angle) * y,
            cy + math.sin(angle) * x + math.cos(angle) * y, z)

pavilion.box((cx, cy, 31.8), (9, 9, 4.0), angle)
for index in range(4):
    a, b = [(-4.5, -4.5), (4.5, -4.5), (4.5, 4.5), (-4.5, 4.5)][index], [(-4.5, -4.5), (4.5, -4.5), (4.5, 4.5), (-4.5, 4.5)][(index + 1) % 4]
    p, q = pavilion_point(*a, 0)[:2], pavilion_point(*b, 0)[:2]
    outward = Vector(((p[0] + q[0]) / 2 - cx, (p[1] + q[1]) / 2 - cy)).normalized()
    side = Facade(profile, {'p': p, 'q': q, 'length': 9, 'outward': list(outward)}, groups)
    side.box('pavilion_glass', 'glass', 4.5, 34.5, 8.6, 1.25, .04, -.07)
    for xx in [.15, 2.3, 4.5, 6.7, 8.85]:
        side.box('pavilion_posts', 'bronze', xx, 34.5, .13, 1.5, .17, .0)
    for z in [33.8, 35.2]:
        side.box('pavilion_band', 'trim', 4.5, z, 9.5, .18, .60, .02)
    roof.add([pavilion_point(a[0] * 1.12, a[1] * 1.12, 35.35),
              pavilion_point(b[0] * 1.12, b[1] * 1.12, 35.35), (cx, cy, 37.7)], [(0, 1, 2)])
pavilion.box((cx, cy, 38.1), (.18, .18, .8), angle)
groups['pavilion'] = pavilion
groups['pavilion_roof'] = roof
flat_roof = Geometry('61A', 'main_roof', 'slate')
for triangle in profile['triangles']:
    flat_roof.add([(px, py, 29.5) for px, py in triangle], [(0, 1, 2)])
groups['main_roof'] = flat_roof
for geometry in groups.values():
    geometry.finish()
bpy.context.view_layer.update()
assert protected_geometry() == before, 'Geometry outside 61A changed'
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / 'result/blender/LSE_campus_detailed_v07.blend'))
record = {
    'code': '61A', 'exteriorDirection': [-.7, .65, .9], 'scope': profile['scope'],
    'sources': profile['sources'], 'osmIds': profile['osmIds'],
    'protectedGeometrySha256': before,
    'components': sum(geometry.parts for geometry in groups.values()),
}
(OUT / 'aldwych-manifest.json').write_text(json.dumps(record, indent=2) + '\n')
print('ALDWYCH_COMPLETE', record, flush=True)
