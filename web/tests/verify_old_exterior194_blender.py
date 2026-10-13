"""Reopen the isolated OLD194 finish component against its accepted baseline."""
from pathlib import Path
import hashlib
import json
import sys
import bpy
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'web/tools'))
from refine_old_exterior194 import shape_state, UV_NAME
from refine_old_painted_frames import material_state
OUT = ROOT / 'result/blender/old-exterior194'
report = json.loads((OUT / 'building-refinement.json').read_text())
base = ROOT / report['baseline']
component = ROOT / report['component']
assert hashlib.sha256(base.read_bytes()).hexdigest() == report['baselineSha256']
assert hashlib.sha256(component.read_bytes()).hexdigest() == report['componentSha256']
bpy.ops.wm.open_mainfile(filepath=str(base))
for scene in bpy.data.scenes:
    for layer in scene.view_layers:
        layer.update()
baseline = {}
for item in report['replacements']:
    obj = bpy.data.objects[item['original']]
    baseline[item['original']] = dict(shape=shape_state(obj), materials=[material_state(m) for m in obj.data.materials])
bpy.ops.wm.read_factory_settings(use_empty=True)
with bpy.data.libraries.load(str(component), link=False) as (available, loaded):
    loaded.objects = report['addedObjects']
collection = bpy.data.collections.new('OLD_EXTERIOR')
bpy.context.scene.collection.children.link(collection)
for obj in loaded.objects:
    collection.objects.link(obj)
bpy.context.view_layer.update()
changed_slots = {(item['object'], item['slot']) for item in report['bindings']}
for item in report['replacements']:
    obj = bpy.data.objects[item['replacement']]
    source = baseline[item['original']]
    assert obj['originalObject'] == item['original']
    state = shape_state(obj)
    assert state['geometry'] == source['shape']['geometry']
    assert all(state['uv'][key] == value for key, value in source['shape']['uv'].items())
    assert len(state['uv']) == len(source['shape']['uv']) + 1
    assert obj.data.uv_layers[UV_NAME].active_render
    for index, material in enumerate(obj.data.materials):
        if (obj.name, index) not in changed_slots:
            assert material_state(material) == source['materials'][index]
            continue
        assert material.get('webBaseColorMap')
        nodes = material.node_tree.nodes
        shader = nodes['Principled BSDF']
        assert shader.inputs['Base Color'].links[0].from_node.type == 'TEX_IMAGE'
        assert shader.inputs['Metallic'].default_value == 0
        assert abs(shader.inputs['Roughness'].default_value - .89) < 1e-6
        texture = shader.inputs['Base Color'].links[0].from_node
        assert texture.image.packed_file and texture.image.colorspace_settings.name == 'sRGB'
        assert list(texture.image.size) == [512, 512]
        assert texture.inputs['Vector'].links[0].from_node.uv_map == UV_NAME
        assert hashlib.sha256(texture.image.packed_file.data).hexdigest() == report['image']['sha256']
assert all(obj.library is None and obj.data.library is None for obj in loaded.objects)
assert all(material.library is None for obj in loaded.objects for material in obj.data.materials)
assert all(image.library is None for image in bpy.data.images)
assert hashlib.sha256(base.read_bytes()).hexdigest() == report['baselineSha256']
proof = dict(componentReopened=True, objects=len(loaded.objects),
             originalTopologyPositionsMaterialIndicesAndUVPreserved=True,
             nonStoneMaterialInputsPreserved=True, imagePackedAndVerified=True,
             baselineUnchanged=True, componentSha256=report['componentSha256'])
(OUT/'verification.json').write_text(json.dumps(proof, indent=2)+'\n')
print('OLD194_REOPENED_VERIFIED', len(loaded.objects), flush=True)
