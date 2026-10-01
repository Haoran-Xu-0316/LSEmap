"""Refine photographed 5LF chimney finish and facade rainwater pipes.
Run in Blender Text Editor. Keep native 90 and every original object intact.
Undated LSE Estate imagery guides colors and pipe placement; dimensions estimated.
"""
from pathlib import Path
import array, hashlib, json, math, shutil
import bpy, bmesh
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'result/blender/stage91'
OUT.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v90.blend'))
bpy.context.window.scene = bpy.data.scenes['00_CAMPUS_COMPLETE']

def fingerprint(obj):
    digest = hashlib.sha256(str([list(row) for row in obj.matrix_world]).encode())
    if obj.type == 'MESH':
        digest.update(array.array('f', [c for v in obj.data.vertices for c in v.co]).tobytes())
        digest.update(array.array('i', [loop.vertex_index for loop in obj.data.loops]).tobytes())
    digest.update(str([m.name if m else None for m in getattr(obj.data, 'materials', [])]).encode())
    return digest.hexdigest()

before = {obj.name: fingerprint(obj) for obj in bpy.data.objects}
source = bpy.data.objects['5LF_D5_chimney_stack_brick']
stack = source.copy()
stack.data = source.data.copy()
stack.name = '5LF_D5_rainwater91_chimney_stacks'
bpy.data.collections['5LF_EXTERIOR'].objects.link(stack)
brick = source.data.materials[0].copy()
brick.name = '5LF_V91_weathered_chimney_brick'
brick.diffuse_color = (.10, .085, .066, 1)
brick.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = brick.diffuse_color
for node in brick.node_tree.nodes:
    if node.type == 'TEX_BRICK':
        node.inputs['Color1'].default_value = (.10, .085, .066, 1)
        node.inputs['Color2'].default_value = (.07, .061, .048, 1)
        node.inputs['Mortar'].default_value = (.13, .12, .105, 1)
stack.data.materials.clear()
stack.data.materials.append(brick)
source.hide_render = True
source.hide_set(True)

building = next(b for b in json.loads((ROOT/'result/blender/site_geometry.json').read_text())['buildings'] if b['id'] == 'way/1184094775')
ring = building['rings'][0]
a, b = Vector((*ring[1], 0)), Vector((*ring[2], 0))
right = (b-a).normalized()
normal = Vector((right.y, -right.x, 0))
if normal.dot((a+b)/2-Vector((*building['center'], 0))) < 0:
    normal = -normal
length = (b-a).length

def point(x, depth, height):
    return a + right*x + normal*depth + Vector((0, 0, height))

metal = bpy.data.materials.new('5LF_V91_black_rainwater_metal')
metal.use_nodes = True
metal.diffuse_color = (.013, .016, .015, 1)
shader = metal.node_tree.nodes['Principled BSDF']
shader.inputs['Base Color'].default_value = metal.diffuse_color
shader.inputs['Roughness'].default_value = .68
shader.inputs['Metallic'].default_value = .15
collection = bpy.data.collections['5LF_EXTERIOR']
added = [stack.name]
pipe_records = []
for side, x in [('start', .055), ('end', length-.055)]:
    # Small offsets carry the pipe across the plaster-to-brick course.
    path = [point(x, .09, .55), point(x, .09, 4.15),
            point(x, .16, 4.31), point(x, .16, 13.92)]
    vertices = []
    for center in path:
        for i in range(12):
            angle = math.tau*i/12
            vertices.append(center + .035*(right*math.cos(angle)+normal*math.sin(angle)))
    faces = [tuple(reversed(range(12))), tuple(range(36, 48))]
    for row in range(3):
        for i in range(12):
            j = (i+1)%12
            faces.append((row*12+i, row*12+j, (row+1)*12+j, (row+1)*12+i))
    mesh = bpy.data.meshes.new('5LF_rainwater91_'+side)
    mesh.from_pydata(vertices, [], faces)
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(mesh)
    bm.free()
    mesh.materials.append(metal)
    obj = bpy.data.objects.new('5LF_D5_rainwater91_pipe_'+side, mesh)
    collection.objects.link(obj)
    obj['scope'] = 'Two photographed facade-edge rainwater pipes; diameter and offsets estimated'
    # Smooth round pipe walls, retain flat terminal caps.
    for face in mesh.polygons:
        face.use_smooth = len(face.vertices) == 4
    added.append(obj.name)
    pipe_records.append({'name': obj.name, 'centerline': [list(p) for p in path], 'radius': .035})

assert all(fingerprint(bpy.data.objects[name]) == value for name, value in before.items())
for name in ['room-studies.json', 'room-spaces.json', 'building-review.json']:
    shutil.copyfile(ROOT/'result/blender/stage90'/name, OUT/name)
shutil.copyfile(ROOT/'web/public/models/catalogue.json', OUT/'catalogue-before.json')
audit = {'version': 91, 'baseline': 90, 'baselineFingerprint': before,
         'sourceStack': source.name, 'ownedStack': stack.name, 'addedObjects': added,
         'pipes': pipe_records, 'source': 'LSE Estate 5LF exterior photograph',
         'sourceUrl': 'https://info.lse.ac.uk/staff/divisions/estates-division/lse-estate/LSE-Estate',
         'reference': 'data/建筑图片/5LF_5 Lincoln_s Inn Fields/01_建筑实拍/exteriors_lse_estate_012.jpg',
         'limitations': ['Photo capture date unknown; not proof of 2026 condition',
                        'Dark chimney colors and pipe dimensions are estimates',
                        'Main wall, windows, terracotta pots, roof and interiors preserved',
                        'Unseen elevations and roof layout remain unverified']}
(OUT/'five-rainwater-audit.json').write_text(json.dumps(audit, indent=2)+'\n')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v91.blend'))
print('FIVE_RAINWATER_SAVED', added, flush=True)
