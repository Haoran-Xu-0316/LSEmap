"""Reopen the integrated campus and probe formerly buried paths at ground level."""
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
OUT = ROOT/'result/blender/pedestrian-surfaces209'
SOURCE = ROOT/'result/blender/LSE_campus_detailed_v208.blend'
CURRENT = ROOT/'result/blender/LSE_campus_detailed_v209.blend'
plan = json.loads((OUT/'surface-plan.json').read_text())
audit = json.loads((OUT/'audit.json').read_text())


def tree(objects):
    vertices, faces = [], []
    for obj in objects:
        offset = len(vertices)
        vertices.extend(obj.matrix_world@v.co for v in obj.data.vertices)
        faces.extend(tuple(offset+index for index in face.vertices) for face in obj.data.polygons)
    return BVHTree.FromPolygons(vertices, faces, all_triangles=False)


bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
original_materials = {m.name: material_fingerprint(m) for m in bpy.data.materials}
park_tree = tree([bpy.data.objects[g['source']] for g in plan['grasses']])
footway = bpy.data.objects[plan['sourceObject']]
points = []
for face in footway.data.polygons:
    vertices = [footway.matrix_world@footway.data.vertices[index].co for index in face.vertices]
    if all(abs(v.z-.024) < 1e-6 for v in vertices):
        center = sum(vertices, Vector())/len(vertices)
        hit = park_tree.ray_cast(Vector((center.x, center.y, .15)), Vector((0, 0, -1)), .2)
        if hit[0] is not None:
            assert abs(hit[0].z-.05) < 1e-5
            points.append((center.x, center.y))
assert len(points) > 20
bpy.ops.wm.open_mainfile(filepath=str(CURRENT))
bpy.context.window.scene = bpy.data.scenes['00_CAMPUS_COMPLETE']
for name, fingerprint in original_materials.items():
    assert material_fingerprint(bpy.data.materials[name]) == fingerprint, name
for name in audit['archivedObjects']:
    assert bpy.data.objects[name].hide_render
owned = [bpy.data.objects[name] for name in audit['addedObjects']]
for obj in owned:
    assert not obj.hide_render and obj.name in bpy.context.scene.objects
    expected = .024 if 'footways' in obj.name else .05
    assert all(abs((obj.matrix_world@vertex.co).z-expected) < 1e-5 for vertex in obj.data.vertices)
    assert all(normal.vector.z > .99 for normal in obj.data.corner_normals)
current_tree = tree(owned)
for x, y in points:
    hit = current_tree.ray_cast(Vector((x, y, .15)), Vector((0, 0, -1)), .2)
    assert hit[0] is not None and abs(hit[0].z-.024) < 1e-5, (x, y, hit[0])
actual = []
for obj in owned:
    actual.append(dict(name=obj.name, vertices=[list(obj.matrix_world@v.co) for v in obj.data.vertices],
                       faces=[list(face.vertices) for face in obj.data.polygons],
                       materials=[m.name for m in obj.data.materials]))
result = dict(sourceModelSha256=hashlib.sha256(CURRENT.read_bytes()).hexdigest(),
              completeModelReopened=True, oldGrassOccludedProbeCount=len(points),
              recoveredPathProbeCount=len(points), originalMaterialsVerified=len(original_materials),
              sourceMaterialNodesUnchanged=True, allOwnedCornersUpward=True,
              onlyMappedSurfaceHeightsRetained=True, objects=actual)
(OUT/'saved-ground-audit.json').write_text(json.dumps(result)+'\n')
print('PEDESTRIAN209_REOPENED_PROBES', len(points), flush=True)
