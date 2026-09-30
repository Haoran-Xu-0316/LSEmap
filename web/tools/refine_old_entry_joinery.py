"""Correct OLD entrance joinery and rectangular stair approach from user photos.
Run in Blender Text Editor. Dimensions are estimates; the sculpture is retained.
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
OUT = ROOT / 'result/blender/stage65'
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(Path(__file__).resolve().parent))
from facade_geometry import Geometry, materials

bpy.ops.wm.open_mainfile(filepath=str(ROOT / 'result/blender/LSE_campus_detailed_v64.blend'))
bpy.context.window.scene = bpy.data.scenes['00_CAMPUS_COMPLETE']
frame = json.loads((ROOT / 'result/blender/stage52/old-houghton-audit.json').read_text())
origin, right, outward = [Vector(frame[key]) for key in ['origin', 'right', 'outward']]
angle = math.atan2(right.y, right.x)

def point(x, depth, height):
    return origin + right * x + outward * depth + Vector((0, 0, height))

def local(position):
    delta = position - origin
    return Vector((delta.dot(right), delta.dot(outward), position.z))

def fingerprint(obj):
    digest = hashlib.sha256(str([list(row) for row in obj.matrix_world]).encode())
    if obj.type == 'MESH':
        digest.update(array.array('f', [c for v in obj.data.vertices for c in v.co]).tobytes())
        digest.update(array.array('i', [loop.vertex_index for loop in obj.data.loops]).tobytes())
    digest.update(str([m.name if m else None for m in getattr(obj.data, 'materials', [])]).encode())
    return digest.hexdigest()

before = {obj.name: fingerprint(obj) for obj in bpy.data.objects}
hidden = ['OLD_Entrance_door_bronze_frame', 'OLD_Entrance_door_handles',
          'OLD_Entrance_transom', 'OLD_Entrance_cut_stone_steps',
          'OLD_Entrance_stainless_handrails', 'OLD_V52_Houghton_glass']
for name in hidden:
    obj = bpy.data.objects[name]
    obj.hide_render = True
    obj.hide_set(True)

# The former door frame shares a mesh with basement vents. Remove complete
# connected door members only, retaining every vent and all other elevations.
obj = bpy.data.objects['OLD_V52_Houghton_iron']
mesh = bmesh.new()
mesh.from_mesh(obj.data)
seen, removed, delete = set(), 0, []
for vertex in list(mesh.verts):
    if vertex in seen:
        continue
    stack, component = [vertex], []
    seen.add(vertex)
    while stack:
        current = stack.pop()
        component.append(current)
        for edge in current.link_edges:
            neighbor = edge.other_vert(current)
            if neighbor not in seen:
                seen.add(neighbor)
                stack.append(neighbor)
    points = [local(obj.matrix_world @ v.co) for v in component]
    if all(abs(p.x) < 2.81 and -.70 < p.y < -.48 and .60 < p.z < 4.20 for p in points):
        delete.extend(component)
        removed += 1
assert removed == 8, removed
bmesh.ops.delete(mesh, geom=delete, context='VERTS')
mesh.to_mesh(obj.data)
obj.data.update()
mesh.free()

materials.clear()
for key, color, roughness, metallic in [
    ('stone', (.56, .555, .53), .85, 0),
    ('frame', (.022, .028, .030), .36, .45),
    ('steel', (.46, .49, .50), .28, .85),
    ('glass', (.12, .175, .19), .18, .16),
]:
    material = bpy.data.materials.new('OLD_V65_' + key)
    material.use_nodes = True
    material.diffuse_color = (*color, 1)
    shader = material.node_tree.nodes['Principled BSDF']
    shader.inputs['Base Color'].default_value = material.diffuse_color
    shader.inputs['Roughness'].default_value = roughness
    shader.inputs['Metallic'].default_value = metallic
    materials[key] = material
batches = {}

def batch(key):
    if key not in batches:
        batches[key] = Geometry('OLD', 'entry65_' + key, key)
    return batches[key]

def box(key, x, depth, z, width, thickness, height):
    batch(key).box(point(x, depth, z), (width, thickness, height), angle)

def tube(key, start, end, radius):
    a, b = point(*start), point(*end)
    axis = (b - a).normalized()
    u = axis.cross(Vector((0, 0, 1)))
    if u.length < .01:
        u = right.copy()
    u.normalize()
    v = axis.cross(u).normalized()
    vertices = [p + radius * (u * math.cos(i * math.tau / 12) + v * math.sin(i * math.tau / 12))
                for p in [a, b] for i in range(12)]
    faces = [(i, (i + 1) % 12, (i + 1) % 12 + 12, i + 12) for i in range(12)]
    faces += [tuple(reversed(range(12))), tuple(range(12, 24))]
    batch(key).add(vertices, faces)

# Four separate glazed leaves under the existing relief, with a narrow transom.
for x in [-2.1, -.7, .7, 2.1]:
    box('glass', x, -.70, 2.16, 1.30, .045, 2.92)
    box('glass', x, -.70, 3.87, 1.30, .045, .39)
for x in [-2.8, -1.4, 0, 1.4, 2.8]:
    box('frame', x, -.575, 2.41, .085, .13, 3.44)
for z in [.69, 3.66, 4.13]:
    box('frame', 0, -.575, z, 5.68, .13, .085)
# Long U-shaped stainless pulls are paired around the two meeting stiles.
for seam in [-1.4, 1.4]:
    for side in [-1, 1]:
        x = seam + side * .13
        tube('steel', (x, -.39, 1.75), (x, -.39, 2.72), .021)
        for z in [1.75, 2.72]:
            tube('steel', (x, -.39, z), (x, -.52, z), .021)

# Replace the concentric chamfered stack with a rectangular landing and four
# straight risers. The right terrace extent is provisional, outside the crop.
box('stone', .4, -.10, .345, 9.60, 1.20, .69)
steps = []
for i in range(4):
    top = .69 - i * .1675
    depth = .50 + i * .50
    box('stone', -.6, depth + .25, top / 2, 7.60, .50, top)
    steps.append({'front': depth + .50, 'top': top, 'left': -4.40, 'right': 3.20})
box('stone', 4.0, 1.50, .345, 1.60, 2.0, .69)
# Fine paving joints on the landing stay confined to the stone surface.
for x in [-3.4, -2.4, -1.4, -.4, .6, 1.6, 2.6, 3.6]:
    box('frame', x, -.10, .6905, .008, 1.19, .001)

# Black upright supports with silver rails, including the photographed divider.
for x in [-4.20, 1.50]:
    tube('steel', (x, .35, 1.60), (x, 2.65, 1.01), .025)
    tube('steel', (x, -.40, 1.60), (x, .35, 1.60), .025)
    for depth, ground, top in [(-.35, .69, 1.60), (.45, .69, 1.574), (2.55, .02, 1.036)]:
        box('frame', x, depth, (ground + top) / 2, .075, .075, top - ground)
        box('steel', x, depth, ground + .014, .14, .14, .028)

added = []
for geometry in batches.values():
    new = geometry.finish()
    added.append(new.name)
    for modifier in list(new.modifiers):
        new.modifiers.remove(modifier)
changed = [name for name, prior in before.items() if fingerprint(bpy.data.objects[name]) != prior]
assert changed == ['OLD_V52_Houghton_iron'], changed
for name in ['room-studies.json', 'room-spaces.json', 'building-review.json']:
    (OUT / name).write_bytes((ROOT / 'result/blender/stage64' / name).read_bytes())
audit = {'version': 65, 'baseline': 64, 'changedExistingGeometry': changed,
         'hiddenPreviousObjects': hidden, 'removedDoorMembers': removed,
         'addedObjects': added, 'frame': frame, 'doorLeaves': 4,
         'steps': steps, 'reference': 'User supplied Houghton entrance photograph, capture date unknown',
         'limitations': ['Dimensions and terrace extent estimated, not a survey',
                        'Existing five-figure relief remains an authored interpretation',
                        'Heraldic carving, upper elevations, roof and complete interiors unresolved']}
(OUT / 'old-entry-joinery-audit.json').write_text(json.dumps(audit, indent=2) + '\n')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / 'result/blender/LSE_campus_detailed_v65.blend'))
print('OLD_ENTRY_JOINERY_SAVED', removed, len(steps))
