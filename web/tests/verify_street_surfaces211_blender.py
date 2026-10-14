"""Reopen the complete campus and verify street coverage and original materials."""
from pathlib import Path
import hashlib
import json
import sys
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'web/tools'))
from refine_portsmouth_exterior207 import material_fingerprint
OUT = ROOT/'result/blender/street-surfaces211'
BASE = ROOT/'result/blender/LSE_campus_detailed_v210.blend'
CURRENT = ROOT/'result/blender/LSE_campus_detailed_v211.blend'
plan = json.loads((OUT/'surface-plan.json').read_text())
audit = json.loads((OUT/'audit.json').read_text())
bpy.ops.wm.open_mainfile(filepath=str(BASE))
materials = {m.name: material_fingerprint(m) for m in bpy.data.materials}
bpy.ops.wm.open_mainfile(filepath=str(CURRENT))
bpy.context.window.scene = bpy.data.scenes['00_CAMPUS_COMPLETE']
for name, fingerprint in materials.items():
    assert material_fingerprint(bpy.data.materials[name]) == fingerprint, name
for name in audit['archivedObjects']:
    assert bpy.data.objects[name].hide_render, name
rows, trees = [], {}
for name in audit['addedObjects']:
    obj = bpy.data.objects[name]
    assert not obj.hide_render and name in bpy.context.scene.objects
    points = [obj.matrix_world@v.co for v in obj.data.vertices]
    faces = [list(face.vertices) for face in obj.data.polygons]
    zero = []
    for face in faces:
        a, b, c = [points[i] for i in face]
        area = (b-a).cross(c-a).z/2
        if area <= 0:
            zero.append(area)
    assert not zero, (name, len(zero), zero[:5])
    assert all(n.vector.z > .999 for n in obj.data.corner_normals)
    rows.append(dict(name=name, vertices=[list(p) for p in points], faces=faces))
    trees[name] = BVHTree.FromPolygons(points, faces, all_triangles=True)
probes = 0
for area in plan['areas']:
    paving = trees['SITE211_'+area['name']+'_stone_courses']
    for tile in area['tiles'][::max(1, len(area['tiles'])//120)]:
        triangle = max(tile['triangles'], key=lambda t: abs(sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(t,t[1:]+t[:1]))))
        center = Vector((sum(p[0] for p in triangle)/3, sum(p[1] for p in triangle)/3, .2))
        assert paving.ray_cast(center, Vector((0,0,-1)), .3)[0] is not None
        for source in plan['replacements']:
            assert trees[source['name']].ray_cast(center, Vector((0,0,-1)), .3)[0] is None
        probes += 1
record = dict(sourceModelSha256=hashlib.sha256(CURRENT.read_bytes()).hexdigest(),
              originalMaterialsVerified=len(materials), completeModelReopened=True,
              mappedWalkingProbes=probes, misplacedAsphaltAbsentAtEveryProbe=True,
              allOwnedTrianglesUpwardAndNondegenerate=True, objects=rows)
(OUT/'saved-ground-audit.json').write_text(json.dumps(record)+'\n')
print('STREET211_SAVED', probes, len(materials), flush=True)
