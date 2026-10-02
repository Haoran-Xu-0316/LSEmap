"""Prepare an isolated MAR upper-screen candidate from the saved v113 campus.

Run in Blender's Text Editor. This file never exports web assets or overwrites
its input. North-screen span and vertical datum remain photographic estimates.
"""
from pathlib import Path
import array
import hashlib
import json
import math
import sys
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'result/blender/stage114/mar'
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(Path(__file__).resolve().parent))
from facade_geometry import Geometry, materials

INPUT = ROOT / 'result/blender/LSE_campus_detailed_v113.blend'
bpy.ops.wm.open_mainfile(filepath=str(INPUT))
for scene in bpy.data.scenes:
    for layer in scene.view_layers:
        layer.update()

def fingerprint(obj):
    digest = hashlib.sha256()
    digest.update(array.array('f', [value for row in obj.matrix_world for value in row]).tobytes())
    if obj.type == 'MESH':
        digest.update(array.array('f', [value for vertex in obj.data.vertices for value in vertex.co]).tobytes())
        digest.update(array.array('i', [loop.vertex_index for loop in obj.data.loops]).tobytes())
        digest.update(str([tuple(face.vertices) for face in obj.data.polygons]).encode())
    digest.update(str([material.name if material else None for material in getattr(obj.data, 'materials', [])]).encode())
    return digest.hexdigest()

before = {obj.name: fingerprint(obj) for obj in bpy.data.objects}
source = bpy.data.objects['MAR_upper_screen_fins']
assert not source.hide_render
assert len(source.data.vertices) == 43 * 8
surface = json.loads((ROOT / 'result/blender/stage02/detail_geometry.json').read_text())
centre_x, centre_y = surface['mar_center']
angle = math.radians(22)

def point(x, depth, height):
    return (centre_x + math.cos(angle) * x - math.sin(angle) * depth,
            centre_y + math.sin(angle) * x + math.cos(angle) * depth, height)

material = source.data.materials[0].copy()
material.name = 'MAR_NEXT_upper_fins_precast'
# Manufacturer describes outer fins as slightly darker than recessed panels.
# Numeric reflectance is an estimate, not a measured material specification.
color = (.64, .625, .59, 1.0)
material.diffuse_color = color
shader = material.node_tree.nodes.get('Principled BSDF')
if shader:
    shader.inputs['Base Color'].default_value = color
    shader.inputs['Roughness'].default_value = .78
materials.clear()
materials['precast'] = material
fins = Geometry('MAR', 'NEXT_upper_screen_shafts', 'precast')
heads = Geometry('MAR', 'NEXT_upper_screen_hammerheads', 'precast')
parameters = {'count': 38, 'height': 11.5, 'streetFaceWidth': .3, 'shaftDepth': .5,
              'topReturn': 2.4, 'estimatedSpan': 54.0, 'estimatedTop': 35.6,
              'estimatedReturnThickness': .5, 'estimatedOutwardEdge': 21.0}
records = []
for index in range(parameters['count']):
    x = -30 + index * parameters['estimatedSpan'] / (parameters['count'] - 1)
    fins.box(point(x, 20.75, 29.85), (.3, .5, 11.5), angle)
    # Return joins the shaft at its top and extends inward to the inner facade.
    # Avoid overlapping solid volumes at their shared connection.
    heads.box(point(x, 19.55, 35.35), (.3, 1.9, .5), angle)
    records.append({'index': index, 'localX': x, 'shaftBottom': 24.1, 'shaftTop': 35.6,
                    'outerDepth': 21.0, 'innerReturnDepth': 18.6})
added = []
for geometry in (fins, heads):
    obj = geometry.finish()
    for modifier in list(obj.modifiers):
        obj.modifiers.remove(modifier)
    obj['evidence'] = 'Concrete Quarterly 279, summer 2022; Techrete project manager interview'
    obj['scope'] = 'North upper screen only; retained span and absolute heights estimated'
    added.append(obj.name)
source.hide_render = True
source.hide_set(True)
for scene in bpy.data.scenes:
    for layer in scene.view_layers:
        layer.update()
assert all(fingerprint(bpy.data.objects[name]) == value for name, value in before.items())
assert set(obj.name for obj in bpy.data.objects) - set(before) == set(added)
assert fins.parts == heads.parts == 38
candidate = OUT / 'MAR_upper_screen_candidate_v113.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(candidate))
audit = {'status': 'isolated-candidate-not-integrated', 'baseline': 113,
         'inputModel': str(INPUT.relative_to(ROOT)), 'candidate': str(candidate.relative_to(ROOT)),
         'sourceModelSha256': hashlib.sha256(INPUT.read_bytes()).hexdigest(),
         'parameters': parameters, 'fins': records, 'addedObjects': added,
         'archivedObjects': [source.name], 'originalGeometryRetained': True,
         'otherBuildingsAndInteriorsRetained': True,
         'referenceUrl': 'https://www.concretecentre.com/Case-Studies/Marshall-Building,-London.aspx',
         'photoReferences': ['MAR_mar_kane_02.jpg', 'MAR_mar_kane_03.jpg'],
         'limitations': ['No measured as-built absolute level, span or return thickness',
                        '38 north fins are distinct from 19 fins on other elevations',
                        'Lower screen, roof masses, interior and north backing walls untouched',
                        'Final visual review and independent saved-file verification still required']}
(OUT / 'mar-upper-screen-audit.json').write_text(json.dumps(audit, indent=2) + '\n')
print('MAR_UPPER_SCREEN_CANDIDATE_SAVED', len(records), flush=True)
