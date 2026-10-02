"""Rebuild Carey Street and the curved LRB entrance from the 2025 existing drawing.
Run in Blender Text Editor after prepare_library_street_survey.py. Originals are
retained unchanged on disk; only replaced exterior objects become invisible.
"""
from pathlib import Path
import array
import hashlib
import json
import math
import sys
import bisect
import bpy
import bmesh
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'result/blender/stage117'
sys.path.insert(0, str(Path(__file__).resolve().parent))
from facade_geometry import Geometry, materials

baseline = ROOT/'result/blender/LSE_campus_detailed_v116.blend'
current = ROOT/'result/blender/LSE_campus_detailed_v117.blend'
rebuild_current = not baseline.exists()
# The current complete file contains all original geometry. Once edition116 is
# cleaned up, restore its visibility checkpoint and replace only our owned output.
# A lightweight audit is sufficient; no historical full model is required.
bpy.ops.wm.open_mainfile(filepath=str(current if rebuild_current else baseline))
if rebuild_current:
    previous = json.loads((OUT/'carey-frontage-audit.json').read_text())
    owned = previous['addedObjects'] + [r['copy'] for r in previous['retainedCopies'] if r['copy']]
    for name in owned:
        obj = bpy.data.objects.get(name)
        if obj is None: continue
        mesh = obj.data
        bpy.data.objects.remove(obj, do_unlink=True)
        if mesh.users == 0: bpy.data.meshes.remove(mesh)
    for name in previous['archivedObjects']:
        obj = bpy.data.objects[name]
        obj.hide_render = previous['originalVisibility'][name]
        obj.hide_set(obj.hide_render)
    for material in list(bpy.data.materials):
        if material.name.startswith('LRB_V117_carey_') and material.users == 0:
            bpy.data.materials.remove(material)
for scene in bpy.data.scenes:
    for layer in scene.view_layers: layer.update()
bpy.context.window.scene = bpy.data.scenes['00_CAMPUS_COMPLETE']
plan = json.loads((OUT/'street-survey-geometry.json').read_text())
collection = bpy.data.collections['LRB_EXTERIOR']
origin = Vector((*plan['careyOrigin'], 0))
axis = Vector((*plan['careyAxis'], 0))
normal = Vector((*plan['careyNormal'], 0))
corner = [Vector((*p, 0)) for p in plan['cornerCurve']]
length = plan['careyLength']
corner_length = plan['cornerLength']

def fingerprint(obj):
    h = hashlib.sha256(str([list(r) for r in obj.matrix_world]).encode())
    if obj.type == 'MESH':
        vertices = array.array('f', [0]) * (3*len(obj.data.vertices))
        indices = array.array('i', [0]) * len(obj.data.loops)
        obj.data.vertices.foreach_get('co', vertices)
        obj.data.loops.foreach_get('vertex_index', indices)
        h.update(vertices.tobytes()); h.update(indices.tobytes())
    h.update(str([m.name if m else None for m in getattr(obj.data, 'materials', [])]).encode())
    return h.hexdigest()

before = {o.name: fingerprint(o) for o in bpy.data.objects}
visibility = {o.name: o.hide_render for o in bpy.data.objects}
archived, retained = [], []
def archive(obj):
    obj.hide_render = True; obj.hide_set(True); archived.append(obj.name)

# Remove the old segmented corner and straight Carey wall. Portugal Street's
# authored objects, the central dome and the three other elevations are retained.
for source in list(collection.all_objects):
    if source.hide_render or source.type != 'MESH': continue
    if source.name in [f'LRB_V109_facade_wall_0_{i}' for i in range(2, 7)]:
        archive(source)
        continue
    if not source.name.startswith('LRB_V110_retained_'): continue
    mesh = source.data.copy()
    editable = bmesh.new(); editable.from_mesh(mesh)
    inverse = source.matrix_world.inverted()
    removed = 0
    for edge in range(2, 7):
        a, b = [Vector((*plan['ring'][i], 0)) for i in [edge, edge+1]]
        u = (b-a).normalized(); n = Vector((-u.y, u.x, 0)); span = (b-a).length
        for p, direction in [(a-n*.85,n), (a,u), (b,u)]:
            bmesh.ops.bisect_plane(editable, geom=list(editable.verts)+list(editable.edges)+list(editable.faces),
                plane_co=inverse@p, plane_no=source.matrix_world.to_3x3().transposed()@direction, dist=1e-6)
        faces = []
        for face in editable.faces:
            p = source.matrix_world@face.calc_center_median()-a
            if -.00001 <= p.dot(u) <= span+.00001 and p.dot(n) >= -.85001: faces.append(face)
        removed += len(faces)
        if faces: bmesh.ops.delete(editable, geom=faces, context='FACES')
    if not removed:
        editable.free(); bpy.data.meshes.remove(mesh); continue
    editable.to_mesh(mesh); editable.free(); mesh.update()
    record = dict(source=source.name, removedFaces=removed, copy=None)
    if mesh.polygons:
        copy = source.copy(); copy.data = mesh; copy.name = 'LRB_V117_retained_'+source.name
        collection.objects.link(copy); copy.hide_render = False; copy.hide_set(False)
        record['copy'] = copy.name
    else: bpy.data.meshes.remove(mesh)
    archive(source); retained.append(record)

# Replace only the flat perimeter roof triangles. The 2025 raised roof, dome,
# skylight aperture, grille, PV panels and their authored coordinates stay intact.
source = bpy.data.objects['LRB_D5_roof109_roof']
mesh = source.data.copy(); editable = bmesh.new(); editable.from_mesh(mesh)
low_faces = [f for f in editable.faces if all(abs((source.matrix_world@v.co).z-20.24)<.001 for v in f.verts)]
assert len(low_faces) == 29
bmesh.ops.delete(editable, geom=low_faces, context='FACES')
uv_layer = editable.loops.layers.uv.get('SurfaceUV') or editable.loops.layers.uv.new('SurfaceUV')
inverse = source.matrix_world.inverted()
for triangle in plan['lowerRoofTriangles']:
    face = editable.faces.new([editable.verts.new(inverse@Vector((p[0],p[1],20.24))) for p in triangle])
    if face.normal.z < 0: face.normal_flip()
    for loop in face.loops:
        world = source.matrix_world@loop.vert.co
        loop[uv_layer].uv = (world.x, world.y)
editable.to_mesh(mesh); editable.free(); mesh.update()
roof = source.copy(); roof.data = mesh; roof.name = 'LRB_V117_current_perimeter_roof'
collection.objects.link(roof); roof.hide_render = False; roof.hide_set(False)
archive(source)

materials.clear()
for key, family in [('brick','brick'), ('stone','stone'), ('glass','glass'),
                    ('frame','frame'), ('rail','roof_rail')]:
    materials[key] = bpy.data.objects['LRB_D5_portugal110_'+family].data.materials[0].copy()
    materials[key].name = 'LRB_V117_carey_'+key
# The street front uses the same photograph-informed stone and brick palette as
# Portugal Street. No source photographs are embedded as facade textures.
batches = {}
def batch(key):
    if key not in batches: batches[key] = Geometry('LRB', 'carey117_'+key, key)
    return batches[key]

def basis(x, curved=False):
    if not curved: return origin+axis*x, axis, normal
    distances = plan['cornerDistances']
    index = min(47, max(0, bisect.bisect_right(distances, x)-1))
    u = (corner[index+1]-corner[index]).normalized()
    p = corner[index]+u*(x-distances[index])
    return p, u, Vector((-u.y,u.x,0))

def point(x, d, z, curved=False):
    p, u, n = basis(x, curved)
    return p+n*d+Vector((0,0,z))

def prism(key, x, d, z, w, depth, height, curved=False):
    if not curved:
        batch(key).box(point(x,d,z), (w,depth,height), math.atan2(axis.y,axis.x)); return
    segments = max(1, math.ceil(w/.15))
    for i in range(segments):
        a, b = x-w/2+w*i/segments, x-w/2+w*(i+1)/segments
        vertices = [point(t, q, h, True) for t,q,h in
                    [(a,d-depth/2,z-height/2),(a,d-depth/2,z+height/2),
                     (a,d+depth/2,z-height/2),(a,d+depth/2,z+height/2),
                     (b,d-depth/2,z-height/2),(b,d-depth/2,z+height/2),
                     (b,d+depth/2,z-height/2),(b,d+depth/2,z+height/2)]]
        batch(key).add(vertices, [(0,4,6,2),(1,3,7,5),(0,1,5,4),(2,6,7,3),(0,2,3,1),(4,5,7,6)])

for curved, triangles in [(False,plan['careyWallTriangles']), (True,plan['cornerWallTriangles'])]:
    # Thick wall faces and aperture reveals; triangulated around every real void.
    for triangle in triangles:
        vertices = [point(x,d,z,curved) for d in [-.42,0] for x,z in triangle]
        faces = [(0,1,2),(5,4,3),(0,3,4,1),(1,4,5,2),(2,5,3,0)]
        wall = batch('brick')
        wall.add(vertices, faces)
        # One continuous horizontal metric coordinate system across triangles.
        # Using each triangle's first edge rotates bricks at triangulation seams.
        coordinates = [tuple(p) for p in triangle] * 2
        wall.uvs[-5:] = [[coordinates[i] for i in face] for face in faces]

for opening in plan['openings']:
    x,w,lo,hi = [opening[k] for k in ['x','width','low','high']]
    curved,d = opening['curved'],opening['depth']
    prism('glass',x,d,(lo+hi)/2,w,.035,hi-lo,curved)
    for sign in [-1,1]: prism('frame',x+sign*(w/2-.025),d+.05,(lo+hi)/2,.05,.08,hi-lo,curved)
    for z in [lo,hi]: prism('frame',x,d+.05,z,w,.08,.05,curved)
    for i in range(1,opening['columns']): prism('frame',x-w/2+w*i/opening['columns'],d+.065,(lo+hi)/2,.035,.09,hi-lo,curved)
    for i in range(1,opening['rows']): prism('frame',x,d+.065,lo+(hi-lo)*i/opening['rows'],w,.09,.035,curved)
    if opening['kind']=='louvre': continue
    for sign in [-1,1]: prism('stone',x+sign*(w/2+.065),d+.035,(lo+hi)/2,.13,.24,hi-lo+.14,curved)
    for z in [lo-.08,hi+.08]: prism('stone',x,d+.09,z,w+.25,.34,.14,curved)

# Projecting wide oriels have shared sills, stone spandrels and visible cheeks.
for x in plan['careyCentres']:
    w = plan['orielWidth']
    for z,h in [(5.25,.20),(8.85,.26),(9.12,.16),(12.53,.28),(12.82,.16),(16.15,.28)]:
        prism('stone',x,.18,z,w+.30,.72,h)
    for lo,hi in plan['bodyRows']:
        for sign in [-1,1]: prism('stone',x+sign*(w/2+.06),.13,(lo+hi)/2,.16,.65,hi-lo+.20)
    for z in [9.47,12.91]:
        for shift in [-w/3,0,w/3]:
            centre=x+shift;radius=.09
            batch('stone').add([point(centre+radius*math.cos(i*math.tau/24),.22,z+radius*math.sin(i*math.tau/24)) for i in range(24)], [tuple(reversed(range(24)))])

# Five semicircular glazed heads with radial stone voussoirs. Meshes follow the
# same 48-segment silhouette used to cut the actual upper wall openings.
for arch in plan['arches']:
    x,r,z = arch['x'],arch['radius'],arch['spring']
    outline = [point(x+r*math.cos(i*math.pi/48),-.075,z+r*math.sin(i*math.pi/48)) for i in range(49)]
    batch('glass').add(outline, [tuple(reversed(range(49)))])
    for i in range(48):
        a,b = i*math.pi/48,(i+1)*math.pi/48
        v = [point(x+radius*math.cos(t),d,z+radius*math.sin(t))
             for d in [-.12,.23] for radius,t in [(r,a),(r,b),(r+.24,b),(r+.24,a)]]
        batch('stone').add(v, [(0,1,2,3),(4,7,6,5),(0,4,5,1),(3,2,6,7),(1,5,6,2),(0,3,7,4)])
        # A dark, thin metal perimeter follows the glazed side of the arch.
        v=[point(x+radius*math.cos(t),d,z+radius*math.sin(t))
           for d in [-.04,.04] for radius,t in [(r-.04,a),(r-.04,b),(r,b),(r,a)]]
        batch('frame').add(v,[(0,1,2,3),(4,7,6,5),(0,4,5,1),(3,2,6,7),(1,5,6,2),(0,3,7,4)])
    prism('stone',x,.15,z-.10,2*r+.50,.52,.18)
    prism('stone',x,.20,z+r+.10,.27,.46,.44)
    # Nine vertical lights; transoms terminate at the circular head.
    for i in range(1,9):
        offset=-r+2*r*i/9; h=math.sqrt(max(0,r*r-offset*offset))
        prism('frame',x+offset,-.005,z+h/2,.035,.08,h)
    for rise in [.48,1.02,1.56]:
        if rise>=r:continue
        half=math.sqrt(r*r-rise*rise)
        prism('frame',x,-.005,z+rise,2*half,.08,.035)
    prism('frame',x,-.005,z,2*r,.08,.05)

# Continuous carved bands wrap around the rounded corner and meet the retained
# Portugal Street frontage, with a shallow upper frieze and projecting cornices.
for z,h,depth in [(4.90,.26,.58),(16.48,.20,.55),(16.80,.22,.62),(17.22,.24,.70),(20.55,.20,.52)]:
    prism('stone',length/2,.06,z,length,depth,h)
    prism('stone',corner_length/2,.06,z,corner_length,depth,h,True)
# Rusticated ground-level stone courses stay between glazed bays.
for i in range(9):
    z=.22+i*.53
    for a,b in [(0,.35),(length-.4,length)]: prism('stone',(a+b)/2,.09,z,b-a,.25,.38)
# Curved entrance columns and a real roof balcony rather than a faceted box.
for ratio in [.15,.85]:
    x=corner_length*ratio
    prism('stone',x,.16,2.20,.30,.60,4.10,True)
    for z in [.22,4.20]:prism('stone',x,.20,z,.54,.70,.20,True)
prism('stone',corner_length/2,.45,.025,corner_length*.80,1.45,.20,True)
for z in [17.58,18.38]:prism('rail',corner_length/2,.32,z,corner_length,.06,.055,True)
for i in range(7):prism('rail',corner_length*i/6,.32,17.99,.05,.06,.80,True)
for i in range(6):
    a,b=corner_length*i/6,corner_length*(i+1)/6
    for z0,z1 in [(17.63,18.33),(18.33,17.63)]:
        batch('rail').add([point(a,.32,z0-.018,True),point(b,.32,z1-.018,True),point(b,.32,z1+.018,True),point(a,.32,z0+.018,True)],[(0,1,2,3)])

added = [roof.name]
for geometry in batches.values():
    obj=geometry.finish();added.append(obj.name)
    obj['scope']='2025 existing Carey Street drawing; GIS registration and unlabelled dimensions estimated'
    for modifier in list(obj.modifiers): obj.modifiers.remove(modifier)
assert all(fingerprint(bpy.data.objects[n])==h for n,h in before.items())
audit = dict(version=117, baseline=116, originalFingerprints=before,
             originalVisibility=visibility, archivedObjects=archived,
             retainedCopies=retained, addedObjects=added, openingCount=len(plan['openings']),
             archCount=len(plan['arches']), source=plan['source'], drawing=plan['drawing'],
             registration=plan['registration'], limits=plan['limits'])
(OUT/'carey-frontage-audit.json').write_text(json.dumps(audit,indent=2)+'\n')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v117.blend'))
print('LIBRARY_CAREY_FRONTAGE_SAVED',len(plan['openings']),len(archived),len(added),flush=True)
