"""Verify that geometry, shading and camera changes invalidate render reuse."""
from pathlib import Path
import json
import sys
import bpy
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from gallery_fingerprint import RenderFingerprint

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.world = bpy.data.worlds.new('World')
scene.world.use_nodes = True
bpy.ops.mesh.primitive_cube_add()
cube = bpy.context.object
material = bpy.data.materials.new('Surface')
material.use_nodes = True
cube.data.materials.append(material)
camera = bpy.data.objects.new('Camera', bpy.data.cameras.new('Camera'))
scene.collection.objects.link(camera)
scene.camera = camera
light = bpy.data.objects.new('Light', bpy.data.lights.new('Light', 'AREA'))
scene.collection.objects.link(light)

def signature():
    return RenderFingerprint().scene(scene)

baseline = signature()
checks = {'repeatable': signature() == baseline}
cube.name = 'RenamedObject'
checks['object_name_does_not_change_image'] = signature() == baseline
cube.data.vertices[0].co.x += .1
checks['geometry_invalidates'] = signature() != baseline
cube.data.vertices[0].co.x -= .1
baseline = signature()
shader = material.node_tree.nodes['Principled BSDF']
color = tuple(shader.inputs['Base Color'].default_value)
shader.inputs['Base Color'].default_value = (.1, .2, .3, 1)
checks['material_invalidates'] = signature() != baseline
shader.inputs['Base Color'].default_value = color
camera.data.lens += 1
checks['camera_invalidates'] = signature() != baseline
camera.data.lens -= 1
light.data.energy += 10
checks['lighting_invalidates'] = signature() != baseline
light.data.energy -= 10
scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value += .1
checks['world_invalidates'] = signature() != baseline
baseline = signature()
uv = cube.data.uv_layers.active.data[0]
uv.uv.x += .01
checks['meaningful_uv_change_invalidates'] = signature() != baseline
assert all(checks.values()), checks
root = Path(__file__).resolve().parents[2]
(root / 'result/blender/stage21/fingerprint-audit.json').write_text(json.dumps(checks, indent=2)+'\n')
print('RENDER_FINGERPRINT_AUDIT_PASS', json.dumps(checks), flush=True)
