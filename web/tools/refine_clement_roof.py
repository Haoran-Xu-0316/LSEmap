"""Correct CLM roof character from dated 2018 and 2023 built photographs.
Run in Blender Text Editor. Heights and setbacks remain photographic estimates.
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
OUT = ROOT / 'result/blender/stage73'
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(Path(__file__).resolve().parent))
from facade_geometry import Geometry, materials
bpy.ops.wm.open_mainfile(filepath=str(ROOT / 'result/blender/LSE_campus_detailed_v72.blend'))
bpy.context.window.scene = bpy.data.scenes['00_CAMPUS_COMPLETE']
collection = bpy.data.collections['CLM_EXTERIOR']
def fingerprint(obj):
    h = hashlib.sha256(str([list(row) for row in obj.matrix_world]).encode())
    if obj.type == 'MESH':
        h.update(array.array('f', [c for v in obj.data.vertices for c in v.co]).tobytes())
        h.update(array.array('i', [l.vertex_index for l in obj.data.loops]).tobytes())
    h.update(str([m.name if m else None for m in getattr(obj.data, 'materials', [])]).encode())
    return h.hexdigest()
before = {o.name: fingerprint(o) for o in bpy.data.objects}
owned = {o.name for o in collection.all_objects}
hidden = ['CLM_D3_dormer_stone_cheeks', 'CLM_D3_dormer_cap']
for name in hidden:
    bpy.data.objects[name].hide_render = True
    bpy.data.objects[name].hide_set(True)
old_attic_bottom, old_eaves, old_roof_top = 22.85, 25.67, 29.15
new_eaves, new_roof_top = 24.50, 27.20
removed = {}
def height(z):
    if z <= old_attic_bottom:
        return z
    if z < old_eaves:
        return old_attic_bottom + (z - old_attic_bottom) * (new_eaves - old_attic_bottom) / (old_eaves - old_attic_bottom)
    return new_eaves + (z - old_eaves) * (new_roof_top - new_eaves) / (old_roof_top - old_eaves)
def components(mesh):
    parent = list(range(len(mesh.vertices)))
    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    for edge in mesh.edges:
        a, b = [find(i) for i in edge.vertices]
        parent[a] = b
    groups = {}
    for vertex in mesh.vertices:
        groups.setdefault(find(vertex.index), []).append(vertex.index)
    return groups.values()
for obj in list(collection.all_objects):
    if obj.type != 'MESH' or obj.hide_render:
        continue
    if any(k in obj.name.lower() for k in ['window', 'recess', 'sash', 'glazing', 'bead', '_v16_', '_v17_']):
        selected = []
        for indices in components(obj.data):
            if all((obj.matrix_world @ obj.data.vertices[i].co).z > 22.83 for i in indices):
                selected.extend(indices)
        if selected:
            mesh = bmesh.new()
            mesh.from_mesh(obj.data)
            mesh.verts.ensure_lookup_table()
            bmesh.ops.delete(mesh, geom=[mesh.verts[i] for i in selected], context='VERTS')
            mesh.to_mesh(obj.data)
            mesh.free()
            removed[obj.name] = len(selected)
    inverse = obj.matrix_world.inverted()
    changed = False
    for vertex in obj.data.vertices:
        p = obj.matrix_world @ vertex.co
        new_z = height(p.z)
        if abs(new_z - p.z) > .00001:
            p.z = new_z
            vertex.co = inverse @ p
            changed = True
    if changed:
        obj.data.update()
        if obj.data.uv_layers:
            layer = obj.data.uv_layers.active
            for poly in obj.data.polygons:
                points = [obj.matrix_world @ obj.data.vertices[i].co for i in poly.vertices]
                if len(points) < 3:
                    continue
                origin = points[0]
                u = (points[1] - origin).normalized()
                normal = (points[1] - origin).cross(points[-1] - origin).normalized()
                v = normal.cross(u)
                for loop, point in zip(poly.loop_indices, points):
                    layer.data[loop].uv = ((point - origin).dot(u), (point - origin).dot(v))
materials.clear()
materials['stone'] = bpy.data.materials['CLM_D3_Portland_stone']
for key, color, roughness in [('slate', (.055, .060, .061), .87), ('asphalt', (.039, .042, .041), .97), ('metal', (.045, .049, .047), .55), ('paint', (.47, .48, .44), .56), ('joint', (.27, .255, .22), .9)]:
    mat = bpy.data.materials.new('CLM_V73_' + key)
    mat.use_nodes = True
    mat.diffuse_color = (*color, 1)
    shader = mat.node_tree.nodes['Principled BSDF']
    shader.inputs['Base Color'].default_value = mat.diffuse_color
    shader.inputs['Roughness'].default_value = roughness
    materials[key] = mat
materials['glass'] = bpy.data.objects['CLM_D3_window_glass'].data.materials[0].copy()
materials['glass'].name = 'CLM_V73_glass'
for name, key in [('CLM_D3_slate_mansard_planes', 'slate'), ('CLM_D3_mansard_flat_top', 'asphalt')]:
    obj = bpy.data.objects[name]
    obj.data.materials[0] = materials[key]
site = json.loads((ROOT / 'result/blender/site_geometry.json').read_text())
building = next(b for b in site['buildings'] if b['code'] == 'CLM')
ring = building['rings'][0]
points = [Vector(ring[i]) for i in (5, 4, 3, 2, 1)]
center = Vector(building['center'])
segments, length = [], 0
for a, b in zip(points, points[1:]):
    u = (b - a).normalized()
    n = Vector((u.y, -u.x))
    if n.dot((a + b) / 2 - center) < 0:
        n = -n
    size = (b - a).length
    segments.append((length, length + size, a, u, n))
    length += size
bay = length / 7
def point(s, d, z):
    segment = next((p for p in segments if s <= p[1]), segments[-1])
    start, end, a, u, n = segment
    p = a + u * (s - start) + n * d
    return Vector((p.x, p.y, z))
batches = {}
def batch(key, family):
    name = key + '_' + family
    if name not in batches:
        batches[name] = Geometry('CLM', 'roof73_' + family + '_' + key, key)
    return batches[name]
def box(key, family, s, d, z, w, depth, h):
    vertices = [point(s + x * w / 2, d + y * depth / 2, z + k * h / 2) for x, y, k in [(-1,-1,-1),(-1,-1,1),(-1,1,-1),(-1,1,1),(1,-1,-1),(1,-1,1),(1,1,-1),(1,1,1)]]
    batch(key, family).add(vertices, [(0,4,6,2),(1,3,7,5),(0,1,5,4),(2,6,7,3),(0,2,3,1),(4,5,7,6)])
def window(s, d, z, w, h, family, columns):
    box('glass', family, s, d, z, w, .025, h)
    frame = 'paint' if family == 'dormer' else 'metal'
    for side in [-1, 1]:
        box(frame, family, s + side * w / 2, d + .03, z, .055, .06, h + .07)
        box(frame, family, s, d + .03, z + side * h / 2, w + .06, .06, .055)
    for j in range(1, columns):
        box(frame, family, s - w / 2 + j * w / columns, d + .034, z, .032, .054, h)
    box(frame, family, s, d + .037, z, w, .054, .032)
for i in range(7):
    window((i + .5) * bay, -1.04, height(24.20), 1.68, 1.04, 'attic', 3)
# Five dormers, with shallow curved dark caps and metal cheeks, occupy middle bays.
for i in range(1, 6):
    s = (i + .5) * bay
    z = 25.68
    window(s, -.96, z, 1.20, 1.42, 'dormer', 2)
    for side in [-1, 1]:
        box('metal', 'dormer', s + side * .69, -1.42, z, .16, 1.0, 1.67)
    box('metal', 'dormer', s, -1.40, z - .77, 1.50, 1.0, .13)
    # A shallow segmental camber replaces the former flat stone hood.
    for j in range(24):
        x0, x1 = -.79 + 1.58 * j / 24, -.79 + 1.58 * (j + 1) / 24
        h0, h1 = z + .90 + .09 * (1 - (x0 / .79)**2), z + .90 + .09 * (1 - (x1 / .79)**2)
        vertices = [point(s + x, d, h) for d in [-1.95, -.77] for x, h in [(x0,h0),(x1,h1)]]
        face = (0, 1, 3, 2)
        if (vertices[1] - vertices[0]).cross(vertices[2] - vertices[0]).z < 0:
            face = tuple(reversed(face))
        batch('metal', 'caps').add(vertices, [face])
        batch('metal', 'cap_fascia').add([point(s + x0, -.77, z + .825), point(s + x1, -.77, z + .825), point(s + x1, -.77, h1), point(s + x0, -.77, h0)], [(0,1,2,3)])
# Four tall rusticated stone stacks are visible in both dated photographs.
stacks = [(.25 * bay, 3.1), (2.25 * bay, 4.1), (4.75 * bay, 4.1), (6.75 * bay, 3.1)]
for s, rise in stacks:
    base, top = new_eaves, new_eaves + rise
    box('stone', 'chimneys', s, -1.72, (base + top) / 2, .94, 1.30, rise)
    for side in [-1, 1]:
        box('stone', 'chimney_pilasters', s + side * .39, -1.04, (base + top) / 2, .14, .13, rise - .20)
    for j in range(1, int(rise / .42)):
        box('joint', 'chimney_courses', s, -1.05, base + j * .42, .94, .014, .015)
    for z, w, depth, h in [(top - .13, 1.16, 1.48, .12), (top, 1.30, 1.62, .10), (top + .10, .94, 1.26, .12)]:
        box('stone', 'chimney_caps', s, -1.72, z, w, depth, h)
# Retain the shallow continuous iron railing seen across the attic frontage.
for z in [23.20, 23.46, 23.72]:
    for j in range(64):
        s0, s1 = j * length / 64, (j + 1) * length / 64
        box('metal', 'attic_rail', (s0 + s1) / 2, -.42, z, s1 - s0 + .005, .026, .026)
for j in range(35):
    box('metal', 'attic_rail', j * length / 34, -.42, 23.46, .025, .026, .54)
added = []
for geometry in batches.values():
    obj = geometry.finish()
    added.append(obj.name)
    for modifier in list(obj.modifiers):
        obj.modifiers.remove(modifier)
changed = [name for name, value in before.items() if fingerprint(bpy.data.objects[name]) != value]
assert all(name in owned for name in changed), changed
for name in ['room-studies.json', 'room-spaces.json', 'building-review.json']:
    (OUT / name).write_bytes((ROOT / 'result/blender/stage72' / name).read_bytes())
audit = {'version': 73, 'baseline': 72, 'dormerCount': 5, 'chimneyCount': 4, 'atticHeightEstimate': 1.65, 'mansardRiseEstimate': 2.70, 'newEaves': new_eaves, 'newRoofTop': new_roof_top, 'addedObjects': added, 'changedExistingObjects': changed, 'hiddenPreviousObjects': hidden, 'removedUpperWindowVertices': removed, 'stacks': stacks, 'length': length, 'references': 'Dated 2018-04-24 and 2023-11-15 CLM photographs, see private stage73/references.json', 'limitations': ['Heights, setbacks, stack positions and ornamental profiles remain photographic estimates', 'Dated photographs are not a 2026 rooftop survey; recent plant works are not presumed complete', 'Exact rear roof plan, equipment and complete interiors remain unresolved']}
(OUT / 'clement-roof-audit.json').write_text(json.dumps(audit, indent=2) + '\n')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / 'result/blender/LSE_campus_detailed_v73.blend'))
print('CLEMENT_ROOF_SAVED', len(changed), len(added))
