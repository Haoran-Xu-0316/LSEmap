"""Render the edition 04 street studies and refresh the public campus overview."""
from pathlib import Path
import bpy

ROOT = Path(__file__).resolve().parents[2]
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v04.blend'))
# Never distribute the archive's photo-projected relief, including in the overview.
for material in bpy.data.materials:
    if not material.use_nodes:continue
    for node in list(material.node_tree.nodes):
        if node.type=='TEX_IMAGE':material.node_tree.nodes.remove(node)
    if 'photo_projection' in material.name:
        material.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(.55,.52,.46,1)
try:
    preferences=bpy.context.preferences.addons['cycles'].preferences
    preferences.compute_device_type='METAL';preferences.get_devices()
    for device in preferences.devices:device.use=device.type=='METAL'
    device_type='GPU'
except Exception:
    device_type='CPU'
views=[('12_COL_DETAIL_REVIEW','COL_D4_facade','col-exterior',1200,1400),
       ('12_COL_DETAIL_REVIEW','COL_D4_entrance','col-entrance',1200,1400),
       ('13_CON_DETAIL_REVIEW','CON_D4_facade','con-exterior',1200,1400),
       ('13_CON_DETAIL_REVIEW','CON_D4_entrance','con-entrance',1200,1400),
       ('00_CAMPUS_COMPLETE','01_campus_aerial','campus',1800,1200)]
for scene_name,camera_name,filename,width,height in views:
    scene=bpy.data.scenes[scene_name];bpy.context.window.scene=scene
    scene.camera=bpy.data.objects[camera_name]
    scene.render.engine='CYCLES';scene.cycles.device=device_type
    scene.cycles.samples=32;scene.cycles.use_denoising=True
    scene.render.resolution_x=width;scene.render.resolution_y=height;scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='WEBP';scene.render.image_settings.quality=88
    scene.render.filepath=str(ROOT/'web/public/images'/f'{filename}.webp')
    bpy.ops.render.render(write_still=True,scene=scene.name)
    print('RENDERED',filename,flush=True)
