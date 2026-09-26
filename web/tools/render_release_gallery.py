"""Render edition 24, reusing only views with identical evaluated render inputs.

Run in Blender. The original render edition and the verified current model edition
are both recorded, so reuse never masquerades as a new render or an unchecked copy.
"""
from pathlib import Path
import bpy, json, hashlib, math, shutil, sys
from mathutils import Vector
sys.path.insert(0, str(Path(__file__).resolve().parent))
from gallery_fingerprint import RenderFingerprint
ROOT = Path(__file__).resolve().parents[2]
RELEASE = ROOT / 'result/web/release24'
OUT = RELEASE / 'renders'
OUT.mkdir(parents=True, exist_ok=True)
MODEL = ROOT / 'result/blender/LSE_campus_detailed_v24.blend'
PREVIOUS = ROOT / 'result/blender/LSE_campus_detailed_v23.blend'
extras = {'mar-hall':'MAR_D3_hall','mar-stair':'MAR_D3_stair','saw-brick':'SAW_brick_screen_closeup','ocs-roof':'OCS_D3_front_street_camera','pan-faw-entrance':'PAN_FAW_D3_entrance'}
def native(vector):
 return Vector((vector[0], -vector[2], vector[1]))
def open_public_model(path):
 bpy.ops.wm.open_mainfile(filepath=str(path))
 for scene in bpy.data.scenes:
  for layer in scene.view_layers:layer.update()
 for material in bpy.data.materials:
  if material.use_nodes:
   for node in list(material.node_tree.nodes):
    if node.type=='TEX_IMAGE':material.node_tree.nodes.remove(node)
   if 'photo_projection' in material.name:
    material.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(.55,.52,.46,1)
def build_scene(job, catalogue):
 name, code = job['name'], job['code']
 record=catalogue.get(code)
 if job.get('spaceId'):
  space=next(item for item in record['interiorSpaces'] if item['id']==job['spaceId'])
  record={**record, **space}
 scene=bpy.data.scenes.new('GALLERY_'+name)
 if code=='CAMPUS':
  source=bpy.data.scenes['00_CAMPUS_COMPLETE']
  for col in source.collection.children:scene.collection.children.link(col)
 else:
  is_interior=name.endswith('-interior') or name in {'mar-hall','mar-stair'}
  interior=bpy.data.collections.get(job.get('collection',code+'_PUBLIC_INTERIOR_study'))
  if is_interior:
   objects=list(interior.all_objects)
   if code=='MAR' and not job.get('spaceId'):
    objects=[o for o in objects if '_floor_way/' not in o.name or max((o.matrix_world@Vector(c)).z for c in o.bound_box)<=13]
    objects += [o for o in bpy.data.collections['MAR_EXTERIOR'].all_objects if 'ground_glass_panes' in o.name]
   if code=='LRB':objects += [o for o in bpy.data.collections['LRB_EXTERIOR'].all_objects if 'roof_' in o.name]
   for obj in dict.fromkeys(objects):scene.collection.objects.link(obj)
  else:
   scene.collection.children.link(bpy.data.collections[code+'_EXTERIOR'])
   if interior and not interior.get('roomSample'):scene.collection.children.link(interior)
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
 scene.render.image_settings.file_format='PNG'
 return scene

plan = json.loads((RELEASE / 'gallery-plan.json').read_text())
jobs = plan + [{'code':'CAMPUS', 'name':'campus', 'label':'Campus'}]
old_payload = json.loads((RELEASE / 'previous-catalogue.json').read_text())
old_gallery = json.loads((RELEASE / 'previous-gallery.json').read_text())
previous_hash = hashlib.sha256(PREVIOUS.read_bytes()).hexdigest()
assert old_payload['sourceModelSha256'] == old_gallery['sourceModelSha256'] == previous_hash
old_records = {item['name']: item for item in old_gallery['images']}
old_names = set(old_records)
old_catalogue = {item['code']: item for item in old_payload['buildings']}
old_signatures = {}
open_public_model(PREVIOUS)
fingerprints = RenderFingerprint()
for job in jobs:
 name = job['name']
 if name not in old_names or name in old_signatures:
  continue
 scene = build_scene(job, old_catalogue)
 old_signatures[name] = fingerprints.scene(scene)
 bpy.data.scenes.remove(scene)
(RELEASE / 'previous-scene-fingerprints.json').write_text(json.dumps(old_signatures, indent=2)+'\n')
print('BASELINE_SCENES_VERIFIED', len(old_signatures), flush=True)
open_public_model(MODEL)
payload = json.loads((ROOT / 'web/public/models/catalogue.json').read_text())
model_hash = hashlib.sha256(MODEL.read_bytes()).hexdigest()
assert payload['sourceModelSha256'] == model_hash
catalogue = {item['code']: item for item in payload['buildings']}
fingerprints = RenderFingerprint()
report_path = RELEASE / 'gallery-manifest.json'
reports = json.loads(report_path.read_text()) if report_path.exists() else []
assert all(item['sourceModelSha256'] == model_hash for item in reports), 'Discard only the stale report explicitly before regenerating'
for job in jobs:
 name, code = job['name'], job['code']
 if any(item['name'] == name for item in reports):
  continue
 scene = build_scene(job, catalogue)
 signature = fingerprints.scene(scene)
 previous_image = ROOT / 'result/web/release23/renders' / (name+'.png')
 reused = old_signatures.get(name) == signature and previous_image.exists()
 if reused:
  shutil.copyfile(previous_image, OUT / (name+'.png'))
 else:
  scene.render.filepath = str(OUT / (name+'.png'))
  bpy.ops.render.render(write_still=True)
 reports.append({'name': name, 'code': code, 'sourceModelSha256': model_hash,
                 'renderedFromModelSha256': old_records[name].get('renderedFromModelSha256', previous_hash) if reused else model_hash,
                 'sceneFingerprint': signature, 'reusedEquivalentView': reused})
 report_path.write_text(json.dumps(reports, indent=2)+'\n')
 print('RELEASE_GALLERY', len(reports), name, 'verified-reuse' if reused else 'rendered', flush=True)
 bpy.data.scenes.remove(scene)
print('RELEASE_GALLERY_COMPLETE', flush=True)
