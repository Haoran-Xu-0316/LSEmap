"""Photo-guided PAR pointed window heads, sash hierarchy and roof furniture.
Run in Blender Text Editor. Preserve the version-65 campus and PAR interiors.
"""
from pathlib import Path
import array
import hashlib
import json
import math
import sys
import bpy
import bmesh
from mathutils import Vector
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'result/blender/stage66'
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(Path(__file__).resolve().parent))
from facade_geometry import Geometry, Facade, materials
bpy.ops.wm.open_mainfile(filepath=str(ROOT / 'result/blender/LSE_campus_detailed_v65.blend'))
bpy.context.window.scene = bpy.data.scenes['00_CAMPUS_COMPLETE']
collection = bpy.data.collections['PAR_EXTERIOR']
profile_data = json.loads((ROOT / 'result/blender/stage10/parish/parish-geometry.json').read_text())
profile, wall = profile_data['profile'], profile_data['front']
front = Facade(profile, wall, {})
split = profile_data['entryStart']
pitch = split / 4
origin = Vector((*wall['p'], 0))
u, normal = Vector((*front.u, 0)), Vector((*front.n, 0))

def local(point):
    delta = point - origin
    return Vector((delta.dot(u), delta.dot(normal), point.z))

def fingerprint(obj):
    result = hashlib.sha256(str([list(row) for row in obj.matrix_world]).encode())
    if obj.type == 'MESH':
        result.update(array.array('f', [c for v in obj.data.vertices for c in v.co]).tobytes())
        result.update(array.array('i', [p.vertex_index for p in obj.data.loops]).tobytes())
    result.update(str([m.name if m else None for m in getattr(obj.data, 'materials', [])]).encode())
    return result.hexdigest()

before = {o.name: fingerprint(o) for o in bpy.data.objects}
materials.clear()
palette = {
    'brick': (.34, .155, .092), 'archbrick': (.255, .115, .070),
    'tile': (.32, .105, .060), 'stone': (.67, .64, .56),
    'frame': (.76, .74, .65), 'glass': (.095, .135, .14),
    'metal': (.025, .034, .035), 'timber': (.070, .045, .029),
    'lead': (.37, .40, .40), 'red': (.60, .016, .026),
}
for key, color in palette.items():
    source = bpy.data.materials.get('PAR10_' + key)
    material = source.copy() if source else bpy.data.materials.new('PAR_V66_' + key)
    material.use_nodes = True
    material.name = 'PAR_V66_' + key
    material.diffuse_color = (*color, 1)
    shader = material.node_tree.nodes['Principled BSDF']
    shader.inputs['Base Color'].default_value = material.diffuse_color
    if key == 'glass':
        shader.inputs['Roughness'].default_value = .22
        shader.inputs['Metallic'].default_value = .15
    for node in material.node_tree.nodes:
        if node.type == 'TEX_BRICK':
            node.inputs['Color1'].default_value = (*color, 1)
            second = (.295, .096, .056) if key == 'tile' else (.25, .115, .074)
            node.inputs['Color2'].default_value = (*second, 1)
            node.inputs['Mortar'].default_value = (.19, .085, .048, 1) if key == 'tile' else (.29, .255, .205, 1)
            node.inputs['Brick Width'].default_value = .30 if key == 'tile' else .225
            node.inputs['Row Height'].default_value = .075 if key == 'tile' else .078
            node.inputs['Mortar Size'].default_value = .0018 if key == 'tile' else .004
    materials[key] = material
slate = bpy.data.materials.new('PAR_V66_slate')
slate.use_nodes = True
slate.diffuse_color = (.055, .065, .065, 1)
slate.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = slate.diffuse_color
slate.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = .70
materials['slate'] = slate
# Limit the palette replacement to PAR exterior slots. No shared source material
# is edited, so room studies and other buildings retain their existing finishes.
for obj in list(collection.all_objects):
    for slot in obj.material_slots:
        if slot.material and slot.material.name.startswith('PAR10_'):
            slot.material = materials[slot.material.name.removeprefix('PAR10_')]
    if obj.name == 'PAR_D5_dormer_pitched_roof_tile':
        obj.data.materials[0] = slate

hidden = ['PAR_D5_brick_relieving_arch_archbrick', 'PAR_D5_chimney_pot_archbrick']
for name in hidden:
    obj = bpy.data.objects[name]
    obj.hide_render = True
    obj.hide_set(True)

# Remove whole front-only sash pieces while retaining basement and side windows.
removed = {}
for name in ['PAR_D5_glazing_bar_frame', 'PAR_D5_window_rail_frame', 'PAR_D5_front_stone_course_stone']:
    obj = bpy.data.objects[name]
    mesh = bmesh.new()
    mesh.from_mesh(obj.data)
    seen, delete, count = set(), [], 0
    for vertex in list(mesh.verts):
        if vertex in seen:
            continue
        stack, members = [vertex], []
        seen.add(vertex)
        while stack:
            current = stack.pop()
            members.append(current)
            for edge in current.link_edges:
                other = edge.other_vert(current)
                if other not in seen:
                    seen.add(other)
                    stack.append(other)
        points = [local(obj.matrix_world @ v.co) for v in members]
        center = sum(points, Vector()) / len(points)
        on_front = all(-.19 < p.y < .30 for p in points) and 0 < center.x < split
        replace = abs(center.z - 6.58) < .01 if 'course' in name else 2.70 < center.z < 8.40
        if on_front and replace:
            delete.extend(members)
            count += 1
    bmesh.ops.delete(mesh, geom=delete, context='VERTS')
    mesh.to_mesh(obj.data)
    obj.data.update()
    mesh.free()
    removed[name] = count
assert removed == {'PAR_D5_glazing_bar_frame': 32, 'PAR_D5_window_rail_frame': 24,
                   'PAR_D5_front_stone_course_stone': 1}, removed

# The low entrance gable was a backwards single-sided face, leaving a dark hole.
gable = bpy.data.objects['PAR_D5_entrance_gable_brick']
mesh = bmesh.new()
mesh.from_mesh(gable.data)
faces = [face for face in mesh.faces if face.normal.dot(normal) < 0]
bmesh.ops.reverse_faces(mesh, faces=faces)
mesh.to_mesh(gable.data)
gable.data.update()
mesh.free()
roof_face_corrections = {}
for name in ['PAR_D5_tiled_roof', 'PAR_D5_dormer_pitched_roof_tile']:
    obj = bpy.data.objects[name]
    mesh = bmesh.new()
    mesh.from_mesh(obj.data)
    faces = [face for face in mesh.faces if face.normal.z < 0]
    roof_face_corrections[name] = len(faces)
    bmesh.ops.reverse_faces(mesh, faces=faces)
    mesh.to_mesh(obj.data)
    obj.data.update()
    mesh.free()
groups = {}
front = Facade(profile, wall, groups)
for i in range(4):
    x = (i + .5) * pitch
    for bottom, top, width, tall in [(2.8, 5.15, 2.10, True), (7.0, 8.25, 2.20, False)]:
        midpoint = bottom + (top - bottom) * (.68 if tall else .50)
        for z in [bottom, top, midpoint]:
            front.box('photo66_sash_rail', 'frame', x, z, width, .065, .14, -.015)
        front.box('photo66_central_mullion', 'frame', x, (bottom + top) / 2, .080, top - bottom, .14, -.015)
        for side in [-1, 1]:
            front.box('photo66_fine_vertical', 'frame', x + side * width / 4,
                      (bottom + top) / 2, .027, top - bottom, .08, .01)
        if tall:
            front.box('photo66_lower_sash_bar', 'frame', x, bottom + (top - bottom) * .34,
                      width, .027, .08, .01)
    # Paired circular arcs meet at a pointed apex above the rectangular lintel.
    half, rise, spring, thickness = 1.08, 1.38, 5.26, .16
    center = (rise * rise - half * half) / (2 * half)
    radius = half + center
    end_angle = math.atan2(rise, -center)
    for side in [-1, 1]:
        for segment in range(24):
            a = math.pi + (end_angle - math.pi) * segment / 24
            b = math.pi + (end_angle - math.pi) * (segment + 1) / 24
            vertices = [front.point(x + side * (center + r * math.cos(t)), spring + r * math.sin(t), d)
                        for d in [.015, .135] for r, t in [(radius, a), (radius, b),
                                                         (radius + thickness, b), (radius + thickness, a)]]
            front.group('photo66_pointed_window_head', 'archbrick').add(vertices,
                [(0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1), (3, 2, 6, 7), (1, 5, 6, 2), (0, 3, 7, 4)])
front.box('photo66_brick_stringcourse', 'archbrick', split / 2, 6.90, split, .10, .42, .04)

def cylinder(name, key, x, depth, z0, z1, r0, r1, inner=0):
    sides = 24
    vertices = [front.point(x + r * math.cos(i * math.tau / sides), z, depth + r * math.sin(i * math.tau / sides))
                for z, r in [(z0, r0), (z1, r1)] for i in range(sides)]
    faces = [(i, (i + 1) % sides, (i + 1) % sides + sides, i + sides) for i in range(sides)]
    if inner:
        vertices += [front.point(x + inner * math.cos(i * math.tau / sides), z1, depth + inner * math.sin(i * math.tau / sides)) for i in range(sides)]
        faces += [(i + sides, (i + 1) % sides + sides, (i + 1) % sides + 2 * sides, i + 2 * sides) for i in range(sides)]
    else:
        faces += [tuple(range(sides - 1, -1, -1)), tuple(range(sides, sides * 2))]
    front.group(name, key).add(vertices, faces)

# Two roof cowls, seated on slope-matched lead flashing near the ridge.
vent_positions = [split * .22, split * .80]
for x in vent_positions:
    depth = -4.35
    base = 13 - (depth + 5) * .84
    vertices = [front.point(x + sx * .35, 13 - (d + 5) * .84 + .025, d)
                for sx, d in [(-1, depth - .35), (1, depth - .35), (1, depth + .35), (-1, depth + .35)]]
    vertices += [front.point(x + sx * .20, base + .52, depth + sy * .20)
                 for sx, sy in [(-1, -1), (1, -1), (1, 1), (-1, 1)]]
    front.group('photo66_cowl_flashing', 'lead').add(vertices,
        [(0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7), (4, 5, 6, 7)])
    cylinder('photo66_cowl_neck', 'lead', x, depth, base + .50, base + .82, .15, .17)
    cylinder('photo66_cowl_louvre_core', 'metal', x, depth, base + .78, base + 1.22, .205, .205)
    for dz in [.78, .94, 1.10]:
        cylinder('photo66_cowl_louvre_rim', 'lead', x, depth, base + dz, base + dz + .04, .27, .27)
    cylinder('photo66_cowl_cap', 'lead', x, depth, base + 1.22, base + 1.48, .30, .025)
    cylinder('photo66_cowl_finial', 'metal', x, depth, base + 1.48, base + 1.53, .035, .035)
for x in [.10, split - .10]:
    for offset in [-.22, .22]:
        cylinder('photo66_round_chimney_pot', 'tile', x + offset, -4.8, 15.0, 15.47, .12, .11, .078)
        cylinder('photo66_pot_lip', 'tile', x + offset, -4.8, 15.43, 15.49, .135, .135, .078)

# Angled anti-climb slats span the lightwell instead of stopping at upright bars.
for i in range(int((split - .27) / .22) + 1):
    x = .12 + i * .22
    a, b = Vector(front.point(x, 1.57, 1.00)), Vector(front.point(x, 1.74, .48))
    axis = (b - a).normalized()
    cross = axis.cross(Vector((0, 0, 1))).normalized()
    other = axis.cross(cross).normalized()
    vertices = [p + .016 * (cross * math.cos(j * math.tau / 8) + other * math.sin(j * math.tau / 8))
                for p in [a, b] for j in range(8)]
    front.group('photo66_lightwell_slats', 'metal').add(vertices,
        [(j, (j + 1) % 8, (j + 1) % 8 + 8, j + 8) for j in range(8)])
added = []
for geometry in groups.values():
    obj = geometry.finish()
    added.append(obj.name)
    for modifier in list(obj.modifiers):
        obj.modifiers.remove(modifier)
changed = [name for name, previous in before.items() if fingerprint(bpy.data.objects[name]) != previous]
assert all(name in {o.name for o in collection.all_objects} for name in changed), changed
for filename in ['room-studies.json', 'room-spaces.json', 'building-review.json']:
    (OUT / filename).write_bytes((ROOT / 'result/blender/stage65' / filename).read_bytes())
audit = {'version': 66, 'baseline': 65, 'changedExistingObjects': changed,
         'changedOtherObjects': [], 'hiddenPreviousObjects': hidden, 'removedMembers': removed,
         'roofFaceCorrections': roof_face_corrections, 'addedObjects': added, 'ventPositions': vent_positions, 'chimneyPots': 4,
         'front': wall, 'split': split, 'windowHeads': 4,
         'references': ['2015 LSE completed refurbishment exterior photo', '2025/26 LSE property handbook photo'],
         'limitations': ['Exact photograph capture dates unknown; not a 2026 survey',
                        'Heights, vent positions and decorative profiles estimated',
                        'Unseen elevations, complete interior and present roof plant still require verification']}
(OUT / 'parish-exterior-audit.json').write_text(json.dumps(audit, indent=2) + '\n')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / 'result/blender/LSE_campus_detailed_v66.blend'))
print('PARISH_EXTERIOR_SAVED', len(added), removed)
