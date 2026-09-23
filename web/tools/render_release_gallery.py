"""Render every published gallery from the same edition-16 native model.
Run in Blender. Archive photographs are removed before rendering public assets.
"""
from pathlib import Path
import bpy,json,hashlib,math
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'result/web/release16/renders';OUT.mkdir(parents=True,exist_ok=True)
MODEL=ROOT/'result/blender/LSE_campus_detailed_v16.blend'
bpy.ops.wm.open_mainfile(filepath=str(MODEL))
for scene in bpy.data.scenes:
 for layer in scene.view_layers:layer.update()
for material in bpy.data.materials:
 if material.use_nodes:
  for node in list(material.node_tree.nodes):
   if node.type=='TEX_IMAGE':material.node_tree.nodes.remove(node)
  if 'photo_projection' in material.name:material.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(.55,.52,.46,1)
catalogue={r['code']:r for r in json.loads((ROOT/'web/public/models/catalogue.json').read_text())['buildings']}
plan=json.loads((ROOT/'result/web/release16/gallery-plan.json').read_text())
# Existing source cameras for architectural features beyond entrance presets.
camera_names=[o.name for o in bpy.data.objects if o.type=='CAMERA']
(OUT.parent/'cameras.json').write_text(json.dumps(camera_names,indent=2))
extras={'mar-hall':'MAR_D3_hall','mar-stair':'MAR_D3_stair','saw-brick':'SAW_brick_screen_closeup','ocs-roof':'OCS_D3_front_street_camera','pan-faw-entrance':'PAN_FAW_D3_entrance'}
def native(v):return Vector((v[0],-v[2],v[1]))
reports=json.loads((OUT.parent/'gallery-manifest.json').read_text()) if (OUT.parent/'gallery-manifest.json').exists() else []
for job in plan+[{'code':'CAMPUS','name':'campus','label':'Campus'}]:
 name,code=job['name'],job['code']
 if any(r['name']==name for r in reports):continue
 record=catalogue.get(code)
 scene=bpy.data.scenes.new('RELEASE16_'+name)
 if code=='CAMPUS':
  source=bpy.data.scenes['00_CAMPUS_COMPLETE']
  for col in source.collection.children:scene.collection.children.link(col)
 else:
  is_interior=name.endswith('-interior') or name in {'mar-hall','mar-stair'}
  interior=bpy.data.collections.get(code+'_PUBLIC_INTERIOR_study')
  if is_interior:
   objects=list(interior.all_objects)
   if code=='MAR':
    objects=[o for o in objects if '_floor_way/' not in o.name or max((o.matrix_world@Vector(c)).z for c in o.bound_box)<=13]
    objects += [o for o in bpy.data.collections['MAR_EXTERIOR'].all_objects if 'ground_glass_panes' in o.name]
   if code=='LRB':objects += [o for o in bpy.data.collections['LRB_EXTERIOR'].all_objects if 'roof_' in o.name]
   for obj in dict.fromkeys(objects):scene.collection.objects.link(obj)
  else:
   scene.collection.children.link(bpy.data.collections[code+'_EXTERIOR'])
   if interior:scene.collection.children.link(interior)
  if name.startswith('pan-faw'):
   scene.collection.children.link(bpy.data.collections['FAW_EXTERIOR'])
 bpy.context.window.scene=scene;bpy.context.view_layer.update()
 points=[o.matrix_world@Vector(p) for o in scene.objects if o.type in {'MESH','FONT'} and not o.hide_render for p in o.bound_box]
 lo=Vector(tuple(min(p[i] for p in points) for i in range(3)));hi=Vector(tuple(max(p[i] for p in points) for i in range(3)));center=(lo+hi)/2
 camera=bpy.data.objects.new(name+'_camera',bpy.data.cameras.new(name+'_camera'));scene.collection.objects.link(camera);scene.camera=camera;camera.data.clip_end=3000
 close=record and ('entrance' in name or name.endswith('-windows')) and record.get('detailView')
 interior_view=record and name.endswith('-interior') and record.get('interiorView')
 if code=='CAMPUS':
  original=bpy.data.objects['01_campus_aerial'];camera.matrix_world=original.matrix_world.copy();camera.data=original.data.copy()
 elif interior_view or close:
  view=interior_view or close;camera.location=native(view['position']);target=native(view['target']);camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.type='PERSP';camera.data.angle=math.radians(view.get('fov',50))
 elif name in extras and extras[name] in bpy.data.objects:
  original=bpy.data.objects[extras[name]];camera.matrix_world=original.matrix_world.copy();camera.data=original.data.copy()
 else:
  d=record.get('exteriorDirection',[.7,.4,1]);normal=Vector((d[0],-d[2],.30)).normalized();camera.location=center+normal*200;camera.rotation_euler=(center-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.type='ORTHO'
  bpy.context.view_layer.update();projected=[camera.matrix_world.inverted()@p for p in points];w=max(p.x for p in projected)-min(p.x for p in projected);h=max(p.y for p in projected)-min(p.y for p in projected);camera.data.ortho_scale=max(w,h*1.25)*1.20
 scene.world=bpy.data.worlds.new(name+'_world');scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.55,.63,.70,1);scene.world.node_tree.nodes['Background'].inputs[1].default_value=.75
 for label,offset,power,size in [('key',(-25,-35,55),2500,35),('fill',(30,20,35),1700,30)]:
  light=bpy.data.objects.new(name+label,bpy.data.lights.new(name+label,'AREA'));scene.collection.objects.link(light);light.data.energy=power;light.data.shape='DISK';light.data.size=size;light.location=center+Vector(offset);light.rotation_euler=(center-light.location).to_track_quat('-Z','Y').to_euler()
 sun=bpy.data.objects.new(name+'_sun',bpy.data.lights.new(name+'_sun','SUN'));scene.collection.objects.link(sun);sun.data.energy=2;sun.data.angle=.15;sun.rotation_euler=(.5,-.45,-.5)
 scene.render.engine='CYCLES';scene.cycles.samples=16;scene.cycles.use_denoising=True;scene.cycles.max_bounces=6;scene.render.resolution_x=1400;scene.render.resolution_y=1120;scene.render.resolution_percentage=100;scene.view_settings.view_transform='AgX'
 scene.render.image_settings.file_format='PNG';scene.render.filepath=str(OUT/(name+'.png'))
 bpy.ops.render.render(write_still=True)
 reports.append({'name':name,'code':code,'sourceModelSha256':hashlib.sha256(MODEL.read_bytes()).hexdigest()})
 (OUT.parent/'gallery-manifest.json').write_text(json.dumps(reports,indent=2)+'\n')
 print('RELEASE_GALLERY',len(reports),name,flush=True)
 bpy.data.scenes.remove(scene)
print('RELEASE_GALLERY_COMPLETE',flush=True)
