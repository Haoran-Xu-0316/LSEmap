"""Refine Cowdray street-side attic sashes from contractor photography.
Run in Blender Text Editor. Pane layout is photo-guided; dimensions remain estimates.
"""
from pathlib import Path
import array, hashlib, json, math, shutil
import bpy, bmesh
from mathutils import Vector
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'result/blender/stage98'
OUT.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT / 'result/blender/LSE_campus_detailed_v97.blend'))
bpy.context.window.scene = bpy.data.scenes['00_CAMPUS_COMPLETE']
collection = bpy.data.collections['COW_EXTERIOR']
profile = next(p for p in json.loads((ROOT / 'result/blender/stage05/infill-geometry.json').read_text()) if p['code'] == 'COW')

def fingerprint(obj):
    h = hashlib.sha256(str([list(row) for row in obj.matrix_world]).encode())
    if obj.type == 'MESH':
        h.update(array.array('f', [c for v in obj.data.vertices for c in v.co]).tobytes())
        h.update(array.array('i', [l.vertex_index for l in obj.data.loops]).tobytes())
    h.update(str([m.name if m else None for m in getattr(obj.data, 'materials', [])]).encode())
    return h.hexdigest()

before = {o.name: fingerprint(o) for o in bpy.data.objects}
windows = []
for index in [3, 4, 5]:
    wall = profile['walls'][index]
    start = Vector((*wall['p'], 0)); end = Vector((*wall['q'], 0))
    right = (end - start).normalized(); normal = Vector((*wall['outward'], 0))
    count = 1 if wall['front'] else max(1, round(wall['length'] / 4.6))
    for i in range(count):
        center = start + right * ((i + .5) * wall['length'] / count)
        windows.append({'wall': index, 'center': list(center), 'right': list(right),
                        'normal': list(normal), 'bottom': 18.54, 'top': 20.24,
                        'width': .96, 'depth': .005})

source = bpy.data.objects['COW_D5_sash_glazing_bar_frame']
bm = bmesh.new(); bm.from_mesh(source.data)
seen, delete, removed = set(), [], 0
retained = []
for seed in list(bm.verts):
    if seed in seen: continue
    component = []; pending = [seed]; seen.add(seed)
    while pending:
        vertex = pending.pop(); component.append(vertex)
        for edge in vertex.link_edges:
            other = edge.other_vert(vertex)
            if other not in seen: seen.add(other); pending.append(other)
    ps = [source.matrix_world @ v.co for v in component]
    matched = False
    for window in windows:
        center, right, normal = [Vector(window[k]) for k in ['center', 'right', 'normal']]
        xs = [(p - center).dot(right) for p in ps]
        ds = [(p - center).dot(normal) for p in ps]
        zs = [p.z for p in ps]
        mid = sum(zs) / len(zs)
        quarters = [window['bottom'] + (window['top'] - window['bottom']) * f for f in [.25, .75]]
        if (max(xs) - min(xs) > .90 and max(zs) - min(zs) < .03
            and max(abs(x) for x in xs) < .51 and max(abs(d - .005) for d in ds) < .04
            and min(abs(mid - z) for z in quarters) < .01):
            matched = True; break
    if matched: delete.extend(component); removed += 1
    else: retained.extend([list(p) for p in ps])
assert removed == len(windows) * 2, (removed, len(windows))
copy = source.copy(); copy.data = source.data.copy(); copy.name = 'COW_V98_retained_sash_bars'
collection.objects.link(copy)
bmesh.ops.delete(bm, geom=delete, context='VERTS')
bm.to_mesh(copy.data); bm.free()
source.hide_render = True; source.hide_set(True)
copy.hide_render = False; copy.hide_set(False)

# Preserve original outer frames, vertical muntins and central meeting rails.
# Replace only the two quarter rails with four smaller sash subdivisions.
bm = bmesh.new()
for window in windows:
    center, right, normal = [Vector(window[k]) for k in ['center', 'right', 'normal']]
    for fraction in [1/6, 2/6, 4/6, 5/6]:
        height = window['bottom'] + (window['top'] - window['bottom']) * fraction
        created = bmesh.ops.create_cube(bm, size=1)
        for v in created['verts']:
            x, d, z = v.co
            v.co = center + right * (x * .96) + normal * (.005 + d * .06) + Vector((0, 0, height + z * .024))
bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
mesh = bpy.data.meshes.new('COW_V98_dormer_rails_mesh'); bm.to_mesh(mesh); bm.free()
rails = bpy.data.objects.new('COW_V98_dormer_six_row_rails', mesh); collection.objects.link(rails)
mesh.materials.append(source.data.materials[0])
assert all(fingerprint(bpy.data.objects[n]) == h for n, h in before.items())
for name in ['room-studies.json', 'room-spaces.json', 'building-review.json']:
    shutil.copyfile(ROOT / 'result/blender/stage97' / name, OUT / name)
audit = {'version': 98, 'baseline': 97, 'originalFingerprints': before, 'windows': windows,
         'removedQuarterRails': removed, 'retainedVertices': retained,
         'addedObjects': [copy.name, rails.name], 'replacedObject': source.name,
         'columns': 3, 'rows': 6,
         'reference': 'data/建筑图片/COW_Cowdray House/01_建筑实拍/campus_photos_round2_COW_cow_russell_05.jpg',
         'sourcePage': 'https://www.russellcawberry.com/projects/cowdray-house',
         'projectYear': 2019, 'captureDate': None,
         'scope': 'Street sides 3,4,5 only. Retained original windows, positions, central meeting rails, vertical muntins, cornices, roof, materials and interiors. No photographic textures.',
         'limitations': ['Unsurveyed dimensions and partly foreshortened pane divisions', 'Roof arrangement, unseen elevations and complete interiors unresolved']}
(OUT / 'cowdray-dormer-audit.json').write_text(json.dumps(audit, indent=2) + '\n')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / 'result/blender/LSE_campus_detailed_v98.blend'))
print('COWDRAY_DORMER_SASHES_SAVED', len(windows), removed)
