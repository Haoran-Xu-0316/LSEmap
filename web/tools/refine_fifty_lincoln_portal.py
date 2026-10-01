"""Rebuild No.50's photographed stone portal without neighboring round windows.
Run in Blender Text Editor. Heights and carved profiles are photo estimates.
"""
from pathlib import Path
import array
import hashlib
import json
import math
import sys
import bpy
from mathutils import Matrix, Vector
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'result/blender/stage72'
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(Path(__file__).resolve().parent))
from facade_geometry import Geometry, materials
bpy.ops.wm.open_mainfile(filepath=str(ROOT / 'result/blender/LSE_campus_detailed_v71.blend'))
bpy.context.window.scene = bpy.data.scenes['00_CAMPUS_COMPLETE']
profile = next(p for p in json.loads((ROOT / 'result/blender/stage08/coopers-geometry.json').read_text())['profiles'] if p['code'] == '50L')
a, b = map(Vector, [profile['ring'][5], profile['ring'][0]])
u = (b - a).normalized()
n = Vector((u.y, -u.x))
if n.dot((a + b) / 2 - Vector(profile['center'])) < 0:
    n = -n
length = (b - a).length
count = max(2, round(length / 2.8))
x = (count - .5) * length / count
position = a + u * x
origin = Vector((position.x, position.y, 0))
outward = Vector((*n, 0))
right = Vector((0, 0, 1)).cross(outward)
collection = bpy.data.collections['50L_EXTERIOR']
def point(x, d, z):
    return origin + right * x + outward * d + Vector((0, 0, z))
def fingerprint(obj):
    h = hashlib.sha256(str([list(row) for row in obj.matrix_world]).encode())
    if obj.type == 'MESH':
        h.update(array.array('f', [c for v in obj.data.vertices for c in v.co]).tobytes())
        h.update(array.array('i', [l.vertex_index for l in obj.data.loops]).tobytes())
    h.update(str([m.name if m else None for m in getattr(obj.data, 'materials', [])]).encode())
    return h.hexdigest()
before = {o.name: fingerprint(o) for o in bpy.data.objects}
hidden = []
for obj in list(collection.all_objects):
    old_portal = obj.name.startswith(('50L_V19_REM_', '50L_V20_EXT_')) and 'retained_' not in obj.name
    old_entry = obj.name in ['50L_D5_arched_entry_stone', '50L_D5_entry_header_stone', '50L_D5_sign.001']
    if old_portal or old_entry:
        obj.hide_render = True
        obj.hide_set(True)
        hidden.append(obj.name)
materials.clear()
colors = {'stone': (.50, .405, .275), 'recess': (.39, .315, .215), 'wood': (.18, .095, .043), 'panel': (.155, .081, .035), 'glass': (.019, .023, .026), 'iron': (.033, .038, .036), 'brass': (.48, .34, .13), 'steel': (.34, .37, .38), 'step': (.39, .375, .33), 'red': (.62, .008, .014), 'paint': (.78, .79, .76)}
for key, color in colors.items():
    mat = bpy.data.materials.new('50L_V72_' + key)
    mat.use_nodes = True
    mat.diffuse_color = (*color, 1)
    shader = mat.node_tree.nodes['Principled BSDF']
    shader.inputs['Base Color'].default_value = mat.diffuse_color
    shader.inputs['Roughness'].default_value = .86 if key in ['stone', 'recess', 'step'] else .52
    if key in ['brass', 'steel']:
        shader.inputs['Metallic'].default_value = .65
        shader.inputs['Roughness'].default_value = .32
    materials[key] = mat
batches = {}
def batch(key):
    if key not in batches:
        batches[key] = Geometry('50L', 'portal72_' + key, key)
    return batches[key]
def box(key, x, d, z, width, depth, height):
    batch(key).box(point(x, d, z), (width, depth, height), math.atan2(right.y, right.x))
def face(key, vertices):
    vertices = [Vector(v) for v in vertices]
    if (vertices[1] - vertices[0]).cross(vertices[-1] - vertices[0]).dot(outward) < 0:
        vertices.reverse()
    batch(key).add(vertices, [tuple(range(len(vertices)))])
def ring(key, inner, outer, spring, depth, segments=64):
    for j in range(segments):
        a, b = j * math.pi / segments, (j + 1) * math.pi / segments
        face(key, [point(r * math.cos(t), depth, spring + r * math.sin(t)) for r, t in [(inner, a), (outer, a), (outer, b), (inner, b)]])
def ball(key, x, d, z, radius):
    vertices = [point(x + radius * math.cos(p) * math.cos(t), d + radius * math.cos(p) * math.sin(t), z + radius * math.sin(p)) for p in [-math.pi / 2 + math.pi * j / 8 for j in range(9)] for t in [math.tau * k / 16 for k in range(16)]]
    batch(key).add(vertices, [(j * 16 + k, j * 16 + (k + 1) % 16, (j + 1) * 16 + (k + 1) % 16, (j + 1) * 16 + k) for j in range(8) for k in range(16)])
width, spring, radius = 1.55, 2.70, .775
# Broad sandstone piers cover the formerly exposed brick around the doorway.
for side in [-1, 1]:
    box('stone', side * .9725, .115, 1.35, .395, .34, 2.70)
    for z in [.64, 1.29, 1.90, 2.42]:
        box('recess', side * .9725, .291, z, .395, .012, .012)
    box('stone', side * 1.13, .185, 3.18, .12, .38, 1.01)
# Solid curved shoulders with a real semicircular opening, not a stone plug.
for j in range(80):
    xx = -1.17 + (j + .5) * 2.34 / 80
    low = spring + math.sqrt(max(0, radius * radius - xx * xx)) if abs(xx) < radius else spring
    box('stone', xx, .11, (low + 3.97) / 2, 2.34 / 80 + .0005, .33, 3.97 - low)
ring('stone', radius, 1.00, spring, .285)
ring('recess', radius - .037, radius + .013, spring, .299)
# Shallow panelled frieze and cornice, observed above the arch.
for j in range(7):
    xx = -.90 + j * .30
    low = spring + math.sqrt(max(0, 1.02**2 - xx**2)) + .035
    high = 3.94
    if high - low > .08:
        box('recess', xx, .290, (low + high) / 2, .225, .014, high - low)
        for side in [-1, 1]:
            box('stone', xx + side * .113, .320, (low + high) / 2, .030, .050, high - low)
        box('stone', xx, .325, high, .265, .070, .050)
for z, w, depth, height in [(3.99, 2.50, .48, .10), (4.09, 2.58, .57, .09)]:
    box('stone', 0, .19, z, w, depth, height)
# Dark unbarred fanlight, wood head rail and six raised rectangular door panels.
outline = [point(0, -.19, spring)] + [point(radius * math.cos(t), -.19, spring + radius * math.sin(t)) for t in [j * math.pi / 64 for j in range(65)]]
batch('glass').add(outline, [(0, j + 1, j + 2) for j in range(64)])
ring('wood', radius - .028, radius, spring, -.12)
box('stone', 0, .20, spring - .04, 1.80, .35, .12)
for side in [-1, 1]:
    xx = side * width / 4
    box('wood', xx, -.18, 1.48, width / 2 - .014, .055, 2.44)
    for z, h in [(.67, .61), (1.76, .68), (2.38, .40)]:
        box('panel', xx, -.139, z, .55, .018, h)
        for edge in [-1, 1]:
            box('wood', xx + edge * .285, -.112, z, .032, .034, h + .065)
            box('wood', xx, -.112, z + edge * (h / 2 + .015), .60, .034, .032)
    key = 'iron' if side < 0 else 'brass'
    ball(key, xx, -.05, 1.20, .044)
box('wood', 0, -.109, 1.48, .035, .06, 2.44)
for side in [-1, 1]:
    box('wood', side * .771, -.095, 1.48, .052, .06, 2.44)
box('wood', 0, -.095, 2.65, 1.55, .07, .075)
box('iron', -width / 4, -.092, 1.00, .30, .026, .102)
box('recess', -width / 4, -.074, 1.012, .235, .011, .038)
for z, d in [(.13, .31), (.26, .14)]:
    box('step', 0, d, z / 2, 1.64, .32, z)
    box('steel', 0, d + .162, z, 1.61, .033, .024)
# Painted pier numbers and a small modern address plaque belong to No.50.
letters = []
rotation = Matrix((right, Vector((0, 0, 1)), outward)).transposed().to_euler()
for side in [-1, 1]:
    curve = bpy.data.curves.new('50L_V72_pier_number', 'FONT')
    curve.body, curve.align_x, curve.size, curve.extrude = '50', 'CENTER', .19, .001
    curve.materials.append(materials['iron'])
    obj = bpy.data.objects.new(curve.name, curve)
    collection.objects.link(obj)
    obj.location, obj.rotation_euler = point(side * .97, .300, 1.92), rotation
    letters.append(obj.name)
box('iron', 1.025, .322, .81, .30, .028, .35)
box('brass', 1.025, .340, .977, .30, .008, .014)
box('red', .942, .342, .926, .092, .008, .07)
for body, xx, z, size in [('LSE', .942, .905, .040), ("50 Lincoln's", 1.022, .838, .044), ('Inn Fields', 1.009, .772, .044)]:
    curve = bpy.data.curves.new('50L_V72_address', 'FONT')
    curve.body, curve.align_x, curve.size, curve.extrude = body, 'CENTER', size, .0005
    curve.materials.append(materials['paint'])
    obj = bpy.data.objects.new(curve.name, curve)
    collection.objects.link(obj)
    obj.location, obj.rotation_euler = point(xx, .349, z), rotation
    letters.append(obj.name)
added = letters.copy()
for g in batches.values():
    obj = g.finish()
    added.append(obj.name)
    for modifier in list(obj.modifiers):
        obj.modifiers.remove(modifier)
changed = [name for name, value in before.items() if fingerprint(bpy.data.objects[name]) != value]
assert not changed, changed
for name in ['room-studies.json', 'room-spaces.json', 'building-review.json']:
    (OUT / name).write_bytes((ROOT / 'result/blender/stage71' / name).read_bytes())
audit = {'version': 72, 'baseline': 71, 'frame': {'origin': list(origin), 'right': list(right), 'outward': list(outward)}, 'addedObjects': added, 'hiddenPreviousObjects': hidden, 'changedExistingGeometry': changed, 'doorPanels': 6, 'friezePanels': 7, 'fanlightRadialBars': 0, 'reference': 'LSE property handbook 2025/26 No.50 entrance photograph, capture date unknown', 'limitations': ['Portal dimensions and ornament estimated from photography', 'Neighboring 49L and 50A round windows excluded from the No.50 portal', 'Upper elevations, roof and complete interior still require review']}
(OUT / 'fifty-lincoln-portal-audit.json').write_text(json.dumps(audit, indent=2) + '\n')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / 'result/blender/LSE_campus_detailed_v72.blend'))
print('FIFTY_LINCOLN_PORTAL_SAVED', len(added))
