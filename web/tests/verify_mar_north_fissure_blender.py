"""Independently inspect saved MAR north geometry in Blender's Text Editor.
No source or candidate model is changed. Writes private verification evidence.
"""
from pathlib import Path
import array
import hashlib
import json
import math
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'result/blender/stage115/mar'
OUT.mkdir(parents=True, exist_ok=True)

def update():
    for scene in bpy.data.scenes:
        for layer in scene.view_layers:
            layer.update()

def fingerprint(obj):
    h = hashlib.sha256(str([list(row) for row in obj.matrix_world]).encode())
    if obj.type == 'MESH':
        vertices = array.array('f', [0]) * (3 * len(obj.data.vertices))
        loops = array.array('i', [0]) * len(obj.data.loops)
        obj.data.vertices.foreach_get('co', vertices)
        obj.data.loops.foreach_get('vertex_index', loops)
        h.update(vertices.tobytes())
        h.update(loops.tobytes())
    h.update(str([m.name if m else None for m in getattr(obj.data, 'materials', [])]).encode())
    return h.hexdigest()

baseline_path = ROOT / 'result/blender/LSE_campus_detailed_v114.blend'
audit = json.loads((ROOT / 'result/blender/stage115/mar-north-fissure-audit.json').read_text())
before = audit['originalFingerprints']
visibility = audit['originalVisibility']
baseline_available = baseline_path.exists()
if baseline_available:
    bpy.ops.wm.open_mainfile(filepath=str(baseline_path))
    update()
    assert {obj.name:fingerprint(obj) for obj in bpy.data.objects} == before
    assert {obj.name:obj.hide_render for obj in bpy.data.objects} == visibility
bpy.ops.wm.open_mainfile(filepath=str(ROOT / 'result/blender/LSE_campus_detailed_v115.blend'))
update()
bpy.context.window.scene = bpy.data.scenes['00_CAMPUS_COMPLETE']
assert all(fingerprint(bpy.data.objects[name]) == value for name, value in before.items())
archived = set(audit['archivedObjects'])
assert all(bpy.data.objects[name].hide_render == (True if name in archived else state)
           for name, state in visibility.items())
assert all(name.startswith('MAR_') for name in archived)
assert set(bpy.data.objects.keys()) - set(before) == set(audit['addedObjects'])

# Retained MAR local basis, captured before external source-file loss.
cx, cy = -8.696325894899289, 49.33154396120258
angle = math.radians(22)
u = Vector((math.cos(angle), math.sin(angle), 0))
n = Vector((-math.sin(angle), math.cos(angle), 0))
origin = Vector((cx, cy, 0))
def point(x, y, z):
    return origin + u*x + n*y + Vector((0, 0, z))
def local(p):
    return ((p-origin).dot(u), (p-origin).dot(n), p.z)

fin_checks = []
for name, dimensions in [('MAR_V115_retained_D5_NEXT_upper_screen_shafts', (.3, .5, 11.5)),
                         ('MAR_V115_retained_D5_NEXT_upper_screen_hammerheads', (.3, 1.9, .5))]:
    obj = bpy.data.objects[name]
    assert not obj.hide_render and len(obj.data.vertices) == 38*8
    for first in range(0, len(obj.data.vertices), 8):
        coords = [local(obj.matrix_world @ v.co) for v in list(obj.data.vertices)[first:first+8]]
        measured = [max(p[i] for p in coords)-min(p[i] for p in coords) for i in range(3)]
        assert all(abs(a-b) < 1e-4 for a,b in zip(measured, dimensions))
    fin_checks.append({'object':name, 'count':38, 'dimensions':dimensions})
lower = bpy.data.objects['MAR_D5_north115_fin']
assert not lower.hide_render and len(lower.data.vertices) == 20*8
for first in range(0, len(lower.data.vertices), 8):
    coords = [local(lower.matrix_world @ v.co) for v in list(lower.data.vertices)[first:first+8]]
    assert abs(max(p[2] for p in coords)-min(p[2] for p in coords)-10.6) < 1e-4
    front = [p[0] for p in coords if p[1]>20.5]
    back = [p[0] for p in coords if p[1]<19.5]
    assert sum(back)/len(back) - sum(front)/len(front) > .4

# Include visible public-interior meshes as well as exterior: old slabs must not
# silently remain inside the newly open court. Glass panes are excluded only
# from aperture rays; the complete geometry is used to inspect the fissure.
root = next(c for c in bpy.data.collections['02_LSE_BUILDINGS'].children if c.name.startswith('MAR_'))
objects = [o for o in root.all_objects if o.type=='MESH' and not o.hide_render]

def bvh(mesh_objects, omit_glass=False):
    vertices, polygons, owners = [], [], []
    for obj in mesh_objects:
        points = [obj.matrix_world @ vertex.co for vertex in obj.data.vertices]
        for face in obj.data.polygons:
            mat = obj.data.materials[face.material_index] if len(obj.data.materials) else None
            if omit_glass and mat and any(k in mat.name.lower() for k in ['glass','glazing']):
                continue
            start = len(vertices)
            vertices.extend(points[index] for index in face.vertices)
            polygons.append(tuple(range(start, len(vertices))))
            owners.append(obj.name)
    return BVHTree.FromPolygons(vertices, polygons, all_triangles=False), owners

opaque, owners = bvh(objects, True)
window_hits = []
for index, probe in enumerate(audit['windowProbes']):
    p, normal = Vector(probe['point']), Vector(probe['normal']).normalized()
    location, _, face, distance = opaque.ray_cast(p+normal*.003, normal, .30)
    if location is not None:
        window_hits.append({'index':index,'object':owners[face],'distance':distance})
    # North street windows must face +Y; their glass is recessed to y=18.68.
    x,y,z = local(p)
    if abs(y-18.68)<.01:
        assert normal.dot(n)>.999
assert not window_hits, window_hits

# The thin front screen and its hammerheads intentionally span the open
# frontage. Inspect the court's roof, walls and floors independently of them.
screen_names = {'MAR_V115_retained_D5_NEXT_upper_screen_shafts',
                'MAR_V115_retained_D5_NEXT_upper_screen_hammerheads',
                'MAR_D5_north115_fin'}
roof_objects = [obj for obj in objects if obj.name not in screen_names
                and 'north_screen_horizontal_edges' not in obj.name]
complete, owners = bvh(roof_objects)
fissure = audit['fissureEstimate']
def inside(x,y):
    for a,b in zip(fissure, fissure[1:]+fissure[:1]):
        cross = (b[0]-a[0])*(y-a[1])-(b[1]-a[1])*(x-a[0])
        if cross/math.hypot(b[0]-a[0],b[1]-a[1]) < .16:
            return False
    return True
hits, tested = [], 0
for ix in range(27):
    for iy in range(36):
        x,y = -15.0+ix*.5, 3.75+iy*.5
        if not inside(x,y):continue
        tested += 1
        location, _, face, distance = complete.ray_cast(point(x,y,12.82), Vector((0,0,1)), 32.0)
        if location is not None:
            hits.append({'local':[x,y,location.z],'object':owners[face],'distance':distance})
# Preserve diagnostic evidence even on a failure; an obscured court must not be
# accepted as an open fissure merely because the new facade looks plausible.
report = {'version':115, 'baseline':114, 'originalObjectsChecked':len(before),
          'originalFingerprintsRetained':True,'visibilityChangesLimitedToMARArchive':True,
          'baselineNativeAvailableThisRun':baseline_available,
          'baselineComparisonLimit':'Initial run compared opened114 and115 successfully before its missing-stage02 error; final run uses preserved audit fingerprints if114 is unavailable',
          'upperFinChecks':fin_checks,'lowerAngledFins':20,
          'clearWindowApertures':len(audit['windowProbes'])-len(window_hits),
          'windowHits':window_hits,'fissureVerticalRays':tested,'fissureHits':hits,
          'roofDatum':audit['northRoofEstimate'], 'roofAndFissureDimensionsEstimated':True,
          'sourceModelSha256':hashlib.sha256((ROOT/'result/blender/LSE_campus_detailed_v115.blend').read_bytes()).hexdigest()}
(OUT/'saved-verification.json').write_text(json.dumps(report,indent=2)+'\n')
assert not hits, hits[:20]
print('MAR_NORTH_FISSURE_INDEPENDENTLY_VERIFIED', tested, len(audit['windowProbes']), flush=True)
