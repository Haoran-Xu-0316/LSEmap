"""Complete the photo-confirmed Columbia school-name inscription.
Run in Blender, no parameters. Preserve native lettering height and font.
"""
from pathlib import Path
import array,hashlib,json
import bpy
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'result/blender/columbia_lettering_next';OUT.mkdir(parents=True,exist_ok=True)
BASE=max((ROOT/'result/blender').glob('LSE_campus_detailed_v[0-9]*.blend'),key=lambda p:int(p.stem.rsplit('v',1)[1]))
COMPONENT=OUT/'columbia-lettering-component.blend'
SOURCE='COL_D4_school_name';OWNED='COL_NEXT_complete_school_name'
FULL_NAME='The London School of Economics and Political Science'
def open_clean():
 bpy.ops.wm.open_mainfile(filepath=str(BASE));bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE']
 previous=json.loads((OUT/'audit.json').read_text()) if (OUT/'audit.json').exists() else {}
 obj=bpy.data.objects.get(OWNED)
 if obj:
  curve=obj.data;bpy.data.objects.remove(obj,do_unlink=True)
  if curve.users==0:bpy.data.curves.remove(curve)
  state=previous.get('originalVisibility',{}).get(SOURCE,[False,False,False]);original=bpy.data.objects[SOURCE]
  original.hide_render,original.hide_viewport=state[:2];original.hide_set(state[2])
 for layer in bpy.context.scene.view_layers:layer.update()
open_clean()
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

def curve_signature(obj):
 curve=obj.data
 return {'body':curve.body,'size':curve.size,'font':curve.font.name,'extrude':curve.extrude,'alignX':curve.align_x,'alignY':curve.align_y,'spaceCharacter':curve.space_character,'spaceWord':curve.space_word,'shear':curve.shear,'matrix':[list(row) for row in obj.matrix_world],'materials':[m.name for m in curve.materials]}
original=bpy.data.objects[SOURCE];assert original.type=='FONT' and not original.hide_render
assert original.data.body=='The London School of Economics', 'Already complete or a different source; proposal needs re-review'
originals={obj.name:fingerprint(obj) for obj in bpy.data.objects};visibility={obj.name:[obj.hide_render,obj.hide_viewport,obj.hide_get()] for obj in bpy.data.objects};original_curve=curve_signature(original)
ring=next(b for b in json.loads((ROOT/'result/blender/site_geometry.json').read_text())['buildings'] if b['code']=='COL')['rings'][0]
p=Vector((*ring[10],0));q=Vector((*ring[11],0));u=(q-p).normalized();length=(q-p).length
signed=sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(ring,ring[1:]+ring[:1]));n=Vector((u.y,-u.x,0))*(1 if signed>0 else -1)
assert original.matrix_world.to_3x3().col[0].normalized().dot(-u)>.999
entry=length*1.5/4
# The photographed final words end slightly viewer-left of the portal centre.
# Keep the existing glyph size: align the actual right endpoint instead of
# horizontally squeezing the full school name into the old short sentence.
anchor=entry+.20
owned=original.copy();owned.data=original.data.copy();owned.name=OWNED
collection=original.users_collection[0];collection.objects.link(owned)
owned.data.body=FULL_NAME;owned.data.align_x='RIGHT'
depth=(original.location-p).dot(n);height=original.location.z
owned.location=p+u*anchor+n*depth+Vector((0,0,height));bpy.context.view_layer.update()
points=[owned.matrix_world @ Vector(c) for c in owned.bound_box]
letter_bounds=[min((v-p).dot(u) for v in points),max((v-p).dot(u) for v in points)]
assert .35<letter_bounds[0]<letter_bounds[1]<length-.35, (letter_bounds,length)
assert owned.data.size==original.data.size and owned.data.font==original.data.font
assert owned.data.space_character==original.data.space_character and owned.data.space_word==original.data.space_word
assert all(fingerprint(bpy.data.objects[name])==value for name,value in originals.items())
assert curve_signature(original)==original_curve
bpy.data.libraries.write(str(COMPONENT),{owned},fake_user=True,compress=True)
audit={'baseline':str(BASE.relative_to(ROOT)),'baselineSha256':hashlib.sha256(BASE.read_bytes()).hexdigest(),'originalFingerprints':originals,'originalVisibility':visibility,'originalCurveSignature':original_curve,'ownedObjects':[OWNED],'archivedObjects':[SOURCE],'changes':[{'source':SOURCE,'owned':OWNED,'collection':collection.name}],'destinationCollection':collection.name,'sourceCollection':collection.name,'fullName':FULL_NAME,'lettering':{'originalHeight':original.data.size,'ownedHeight':owned.data.size,'font':original.data.font.name,'extrude':original.data.extrude,'materialNames':[m.name for m in original.data.materials],'oldTextWidth':original.dimensions.x,'actualFullPhraseFrontageWidth':letter_bounds[1]-letter_bounds[0],'frontageBounds':letter_bounds,'availableFrontageLength':length,'portalCentreFrontage':entry,'photographedRightEndAnchor':anchor,'wallDepth':depth,'height':height,'horizontalScalingApplied':False},'sourceReferences':[{'local':'data/建筑图片/COL_Columbia House/01_建筑实拍/small_round5_COL_handbook-000.png','url':'https://info.lse.ac.uk/staff/divisions/estates-division/Assets/Documents/Property-and-Space/LSE-Property-Handbook.pdf','date':'2025/26 publication; photograph capture unknown','supports':'Visible final words Political Science on same stone entablature; endpoint slightly viewer-left of portal centre'}],'limitations':['Full school-name text is verified; endpoint offset0.20m is a photo-based registration estimate, not survey.','Existing font, glyph size, vertical location, wall depth, material and extrusion retained; spacing and horizontal scale unchanged.','Whole Columbia facade and interiors remain unresolved as recorded in columbia_facade_next/audit.json.']}
(OUT/'audit.json').write_text(json.dumps(audit,indent=2)+'\n')
open_clean()
with bpy.data.libraries.load(str(COMPONENT),link=False) as (available,loaded):loaded.objects=[OWNED]
owned=loaded.objects[0];bpy.data.collections[audit['sourceCollection']].objects.link(owned)
original=bpy.data.objects[SOURCE];original.hide_render=True;original.hide_set(True)
for layer in bpy.context.scene.view_layers:layer.update()
assert curve_signature(original)==original_curve
assert all(fingerprint(bpy.data.objects[name])==value for name,value in originals.items())
assert owned.data.body==FULL_NAME and owned.data.size==original_curve['size']
actual=[owned.matrix_world@Vector(c) for c in owned.bound_box];bounds=[min((v-p).dot(u) for v in actual),max((v-p).dot(u) for v in actual)]
assert max(abs(a-b) for a,b in zip(bounds,letter_bounds))<1e-5
scene=bpy.context.scene
for obj in bpy.data.objects:
 if obj.type in {'MESH','FONT','CURVE'} and not obj.name.startswith('COL_'):obj.hide_render=True
focus=sum(actual,Vector())/len(actual)
camera_data=bpy.data.cameras.new('COL_NEXT_lettering_camera');camera=bpy.data.objects.new(camera_data.name,camera_data);scene.collection.objects.link(camera);camera.location=focus+n*16+Vector((0,0,.8));camera.rotation_euler=(focus-camera.location).to_track_quat('-Z','Y').to_euler();camera_data.type='ORTHO';camera_data.ortho_scale=(bounds[1]-bounds[0])+1.4;scene.camera=camera
world=bpy.data.worlds.new('COL_NEXT_lettering_world');world.use_nodes=True;world.node_tree.nodes['Background'].inputs['Color'].default_value=(.65,.65,.65,1);world.node_tree.nodes['Background'].inputs['Strength'].default_value=.8;scene.world=world
for obj in bpy.data.objects:
 if obj.type=='LIGHT':obj.hide_render=True
light_data=bpy.data.lights.new('COL_NEXT_lettering_area','AREA');light_data.energy=900;light_data.size=10;light=bpy.data.objects.new(light_data.name,light_data);scene.collection.objects.link(light);light.location=focus+n*8+Vector((0,0,6));light.rotation_euler=(focus-light.location).to_track_quat('-Z','Y').to_euler()
scene.render.engine='BLENDER_EEVEE';scene.render.resolution_x=1600;scene.render.resolution_y=650;scene.render.resolution_percentage=100;scene.render.filepath=str(OUT/'reloaded-complete-lettering.png');bpy.ops.render.render(write_still=True)
verification={'componentSha256':hashlib.sha256(COMPONENT.read_bytes()).hexdigest(),'savedComponentReopened':True,'originalGeometryPreserved':True,'originalCurvePreserved':True,'allOriginalFingerprintsPreserved':True,'originalObjectCount':len(originals),'fullTextReopened':owned.data.body,'glyphSizeRetained':True,'fontRetained':True,'horizontalScalingApplied':False,'reopenedFrontageBounds':bounds,'frontageMarginLeft':bounds[0],'frontageMarginRight':length-bounds[1],'nativeRender':'reloaded-complete-lettering.png','renderCount':1}
(OUT/'verification.json').write_text(json.dumps(verification,indent=2)+'\n');print('COL_LETTERING_VERIFIED',verification['componentSha256']);bpy.ops.wm.quit_blender()
