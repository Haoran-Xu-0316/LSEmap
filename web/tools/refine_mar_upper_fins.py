"""Refine MAR upper concrete blades from attributed north-elevation photographs.

Open in Blender's Text Editor. Writes an independent candidate, not a release.
Blade taper is a photographic proportion estimate; spacing and heights are retained.
References: architecture_round5 MAR_mar_kane_02 and MAR_mar_kane_03.
"""
from pathlib import Path
import array
import hashlib
import json
import math
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'result/blender/stage25'
OUT.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT / 'result/blender/LSE_campus_detailed_v24.blend'))

def fingerprint(obj):
    digest = hashlib.sha256()
    digest.update(array.array('f', [x for row in obj.matrix_world for x in row]).tobytes())
    coords = array.array('f', [0]) * (len(obj.data.vertices) * 3)
    obj.data.vertices.foreach_get('co', coords)
    digest.update(coords.tobytes())
    digest.update(str([tuple(face.vertices) for face in obj.data.polygons]).encode())
    digest.update(str([m.name for m in obj.data.materials]).encode())
    return digest.hexdigest()

before = {o.name: fingerprint(o) for o in bpy.data.objects if o.type == 'MESH'}
obj = bpy.data.objects['MAR_upper_screen_fins']
assert len(obj.data.vertices) == 43 * 8
angle = math.radians(22)
axis_x = Vector((math.cos(angle), math.sin(angle), 0))
axis_y = Vector((-math.sin(angle), math.cos(angle), 0))
inverse = obj.matrix_world.inverted()
blades = []
for start in range(0, len(obj.data.vertices), 8):
    vertices = list(obj.data.vertices)[start:start + 8]
    points = [obj.matrix_world @ v.co for v in vertices]
    centre = sum(points, Vector()) / 8
    xs = [(point-centre).dot(axis_x) for point in points]
    ys = [(point-centre).dot(axis_y) for point in points]
    assert abs(max(xs)-min(xs)-0.19) < 0.002
    assert abs(max(ys)-min(ys)-2.0) < 0.002
    # Wider root behind the narrow outer edge; no additional facade bays.
    for vertex, point, x, y in zip(vertices, points, xs, ys):
        depth_fraction = (max(ys)-y)/(max(ys)-min(ys))
        width = 0.19 + depth_fraction * (0.60-0.19)
        vertex.co = inverse @ (point + axis_x * (x * width/0.19 - x))
    blades.append({'centre': list(centre), 'frontWidth': 0.19, 'rootWidth': 0.60, 'depth': 2.0})
obj.data.update()
obj['refinementEvidence'] = 'MAR_mar_kane_02; MAR_mar_kane_03; taper dimensions estimated'
after = {o.name: fingerprint(o) for o in bpy.data.objects if o.type == 'MESH'}
changed = [name for name in before if before[name] != after[name]]
assert set(before) == set(after)
assert changed == ['MAR_upper_screen_fins'], changed
model = OUT / 'MAR_upper_screen_candidate.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(model))
report = {'status':'native-candidate-not-integrated', 'changedMeshes':changed,
          'unchangedMeshes':len(before)-1, 'bladeCount':len(blades), 'blades':blades,
          'scope':'Upper blade taper only. Interior geometry unchanged. Dimensions estimated from photographs.',
          'sourcePhotos':['MAR_mar_kane_02','MAR_mar_kane_03']}
(OUT/'mar-fins-audit.json').write_text(json.dumps(report, indent=2)+'\n')
scene = bpy.data.scenes.new('MAR_UPPER_FINS_REVIEW')
scene.collection.children.link(bpy.data.collections['MAR_EXTERIOR'])
scene.collection.children.link(bpy.data.collections['MAR_PUBLIC_INTERIOR_study'])
scene.camera = bpy.data.objects['02_MAR_Lincolns_Inn_Fields']
scene.collection.objects.link(scene.camera)
if scene.camera:
    bpy.context.window.scene = scene
    scene.render.engine = 'BLENDER_WORKBENCH'
    scene.display.shading.light = 'STUDIO'
    scene.display.shading.color_type = 'MATERIAL'
    scene.display.shading.show_shadows = True
    scene.display.shading.show_cavity = True
    scene.render.resolution_x = 1200
    scene.render.resolution_y = 1000
    scene.render.resolution_percentage = 100
    scene.render.filepath = str(OUT/'mar-fins-candidate.png')
    bpy.ops.render.render(write_still=True)
print(json.dumps({k:v for k,v in report.items() if k != 'blades'}))
