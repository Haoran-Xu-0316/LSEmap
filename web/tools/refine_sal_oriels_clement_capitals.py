"""Correct SAL's excess storey and glazed oriel sides; detail CLM capitals.
Run in Blender Text Editor. All heights and ornament profiles remain estimates.
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
OUT = ROOT / 'result/blender/stage70'
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(Path(__file__).resolve().parent))
from facade_geometry import Geometry, materials
bpy.ops.wm.open_mainfile(filepath=str(ROOT / 'result/blender/LSE_campus_detailed_v69.blend'))
bpy.context.window.scene = bpy.data.scenes['00_CAMPUS_COMPLETE']

def fingerprint(obj):
    h = hashlib.sha256(str([list(r) for r in obj.matrix_world]).encode())
    if obj.type == 'MESH':
        h.update(array.array('f', [c for v in obj.data.vertices for c in v.co]).tobytes())
        h.update(array.array('i', [l.vertex_index for l in obj.data.loops]).tobytes())
    h.update(str([m.name if m else None for m in getattr(obj.data, 'materials', [])]).encode())
    return h.hexdigest()

before = {o.name: fingerprint(o) for o in bpy.data.objects}
collection = bpy.data.collections['SAL_EXTERIOR']
# Remove one whole architectural storey, rather than hiding windows while keeping
# the incorrect mass. The previous fourth upper window band lay in this interval.
cut_bottom, cut_top = 17.60, 21.95
removed_faces = 0
changed_geometry = []
for obj in list(collection.all_objects):
    if obj.type != 'MESH' or obj.hide_render:
        continue
    mesh = bmesh.new()
    mesh.from_mesh(obj.data)
    seen, remove = set(), []
    for vertex in list(mesh.verts):
        if vertex in seen:
            continue
        component, stack = [], [vertex]
        seen.add(vertex)
        while stack:
            current = stack.pop()
            component.append(current)
            for edge in current.link_edges:
                neighbor = edge.other_vert(current)
                if neighbor not in seen:
                    seen.add(neighbor)
                    stack.append(neighbor)
        heights = [(obj.matrix_world @ v.co).z for v in component]
        # Upper-storey window, reveal and projecting-bay members must disappear
        # entirely, including pieces crossing the structural removal boundaries.
        if any(k in obj.name for k in ['Window_', 'Oriel_']) and 17.65 < sum(heights) / len(heights) < 22.05:
            remove.extend(component)
    if remove:
        bmesh.ops.delete(mesh, geom=remove, context='VERTS')
    inverse = obj.matrix_world.inverted()
    changed = bool(remove)
    for vertex in mesh.verts:
        p = obj.matrix_world @ vertex.co
        if p.z > cut_bottom:
            p.z = cut_bottom + max(0, p.z - cut_top)
            vertex.co = inverse @ p
            changed = True
    degenerate = [f for f in mesh.faces if f.calc_area() < .000001]
    removed_faces += len(degenerate)
    if degenerate:
        bmesh.ops.delete(mesh, geom=degenerate, context='FACES')
    if changed:
        # Regenerate metric UVs only on wall batches that lose a storey. Rigidly
        # translated slate roofs retain the dedicated slate mapping already fixed.
        if any(k in obj.name for k in ['Front_brick_piers', 'Pilaster_brick_cores', 'Side_back']):
            mesh.normal_update()
            uv = mesh.loops.layers.uv.active
            if uv:
                for face in mesh.faces:
                    points = [obj.matrix_world @ loop.vert.co for loop in face.loops]
                    if len(points) < 3:
                        continue
                    axis = (points[1] - points[0]).normalized()
                    normal = (points[1] - points[0]).cross(points[-1] - points[0]).normalized()
                    across = normal.cross(axis).normalized()
                    for loop, p in zip(face.loops, points):
                        loop[uv].uv = ((p - points[0]).dot(axis), (p - points[0]).dot(across))
        mesh.to_mesh(obj.data)
        obj.data.update()
        changed_geometry.append(obj.name)
    mesh.free()

# Copy the sash material only on SAL exterior slots; interiors retain their own
# finishes. Blue paint is corroborated by the architect and September 2023 photo.
blue = None
remapped = []
for obj in list(collection.all_objects):
    for index, old in enumerate(list(getattr(obj.data, 'materials', []))):
        if old and 'SAL_Dark_bronze_sash' in old.name:
            if blue is None:
                blue = old.copy()
                blue.name = 'SAL_V70_blue_painted_sash'
                blue.diffuse_color = (.018, .052, .105, 1)
                node = blue.node_tree.nodes['Principled BSDF']
                node.inputs['Base Color'].default_value = blue.diffuse_color
                node.inputs['Roughness'].default_value = .43
                node.inputs['Metallic'].default_value = .18
            obj.data.materials[index] = blue
            remapped.append(obj.name)
assert blue is not None
hidden = ['SAL_Oriel_stone_side_walls', 'SAL_Oriel_chamfered_corner_piers']
for name in hidden:
    bpy.data.objects[name].hide_render = True
    bpy.data.objects[name].hide_set(True)

materials.clear()
materials['blue'] = blue
for key, name in [('stone', 'SAL_Cut_stone_edges'), ('glass', 'SAL_Recessed_reflective_glazing')]:
    materials[key] = next(m for m in bpy.data.materials if m.name == name or m.name.startswith(name + '_'))
a = math.radians(24.35)
sal_origin = Vector((120.73, 121.65, 0))
u, n = Vector((-math.cos(a), -math.sin(a), 0)), Vector((-math.sin(a), math.cos(a), 0))
def sal_point(x, depth, z):
    return sal_origin + u * x + n * depth + Vector((0, 0, z))
groups = {}
def group(code, key):
    name = code + ':' + key
    if name not in groups:
        groups[name] = Geometry(code, 'photo70_' + key, key)
    return groups[name]

def edge_box(code, key, p, q, z, height, width, offset=0):
    axis = (q - p).normalized()
    normal = Vector((axis.y, -axis.x, 0))
    if code == 'SAL' and normal.dot(n) < 0:
        normal.negate()
    center = (p + q) / 2 + normal * offset + Vector((0, 0, z))
    group(code, key).box(center, ((q - p).length, width, height), math.atan2(axis.y, axis.x))

side_windows = []
for x in [-22.25, 0, 22.25]:
    depth = 1.0 if x == 0 else .15
    for z, height in [(7.30, 3.45), (11.65, 3.35), (15.85, 3.35)]:
        for side in [-1, 1]:
            back = sal_point(x + side * 1.77, depth + .06, 0)
            front = sal_point(x + side * 1.325, depth + 1.13, 0)
            length = (front - back).length
            for k, z0 in [('glass', z)]:
                edge_box('SAL', k, back, front, z0, height - .06, .035, -.07)
            # Slim blue-painted sashes, horizontal rails and one fine center bar.
            for zz in [z - height / 2 + .035, z + height / 2 - .035]:
                edge_box('SAL', 'blue', back, front, zz, .065, .10)
            axis = (front - back).normalized()
            normal = Vector((axis.y, -axis.x, 0))
            if normal.dot(n) < 0:
                normal.negate()
            for t in [0, .5, 1]:
                center = back.lerp(front, t) + Vector((0, 0, z))
                group('SAL', 'blue').box(center, (.055 if t != .5 else .032, .10, height), math.atan2(axis.y, axis.x))
            for row in [1, 2, 3]:
                edge_box('SAL', 'blue', back, front, z - height / 2 + height * row / 4,
                         .060 if row == 2 else .030, .10)
            # Pale stone caps keep the projecting side panes tied to front sills.
            for zz in [z - height / 2 - .10, z + height / 2 + .08]:
                edge_box('SAL', 'stone', back, front, zz, .17, .32)
            side_windows.append({'bay': x, 'height': z, 'side': side, 'width': length})

# Clement House: curled capitals visible in the school handbook. Retain the
# existing column shafts and abaci; the small scroll profiles are authored.
clm_material = next(m for m in bpy.data.objects['CLM_D3_column_capital_abacus'].data.materials if m)
materials['capital'] = clm_material
site = json.loads((ROOT / 'result/blender/site_geometry.json').read_text())
clm = next(b for b in site['buildings'] if b['code'] == 'CLM')
points = [Vector((*clm['rings'][0][i], 0)) for i in (5, 4, 3, 2, 1)]
lengths = [(q - p).length for p, q in zip(points, points[1:])]
length = sum(lengths)
def clm_point(distance, depth, z):
    start = 0
    for i, segment in enumerate(lengths):
        if distance <= start + segment or i == len(lengths) - 1:
            axis = (points[i + 1] - points[i]).normalized()
            normal = Vector((axis.y, -axis.x, 0))
            center = Vector((*clm['center'], 0))
            if normal.dot((points[i] + points[i + 1]) / 2 - center) < 0:
                normal.negate()
            return points[i] + axis * (distance - start) + normal * depth + Vector((0, 0, z))
        start += segment

def tube(vertices, radius):
    # A continuous small-profile scroll avoids overlapping primitive spheres.
    batch = group('CLM', 'capital')
    for start, end in zip(vertices, vertices[1:]):
        axis = (end - start).normalized()
        cross = axis.cross(Vector((0, 0, 1)))
        if cross.length < .01:
            cross = axis.cross(Vector((0, 1, 0)))
        cross.normalize()
        other = axis.cross(cross).normalized()
        ring = [p + radius * (cross * math.cos(j * math.tau / 8) + other * math.sin(j * math.tau / 8))
                for p in [start, end] for j in range(8)]
        batch.add(ring, [(j, (j + 1) % 8, (j + 1) % 8 + 8, j + 8) for j in range(8)])

scrolls = 0
for center in [2.25 * length / 7, 4.75 * length / 7]:
    for delta in [-.37, .37]:
        distance = center + delta
        for side in [-1, 1]:
            path = []
            for i in range(65):
                t = i / 64
                angle = side * (math.pi / 2 + t * math.tau * 1.55)
                radius = .10 * (1 - .88 * t)
                path.append(clm_point(distance + side * .24 + radius * math.cos(angle),
                                      .93, 7.84 + radius * math.sin(angle)))
            tube(path, .015)
            scrolls += 1

added = []
for geometry in groups.values():
    obj = geometry.finish()
    added.append(obj.name)
    for modifier in list(obj.modifiers):
        obj.modifiers.remove(modifier)
changed = [name for name, prior in before.items() if fingerprint(bpy.data.objects[name]) != prior]
assert all(name.startswith('SAL_') for name in changed), changed
for name in ['room-studies.json', 'room-spaces.json', 'building-review.json']:
    (OUT / name).write_bytes((ROOT / 'result/blender/stage69' / name).read_bytes())
audit = {'version': 70, 'baseline': 69, 'storeyRemoval': [cut_bottom, cut_top],
         'changedExistingObjects': changed, 'removedDegenerateFaces': removed_faces,
         'remappedSashObjects': remapped, 'hiddenPreviousObjects': hidden,
         'sideWindows': side_windows, 'clementCapitalScrolls': scrolls, 'addedObjects': added,
         'salFrame': {'origin': list(sal_origin), 'right': list(u), 'outward': list(n)},
         'references': ['SAL September 10 2023, Jonas Magnus Lystad, Wikimedia Commons CC BY-SA 4.0',
                        'SAL Jestico + Whiles 2012 project photography, capture date unknown',
                        'CLM LSE property handbook page 18, capture date unknown'],
         'limitations': ['Floor count is photograph-supported; absolute heights and removal interval estimated',
                        'Oriel pane dimensions, blue paint and capital scroll profiles are estimates',
                        'Rear elevations, roof arrangement, carving and complete interiors remain unverified']}
(OUT / 'sal-clement-facade-audit.json').write_text(json.dumps(audit, indent=2) + '\n')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / 'result/blender/LSE_campus_detailed_v70.blend'))
print('SAL_CLEMENT_SAVED', len(changed), len(side_windows), scrolls)
