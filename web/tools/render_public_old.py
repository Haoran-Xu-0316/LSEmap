"""Render a public OLD entrance image without the archive's photographic relief."""
from pathlib import Path
import bpy

ROOT = Path(__file__).resolve().parents[2]
bpy.ops.wm.open_mainfile(filepath=str(ROOT / 'result/blender/LSE_campus_detailed_v03.blend'))
for material in bpy.data.materials:
    if not material.use_nodes:
        continue
    for node in list(material.node_tree.nodes):
        if node.type == 'TEX_IMAGE':
            material.node_tree.nodes.remove(node)
    if 'photo_projection' in material.name:
        material.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.55, 0.52, 0.46, 1)
scene = bpy.data.scenes['06_OLD_DETAIL_REVIEW']
scene.camera = bpy.data.objects['OLD_DETAIL_Houghton_entry']
scene.render.resolution_x = 1000
scene.render.resolution_y = 1400
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'WEBP'
scene.render.image_settings.quality = 86
scene.render.filepath = str(ROOT / 'web/public/images/old-exterior.webp')
scene.cycles.samples = 32
scene.cycles.use_denoising = True
scene.view_settings.exposure = -0.8
try:
    preferences = bpy.context.preferences.addons['cycles'].preferences
    preferences.compute_device_type = 'METAL'
    preferences.get_devices()
    for device in preferences.devices:
        device.use = device.type == 'METAL'
    scene.cycles.device = 'GPU'
except Exception:
    scene.cycles.device = 'CPU'
bpy.ops.render.render(write_still=True, scene=scene.name)
