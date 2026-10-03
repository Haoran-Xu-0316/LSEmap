"""Give SAL's registered recessed alley middle its photograph-supported pale sash.
Run inside Blender. No full campus file is saved. Dimensions remain estimates.
"""
from pathlib import Path
import array,hashlib,json,math
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'result/blender/sal_middle_next';OUT.mkdir(parents=True,exist_ok=True)
BASE=ROOT/'result/blender/LSE_campus_detailed_v129.blend'
if not BASE.exists():BASE=max((ROOT/'result/blender').glob('LSE_campus_detailed_v[0-9]*.blend'),key=lambda p:int(p.stem.rsplit('v',1)[1]))
a=math.radians(24.35);right=Vector((-math.cos(a),-math.sin(a),0));outward=Vector((-math.sin(a),math.cos(a),0))
def local(v):return v.dot(right),v.dot(outward),v.z
def fingerprint(o):
 h=hashlib.sha256(str([list(row)for row in o.matrix_world]).encode())
 if o.type=='MESH':
  for data,field,kind,count in ((o.data.vertices,'co','f',3),(o.data.loops,'vertex_index','i',1),(o.data.polygons,'material_index','i',1)):
   values=array.array(kind,[0])*(len(data)*count);data.foreach_get(field,values);h.update(values.tobytes())
  for layer in o.data.uv_layers:
   values=array.array('f',[0])*(len(layer.data)*2);layer.data.foreach_get('uv',values);h.update(values.tobytes())
 h.update(str([m.name if m else None for m in getattr(o.data,'materials',[])]).encode());return h.hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(BASE));scene=bpy.data.scenes['00_CAMPUS_COMPLETE'];bpy.context.window.scene=scene;col=bpy.data.collections['SAL_EXTERIOR']
previous=json.loads((OUT/'audit.json').read_text())if (OUT/'audit.json').exists()else None
def restore_component_baseline():
 if previous:
  for name in previous.get('ownedObjects',[]):
   old=bpy.data.objects.get(name)
   if old:bpy.data.objects.remove(old,do_unlink=True)
  for name in previous.get('archivedObjects',[]):
   old=bpy.data.objects.get(name)
   if old:
    state=previous['originalVisibility'][name];old.hide_render,old.hide_viewport=state[:2];old.hide_set(state[2])
 for mat in list(bpy.data.materials):
  if mat.name.startswith(('SAL_NEXT_middle_',)) and mat.users==int(mat.use_fake_user):
   mat.use_fake_user=False;bpy.data.materials.remove(mat)
restore_component_baseline()
originals={o.name:fingerprint(o)for o in bpy.data.objects};visibility={o.name:[o.hide_render,o.hide_viewport,o.hide_get()]for o in bpy.data.objects}
ring=next(b for b in json.loads((ROOT/'result/blender/site_geometry.json').read_text())['buildings']if b.get('code')=='SAL')['rings'][0]
registration=[]
for i in [0,2,4]:
 p,q=[Vector((*ring[k],0))for k in [i,i+1]];length=(q-p).length
 registration.append({'edge':i,'start':local(p),'end':local(q),'length':length,'builderBayCount':max(1,round(length/3.65))})
# Recolor the registered recessed middle upper sash only. Retain ground,
# near charcoal, opposite side and principal blue frontage.
copies=[];archives=[];selected_counts={};probe_points=[]
near_material=next(m.name for m in bpy.data.objects['SAL_FRAME_NEXT_sash_frames'].data.materials if 'near_wing_charcoal' in m.name)
mat=bpy.data.materials['SAL_V70_blue_painted_sash'].copy();mat.name='SAL_NEXT_middle_pale_sash';mat.diffuse_color=(.47,.43,.35,1)
if mat.use_nodes:mat.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(.47,.43,.35,1)
for suffix in ['frames','bars']:
 old=bpy.data.objects['SAL_FRAME_NEXT_sash_'+suffix];new=old.copy();new.data=old.data.copy();new.name='SAL_NEXT_middle_sash_'+suffix;new.data.name=new.name;col.objects.link(new);new.data.materials.append(mat)
 for modifier in list(new.modifiers):
  if modifier.type=='BEVEL':new.modifiers.remove(modifier)
 selected=[]
 for face in new.data.polygons:
  coords=[local(new.matrix_world@new.data.vertices[k].co)for k in face.vertices]
  if all(-135.61<x<-135.30 and 29.42<d<55.09 and 5.55<z<17.54 for x,d,z in coords):
   face.material_index=len(new.data.materials)-1;selected.append(face.index)
   if suffix=='frames':
    mid=sum((new.matrix_world@new.data.vertices[k].co for k in face.vertices),Vector())/len(face.vertices)
    if face.normal.length and len(probe_points)<20:probe_points.append(list(mid))
 assert selected,suffix
 selected_counts[old.name]=len(selected);old.hide_render=True;old.hide_set(True);copies.append(new);archives.append(old.name)
# Whole-visible-exterior first hits verify all middle jambs and retained charcoal.
def probes():
 trees=[(o,BVHTree.FromPolygons([o.matrix_world@v.co for v in o.data.vertices],[tuple(f.vertices)for f in o.data.polygons],all_triangles=False))for o in col.all_objects if o.type=='MESH' and not o.hide_render and len(o.data.polygons)]
 records=[]
 for edge,bays,expected in [(2,7,'SAL_NEXT_middle_pale_sash'),(0,2,near_material)]:
  p,q=[Vector((*ring[k],0))for k in [edge,edge+1]];axis=(q-p).normalized();normal=Vector((axis.y,-axis.x,0))
  if normal.dot(right)<0:normal=-normal
  length=(q-p).length
  for bay in range(bays):
   for z in [7.3,11.65,15.85]:
    for dx in [-1.055,1.055]:
     start=p+axis*(length*(bay+.5)/bays+dx)+Vector((0,0,z))+normal*.8;best=None
     for o,tree in trees:
      hit=tree.ray_cast(start,-normal,2)
      if hit[0] is not None and (best is None or hit[3]<best[0]):best=(hit[3],o,hit[2])
     assert best and best[1].name=='SAL_NEXT_middle_sash_frames',(edge,bay,z,dx,best and best[1].name)
     material=best[1].data.materials[best[1].data.polygons[best[2]].material_index].name
     assert material==expected,(edge,bay,material)
     records.append({'edge':edge,'bay':bay,'point':list(start),'firstSurface':best[1].name,'material':material})
 return records
for layer in scene.view_layers:layer.update()
checks=probes();assert all(fingerprint(bpy.data.objects[n])==v for n,v in originals.items())
component=OUT/'sal-middle-component.blend';bpy.data.libraries.write(str(component),set(copies),fake_user=True)
photo=ROOT/'data/collections/library_round5/photos/SAL_5b39324ea103.jpg'
audit={'baseline':str(BASE.relative_to(ROOT)),'baselineSha256':hashlib.sha256(BASE.read_bytes()).hexdigest(),'originalFingerprints':originals,'originalVisibility':visibility,'ownedObjects':[o.name for o in copies],'archivedObjects':archives,'registration':registration,'selectedFaceCounts':selected_counts,'reference':{'path':str(photo.relative_to(ROOT)),'sha256':hashlib.sha256(photo.read_bytes()).hexdigest(),'captureDate':'unknown'},'scope':'Pale recessed-middle sash: seven bays, three upper rows;21 windows. Near charcoal6 windows preserved.','registrationReason':'Entrance pavilion anchors front at depth61; GIS short/middle/front edge sequence has 2/7/2 bays and middle wall inset0.46m, matching the photographed near-dark/recessed-pale/far-corner progression.','limitations':['Block correspondence is GIS/photo estimation, not measured elevation.','Photograph supports repeated pale sash across the recessed block; seven model bays are inherited GIS estimates, not independently counted from the perspective crop.','Ground doors, principal blue frontage and opposite alley unchanged; no new roof/top-storey geometry inferred.','Pale frame color is a visual estimate; existing glass, geometry and near charcoal unchanged.'],'firstSurfaceChecks':checks}
(OUT/'audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n')
bpy.ops.wm.open_mainfile(filepath=str(BASE));scene=bpy.data.scenes['00_CAMPUS_COMPLETE'];bpy.context.window.scene=scene;col=bpy.data.collections['SAL_EXTERIOR']
restore_component_baseline()
with bpy.data.libraries.load(str(component),link=False)as(src,dst):dst.objects=src.objects
for o in dst.objects:
 col.objects.link(o)
 for slot in o.material_slots:
  material=slot.material
  if material and '.' in material.name and material.name.rsplit('.',1)[1].isdigit():
   canonical=bpy.data.materials.get(material.name.rsplit('.',1)[0])
   if canonical:slot.material=canonical
for name in archives:bpy.data.objects[name].hide_render=True;bpy.data.objects[name].hide_set(True)
for layer in scene.view_layers:layer.update()
reloaded=probes();assert reloaded==checks;assert all(fingerprint(bpy.data.objects[n])==v for n,v in originals.items())
visible={o.name for o in col.all_objects}
for o in scene.objects:
 if o.type=='MESH' and o.name not in visible:o.hide_render=True
focus=right*-135+outward*42+Vector((0,0,11));cd=bpy.data.cameras.new('SAL_MIDDLE_NEXT_REVIEW');cam=bpy.data.objects.new(cd.name,cd);scene.collection.objects.link(cam);cam.location=focus+right*50-outward*8+Vector((0,0,2));cam.rotation_euler=(focus-cam.location).to_track_quat('-Z','Y').to_euler();cd.type='ORTHO';cd.ortho_scale=35;scene.camera=cam;scene.render.engine='BLENDER_EEVEE';scene.render.resolution_x=1100;scene.render.resolution_y=900;scene.render.resolution_percentage=100;scene.render.filepath=str(OUT/'reloaded-middle-sash.png');bpy.ops.render.render(write_still=True)
proof={'componentSha256':hashlib.sha256(component.read_bytes()).hexdigest(),'savedComponentReopened':True,'originalGeometryPreserved':True,'originalObjectCount':len(originals),'fullModelSaved':False,'firstSurfaceChecks':reloaded,'windowCount':21,'retainedCharcoalWindowCount':6,'bevelRemovedFromCopies':True}
(OUT/'verification.json').write_text(json.dumps(proof,indent=2)+'\n');print('SAL_MIDDLE_NEXT_RELOADED',len(originals),len(reloaded));bpy.ops.wm.quit_blender()
