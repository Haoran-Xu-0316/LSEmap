"""Photo-guided radial masonry and carved shield surround for OLD.
Run in Blender Text Editor. Heraldic devices remain unresolved, not invented.
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
OUT = ROOT / 'result/blender/stage69'
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(Path(__file__).resolve().parent))
from facade_geometry import Geometry, materials

bpy.ops.wm.open_mainfile(filepath=str(ROOT / 'result/blender/LSE_campus_detailed_v68.blend'))
bpy.context.window.scene = bpy.data.scenes['00_CAMPUS_COMPLETE']
frame = json.loads((ROOT / 'result/blender/stage52/old-houghton-audit.json').read_text())
origin, right, outward = [Vector(frame[key]) for key in ['origin', 'right', 'outward']]

def point(x, depth, z):
    return origin + right * x + outward * depth + Vector((0, 0, z))

def fingerprint(obj):
    digest = hashlib.sha256(str([list(row) for row in obj.matrix_world]).encode())
    if obj.type == 'MESH':
        digest.update(array.array('f', [c for v in obj.data.vertices for c in v.co]).tobytes())
        digest.update(array.array('i', [loop.vertex_index for loop in obj.data.loops]).tobytes())
    digest.update(str([m.name if m else None for m in getattr(obj.data, 'materials', [])]).encode())
    return digest.hexdigest()

before = {obj.name: fingerprint(obj) for obj in bpy.data.objects}
hidden = ['OLD_V56_Entry_reveal', 'OLD_V56_Entry_joint', 'OLD_V56_Entry_rim',
          'OLD_Heraldic_shield_simplified']
for name in hidden:
    obj = bpy.data.objects[name]
    obj.hide_render = True
    obj.hide_set(True)

materials.clear()
for key, color in [('stone', (.61, .595, .55)), ('recess', (.48, .475, .44)),
                   ('joint', (.43, .425, .40)), ('letter', (.40, .395, .36))]:
    material = bpy.data.materials.new('OLD_V69_' + key)
    material.use_nodes = True
    material.diffuse_color = (*color, 1)
    shader = material.node_tree.nodes['Principled BSDF']
    shader.inputs['Base Color'].default_value = material.diffuse_color
    shader.inputs['Roughness'].default_value = .85
    materials[key] = material
batches = {}

def batch(key):
    if key not in batches:
        batches[key] = Geometry('OLD', 'arch69_' + key, key)
    return batches[key]

def face(key, vertices):
    # These shallow relief faces must face the street in both native and GLB.
    vertices = [Vector(p) for p in vertices]
    normal = (vertices[1] - vertices[0]).cross(vertices[-1] - vertices[0])
    if normal.dot(outward) < 0:
        vertices.reverse()
    batch(key).add(vertices, [tuple(range(len(vertices)))])

def clip_polygon(polygon, axis, value, keep_less):
    result = []
    for previous, current in zip(polygon[-1:] + polygon[:-1], polygon):
        inside = lambda p: p[axis] <= value if keep_less else p[axis] >= value
        if inside(previous) != inside(current):
            t = (value - previous[axis]) / (current[axis] - previous[axis])
            result.append(tuple(a + t * (b - a) for a, b in zip(previous, current)))
        if inside(current):
            result.append(current)
    return result

# Broader wedge courses replace the former narrow concentric border. Their
# outer tails cover horizontal ashlar joints only inside the photographed fan.
segments = 20
profile = [(2.90 + 1.30 * j / 12, -.63 + .85 * (j / 12) ** .65) for j in range(13)]
outer_faces = 0
for segment in range(segments):
    start, end = segment * math.pi / segments, (segment + 1) * math.pi / segments
    a, b = start + .0015, end - .0015
    for (r0, d0), (r1, d1) in zip(profile, profile[1:]):
        for key, ta, tb, offset in [('stone', a, b, 0), ('joint', start, end, -.014)]:
            face(key, [point(r * math.cos(t), d + offset, 4.8 + r * math.sin(t))
                       for r, d, t in [(r0, d0, ta), (r1, d1, ta), (r1, d1, tb), (r0, d0, tb)]])
    # Faceted arc sampling is kept fine; only the visible stone joint count falls.
    angles = [a + (b - a) * j / 8 for j in range(9)]
    polygon = [(4.2 * math.cos(t), 4.8 + 4.2 * math.sin(t)) for t in angles]
    polygon += [(6.8 * math.cos(t), 4.8 + 6.8 * math.sin(t)) for t in reversed(angles)]
    for axis, value, keep_less in [(0, -4.75, False), (0, 4.75, True), (1, 10.32, True)]:
        if polygon:
            polygon = clip_polygon(polygon, axis, value, keep_less)
    if len(polygon) >= 3:
        face('stone', [point(x, .239, z) for x, z in polygon])
        outer_faces += 1
    # A recessed continuous backing makes radial joints legible without
    # exposing the unrelated horizontal courses behind the wedge stones.
    angles = [start + (end - start) * j / 8 for j in range(9)]
    backing = [(4.2 * math.cos(t), 4.8 + 4.2 * math.sin(t)) for t in angles]
    backing += [(6.8 * math.cos(t), 4.8 + 6.8 * math.sin(t)) for t in reversed(angles)]
    for axis, value, keep_less in [(0, -4.75, False), (0, 4.75, True), (1, 10.32, True)]:
        if backing:
            backing = clip_polygon(backing, axis, value, keep_less)
    if len(backing) >= 3:
        face('joint', [point(x, .227, z) for x, z in backing])
    # A small dressed lip remains at the edge of the recessed artwork.
    for j in range(8):
        ta, tb = a + (b - a) * j / 8, a + (b - a) * (j + 1) / 8
        face('stone', [point(r * math.cos(t), -.575, 4.8 + r * math.sin(t))
                       for r, t in [(2.84, ta), (2.92, ta), (2.92, tb), (2.84, tb)]])

# A shallow shield inset and doubled carved border replace the solid blank slab.
# The central heraldic device cannot be recovered reliably from this photograph.
shield = [(-.60, 10.76), (.60, 10.76), (.69, 10.14), (.57, 9.62),
          (.27, 9.39), (0, 9.28), (-.27, 9.39), (-.57, 9.62), (-.69, 10.14)]
center = Vector((0, 10.05))
for outer_scale, inner_scale, depth in [(1.12, 1.0, .81), (.96, .88, .835)]:
    for i, a in enumerate(shield):
        b = shield[(i + 1) % len(shield)]
        vertices = []
        for p, scale in [(a, outer_scale), (b, outer_scale), (b, inner_scale), (a, inner_scale)]:
            q = center + (Vector(p) - center) * scale
            vertices.append(point(q.x, depth, q.y))
        face('stone', vertices)
face('recess', [point(x * .88, .785, center.y + (z - center.y) * .88) for x, z in shield])
# The scroll has a shallow sag and turned-back ends rather than a rectangular sign.
ribbon_segments = 24
for i in range(ribbon_segments):
    x0, x1 = -1.13 + 2.26 * i / ribbon_segments, -1.13 + 2.26 * (i + 1) / ribbon_segments
    z0, z1 = 9.16 + .12 * (x0 / 1.13) ** 2, 9.16 + .12 * (x1 / 1.13) ** 2
    face('stone', [point(x0, .89, z0 - .10), point(x1, .89, z1 - .10),
                   point(x1, .89, z1 + .10), point(x0, .89, z0 + .10)])
for side in [-1, 1]:
    face('stone', [point(side * 1.08, .89, 9.18), point(side * 1.32, .71, 9.24),
                   point(side * 1.21, .70, 9.40), point(side * 1.06, .89, 9.38)])
# The legible motto in the supplied image is laid out along the stone scroll.
text = 'RERUM COGNOSCERE CAUSAS'
curve = bpy.data.curves.new('OLD_V69_scroll_motto', 'FONT')
curve.body, curve.align_x, curve.align_y = text, 'CENTER', 'CENTER'
curve.size, curve.space_character, curve.extrude = .105, 1.05, .001
curve.materials.append(materials['letter'])
font_path = Path('/System/Library/Fonts/Supplemental/Times New Roman.ttf')
if font_path.exists():
    curve.font = bpy.data.fonts.load(str(font_path))
motto = bpy.data.objects.new('OLD_V69_scroll_motto', curve)
bpy.data.collections['OLD_EXTERIOR'].objects.link(motto)
motto.location = point(0, .895, 9.17)
motto.rotation_euler = Matrix((Vector((0, 0, 1)).cross(outward), Vector((0, 0, 1)), outward)).transposed().to_euler()
added = [motto.name]
for geometry in batches.values():
    obj = geometry.finish()
    added.append(obj.name)
    for modifier in list(obj.modifiers):
        obj.modifiers.remove(modifier)
changed = [name for name, prior in before.items() if fingerprint(bpy.data.objects[name]) != prior]
assert changed == [], changed
for name in ['room-studies.json', 'room-spaces.json', 'building-review.json']:
    (OUT / name).write_bytes((ROOT / 'result/blender/stage68' / name).read_bytes())
audit = {'version': 69, 'baseline': 68, 'frame': frame, 'archSegments': segments,
         'outerFanStones': outer_faces, 'motto': text, 'addedObjects': added,
         'hiddenPreviousObjects': hidden, 'changedExistingGeometry': changed,
         'reference': 'User supplied OLD Houghton entrance close photograph, capture date unknown',
         'limitations': ['Stone joint count, profile and dimensions estimated from the photograph',
                        'Central heraldic device remains unresolved; no invented arms',
                        'Existing figure relief is an authored interpretation, not an exact sculpture reproduction',
                        'Upper elevations, roof and complete interiors remain unresolved']}
(OUT / 'old-arch-masonry-audit.json').write_text(json.dumps(audit, indent=2) + '\n')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / 'result/blender/LSE_campus_detailed_v69.blend'))
print('OLD_ARCH_MASONRY_SAVED', outer_faces, len(added))
