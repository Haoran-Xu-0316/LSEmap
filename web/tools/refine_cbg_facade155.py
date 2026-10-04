"""Correct CBG office vision-transom heights and visible floor-edge spandrels.

Run in Blender's Text Editor. Built photograph geometry supports the division;
all dimensions are estimates. Existing red/orange palette and neutral glass stay.
"""
from pathlib import Path
import array
import ast
import hashlib
import json
import math
import bpy
import bmesh
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'result/blender/cbg_facade155'
WEB = ROOT / 'result/web/cbg_facade155'
OUT.mkdir(parents=True, exist_ok=True)
(WEB / 'models/details').mkdir(parents=True, exist_ok=True)
BASE = ROOT / 'result/blender/LSE_campus_detailed_v154.blend'
PREFIX = 'CBG_NEXT_FACADE155_'
SOURCE = 'CBG_NEXT_office_retained_CBG_D_window_transoms'
LOUVRE_SOURCE = 'CBG_D_tower_end_horizontal_louvres'
ARCHIVED = [SOURCE, LOUVRE_SOURCE]
EXPECTED = '2dbec0ee001ba3347de9de9ee50ed9e974401e301f4d4159a65b84b5c771f02c'
assert hashlib.sha256(BASE.read_bytes()).hexdigest() == EXPECTED


def open_baseline():
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    scene = bpy.data.scenes['00_CAMPUS_COMPLETE']
    bpy.context.window.scene = scene
    for layer in scene.view_layers:
        layer.update()
    return scene


def fingerprint(obj):
    digest = hashlib.sha256(str([list(row) for row in obj.matrix_world]).encode())
    if obj.type == 'MESH':
        for data, field, kind, count in ((obj.data.vertices, 'co', 'f', 3),
                                       (obj.data.loops, 'vertex_index', 'i', 1),
                                       (obj.data.polygons, 'material_index', 'i', 1)):
            values = array.array(kind, [0]) * (len(data) * count)
            data.foreach_get(field, values)
            digest.update(values.tobytes())
        for layer in obj.data.uv_layers:
            values = array.array('f', [0]) * (len(layer.data) * 2)
            layer.data.foreach_get('uv', values)
            digest.update(values.tobytes())
    digest.update(str([m.name if m else None for m in getattr(obj.data, 'materials', [])]).encode())
    return digest.hexdigest()


scene = open_baseline()
original = {obj.name: fingerprint(obj) for obj in bpy.data.objects}
visibility = {obj.name: [obj.hide_render, obj.hide_viewport, obj.hide_get()] for obj in bpy.data.objects}
assert len(original) == 5887
col = bpy.data.collections['CBG_EXTERIOR']
site = json.loads((ROOT / 'result/blender/site_geometry.json').read_text())
cx, cy = next(b['center'] for b in site['buildings'] if b['code'] == 'CBG')
a = math.radians(58)
c, s = math.cos(a), math.sin(a)


def local(p):
    return Vector((c * (p.x-cx) + s * (p.y-cy), -s * (p.x-cx) + c * (p.y-cy), p.z))


def world(p):
    x, y, z = p
    return Vector((cx + c*x-s*y, cy+s*x+c*y, z))


old = bpy.data.objects[SOURCE]
assert not old.hide_render
new = old.copy()
new.data = old.data.copy()
new.name = PREFIX + 'vision_transoms'
new.data.name = new.name
col.objects.link(new)
bm = bmesh.new()
bm.from_mesh(new.data)
visited = set()
transom_rows = []
for seed in bm.verts:
    if seed in visited:
        continue
    part, stack = [], [seed]
    visited.add(seed)
    while stack:
        vertex = stack.pop()
        part.append(vertex)
        for edge in vertex.link_edges:
            neighbour = edge.other_vert(vertex)
            if neighbour not in visited:
                visited.add(neighbour)
                stack.append(neighbour)
    points = [local(new.matrix_world @ v.co) for v in part]
    centre = sum(points, Vector()) / len(points)
    step = 52.2/13 if centre.x < 7 else 25/6
    floor = int(centre.z / step)
    znew = floor*step + step*.665
    shift = znew - centre.z
    for vertex, p in zip(part, points):
        p.z += shift
        vertex.co = new.matrix_world.inverted() @ world(p)
    transom_rows.append({'oldCenter':list(centre), 'newZ':znew, 'floor':floor})
bm.to_mesh(new.data)
bm.free()
new.data.update()
old.hide_render = True
old.hide_set(True)

# The actual dark floor-edge skin is shallow, bounded to shaded office runs.
# It does not span the meandering clear circulation zone or any whole window.
shade = bpy.data.objects['CBG_NEXT_REGISTERED_gold_solar_blades']
vertices = shade.data.vertices
modules = {}
for start in range(0, len(vertices), 8):
    points = [local(shade.matrix_world @ vertices[i].co) for i in range(start, start+8)]
    centre = sum(points, Vector())/8
    loz = min(p.z for p in points)
    step = 52.2/13 if centre.x < 7 else 25/6
    floor = round((loz-.30)/step)
    yface = min((-14,-2,2,14), key=lambda y:abs(y-centre.y))
    wing = 'tower' if centre.x < 7 else 'low'
    modules.setdefault((wing,yface,floor), []).append(centre.x+.23)

mesh_vertices, faces = [], []
spandrel_rows = []

def box(x0,x1,y0,y1,z0,z1):
    start = len(mesh_vertices)
    mesh_vertices.extend(world(p) for p in [(x0,y0,z0),(x1,y0,z0),(x1,y1,z0),(x0,y1,z0),
                                            (x0,y0,z1),(x1,y0,z1),(x1,y1,z1),(x0,y1,z1)])
    faces.extend(tuple(start+i for i in f) for f in [(3,2,1,0),(4,5,6,7),(0,1,5,4),
                                                       (1,2,6,5),(2,3,7,6),(3,0,4,7)])

for (wing,y,floor), xs in sorted(modules.items()):
    step = 52.2/13 if wing == 'tower' else 25/6
    pitch = 49/45 if wing == 'tower' else 28/26
    out = 1 if y in (14,2) else -1
    xs = sorted(xs)
    groups = [[xs[0]]]
    for x in xs[1:]:
        if x-groups[-1][-1] > pitch*1.4:
            groups.append([])
        groups[-1].append(x)
    for group in groups:
        x0, x1 = group[0]-pitch*.50, group[-1]+pitch*.50
        # At the outer glass plane, clear of the outward shade assembly.
        y0,y1 = sorted((y+out*.045,y+out*.105))
        z0,z1 = floor*step+.235, floor*step+.56
        box(x0,x1,y0,y1,z0,z1)
        spandrel_rows.append({'wing':wing,'floor':floor,'bounds':[[x0,x1],[y0,y1],[z0,z1]],'visionOpeningHeight':step-.325})

mat = bpy.data.materials['CBG_D_charcoal_thermal_frames'].copy()
mat.name = PREFIX + 'charcoal_floor_edge'
mat.diffuse_color = (.045,.065,.067,1)
node = mat.node_tree.nodes.get('Principled BSDF')
node.inputs['Base Color'].default_value = mat.diffuse_color
node.inputs['Roughness'].default_value = .43
mesh = bpy.data.meshes.new(PREFIX+'floor_edge_spandrels')
mesh.from_pydata(mesh_vertices, [], faces)
mesh.materials.append(mat)
mesh.update()
bands = bpy.data.objects.new(mesh.name,mesh)
col.objects.link(bands)
# Built joas05/12 show glass at the front of the east end and louvres at
# the rear. The opposite end in built ArchDaily000 repeats the rear service
# screen behind exposed X-bracing. Retain real slit gaps, no opaque backplate.
louvre_objects = []
louvre_source = bpy.data.objects[LOUVRE_SOURCE]
for side in ('east','west'):
    obj = louvre_source.copy()
    obj.data = louvre_source.data.copy()
    obj.name = PREFIX + side + '_rear_service_louvres'
    obj.data.name = obj.name
    col.objects.link(obj)
    for vertex in obj.data.vertices:
        p = local(obj.matrix_world @ vertex.co)
        p.y += 5.8
        if side == 'west':
            p.x = -35-p.x
        vertex.co = obj.matrix_world.inverted() @ world(p)
    editable = bmesh.new()
    editable.from_mesh(obj.data)
    bmesh.ops.recalc_face_normals(editable, faces=list(editable.faces))
    editable.to_mesh(obj.data)
    editable.free()
    obj.data.update()
    louvre_objects.append(obj)
louvre_source.hide_render = True
louvre_source.hide_set(True)
owned = [new,bands] + louvre_objects
names = [o.name for o in owned]
component = OUT/'cbg-facade155-component.blend'
bpy.data.libraries.write(str(component),set(owned),fake_user=True)
references = []
for file in ['data/collections/campus_photos_round2/images/CBG/CBG_cbg_joas_06.webp',
             'data/collections/campus_photos_round2/images/CBG/CBG_cbg_joas_07.webp',
             'data/collections/campus_photos_round2/images/CBG/CBG_cbg_joas_10.webp',
             'data/collections/campus_photos_round2/images/CBG/CBG_cbg_joas_05.jpg',
             'data/collections/campus_photos_round2/images/CBG/CBG_cbg_joas_12.jpg',
             'data/建筑图片/CBG_Centre Building/01_建筑实拍/exteriors_cbg_archdaily_000.jpg']:
    path = ROOT/file
    references.append({'file':file,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                       'role':'Built office windows, floor-edge dark bands and exposed external shade shelving',
                       'captureDate':'unknown'})
audit = {'baselineSha256':EXPECTED,'baselinePath':str(BASE),'originalObjectCount':len(original),
         'ownedObjects':names,'archivedObjects':ARCHIVED,
         'sourceCollection':'CBG_EXTERIOR','destinationCollection':'CBG_EXTERIOR',
         'originalFingerprints':original,'originalVisibility':visibility,'references':references,
         'sourceMaterialSlots':{o.name:[m.name for m in o.data.materials] for o in owned},
         'changes':[{'source':SOURCE,'owned':new.name,'action':'Lower all retained vision crossbars from top0.72m to0.665of floor height, retaining existing public circulation omissions and silver finish'},
                    {'source':'CBG_NEXT_REGISTERED_gold_solar_blades','owned':bands.name,'action':'Add shallow charcoal floor-edge spandrels only along existing shaded office runs; preserve stair glazing openings'},
                    {'source':LOUVRE_SOURCE,'owned':[o.name for o in louvre_objects],'action':'Register both actual rear-service end screens toY4.2..13.4; restore east end front glass and repeat west rear slat screen behindXbrace, preserving genuine0.077mopen horizontal slots'}],
         'transomRows':transom_rows,'spandrelRows':spandrel_rows,
         'limitations':['Transom ratio0.665and spandrel height0.325m are photograph-informed estimates, not surveyed dimensions.',
                        'User-requested red-dominant fronts/orange returns retained; daylight built photographs show pale/bronze shades, not measured red RGB.',
                        'Neutral70/37glass finish, transparency, source panes and rooms preserved; no added hidden interior or whole-window backing.']}
(OUT/'audit.json').write_text(json.dumps(audit,indent=2))
assert all(fingerprint(bpy.data.objects[n])==h for n,h in original.items())
assert all([bpy.data.objects[n].hide_render,bpy.data.objects[n].hide_viewport,bpy.data.objects[n].hide_get()]==v for n,v in visibility.items() if n not in ARCHIVED)
# Reopen the exact baseline, append only the saved candidate, and validate source boundaries.
scene = open_baseline()
with bpy.data.libraries.load(str(component),link=False) as (src,dst):
    dst.objects = names
for obj in dst.objects:
    bpy.data.collections['CBG_EXTERIOR'].objects.link(obj)
    if obj.name==names[0]:
        obj.data.materials[0] = bpy.data.objects[SOURCE].data.materials[0]
for name in ARCHIVED:
    bpy.data.objects[name].hide_render = True
    bpy.data.objects[name].hide_set(True)
for layer in scene.view_layers:
    layer.update()
assert all(fingerprint(bpy.data.objects[n])==h for n,h in original.items())
assert all([bpy.data.objects[n].hide_render,bpy.data.objects[n].hide_viewport,bpy.data.objects[n].hide_get()]==v for n,v in visibility.items() if n not in ARCHIVED)
proof = {'componentSha256':hashlib.sha256(component.read_bytes()).hexdigest(),
         'savedComponentReopened':True,'originalGeometryPreserved':True,'unrelatedVisibilityPreserved':True,
         'originalObjectCount':len(original),'fullModelSaved':False,'transomSolidCount':len(transom_rows),
         'spandrelSolidCount':len(spandrel_rows),'redOrangeAndGlassMaterialsPreserved':True,
         'clearCirculationOpeningsPreserved':True,'eastLouvreShiftY':5.8,
         'westRearLouvreScreenAdded':True,'louvreSlotsRemainOpen':True,
         'louvreWidthEstimate':9.2,'louvreFrontGlassWidthEstimate':6.2}
(OUT/'verification.json').write_text(json.dumps(proof,indent=2))
# Privately reuse production exporter functions without executing its publication code.
source = ROOT/'web/tools/export_scene.py'
tree = ast.parse(source.read_text())
imports = [n for n in tree.body if isinstance(n,(ast.Import,ast.ImportFrom))]
functions = [n for n in tree.body if isinstance(n,ast.FunctionDef)]
namespace = {'__file__':str(source),'ROOT':ROOT,'OUTPUT':WEB/'models','full_detail':True,
             'material_cache':{},'detail_report':[],'depsgraph':bpy.context.evaluated_depsgraph_get()}
exec(compile(ast.Module(body=imports+functions,type_ignores=[]),str(source),'exec'),namespace)
objects = list(bpy.data.collections['CBG_EXTERIOR'].all_objects) + list(bpy.data.collections['CBG_PUBLIC_INTERIOR_study'].all_objects)
descriptor = namespace['export_detail'](list(dict.fromkeys(objects)),'CBG','exterior')
(WEB/'candidate-descriptor.json').write_text(json.dumps(descriptor,indent=2))
print('CBG_FACADE155_VERIFIED',len(transom_rows),len(spandrel_rows),proof['componentSha256'],flush=True)
bpy.ops.wm.quit_blender()
