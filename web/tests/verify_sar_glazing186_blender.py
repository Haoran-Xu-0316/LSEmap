"""Reopen SAR treatment and verify preserved geometry and two-layer sightlines."""
from pathlib import Path
import hashlib
import json
import sys
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'web/tools'))
from refine_sar_glazing186 import SOURCE, TARGET, SHADING, BACKING, facade_registration, apply_sar_glazing186
from refine_rooms import geometry_signatures
from refine_building_details import REPORT as STAGE, TARGET as MODEL
proof = json.loads((STAGE / 'building-refinement.json').read_text())
assert hashlib.sha256(MODEL.read_bytes()).hexdigest() == proof['sourceModelSha256']
bpy.ops.wm.open_mainfile(filepath=str(MODEL))
bpy.context.window.scene = bpy.data.scenes['00_CAMPUS_COMPLETE']
for scene in bpy.data.scenes:
    for layer in scene.view_layers:
        layer.update()
assert geometry_signatures() == proof['geometrySignatures']
source, target = bpy.data.objects[SOURCE], bpy.data.objects[TARGET]
assert source.hide_render and not target.hide_render
assert source.matrix_world == target.matrix_world
assert [tuple(v.co) for v in source.data.vertices] == [tuple(v.co) for v in target.data.vertices]
assert [tuple(p.vertices) for p in source.data.polygons] == [tuple(p.vertices) for p in target.data.polygons]
for layer in source.data.uv_layers:
    assert [tuple(p.uv) for p in layer.data] == [tuple(p.uv) for p in target.data.uv_layers[layer.name].data]
change = json.loads((ROOT / 'result/blender/stage186/building-refinement.json').read_text())['changes'][0]
selected = set(index for pane in change['selectedPanes'] for index in pane['vertices'])
changed_faces = 0
for old, new in zip(source.data.polygons, target.data.polygons):
    if set(old.vertices) <= selected:
        assert target.data.materials[new.material_index].name == 'SAR186_clear_street_glass'
        changed_faces += 1
    else:
        assert target.data.materials[new.material_index] == source.data.materials[old.material_index]
assert changed_faces == 24 and len(change['selectedPanes']) == 4
material = bpy.data.materials['SAR186_clear_street_glass']
assert material['webClosedGlazing'] and abs(material['webOpacity'] - .38) < 1e-6
assert material.node_tree.nodes['Principled BSDF'].inputs['Metallic'].default_value == 0
assert len(bpy.data.objects[SHADING].data.polygons) == 84 * 6
assert len(bpy.data.objects[BACKING].data.polygons) == 4
vertices, faces, owners = [], [], []
for obj in bpy.data.collections['SAR_EXTERIOR'].all_objects:
    if obj.type != 'MESH' or obj.hide_render:
        continue
    offset = len(vertices)
    vertices.extend(obj.matrix_world @ vertex.co for vertex in obj.data.vertices)
    obj.data.calc_loop_triangles()
    for face in obj.data.loop_triangles:
        faces.append(tuple(offset + index for index in face.vertices))
        owners.append(obj.name)
facade = BVHTree.FromPolygons(vertices, faces, all_triangles=True)
_, origin, axis, normal = facade_registration()
probes = []
for window in change['windows']:
    width = window['width'] - .08
    left = window['x'] - width / 2
    for slat in [3, 8, 13, 18]:
        x = left + (slat + .5) * width / 20
        for z in [.9, 1.6, 2.25]:
            point = origin + axis * x + Vector((0, 0, z))
            first = facade.ray_cast(point + normal * .50, -normal, 1)
            behind = facade.ray_cast(point - normal * .10, -normal, .35)
            assert first[2] is not None and owners[first[2]] == TARGET, (window['bay'], slat, z, first)
            assert behind[2] is not None and owners[behind[2]] == SHADING, (window['bay'], slat, z, behind)
            assert first[1].dot(normal) > .99 and behind[1].dot(normal) > .99
            probes.append({'bay': window['bay'], 'slat': slat, 'height': z,
                           'firstSurface': owners[first[2]], 'behindGlass': owners[behind[2]]})
assert len(probes) == 48
assert all(name in bpy.context.scene.objects for name in [TARGET, SHADING, BACKING])
assert apply_sar_glazing186()['alreadyApplied']
assert geometry_signatures() == proof['geometrySignatures']
(STAGE / 'glazing-verification.json').write_text(json.dumps({
    'sourceModelSha256': proof['sourceModelSha256'], 'savedSceneReopened': True,
    'treatedWindows': 4, 'blindSlats': 80, 'twoLayerSightlines': probes,
    'originalGlassGeometryAndUVsPreserved': True, 'otherPaneFinishesPreserved': True,
}, indent=2) + '\n')
print('SAR186_GLAZING_VERIFIED')
