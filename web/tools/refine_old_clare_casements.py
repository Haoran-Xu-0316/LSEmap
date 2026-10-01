"""Correct Clare Market casement subdivisions from the supplied frontal photograph.
Run in Blender Text Editor. Existing openings and photographic dimension estimates remain.
"""
from pathlib import Path
import array, hashlib, json, math, shutil, sys
import bpy, bmesh
from mathutils import Vector
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'result/blender/stage87'
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(Path(__file__).resolve().parent))
from facade_geometry import Geometry, materials
bpy.ops.wm.open_mainfile(filepath=str(ROOT / 'result/blender/LSE_campus_detailed_v86.blend'))
bpy.context.window.scene = bpy.data.scenes['00_CAMPUS_COMPLETE']
ring = next(b for b in json.loads((ROOT / 'result/blender/site_geometry.json').read_text())['buildings']
            if b['code'] == 'OLD')['rings'][0]
a, b = Vector((*ring[7], 0)), Vector((*ring[8], 0))
origin, right = (a + b) / 2, (a - b).normalized()
outward = Vector((right.y, -right.x, 0))
length = (b - a).length
width = length / 5 - .92
centres = [-length / 2 + length * (i + .5) / 5 for i in range(5)]

def point(x, depth, z):
    return origin + right * x + outward * depth + Vector((0, 0, z))

def local(obj, vertex):
    p = obj.matrix_world @ vertex.co - origin
    return Vector((p.dot(right), p.dot(outward), p.z))

def fingerprint(obj, with_materials=True):
    digest = hashlib.sha256(str([list(r) for r in obj.matrix_world]).encode())
    if obj.type == 'MESH':
        digest.update(array.array('f', [c for v in obj.data.vertices for c in v.co]).tobytes())
        digest.update(array.array('i', [loop.vertex_index for loop in obj.data.loops]).tobytes())
    if with_materials:
        digest.update(str([m.name if m else None for m in getattr(obj.data, 'materials', [])]).encode())
    return digest.hexdigest()

def components(mesh):
    seen = set()
    for vertex in mesh.verts:
        if vertex in seen or not vertex.link_faces:
            continue
        todo, group = [vertex], []
        seen.add(vertex)
        while todo:
            v = todo.pop()
            group.append(v)
            for edge in v.link_edges:
                other = edge.other_vert(v)
                if other not in seen:
                    seen.add(other)
                    todo.append(other)
        yield group

before = {obj.name: fingerprint(obj) for obj in bpy.data.objects}
windows = []
for i, x in enumerate(centres):
    if i:
        windows.append({'x': x, 'z': 2.95, 'w': width, 'h': 4.4, 'rows': 5, 'columns': 4, 'family': 'lower'})
    windows.append({'x': x, 'z': 8.05, 'w': width, 'h': 3.1, 'rows': 4,
                    'columns': 2 if i == 0 else 4, 'family': 'upper'})

def is_internal_member(points, window):
    lo = [min(p[i] for p in points) for i in range(3)]
    hi = [max(p[i] for p in points) for i in range(3)]
    cx, cy, cz = [(lo[i] + hi[i]) / 2 for i in range(3)]
    dx, dy, dz = [hi[i] - lo[i] for i in range(3)]
    near = abs(cy + .10) < .015
    vertical = abs(cx - window['x']) < window['w']/2 - .10 and abs(cz-window['z']) < .01 and dx < .08 and abs(dz-window['h']) < .01
    horizontal = abs(cx-window['x']) < .01 and abs(cz-window['z']) < window['h']/2 - .1 and abs(dx-window['w']) < .01 and dz < .06
    return near and (vertical or horizontal)

source = bpy.data.objects['OLD_V53_Clare_blue']
retained = source.copy()
retained.data = source.data.copy()
retained.name = 'OLD_D5_clare87_retained_blue'
bpy.data.collections['OLD_EXTERIOR'].objects.link(retained)
mesh = bmesh.new()
mesh.from_mesh(retained.data)
removed, vertices = 0, []
for group in components(mesh):
    if any(is_internal_member([local(retained, v) for v in group], w) for w in windows):
        removed += 1
        vertices.extend(group)
assert removed == 48, removed
bmesh.ops.delete(mesh, geom=vertices, context='VERTS')
mesh.to_mesh(retained.data)
mesh.free()
source.hide_render = True
source.hide_set(True)
materials.clear()
materials['blue'] = source.data.materials[0].copy()
materials['blue'].name = 'OLD_V87_Clare_four_column_blue'
bars = Geometry('OLD', 'clare87_casements', 'blue')
angle = math.atan2(right.y, right.x)
members = []
for index, w in enumerate(windows):
    for j in range(1, w['columns']):
        x = w['x'] - w['w']/2 + w['w']*j/w['columns']
        size = (.052 if j*2 == w['columns'] else .028, .15, w['h'])
        centre = (x, -.10, w['z'])
        bars.box(point(*centre), size, angle)
        members.append({'window': index, 'kind': 'vertical', 'centre': centre, 'size': size})
    for j in range(1, w['rows']):
        z = w['z'] - w['h']/2 + w['h']*j/w['rows']
        heavy = w['family'] == 'upper' and j == 2
        size, centre = (w['w'], .15, .095 if heavy else .045), (w['x'], -.10, z)
        bars.box(point(*centre), size, angle)
        members.append({'window': index, 'kind': 'horizontal', 'centre': centre, 'size': size})
new = bars.finish()
for modifier in list(new.modifiers):
    new.modifiers.remove(modifier)
mesh = bmesh.new()
mesh.from_mesh(new.data)
bmesh.ops.recalc_face_normals(mesh, faces=list(mesh.faces))
mesh.to_mesh(new.data)
mesh.free()
assert len(members) == 56
assert all(fingerprint(bpy.data.objects[n]) == prior for n, prior in before.items())
for name in ['room-studies.json', 'room-spaces.json', 'building-review.json']:
    shutil.copyfile(ROOT / 'result/blender/stage86' / name, OUT / name)
shutil.copyfile(ROOT / 'web/public/models/catalogue.json', OUT / 'catalogue-before.json')
audit = {'version': 87, 'baseline': 86, 'baselineFingerprint': before,
         'frame': {'origin': list(origin), 'right': list(right), 'outward': list(outward)},
         'windows': windows, 'members': members, 'removedComponents': removed,
         'hiddenObject': source.name, 'retainedObject': retained.name, 'newBars': new.name,
         'reference': 'User frontal Clare Market entrance photograph; precise capture date unknown',
         'limitations': ['Existing opening centres and dimensions retained as estimates',
                         'Lower five-row subdivisions retained where the photograph is partly obscured',
                         'Frith figurative carvings remain unresolved; source photo is not shipped',
                         'Upper facade, roof and full interiors still require review']}
(OUT / 'old-clare-casement-audit.json').write_text(json.dumps(audit, indent=2)+'\n')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / 'result/blender/LSE_campus_detailed_v87.blend'))
print('OLD_CLARE_CASEMENTS_SAVED', len(windows), len(members), removed, flush=True)
