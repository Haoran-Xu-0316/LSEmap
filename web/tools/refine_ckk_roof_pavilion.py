"""Replace CKK's opaque rooftop block with a photo-guided pavilion and loggia.
Run in Blender Text Editor. Existing placement and height remain estimates.
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
OUT = ROOT / 'result/blender/stage80'
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(Path(__file__).resolve().parent))
from facade_geometry import Geometry, materials

bpy.ops.wm.open_mainfile(filepath=str(ROOT / 'result/blender/LSE_campus_detailed_v79.blend'))
bpy.context.window.scene = bpy.data.scenes['00_CAMPUS_COMPLETE']
site = json.loads((ROOT / 'result/blender/site_geometry.json').read_text())
centre = Vector((*next(b['center'] for b in site['buildings'] if b['code'] == 'CKK'), 0))
angle = math.radians(22)
axis_x = Vector((math.cos(angle), math.sin(angle), 0))
axis_y = Vector((-math.sin(angle), math.cos(angle), 0))

def point(x, y, z):
    return centre + axis_x*x + axis_y*y + Vector((0, 0, z))

def fingerprint(obj):
    digest = hashlib.sha256(str([list(row) for row in obj.matrix_world]).encode())
    if obj.type == 'MESH':
        digest.update(array.array('f', [c for v in obj.data.vertices for c in v.co]).tobytes())
        digest.update(array.array('i', [loop.vertex_index for loop in obj.data.loops]).tobytes())
    digest.update(str([m.name if m else None for m in getattr(obj.data, 'materials', [])]).encode())
    return digest.hexdigest()

before = {obj.name: fingerprint(obj) for obj in bpy.data.objects}
old = bpy.data.objects['CKK_setback_roof_wing']
old.hide_render = True
old.hide_set(True)
materials.clear()
for key, color, roughness, metallic, alpha in [
    ('frame', (.075, .090, .095), .30, .55, 1),
    ('steel', (.62, .65, .65), .32, .6, 1),
    ('roof', (.39, .43, .44), .58, .3, 1),
    ('paving', (.48, .49, .46), .88, 0, 1),
    ('glass', (.18, .27, .29), .19, .12, .55),
]:
    mat = bpy.data.materials.new('CKK_V80_' + key)
    mat.use_nodes = True
    mat.diffuse_color = (*color, alpha)
    shader = mat.node_tree.nodes['Principled BSDF']
    shader.inputs['Base Color'].default_value = (*color, 1)
    shader.inputs['Alpha'].default_value = alpha
    shader.inputs['Roughness'].default_value = roughness
    shader.inputs['Metallic'].default_value = metallic
    if key == 'glass':
        shader.inputs['Transmission Weight'].default_value = .12
        mat['webOpacity'] = .55
    materials[key] = mat
batches = {}

def batch(family, material):
    name = family + '_' + material
    if name not in batches:
        batches[name] = Geometry('CKK', 'pavilion80_' + name, material)
    return batches[name]

def box(family, material, x, y, z, width, depth, height):
    batch(family, material).box(point(x, y, z), (width, depth, height), angle)

def beam(family, material, start, end, width=.12):
    start, end = point(*start), point(*end)
    direction = (end-start).normalized()
    side = direction.cross(axis_x).normalized()
    normal = direction.cross(side).normalized()
    vertices = [p + a*width/2*side + b*width/2*normal
                for p in [start, end] for a, b in [(-1,-1),(-1,1),(1,1),(1,-1)]]
    faces = [(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]
    batch(family, material).add(vertices, [tuple(reversed(face)) for face in faces])

# Retain the former block's 5m x 28m envelope, 25m floor and 29m roof datum.
box('floor', 'paving', -18, 0, 25.06, 5, 28, .12)
box('roof', 'roof', -18, 0, 28.93, 5.12, 28.12, .14)
for x in [-20.5, -15.5]:
    for i in range(8):
        y = -14 + (i+.5)*3.5
        box('glazing', 'glass', x, y, 26.95, .045, 3.39, 3.66)
    for y in [-14 + i*3.5 for i in range(9)]:
        box('joinery', 'frame', x, y, 26.95, .10, .10, 3.8)
    for z in [25.12, 28.80]:
        box('joinery', 'frame', x, 0, z, .10, 28.1, .10)
for y in [-14, 14]:
    box('glazing', 'glass', -18, y, 26.95, 4.82, .045, 3.66)
    for x in [-20.5, -18, -15.5]:
        box('joinery', 'frame', x, y, 26.95, .10, .10, 3.8)
    for z in [25.12, 28.80]:
        box('joinery', 'frame', -18, y, z, 5.1, .10, .10)
# Pale structure and diagonals remain distinct from the dark glazing rails.
for y in [-14, -7, 0, 7, 14]:
    box('structure', 'steel', -15.72, y, 26.95, .16, .16, 3.68)
for y in [-10.5, 3.5]:
    beam('brace', 'steel', (-15.74,y-3.25,28.78), (-15.74,y,25.16), .14)
    beam('brace', 'steel', (-15.74,y+3.25,28.78), (-15.74,y,25.16), .14)
# The external sun-shading loggia follows the project photographs. Terrace depth
# is provisional and does not represent a verified contemporary furniture plan.
box('terrace', 'paving', -14.1, 0, 25.06, 2.8, 28, .12)
for y in [-14, -7, 0, 7, 14]:
    box('loggia_post', 'steel', -13.10, y, 26.94, .14, .14, 3.64)
    box('loggia_beam', 'frame', -14.25, y, 28.81, 2.6, .14, .18)
for x in [-15.50, -13.05]:
    box('loggia_edge', 'frame', x, 0, 28.90, .12, 28.14, .24)
for i in range(14):
    box('louvre', 'steel', -15.44+i*.18, 0, 28.94, .08, 28, .12)
# Solid low parapet and a light top rail match the fixed terrace perimeter.
box('parapet', 'paving', -12.72, 0, 25.50, .15, 28, .88)
box('guardrail', 'steel', -12.72, 0, 26.06, .045, 28.1, .045)
for y in [-14, -7, 0, 7, 14]:
    box('guardrail', 'steel', -12.72, y, 25.98, .035, .035, .20)

added = []
for geometry in batches.values():
    obj = geometry.finish()
    mesh = bmesh.new()
    mesh.from_mesh(obj.data)
    bmesh.ops.recalc_face_normals(mesh, faces=list(mesh.faces))
    mesh.to_mesh(obj.data)
    mesh.free()
    obj.data.update()
    for modifier in list(obj.modifiers):
        obj.modifiers.remove(modifier)
    added.append(obj.name)
changed = [name for name, value in before.items() if fingerprint(bpy.data.objects[name]) != value]
assert not changed, changed
for filename in ['room-studies.json', 'room-spaces.json', 'building-review.json']:
    (OUT / filename).write_bytes((ROOT / 'result/blender/stage79' / filename).read_bytes())
audit = {
    'version':80, 'baseline':79, 'hiddenPreviousObjects':[old.name],
    'changedExistingObjects':changed, 'addedObjects':added,
    'pavilionEnvelope':{'x':[-20.5,-15.5], 'y':[-14,14], 'z':[25,29]},
    'glazingPanels':18, 'louvres':14, 'loggiaPosts':5, 'braces':4,
    'referenceUrls':[
        'https://grimshaw.global/projects/education-and-science/london-school-of-economics-new-academic-building/',
        'https://www.willebrand.com/en/projects/lse-london-school-of-economics-grimshaw-architects.398'],
    'referenceFiles':['data/collections/library_round5/photos/CKK_6be44f0cc315.jpg',
                      'data/collections/library_round5/photos/CKK_a21dc17eb73f.jpg',
                      'data/collections/library_round5/photos/CKK_3e5594008a57.jpg'],
    'limitations':[
        'Roof pavilion and loggia are photo-guided, not a surveyed reconstruction',
        'Historical project photographs; precise capture date and 2026 arrangement unverified',
        'Inherited pavilion placement, footprint and roof height retained as estimates; terrace depth estimated',
        'Historic frontage, mansard, atrium geometry and other buildings retained',
        'Full executive meeting interiors, movable terrace furniture and remaining building elevations unresolved']
}
(OUT / 'ckk-roof-pavilion-audit.json').write_text(json.dumps(audit,indent=2)+'\n')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / 'result/blender/LSE_campus_detailed_v80.blend'))
print('CKK_ROOF_PAVILION_SAVED',len(added))
