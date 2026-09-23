"""Render the original local POR reconstruction; no archive photo is embedded."""
from pathlib import Path
import json
import bpy
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'result/blender/stage16/renders';OUT.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v16.blend'))
record=json.loads((ROOT/'result/blender/stage16/portsmouth/portsmouth-manifest.json').read_text())['buildings'][0]
scene=bpy.data.scenes.new('REVIEW_POR_V16')
scene.collection.children.link(bpy.data.collections['POR_EXTERIOR'])
bpy.context.window.scene=scene;bpy.context.view_layer.update()
points=[o.matrix_world@Vector(p) for o in scene.objects if o.type in {'MESH','FONT'} for p in o.bound_box]
low=Vector(tuple(min(p[i] for p in points) for i in range(3)));high=Vector(tuple(max(p[i] for p in points) for i in range(3)));center=(low+high)/2
camera=bpy.data.objects.new('POR_V16_CAMERA',bpy.data.cameras.new('POR_V16_CAMERA'));scene.collection.objects.link(camera);scene.camera=camera
scene.world=bpy.data.worlds.new('POR_V16_WORLD');scene.world.use_nodes=True
scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.65,.70,.74,1)
scene.world.node_tree.nodes['Background'].inputs[1].default_value=.8
sun=bpy.data.objects.new('POR_V16_SUN',bpy.data.lights.new('POR_V16_SUN','SUN'));scene.collection.objects.link(sun);sun.data.energy=2;sun.data.angle=.15;sun.rotation_euler=(.5,-.45,-.5)
scene.render.engine='CYCLES';scene.cycles.samples=24;scene.cycles.use_denoising=True
scene.render.resolution_x=1400;scene.render.resolution_y=1200;scene.render.resolution_percentage=100
scene.view_settings.view_transform='AgX';scene.render.image_settings.file_format='PNG'
direction=record['exteriorDirection'];outward=Vector((direction[0],-direction[2],.30)).normalized()
camera.data.type='ORTHO';camera.data.clip_end=1000
for name,target,normal,scale in [('por-exterior',center,outward,24.5),('por-entrance',Vector(record['detailView']['target']),Vector(record['detailView']['position'])-Vector(record['detailView']['target']),8.0)]:
 camera.location=target+normal.normalized()*60;camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.ortho_scale=scale
 scene.render.filepath=str(OUT/(name+'.png'));bpy.ops.render.render(write_still=True)
 print('RENDERED',name,flush=True)
