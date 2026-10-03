"""Photo-evidenced India fill correction; run in Blender, without parameters.
Only an owned component is saved. No full campus or shared assets are written.
"""
from pathlib import Path
import array
import hashlib
import json
import subprocess
import bpy
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'result/blender/globe_india_next';OUT.mkdir(parents=True,exist_ok=True)
BASE=max((ROOT/'result/blender').glob('LSE_campus_detailed_v[0-9]*.blend'),key=lambda p:int(p.stem.rsplit('v',1)[1]))
COMPONENT=OUT/'globe-india-component.blend'
SOURCE='SITE_V116_Globe_photographed_Australia_fill'
def clean_previous_owned():
 previous=json.loads((OUT/'audit.json').read_text()) if (OUT/'audit.json').exists() else {}
 owned=bpy.data.objects.get('SITE_NEXT_Globe_India_green')
 if owned:
  mesh=owned.data;bpy.data.objects.remove(owned,do_unlink=True);mesh.use_fake_user=False
  if mesh.users==0:bpy.data.meshes.remove(mesh)
  original=bpy.data.objects[SOURCE]
  state=previous.get('originalVisibility',{}).get(SOURCE,[False,False,False])
  original.hide_render,original.hide_viewport=state[:2];original.hide_set(state[2])
 for material in list(bpy.data.materials):
  if material.name.startswith('SITE_NEXT_') and material.users==int(material.use_fake_user):
   material.use_fake_user=False;bpy.data.materials.remove(material)
 for image in list(bpy.data.images):
  if image.name.startswith('SITE_NEXT_') and image.users==int(image.use_fake_user):
   image.use_fake_user=False;bpy.data.images.remove(image)
bpy.ops.wm.open_mainfile(filepath=str(BASE));clean_previous_owned()
scene=bpy.data.scenes['00_CAMPUS_COMPLETE'];bpy.context.window.scene=scene
for layer in scene.view_layers:layer.update()
def geometry(obj):
 h=hashlib.sha256(str([list(r) for r in obj.matrix_world]).encode())
 if obj.type=='MESH':
  for source,key,typecode,count in [(obj.data.vertices,'co','f',3),(obj.data.loops,'vertex_index','i',1)]:
   values=array.array(typecode,[0])*(len(source)*count);source.foreach_get(key,values);h.update(values.tobytes())
  for uv in obj.data.uv_layers:
   values=array.array('f',[0])*(len(uv.data)*2);uv.data.foreach_get('uv',values);h.update(values.tobytes())
  h.update(str([(p.material_index,p.use_smooth) for p in obj.data.polygons]).encode())
 return h.hexdigest()
def fingerprint(obj):
 digest=hashlib.sha256(str([list(row) for row in obj.matrix_world]).encode())
 if obj.type=='MESH':
  for data,field,kind,count in ((obj.data.vertices,'co','f',3),(obj.data.loops,'vertex_index','i',1),(obj.data.polygons,'material_index','i',1)):
   values=array.array(kind,[0])*(len(data)*count);data.foreach_get(field,values);digest.update(values.tobytes())
  for layer in obj.data.uv_layers:
   values=array.array('f',[0])*(len(layer.data)*2);layer.data.foreach_get('uv',values);digest.update(values.tobytes())
 digest.update(str([m.name if m else None for m in getattr(obj.data,'materials',[])]).encode());return digest.hexdigest()
originals={o.name:fingerprint(o) for o in bpy.data.objects};visibility={o.name:[o.hide_render,o.hide_viewport,o.hide_get()] for o in bpy.data.objects}
original=bpy.data.objects[SOURCE];assert not original.hide_render
old_image=next(n.image for n in original.data.materials[0].node_tree.nodes if n.type=='TEX_IMAGE')
(OUT/'source-packed-map.png').write_bytes(bytes(old_image.packed_file.data))
# GeoJSON is the same public-domain geometry used by prepare_globe_map.py.
prepare='''
from pathlib import Path
import json, hashlib
from PIL import Image,ImageDraw
import numpy as np
root=Path.cwd();out=root/'result/blender/globe_india_next'
source=out/'source-packed-map.png';image=Image.open(source).convert('RGB');w,h=image.size
features=json.loads((root/'data/collections/public-realm-2026/globe/countries.geojson').read_text())['features']
feature=next(f for f in features if f['properties'].get('ADMIN')=='India')
polygons=feature['geometry']['coordinates']
if feature['geometry']['type']=='Polygon':polygons=[polygons]
mask=Image.new('L',image.size);draw=ImageDraw.Draw(mask)
def project(p):return ((p[0]+180)/360*w,(90-p[1])/180*h)
for polygon in polygons:
 draw.polygon([project(p) for p in polygon[0]],fill=255)
 for hole in polygon[1:]:draw.polygon([project(p) for p in hole],fill=0)
before=np.array(image);inside=np.asarray(mask)>0
selected=inside & np.all(before==[218,161,146],axis=2)
after=before.copy();after[selected]=[92,166,124]
assert selected.sum()>1000
assert np.array_equal(before[~selected],after[~selected])
assert np.array_equal(before[~inside],after[~inside])
# Australia is outside this mask; preserve its previous yellow correction.
Image.fromarray(after).save(out/'globe-map-India-green.png',optimize=True)
ys,xs=np.where(selected)
(out/'texture-verification.json').write_text(json.dumps({'country':'India','sourceColor':[218,161,146],'photoEstimatedColor':[92,166,124],'changedPixels':int(selected.sum()),'changedPixelBounds':[int(xs.min()),int(ys.min()),int(xs.max()),int(ys.max())],'outsideCountryUnchanged':True,'nonFillPixelsUnchanged':True,'allUnselectedPixelsUnchanged':True,'AustraliaCorrectionPreserved':True,'imageDimensions':[w,h],'sourceSha256':hashlib.sha256(source.read_bytes()).hexdigest(),'candidateSha256':hashlib.sha256((out/'globe-map-India-green.png').read_bytes()).hexdigest()},indent=2)+'\\n')
'''
subprocess.run(['/opt/anaconda3/envs/MachineLearning/bin/python','-c',prepare],cwd=ROOT,check=True)
candidate=original.copy();candidate.data=original.data.copy();candidate.name='SITE_NEXT_Globe_India_green'
collection=original.users_collection[0];collection.objects.link(candidate)
material=original.data.materials[0].copy();material.name='SITE_NEXT_globe_cartography_India_green'
image=bpy.data.images.load(str(OUT/'globe-map-India-green.png'),check_existing=False);image.name='SITE_NEXT_globe_map_India_green';image.pack()
next(n for n in material.node_tree.nodes if n.type=='TEX_IMAGE').image=image
material['scope']='India fill photo-estimated green; all other map pixels retained'
candidate.data.materials.clear();candidate.data.materials.append(material)
assert geometry(candidate)==geometry(original)
assert all(fingerprint(bpy.data.objects[n])==v for n,v in originals.items())
bpy.data.libraries.write(str(COMPONENT),{candidate},fake_user=True,compress=True)
texture=json.loads((OUT/'texture-verification.json').read_text())
audit={'baselineSha256':hashlib.sha256(BASE.read_bytes()).hexdigest(),'baseline':str(BASE.relative_to(ROOT)),'originalFingerprints':originals,'originalVisibility':visibility,'ownedObjects':[candidate.name],'archivedObjects':[SOURCE],'changes':[{'source':SOURCE,'owned':candidate.name,'collection':collection.name,'retainNewMaterials':True}],'retainNewMaterials':True,'sourceCollection':collection.name,'destinationCollection':collection.name,'ownedMesh':candidate.data.name,'ownedMaterial':material.name,'ownedPackedImage':image.name,'textureVerification':texture,'sourceReferences':['data/collections/public-realm-2026/user-references/reference-05.png'],'photoEvidence':'Readable INDIA label on green upside-down triangular subcontinent; crop in ground_globe_next/user-globe-evidence-crop.png','limitations':['Green hue is photograph-supported; RGB is an estimate rather than calibrated reflectance.','Existing Natural Earth coastlines, original UN-cartography differences, labels and globe heading retained.','No road, public-realm geometry or other country color changes.']}
(OUT/'audit.json').write_text(json.dumps(audit,indent=2)+'\n')
# Reload the baseline and append the saved component to prove isolated delivery.
owned_name=candidate.name;original_geometry=geometry(original)
bpy.ops.wm.open_mainfile(filepath=str(BASE));clean_previous_owned();scene=bpy.data.scenes['00_CAMPUS_COMPLETE'];bpy.context.window.scene=scene
with bpy.data.libraries.load(str(COMPONENT),link=False) as (available,loaded):loaded.objects=[owned_name]
candidate=loaded.objects[0];bpy.data.collections[audit['sourceCollection']].objects.link(candidate)
original=bpy.data.objects[SOURCE];original.hide_render=True;original.hide_set(True)
for layer in scene.view_layers:layer.update()
assert geometry(candidate)==original_geometry
assert all(fingerprint(bpy.data.objects[n])==v for n,v in originals.items())
loaded_image=next(n.image for n in candidate.data.materials[0].node_tree.nodes if n.type=='TEX_IMAGE')
assert hashlib.sha256(bytes(loaded_image.packed_file.data)).hexdigest()==texture['candidateSha256']
# Six radial first intersections establish that the reloaded sphere is present.
center=candidate.matrix_world.translation;deps=scene.view_layers[0].depsgraph;probes=[]
for direction in [Vector(v) for v in [(1,0,0),(-1,0,0),(0,1,0),(0,-1,0),(0,0,1),(0,0,-1)]]:
 hit,location,normal,index,obj,matrix=scene.ray_cast(deps,center+direction*2.08,-direction,distance=.2)
 assert hit and obj.name==candidate.name,(direction,obj.name if obj else None)
 probes.append({'direction':list(direction),'firstHit':obj.name,'surfaceDistance':(location-center).length})
# Camera is registered to the sphere's actual UV coordinates near central India.
uv=candidate.data.uv_layers.active.data;target_uv=Vector(((78+180)/360,(22+90)/180))
loop=min(range(len(candidate.data.loops)),key=lambda i:(uv[i].uv-target_uv).length_squared)
point=candidate.matrix_world @ candidate.data.vertices[candidate.data.loops[loop].vertex_index].co
outward=(point-center).normalized()
for obj in bpy.data.objects:
 if obj.type in {'MESH','FONT','CURVE'} and obj!=candidate:obj.hide_render=True
camera_data=bpy.data.cameras.new('SITE_NEXT_India_preview_camera');camera=bpy.data.objects.new(camera_data.name,camera_data);scene.collection.objects.link(camera)
camera.location=center+outward*9;camera.rotation_euler=(center-camera.location).to_track_quat('-Z','Y').to_euler();camera_data.type='ORTHO';camera_data.ortho_scale=4.5;scene.camera=camera
scene.render.engine='BLENDER_EEVEE';scene.render.resolution_x=700;scene.render.resolution_y=700;scene.render.resolution_percentage=100;scene.render.filepath=str(OUT/'reloaded-India-globe.png');bpy.ops.render.render(write_still=True)
verification={'componentSha256':hashlib.sha256(COMPONENT.read_bytes()).hexdigest(),'savedComponentReopened':True,'originalGeometryPreserved':True,'allOriginalFingerprintsPreserved':True,'originalObjectCount':len(originals),'candidateGeometryMatchesSource':True,'meshUVTransformAndPolygonSlotsPreserved':True,'packedImageMatchesVerifiedPixels':True,'radialFirstHits':probes,'renderCameraTargetUV':list(uv[loop].uv),'renderFile':'reloaded-India-globe.png'}
(OUT/'verification.json').write_text(json.dumps(verification,indent=2)+'\n')
print('INDIA_COMPONENT_VERIFIED',verification['componentSha256'])
bpy.ops.wm.quit_blender()
