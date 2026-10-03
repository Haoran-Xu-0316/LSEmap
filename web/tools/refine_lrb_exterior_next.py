"""Open eight LRB plaza stone bays into photo-supported broad windows.

Run in Blender Text Editor. Preserve all original meshes and create small
replacements. Metric bay widths/rows inherit the earlier GIS/photo registration.
"""
from pathlib import Path
import array, hashlib, json, math, sys
import bpy,bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'result/blender/lrb_exterior_next';OUT.mkdir(parents=True,exist_ok=True)
BASE=ROOT/'result/blender/LSE_campus_detailed_v126.blend'
if not BASE.exists():BASE=max((ROOT/'result/blender').glob('LSE_campus_detailed_v[0-9]*.blend'),key=lambda p:int(p.stem.rsplit('v',1)[1]))
bpy.ops.wm.open_mainfile(filepath=str(BASE));scene=bpy.data.scenes['00_CAMPUS_COMPLETE'];bpy.context.window.scene=scene
previous=json.loads((OUT/'audit.json').read_text()) if (OUT/'audit.json').exists() else None
if previous:
 for name in previous.get('ownedObjects',[]):
  old=bpy.data.objects.get(name)
  if old:bpy.data.objects.remove(old,do_unlink=True)
 for name in previous.get('archivedObjects',[]):
  old=bpy.data.objects.get(name)
  if old:
   states=previous['originalVisibility'][name];old.hide_render,old.hide_viewport=states[:2];old.hide_set(states[2])
for layer in scene.view_layers:layer.update()
def fingerprint(obj):
 h=hashlib.sha256(str([list(row)for row in obj.matrix_world]).encode())
 if obj.type=='MESH':
  for data,field,kind,count in ((obj.data.vertices,'co','f',3),(obj.data.loops,'vertex_index','i',1),(obj.data.polygons,'material_index','i',1)):
   values=array.array(kind,[0])*(len(data)*count);data.foreach_get(field,values);h.update(values.tobytes())
  for layer in obj.data.uv_layers:
   values=array.array('f',[0])*(len(layer.data)*2);layer.data.foreach_get('uv',values);h.update(values.tobytes())
 h.update(str([m.name if m else None for m in getattr(obj.data,'materials',[])]).encode());return h.hexdigest()
originals={o.name:fingerprint(o)for o in bpy.data.objects};visibility={o.name:[o.hide_render,o.hide_viewport,o.hide_get()]for o in bpy.data.objects}
col=bpy.data.collections['LRB_EXTERIOR'];ring=next(b for b in json.loads((ROOT/'result/blender/site_geometry.json').read_text())['buildings'] if b['code']=='LRB')['rings'][0]
origin,end=[Vector((*ring[i],0))for i in [0,13]];axis=(end-origin).normalized();normal=Vector((axis.y,-axis.x,0));length=(end-origin).length;pitch=length/12;angle=math.atan2(axis.y,axis.x)
def point(x,z,d):return origin+axis*x+normal*d+Vector((0,0,z))
def local(world):v=world-origin;return v.dot(axis),world.z,v.dot(normal)
old_knots=[0,4.35,5.5,8.8,13.15,14.2,17.5,18.55,21.85,23.0];new_knots=[0,4.35,5.66,8.81,12.43,13.72,16.58,17.59,19.55,20.24]
def remap(z):
 for a,b,c,d in zip(old_knots,old_knots[1:],new_knots,new_knots[1:]):
  if z<=b:return c+(z-a)*(d-c)/(b-a)
 return new_knots[-1]+z-old_knots[-1]
windows=[]
for bay in range(2):
 for bottom,top in [(5.5,8.8),(9.85,13.15),(14.2,17.5),(18.55,21.85)]:windows.append([bay*pitch+pitch*.115,remap(bottom),bay*pitch+pitch*.885,remap(top)])
assert len(windows)==8
sources=['stone_piers','glazing','window_frames','window_mullions','window_transoms','sills'];copies=[];archives=[];removed={}
# Remove only the old skinny openings and two solid stone bridge boxes inside
# each selected upper bay. Ground storefront/entry, outer piers and brick bays stay.
for suffix in sources:
 source=bpy.data.objects['LRB_V109_facade_V35_'+suffix];copy=source.copy();copy.data=source.data.copy();copy.name='LRB_NEXT_retained_'+suffix;copy.data.name=copy.name
 for owner in source.users_collection:owner.objects.link(copy)
 mesh=bmesh.new();mesh.from_mesh(copy.data);delete=[]
 for face in mesh.faces:
  coords=[local(copy.matrix_world@v.co)for v in face.verts]
  if suffix=='sills':selected=any(all(a-.08<=x<=c+.08 and b-.18<=z<=b-.01 and -.31<=d<=.5 for x,z,d in coords)for a,b,c,t in windows)
  else:selected=any(all(a-.001<=x<=c+.001 and b-.001<=z<=t+.001 and -.31<=d<=.5 for x,z,d in coords)for a,b,c,t in windows)
  if selected:delete.append(face)
 assert delete,suffix
 removed[source.name]=len(delete);bmesh.ops.delete(mesh,geom=delete,context='FACES');orphan=[v for v in mesh.verts if not v.link_faces]
 if orphan:bmesh.ops.delete(mesh,geom=orphan,context='VERTS')
 mesh.to_mesh(copy.data);mesh.free();copy.data.update();copy.hide_render=False;copy.hide_set(False);source.hide_render=True;source.hide_set(True);copies.append(copy);archives.append(source.name)
sys.path.insert(0,str(Path(__file__).resolve().parent));from facade_geometry import Geometry,materials
materials.clear()
for key,suffix in [('glass','glazing'),('frame','window_frames'),('stone','sills')]:
 source=bpy.data.objects['LRB_V109_facade_V35_'+suffix];mat=source.data.materials[0].copy();mat.name='LRB_NEXT_broad_window_'+key;materials[key]=mat
batches={key:Geometry('LRB','broad_window_'+key,key)for key in materials}
def box(key,x,z,d,w,h,t):batches[key].box(point(x,z,d),(w,t,h),angle)
for a,b,c,d in windows:
 width,height=c-a,d-b;box('glass',(a+c)/2,(b+d)/2,.13,width,height,.06)
 for x in [a+.04,c-.04]:box('frame',x,(b+d)/2,.23,.08,height,.12)
 for z in [b+.04,d-.04]:box('frame',(a+c)/2,z,.23,width,.08,.12)
 # Keep six glass columns and three horizontal tiers inherited from the three
 # old two-column slots. The photographic pane count remains an estimate;
 # this change corrects the solid subdivision, not a claim of a surveyed sash.
 for k in range(1,6):box('frame',a+width*k/6,(b+d)/2,.235,.055,height,.13)
 for k in [1,2]:box('frame',(a+c)/2,b+height*k/3,.235,width,.055,.13)
 box('stone',(a+c)/2,b-.09,.26,width+.15,.13,.32)
for key,batch in batches.items():
 obj=batch.finish();obj.name='LRB_NEXT_broad_window_'+key;obj.data.name=obj.name;obj.modifiers.clear()
 for owner in list(obj.users_collection):owner.objects.unlink(obj)
 col.objects.link(obj);copies.append(obj)
for layer in scene.view_layers:layer.update()
def trees():
 result=[]
 for obj in col.all_objects:
  if obj.type=='MESH' and not obj.hide_render and len(obj.data.polygons):result.append((obj.name,BVHTree.FromPolygons([obj.matrix_world@v.co for v in obj.data.vertices],[tuple(f.vertices)for f in obj.data.polygons],all_triangles=False)))
 return result

def probes():
 geometry=trees();result=[]
 for a,b,c,d in windows:
  # Interior samples in each old stone-bridge strip test that the actual first
  # surface is glass. Samples stay off new slender sixth-pitch mullions.
  samples=[(f,h)for f in [.245/.77,.525/.77]for h in [.18,.51,.82]]+[(.04,.51),(.96,.51)]
  for fraction,height_fraction in samples:
   x=a+(c-a)*fraction;z=b+(d-b)*height_fraction;start=point(x,z,.75);best=None
   for name,tree in geometry:
    hit=tree.ray_cast(start,-normal,2)
    if hit[0] is not None and (best is None or hit[3]<best[0]):best=(hit[3],name)
   assert best and best[1]=='LRB_NEXT_broad_window_glass',(a,b,fraction,best)
   result.append({'point':list(start),'firstSurface':best[1]})
 return result
before_probes=probes();assert all(fingerprint(bpy.data.objects[name])==value for name,value in originals.items())
component=OUT/'lrb-exterior-component.blend';bpy.data.libraries.write(str(component),set(copies),fake_user=True)
reference=ROOT/'data/previews/property_handbook_p30.png';photo=ROOT/'data/建筑图片/LRB_Lionel Robbins Building_Library/01_建筑实拍/exteriors_lse_estate_016.jpg'
audit={'baseline':str(BASE.relative_to(ROOT)),'baselineSha256':hashlib.sha256(BASE.read_bytes()).hexdigest(),'ownedObjects':[o.name for o in copies],'archivedObjects':archives,'originalFingerprints':originals,'originalVisibility':visibility,'originalGeometryPreserved':True,'removedFaces':removed,'windowCount':8,'windows':windows,'reference':{'file':str(reference.relative_to(ROOT)),'sha256':hashlib.sha256(reference.read_bytes()).hexdigest(),'publication':'LSE Property Handbook 2025/26, printed page28 / PDF page30','url':'https://info.lse.ac.uk/staff/divisions/estates-division/Assets/Documents/Property-and-Space/LSE-Property-Handbook.pdf'},'crossReference':{'file':str(photo.relative_to(ROOT)),'sha256':hashlib.sha256(photo.read_bytes()).hexdigest(),'url':'https://info.lse.ac.uk/staff/divisions/estates-division/lse-estate/LSE-Estate'},'scope':'Join each of eight upper stone-bay windows into a broad opening with metal sash divisions; ground entry and brick bays retained.','limitations':['Photograph capture dates unknown; 2025/26 publication is not a 2026 site survey.','Two-bay registration, aperture width, .055m mullions, six columns and three tiers remain photo/GIS estimates.','Previously measured roof and Carey/Portugal facades unchanged; hidden elevations, complete interiors and ground entrance unresolved.'],'wholeFacadeProbes':before_probes}
(OUT/'audit.json').write_text(json.dumps(audit,indent=2)+'\n')
bpy.ops.wm.open_mainfile(filepath=str(BASE));scene=bpy.data.scenes['00_CAMPUS_COMPLETE'];bpy.context.window.scene=scene;col=bpy.data.collections['LRB_EXTERIOR']
with bpy.data.libraries.load(str(component),link=False)as(src,dst):dst.objects=src.objects
for obj in dst.objects:col.objects.link(obj)
for name in archives:bpy.data.objects[name].hide_render=True;bpy.data.objects[name].hide_set(True)
for layer in scene.view_layers:layer.update()
after_probes=probes();assert before_probes==after_probes;assert all(fingerprint(bpy.data.objects[name])==value for name,value in originals.items())
names={o.name for o in col.all_objects}
for obj in scene.objects:
 if obj.type=='MESH' and obj.name not in names:obj.hide_render=True
focus=point(pitch,12.0,0);cd=bpy.data.cameras.new('LRB_NEXT_WINDOW_REVIEW');cam=bpy.data.objects.new(cd.name,cd);scene.collection.objects.link(cam);cam.location=focus+normal*18+axis*.3+Vector((0,0,1));cam.rotation_euler=(focus-cam.location).to_track_quat('-Z','Y').to_euler();cd.type='ORTHO';cd.ortho_scale=21.2;scene.camera=cam;scene.render.engine='BLENDER_EEVEE';scene.render.resolution_x=1300;scene.render.resolution_y=1400;scene.render.resolution_percentage=100;scene.render.filepath=str(OUT/'reloaded-stone-window-bays.png');bpy.ops.render.render(write_still=True)
verification={'componentSha256':hashlib.sha256(component.read_bytes()).hexdigest(),'savedComponentReopened':True,'originalObjectCount':len(originals),'originalGeometryPreserved':True,'fullModelSaved':False,'windowCount':8,'wholeFacadeProbeCount':len(after_probes),'wholeFacadeFirstSurfaceChecks':after_probes,'nativeRender':'result/blender/lrb_exterior_next/reloaded-stone-window-bays.png'}
(OUT/'verification.json').write_text(json.dumps(verification,indent=2)+'\n');print('LRB_BROAD_WINDOWS_RELOADED',len(originals),len(after_probes),flush=True);bpy.ops.wm.quit_blender()
