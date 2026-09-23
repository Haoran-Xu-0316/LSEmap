"""Render original version-07 street model for public gallery thumbnails.
Run inside Blender. No archival reference photograph is read or embedded.
"""
from pathlib import Path
import json
import bpy
from mathutils import Vector
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'result/blender/stage07/renders'
OUT.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT / 'result/blender/LSE_campus_detailed_v07.blend'))
# Earlier galleries remain unchanged; render the newly developed Aldwych elevation.
records = [json.loads((ROOT / 'result/blender/stage07/aldwych-manifest.json').read_text())]
for record in records:
    code = record['code']
    scene = bpy.data.scenes.new('RENDER_INFILL_'+code)
    scene.collection.children.link(bpy.data.collections[code+'_EXTERIOR'])
    bpy.context.window.scene = scene
    bpy.context.view_layer.update()
    points = [o.matrix_world @ Vector(p) for o in scene.objects if o.type in {'MESH','FONT'} for p in o.bound_box]
    low = Vector(tuple(min(p[i] for p in points) for i in range(3)))
    high = Vector(tuple(max(p[i] for p in points) for i in range(3)))
    center = (low+high)/2
    direction = record['exteriorDirection']
    normal = Vector((direction[0],-direction[2],.38)).normalized()
    camera_data = bpy.data.cameras.new(code+'_gallery_camera')
    camera = bpy.data.objects.new(camera_data.name,camera_data)
    scene.collection.objects.link(camera)
    camera.location = center+normal*100
    camera.rotation_euler = (center-camera.location).to_track_quat('-Z','Y').to_euler()
    bpy.context.view_layer.update()
    projected = [camera.matrix_world.inverted() @ p for p in points]
    width = max(p.x for p in projected)-min(p.x for p in projected)
    height = max(p.y for p in projected)-min(p.y for p in projected)
    camera_data.type='ORTHO'
    camera_data.ortho_scale=max(width,height*1.25)*1.20
    camera_data.clip_end=1000
    scene.camera=camera
    scene.world=bpy.data.worlds.new(code+'_studio')
    scene.world.use_nodes=True
    scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.55,.63,.70,1)
    scene.world.node_tree.nodes['Background'].inputs[1].default_value=.65
    for name,offset,power,size in [('key',Vector((-25,-35,55)),2200,35),('fill',Vector((30,20,35)),1700,30)]:
        light=bpy.data.lights.new(code+'_'+name,'AREA');light.energy=power;light.shape='DISK';light.size=size
        obj=bpy.data.objects.new(light.name,light);scene.collection.objects.link(obj);obj.location=center+offset
        obj.rotation_euler=(center-obj.location).to_track_quat('-Z','Y').to_euler()
    sun=bpy.data.lights.new(code+'_sun','SUN');sun.energy=2;sun.angle=.15
    obj=bpy.data.objects.new(sun.name,sun);scene.collection.objects.link(obj);obj.rotation_euler=(.5,-.45,-.5)
    scene.render.engine='CYCLES';scene.cycles.samples=12;scene.cycles.use_denoising=True
    scene.render.resolution_x=1000;scene.render.resolution_y=800;scene.render.resolution_percentage=100
    scene.view_settings.view_transform='AgX'
    scene.render.image_settings.file_format='PNG';scene.render.filepath=str(OUT/(code.lower()+'-exterior.png'))
    bpy.ops.render.render(write_still=True)
    print('RENDERED',code,flush=True)

# Refresh the overview from the same model, with archival image projections removed.
for material in bpy.data.materials:
    if not material.use_nodes:
        continue
    for node in list(material.node_tree.nodes):
        if node.type == 'TEX_IMAGE':
            material.node_tree.nodes.remove(node)
    if 'photo_projection' in material.name:
        material.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(.55,.52,.46,1)
scene=bpy.data.scenes['00_CAMPUS_COMPLETE']
bpy.context.window.scene=scene
scene.camera=bpy.data.objects['01_campus_aerial']
scene.render.engine='CYCLES';scene.cycles.samples=12;scene.cycles.use_denoising=True
scene.render.resolution_x=1600;scene.render.resolution_y=1000;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.render.filepath=str(OUT/'campus.png')
bpy.ops.render.render(write_still=True)
print('RENDERED_CAMPUS',flush=True)
