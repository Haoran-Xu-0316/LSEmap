"""Verify saved OLD lettering registration and actual stone contact in Blender."""
from pathlib import Path
import hashlib
import json
import sys

import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'web/tools'))
from refine_old_lettering185 import apply_old_lettering185, font_signature
from refine_rooms import geometry_signatures

STAGE = ROOT / 'result/blender/stage185'
MODEL = ROOT / 'result/blender/LSE_campus_detailed_v185.blend'
proof = json.loads((STAGE / 'building-refinement.json').read_text())
assert hashlib.sha256(MODEL.read_bytes()).hexdigest() == proof['sourceModelSha256']
bpy.ops.wm.open_mainfile(filepath=str(MODEL))
bpy.context.window.scene = bpy.data.scenes['00_CAMPUS_COMPLETE']
for scene in bpy.data.scenes:
    for layer in scene.view_layers:
        layer.update()
assert geometry_signatures() == proof['geometrySignatures']
for name, digest in proof['fonts'].items():
    assert font_signature(bpy.data.objects[name]) == digest
for name, digest in proof['originalFonts'].items():
    assert font_signature(bpy.data.objects[name]) == digest

vertices, faces, owners = [], [], []
for obj in bpy.data.collections['OLD_EXTERIOR'].all_objects:
    if obj.type != 'MESH' or obj.hide_render:
        continue
    offset = len(vertices)
    vertices.extend(obj.matrix_world @ vertex.co for vertex in obj.data.vertices)
    obj.data.calc_loop_triangles()
    for triangle in obj.data.loop_triangles:
        faces.append(tuple(offset + index for index in triangle.vertices))
        material = obj.data.materials[obj.data.polygons[triangle.polygon_index].material_index]
        owners.append((obj.name, material.name))
facade = BVHTree.FromPolygons(vertices, faces, all_triangles=True)
contacts = []
for record in proof['changes'][0]['records']:
    source = bpy.data.objects[record['source']]
    target = bpy.data.objects[record['target']]
    assert bpy.data.objects[record['archived']].hide_render
    assert not target.hide_render and target.name in bpy.context.scene.objects
    assert source.data.body == target.data.body == record['body']
    assert source.data.font == target.data.font
    assert list(source.data.materials) == list(target.data.materials)
    expected = Matrix(record['registration']) @ source.matrix_world @ Matrix.Diagonal((record['glyphScale'], record['glyphScale'], 1, 1))
    expected.translation += Vector(record['seatingTranslation'])
    assert max(abs(a - b) for left, right in zip(expected, target.matrix_world)
               for a, b in zip(left, right)) < .00002
    normal = target.matrix_world.to_3x3().inverted().transposed() @ Vector((0, 0, 1))
    normal.normalize()
    evaluated = target.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    points = [target.matrix_world @ vertex.co for vertex in mesh.vertices]
    rear = min(point.dot(normal) for point in points)
    backs = [point for point in points if point.dot(normal) - rear < .00002]
    assert len(backs) >= 9
    samples = [backs[round(index * (len(backs) - 1) / 8)] for index in range(9)]
    hits = []
    for point in samples:
        hit = facade.ray_cast(point + normal * .001, -normal, .12)
        assert hit[2] is not None, ('No nearby support', target.name, list(point))
        owner, material = owners[hit[2]]
        assert any(word in material.lower() for word in ['stone', 'ashlar']), (target.name, owner, material)
        # Stone courses have bevels and recessed joints beneath glyph edges.
        assert hit[3] < .06, (target.name, owner, hit[3])
        front = facade.ray_cast(point + normal * .3, -normal, .6)
        assert front[2] is not None and front[3] > .301, ('Occluded lettering', target.name, front)
        hits.append({'object': owner, 'material': material, 'distance': hit[3]})
    evaluated.to_mesh_clear()
    contacts.append({'target': target.name, 'stoneContactProbes': hits})
assert len(contacts) == 3
assert apply_old_lettering185()['alreadyApplied']
assert geometry_signatures() == proof['geometrySignatures']
(STAGE / 'lettering-verification.json').write_text(json.dumps({
    'sourceModelSha256': proof['sourceModelSha256'],
    'savedSceneReopened': True,
    'registeredLabels': 3,
    'stoneContactProbes': 27,
    'allOriginalFontsPreserved': True,
    'frontVisibilityProbes': 27,
    'contacts': contacts,
}, indent=2) + '\n')
print('OLD185_LETTERING_VERIFIED')
