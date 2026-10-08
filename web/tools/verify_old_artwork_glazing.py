"""Build and inspect a private OLD glass component without replacing release188.

Run in Blender's Text Editor. Keeps before/after browser assets private. Tests
all source mesh signatures, editable lettering and visibility, and then checks
saved/reopened pane position using rays through actual artwork vertices.
"""
from pathlib import Path
import ast
import hashlib
import json
import sys

import bpy
import bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'web/tools'))
from refine_architectural_glass import shape_signature
from refine_old_lettering185 import font_signature
from refine_old_artwork_glazing import apply_old_artwork_glazing, SOURCE, TARGET, ARTWORK

OUT = ROOT / 'result/blender/old-artwork-glazing'
BASE = ROOT / 'result/blender/LSE_campus_detailed_v188.blend'
COMPONENT = OUT / 'old-artwork-glazing.blend'
OUT.mkdir(parents=True, exist_ok=True)
base_hash = hashlib.sha256(BASE.read_bytes()).hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(BASE))
scene = bpy.data.scenes['00_CAMPUS_COMPLETE']
bpy.context.window.scene = scene
for item in bpy.data.scenes:
    for layer in item.view_layers:
        layer.update()
shapes = {o.name: shape_signature(o) for o in bpy.data.objects if o.type == 'MESH'}
fonts = {o.name: font_signature(o) for o in bpy.data.objects if o.type == 'FONT'}
visibility = {o.name: [o.hide_render, o.hide_viewport, o.hide_get()] for o in bpy.data.objects}
module = ast.parse((ROOT / 'web/tools/export_scene.py').read_text())
exporter = {'bpy': bpy, 'bmesh': bmesh, 'Vector': Vector, 'full_detail': True,
            'material_cache': {}, 'OUTPUT': OUT, 'depsgraph': bpy.context.evaluated_depsgraph_get()}
exec(compile(ast.Module(body=[n for n in module.body if isinstance(n, ast.FunctionDef)], type_ignores=[]),
             str(ROOT / 'web/tools/export_scene.py'), 'exec'), exporter)


def export(name):
    bpy.context.window.scene = scene
    bpy.context.view_layer.update()
    exporter['material_cache'] = {}
    exporter['depsgraph'] = bpy.context.evaluated_depsgraph_get()
    temporary = bpy.data.scenes.new('OLD_GLASS_REVIEW')
    objects = list(bpy.data.collections['OLD_EXTERIOR'].all_objects)
    objects += list(bpy.data.collections['OLD_PUBLIC_INTERIOR_study'].all_objects)
    exporter['clone_group'](list(dict.fromkeys(objects)), 'OLD', temporary)
    exporter['export_scene'](temporary, name + '.glb')
    for obj in list(temporary.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    bpy.data.scenes.remove(temporary)
    bpy.context.window.scene = scene


export('before')
audit = apply_old_artwork_glazing()
for name, signature in shapes.items():
    assert shape_signature(bpy.data.objects[name]) == signature, name
for name, signature in fonts.items():
    assert font_signature(bpy.data.objects[name]) == signature, name
for name, state in visibility.items():
    obj = bpy.data.objects[name]
    if name != SOURCE:
        assert [obj.hide_render, obj.hide_viewport, obj.hide_get()] == state, name
assert bpy.data.objects[SOURCE].hide_render
pane = bpy.data.objects[TARGET]
assert len(pane.data.polygons) == len(bpy.data.objects[SOURCE].data.polygons)
assert abs(pane.data.materials[0]['webOpacity'] - .22) < .000001
# Independent saved component; release188 stays the sole complete campus source.
bpy.data.libraries.write(str(COMPONENT), {pane}, fake_user=True, compress=True)
export('after')
normal = Vector(audit['normal'])
points = []
for name in ARTWORK:
    artwork = bpy.data.objects[name]
    matrix = artwork.matrix_world.copy()
    # Cache RNA lookups; a name search per vertex costs minutes on a full campus.
    points.extend(matrix @ vertex.co for vertex in artwork.data.vertices)
print('ARTWORK_POINTS', len(points), flush=True)
expected_matrix = pane.matrix_world.copy()
bpy.data.objects.remove(pane, do_unlink=True)
with bpy.data.libraries.load(str(COMPONENT), link=False) as (available, loaded):
    loaded.objects = [TARGET]
reopened = loaded.objects[0]
scene.collection.objects.link(reopened)
bpy.context.view_layer.update()
assert max(abs(reopened.matrix_world[r][c] - expected_matrix[r][c]) for r in range(4) for c in range(4)) < .00001
verts = [reopened.matrix_world @ v.co for v in reopened.data.vertices]
tree = BVHTree.FromPolygons(verts, [tuple(p.vertices) for p in reopened.data.polygons])
clearances = []
# Sample every50th vertex across all four artwork meshes, not just an empty centre.
for point in points[::50]:
    hit = tree.ray_cast(point, normal, 2)
    assert hit[2] is not None, 'A visible sculpture sample lies outside the protective pane'
    assert hit[3] >= .0349, 'Pane clips the sculpture'
    clearances.append(hit[3])
assert hashlib.sha256(BASE.read_bytes()).hexdigest() == base_hash
proof = {'baselineSha256': base_hash, 'sourceUnchanged': True,
         'originalGeometryUVAndFontsPreserved': True, 'unrelatedVisibilityPreserved': True,
         'savedComponentReopened': True, 'protectedArtworkSamples': len(clearances),
         'minimumSampleClearance': min(clearances), 'maximumSampleClearance': max(clearances),
         'addedSurfaceCount': len(reopened.data.polygons),
         'componentSha256': hashlib.sha256(COMPONENT.read_bytes()).hexdigest(), 'change': audit}
(OUT / 'verification.json').write_text(json.dumps(proof, indent=2) + '\n')
print('OLD_ARTWORK_GLASS_VERIFIED', len(clearances), flush=True)
