"""Refine OLD's photographed limestone finish without changing its geometry.
Run in Blender's Text Editor. Colours are photo estimates, not measured samples.
"""
from pathlib import Path
import array
import hashlib
import json
import shutil
import bpy

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'result/blender/stage86'
OUT.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT / 'result/blender/LSE_campus_detailed_v85.blend'))

def geometry_hash(obj):
    digest = hashlib.sha256(str([list(row) for row in obj.matrix_world]).encode())
    if obj.type == 'MESH':
        digest.update(array.array('f', [c for v in obj.data.vertices for c in v.co]).tobytes())
        digest.update(array.array('i', [loop.vertex_index for loop in obj.data.loops]).tobytes())
    return digest.hexdigest()

before = {obj.name: {'geometry': geometry_hash(obj),
                    'materials': [m.name if m else None for m in getattr(obj.data, 'materials', [])]}
          for obj in bpy.data.objects}
# Include the cut edges and heraldic stone, but exclude glazing, plastic artwork,
# soil, metal and shadow inserts. Preserve the actual recessed-joint colour.
extra_stone = {'OLD_V53_edge', 'V16_OLD_finish', 'V17_OLD_finish',
               'OLD_V74_field', 'OLD_V74_incision'}
copies = {}
assignments = []
for obj in bpy.data.collections['OLD_EXTERIOR'].all_objects:
    if obj.hide_render:
        continue
    for index, source in enumerate(getattr(obj.data, 'materials', [])):
        if not source or not ('stone' in source.name.lower() or 'ashlar' in source.name.lower()
                              or source.name in extra_stone):
            continue
        if source.name not in copies:
            material = source.copy()
            material.name = 'OLD_V86_limestone_' + source.name
            material.use_nodes = True
            nodes, links = material.node_tree.nodes, material.node_tree.links
            # Rebuild the owned finish graph instead of accumulating legacy nodes.
            nodes.clear()
            output = nodes.new('ShaderNodeOutputMaterial')
            shader = nodes.new('ShaderNodeBsdfPrincipled')
            luminance = sum(c * w for c, w in zip(source.diffuse_color[:3], (.2126, .7152, .0722)))
            color = (luminance * 1.025, luminance * 1.007, luminance * .975)
            material.diffuse_color = (*color, 1)
            shader.inputs['Base Color'].default_value = (*color, 1)
            shader.inputs['Roughness'].default_value = .87
            shader.inputs['Metallic'].default_value = 0
            coordinates = nodes.new('ShaderNodeTexCoord')
            noise = nodes.new('ShaderNodeTexNoise')
            noise.inputs['Scale'].default_value = 2.0
            noise.inputs['Detail'].default_value = 2
            ramp = nodes.new('ShaderNodeValToRGB')
            for element, factor in zip(ramp.color_ramp.elements, (.90, 1.08)):
                element.color = (*[c * factor for c in color], 1)
            bump = nodes.new('ShaderNodeBump')
            bump.inputs['Strength'].default_value = .25
            bump.inputs['Distance'].default_value = .0012
            links.new(coordinates.outputs['Object'], noise.inputs['Vector'])
            links.new(noise.outputs['Fac'], ramp.inputs['Fac'])
            links.new(ramp.outputs['Color'], shader.inputs['Base Color'])
            links.new(noise.outputs['Fac'], bump.inputs['Height'])
            links.new(bump.outputs['Normal'], shader.inputs['Normal'])
            links.new(shader.outputs['BSDF'], output.inputs['Surface'])
            # Carry identical finish parameters into the campus overview as well.
            material['siteDetail'] = True
            copies[source.name] = material
        obj.data.materials[index] = copies[source.name]
        assignments.append({'object': obj.name, 'slot': index, 'source': source.name,
                            'material': copies[source.name].name})
assert assignments
assert all(geometry_hash(bpy.data.objects[name]) == record['geometry'] for name, record in before.items())
for name in ['room-studies.json', 'room-spaces.json', 'building-review.json']:
    shutil.copyfile(ROOT / 'result/blender/stage85' / name, OUT / name)
shutil.copyfile(ROOT / 'web/public/models/catalogue.json', OUT / 'catalogue-before.json')
audit = {'version': 86, 'baseline': 85, 'baselineObjects': before, 'assignments': assignments,
         'materials': [m.name for m in copies.values()],
         'reference': 'User supplied OLD Houghton entrance and full frontal Damian Griffiths project photograph',
         'limitations': ['Colour, grain and roughness are photographic estimates, not calibrated samples',
                         'Procedural grain is not a photo texture or a measured weathering pattern',
                         'Roof, building massing and interiors remain unchanged and need further review']}
(OUT / 'old-limestone-audit.json').write_text(json.dumps(audit, indent=2) + '\n')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / 'result/blender/LSE_campus_detailed_v86.blend'))
print('OLD_LIMESTONE_SAVED', len(copies), len(assignments), flush=True)
