"""Make SAW's four omitted curtain walls use the existing building glass shader.
Run in Blender with no parameters. Save only an owned reusable component.
"""
from pathlib import Path
import array,hashlib,json
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'result/blender/saw_glazing_next';OUT.mkdir(parents=True,exist_ok=True)
BASE=max((ROOT/'result/blender').glob('LSE_campus_detailed_v[0-9]*.blend'),key=lambda p:int(p.stem.rsplit('v',1)[1]))
COMPONENT=OUT/'saw-glazing-component.blend'
FAMILIES=['north_fold','central_return','south_fold','glazed_notch_return']
SOURCES=['SAW_D5_curtain82_'+family+'_panes' for family in FAMILIES]
OWNED=['SAW_NEXT_glazing_'+family+'_panes' for family in FAMILIES]
def open_clean():
 bpy.ops.wm.open_mainfile(filepath=str(BASE));bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE']
 previous=json.loads((OUT/'audit.json').read_text()) if (OUT/'audit.json').exists() else {}
 for name,source in zip(OWNED,SOURCES):
  obj=bpy.data.objects.get(name)
  if obj:
   mesh=obj.data;bpy.data.objects.remove(obj,do_unlink=True);mesh.use_fake_user=False
   if mesh.users==0:bpy.data.meshes.remove(mesh)
   state=previous.get('originalVisibility',{}).get(source,[False,False,False])
   original=bpy.data.objects[source];original.hide_render,original.hide_viewport=state[:2];original.hide_set(state[2])
 for material in list(bpy.data.materials):
  if material.name.startswith('SAW_NEXT_') and material.users==int(material.use_fake_user):
   material.use_fake_user=False;bpy.data.materials.remove(material)
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

originals={obj.name:fingerprint(obj) for obj in bpy.data.objects}
visibility={obj.name:[obj.hide_render,obj.hide_viewport,obj.hide_get()] for obj in bpy.data.objects}
collection=bpy.data.collections['SAW_EXTERIOR']
reference_material=bpy.data.objects['SAW_recessed_window_glass'].data.materials[0]
old_material=bpy.data.objects[SOURCES[0]].data.materials[0]
assert old_material.node_tree.nodes['Principled BSDF'].inputs['Transmission Weight'].default_value==0
assert reference_material.node_tree.nodes['Principled BSDF'].inputs['Transmission Weight'].default_value>.75
material=reference_material.copy();material.name='SAW_NEXT_glazing_matched_glass'
# Preserve reflected facade definition in the web alpha approximation.
material['webOpacity']=max(.78,float(reference_material.get('webOpacity',.30)))
owned=[];source_geometry={name:geometry(bpy.data.objects[name]) for name in SOURCES}
for source,name in zip(SOURCES,OWNED):
 original=bpy.data.objects[source];assert not original.hide_render
 obj=original.copy();obj.data=original.data.copy();obj.name=name;collection.objects.link(obj)
 assert len(obj.data.materials)==1
 obj.data.materials[0]=material;assert geometry(obj)==source_geometry[source]
 owned.append(obj)
assert all(fingerprint(bpy.data.objects[n])==v for n,v in originals.items())
bpy.data.libraries.write(str(COMPONENT),set(owned),fake_user=True,compress=True)
changes=[{'source':source,'owned':name,'collection':collection.name,'retainNewMaterials':True} for source,name in zip(SOURCES,OWNED)]
audit={'baseline':str(BASE.relative_to(ROOT)),'baselineSha256':hashlib.sha256(BASE.read_bytes()).hexdigest(),'originalFingerprints':originals,'originalVisibility':visibility,'ownedObjects':OWNED,'archivedObjects':SOURCES,'changes':changes,'destinationCollection':collection.name,'sourceCollection':collection.name,'retainNewMaterials':True,'sourceMaterial':old_material.name,'referenceExistingMaterial':reference_material.name,'ownedMaterial':material.name,'materialProvenance':{'baseColor':list(material.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value),'roughness':float(material.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value),'metallic':float(material.node_tree.nodes['Principled BSDF'].inputs['Metallic'].default_value),'nativeAlpha':float(material.node_tree.nodes['Principled BSDF'].inputs['Alpha'].default_value),'webOpacity':float(material['webOpacity']),'webOpacityBasis':'Conservative 0.78 minimum to avoid distant facade ghosting through the alpha-export approximation; not measured glazing transmittance'},'oldTransmission':0,'newTransmission':float(material.node_tree.nodes['Principled BSDF'].inputs['Transmission Weight'].default_value),'sourceReferences':['data/建筑图片/SAW_Saw Swee Hock Student Centre/01_建筑实拍/architecture_round5_SAW_saw_909_01.jpg','data/建筑图片/SAW_Saw Swee Hock Student Centre/01_建筑实拍/materials_saw_ehsmith_image_04.jpg'],'evidence':'Photographs show reflection and visible interiors behind the timber curtain walls. Four stage82 pane families remained opaque transmission=0 while same-building recessed glass and canopy already used transmission=0.82. Correct the omitted pane shader assignments.','limitations':['Existing same-building glass parameters are reused rather than a measured optical calibration.','Notch sightlines can reach opposite central glazing and north/central sightlines may reach rear masonry about30m away; web opacity constrained to at least0.78 to limit layered facade ghosting.', 'No facade boundary, wooden mullion, canopy, perforated brick or glazing-subdivision geometry changed.','Photographed grouped vertical shading fins are missing from model, but precise registration/proportions need separate frontage calibration; no guessed fins added.']}
(OUT/'audit.json').write_text(json.dumps(audit,indent=2)+'\n')
open_clean()
with bpy.data.libraries.load(str(COMPONENT),link=False) as (available,loaded):loaded.objects=OWNED.copy()
for obj in loaded.objects:collection=bpy.data.collections['SAW_EXTERIOR'];collection.objects.link(obj)
for name in SOURCES:bpy.data.objects[name].hide_render=True;bpy.data.objects[name].hide_set(True)
for layer in bpy.context.scene.view_layers:layer.update()
assert all(fingerprint(bpy.data.objects[n])==v for n,v in originals.items())
for source,name in zip(SOURCES,OWNED):assert geometry(bpy.data.objects[name])==source_geometry[source]
vertices=[];faces=[];names=[]
for obj in collection.all_objects:
 if obj.type!='MESH' or obj.hide_render:continue
 offset=len(vertices);vertices.extend(obj.matrix_world @ v.co for v in obj.data.vertices)
 faces.extend(tuple(offset+i for i in p.vertices) for p in obj.data.polygons);names.extend([obj.name]*len(obj.data.polygons))
tree=BVHTree.FromPolygons(vertices,faces)
facades=json.loads((ROOT/'result/blender/stage82/saw-curtain-audit.json').read_text())['facades']
probes=[]
for family,name in zip(FAMILIES,OWNED):
 record=next(r for r in facades if r['family']==family);normal=Vector(record['n']);obj=bpy.data.objects[name];family_probes=[]
 for polygon in sorted(obj.data.polygons,key=lambda p:p.area,reverse=True):
  point=obj.matrix_world @ polygon.center
  hit=tree.ray_cast(point+normal*.08,-normal,.16)
  if hit[2] is not None and names[hit[2]]==name and all((point-Vector(probe['point'])).length>.05 for probe in family_probes):
   family_probes.append({'point':list(point),'normal':list(normal),'firstHit':names[hit[2]],'distance':hit[3]})
  if len(family_probes)==3:break
 assert len(family_probes)==3,(family,len(family_probes))
 probes.extend(family_probes)
scene=bpy.context.scene
for obj in bpy.data.objects:
 if obj.type in {'MESH','FONT','CURVE'} and not obj.name.startswith('SAW_'):obj.hide_render=True
south=next(r for r in facades if r['family']=='south_fold');p=Vector(south['p']);u=Vector(south['u']);normal=Vector(south['n']);focus=p+u*(south['length']*.7)+Vector((0,0,5.0))
camera_data=bpy.data.cameras.new('SAW_NEXT_glazing_preview_camera');camera=bpy.data.objects.new(camera_data.name,camera_data);scene.collection.objects.link(camera);camera.location=focus+normal*28-u*7+Vector((0,0,8));camera.rotation_euler=(focus-camera.location).to_track_quat('-Z','Y').to_euler();camera_data.type='ORTHO';camera_data.ortho_scale=24;scene.camera=camera
world=bpy.data.worlds.new('SAW_NEXT_glazing_neutral_preview');world.use_nodes=True;world.node_tree.nodes['Background'].inputs['Color'].default_value=(.62,.68,.74,1);world.node_tree.nodes['Background'].inputs['Strength'].default_value=.8;scene.world=world
for obj in bpy.data.objects:
 if obj.type=='LIGHT':obj.hide_render=True
light_data=bpy.data.lights.new('SAW_NEXT_glazing_preview_area','AREA');light_data.energy=2500;light_data.size=18;light=bpy.data.objects.new(light_data.name,light_data);scene.collection.objects.link(light);light.location=focus+normal*18+Vector((0,0,12));light.rotation_euler=(focus-light.location).to_track_quat('-Z','Y').to_euler()
scene.render.engine='CYCLES';scene.cycles.samples=16;scene.cycles.use_denoising=True;scene.render.resolution_x=1000;scene.render.resolution_y=800;scene.render.resolution_percentage=100;scene.render.filepath=str(OUT/'reloaded-SAW-glazing.png');bpy.ops.render.render(write_still=True)
behind=[]
deps=scene.view_layers[0].depsgraph
for probe in probes:
 point=Vector(probe['point']);normal=Vector(probe['normal'])
 hit,location,n,index,obj,matrix=scene.ray_cast(deps,point-normal*.10,-normal,distance=40)
 behind.append({'frontPane':probe['firstHit'],'point':probe['point'],'behindFirstHit':obj.name if hit else None,'distance':(location-point).length if hit else None})
verification={'behindPaneFirstHits':behind,'webOpacity':float(bpy.data.objects[OWNED[0]].data.materials[0]['webOpacity']),'componentSha256':hashlib.sha256(COMPONENT.read_bytes()).hexdigest(),'savedComponentReopened':True,'originalGeometryPreserved':True,'allOriginalFingerprintsPreserved':True,'originalObjectCount':len(originals),'ownedMeshUVTransformIdenticalToSource':True,'newMaterialRetainedOnAllFourPaneFamilies':True,'firstHits':probes,'actualPaneFirstHitCount':len(probes),'render':'reloaded-SAW-glazing.png'}
(OUT/'verification.json').write_text(json.dumps(verification,indent=2)+'\n')
print('SAW_GLAZING_VERIFIED',verification['componentSha256']);bpy.ops.wm.quit_blender()
