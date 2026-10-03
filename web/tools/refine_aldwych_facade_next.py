"""Reconstruct the photographed 61A central street portal, without changing its footprint.

Run in Blender's Text Editor. Only independent component libraries are saved.
The undimensioned2021 letting brochure supports the composition; all metric sizes remain estimates.
"""
from pathlib import Path
import array, hashlib, json, sys, math
import bpy, bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'result/blender/aldwych_facade_next';OUT.mkdir(parents=True,exist_ok=True)
BASE=ROOT/'result/blender/LSE_campus_detailed_v136.blend'
if not BASE.exists():BASE=max((ROOT/'result/blender').glob('LSE_campus_detailed_v[0-9]*.blend'),key=lambda p:int(p.stem.rsplit('v',1)[1]))
sys.path.insert(0,str(Path(__file__).resolve().parent))
from facade_geometry import Geometry, materials

def open_baseline():
 bpy.ops.wm.open_mainfile(filepath=str(BASE));bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE']
 previous=json.loads((OUT/'audit.json').read_text()) if (OUT/'audit.json').exists() else None
 if previous:
  for name in previous.get('ownedObjects',[]):
   obj=bpy.data.objects.get(name)
   if obj:
    mesh=obj.data;bpy.data.objects.remove(obj,do_unlink=True);mesh.use_fake_user=False
    if not mesh.users:bpy.data.meshes.remove(mesh)
  for name in previous.get('archivedObjects',[]):
   obj=bpy.data.objects[name];state=previous['originalVisibility'][name];obj.hide_render,obj.hide_viewport=state[:2];obj.hide_set(state[2])
 for scene in bpy.data.scenes:
  for layer in scene.view_layers:layer.update()

def fingerprint(obj):
 h=hashlib.sha256(str([list(row)for row in obj.matrix_world]).encode())
 if obj.type=='MESH':
  for data,field,kind,width in ((obj.data.vertices,'co','f',3),(obj.data.loops,'vertex_index','i',1),(obj.data.polygons,'material_index','i',1)):
   values=array.array(kind,[0])*(len(data)*width);data.foreach_get(field,values);h.update(values.tobytes())
  for layer in obj.data.uv_layers:
   values=array.array('f',[0])*(len(layer.data)*2);layer.data.foreach_get('uv',values);h.update(values.tobytes())
 h.update(str([m.name if m else None for m in getattr(obj.data,'materials',[])]).encode());return h.hexdigest()
open_baseline();originals={o.name:fingerprint(o)for o in bpy.data.objects};visibility={o.name:[o.hide_render,o.hide_viewport,o.hide_get()]for o in bpy.data.objects};col=bpy.data.collections['61A_EXTERIOR']
centre=Vector((-40.83289811692653,-129.2928742324073,0));axis=Vector((.918904,-.394482,0)).normalized();normal=Vector((axis.y,-axis.x,0));width=6.769

def local(p):
 q=p-centre;return Vector((q.dot(axis),q.dot(normal),p.z))
def world(x,z,d=0):return centre+axis*x+normal*d+Vector((0,0,z))
owned=[];archives=[];removed={}
keys=['window_piers_stone','sill_wall_stone','head_wall_stone','glazing_glass','window_jamb_bronze','window_transom_bronze','window_mullion_bronze','projecting_sill_trim','giant_pilaster_trim','V16_glazing_seal','V16_reveal_bead','V16_metal_sill_channel','V16_sill_drain_slot','V17_folded_jamb_return','V17_cap_shadow_joint','V17_head_flashing','V17_flashing_downstand','V17_sill_front_fascia','V17_sill_expansion_joint','belt64_clipped_stone_joint_shadow']
for key in keys:
 source=bpy.data.objects['61A_D5_'+key];assert not source.hide_render,source.name
 bm=bmesh.new();bm.from_mesh(source.data);bm.verts.ensure_lookup_table();seen=set();delete=[];count=0
 for v in list(bm.verts):
  if v in seen:continue
  stack=[v];seen.add(v);part=[]
  while stack:
   q=stack.pop();part.append(q)
   for edge in q.link_edges:
    other=edge.other_vert(q)
    if other not in seen:seen.add(other);stack.append(other)
  pts=[local(source.matrix_world@q.co)for q in part];c=sum(pts,Vector())/len(pts)
  # The corner face only. Adjacent angled wings do not share this local plane.
  if -3.41<c.x<3.41 and -.6<c.y<.72 and 4.19<c.z<25.81 and min(p.z for p in pts)>4.15 and max(p.z for p in pts)<25.86:
   delete.extend(part);count+=1
 if delete:
  copy=source.copy();copy.data=source.data.copy();copy.name='61A_NEXT_retained_'+key;copy.data.name=copy.name;col.objects.link(copy)
  bmesh.ops.delete(bm,geom=delete,context='VERTS');bm.to_mesh(copy.data);copy.data.update()
  for mod in list(copy.modifiers):
   if mod.type=='BEVEL':copy.modifiers.remove(mod)
  owned.append(copy);archives.append(source.name);removed[source.name]=count;source.hide_render=True;source.hide_set(True)
 bm.free()
assert removed['61A_D5_glazing_glass']==12,removed
materials.clear()
for k in ['stone','trim','glass','bronze','metal']:materials[k]=bpy.data.materials['61A_'+k]
materials['spandrel']=bpy.data.materials['61A_V64_spandrel'];groups={}
def box(name,material,x,lo,hi,w,d=.46,offset=-.15):
 key=name+'_'+material
 if key not in groups:groups[key]=Geometry('61A','NEXT_'+key,material)
 groups[key].box(world(x,(lo+hi)/2,offset),(w,d,hi-lo),math.atan2(axis.y,axis.x))
windows=[]
def plain_row(lo,hi,glow,ghigh,openings):
 cursor=-width/2
 for x,w,panes in openings:
  a,b=x-w/2,x+w/2
  if a>cursor:box('corner_masonry','stone',(cursor+a)/2,lo,hi,a-cursor)
  box('corner_masonry','stone',x,lo,glow,w);box('corner_masonry','stone',x,ghigh,hi,w)
  box('corner_glass','glass',x,glow,ghigh,w,.045,-.27)
  for xx in [a,b]:box('corner_joinery','bronze',xx,glow,ghigh,.065,.12,-.12)
  for z in [glow,ghigh]:box('corner_joinery','bronze',x,z-.0325,z+.0325,w,.12,-.12)
  for j in range(1,panes):box('corner_joinery','bronze',a+j*w/panes,glow,ghigh,.055,.12,-.12)
  windows.append({'x':x,'width':w,'low':glow,'high':ghigh,'panes':panes});cursor=b
 if cursor<width/2:box('corner_masonry','stone',(cursor+width/2)/2,lo,hi,width/2-cursor)
# Three distinct openings below the monumental recess, instead of two repeated bays.
plain_row(4.2,7.8,4.85,7.32,[(-2.15,.68,1),(0,1.5,2),(2.15,.68,1)])
# The centre portal is a continuous dark recessed field with projecting stone piers.
for a,b in [(-width/2,-2.5),(-1.88,-1.5),(1.5,1.88),(2.5,width/2)]:box('corner_masonry','stone',(a+b)/2,7.8,18.6,b-a)
for x,w in [(-2.19,.62),(0,3.0),(2.19,.62)]:
 for lo,hi in [(7.8,8.45),(10.92,12.05),(14.52,15.65),(18.12,18.6)]:box('portal_metal_spandrel','spandrel',x,lo,hi,w,.07,-.24)
 for lo,hi in [(8.45,10.92),(12.05,14.52),(15.65,18.12)]:
  box('corner_glass','glass',x,lo,hi,w,.045,-.27)
  for xx in [x-w/2,x+w/2]:box('corner_joinery','bronze',xx,lo,hi,.065,.12,-.12)
  for z in [lo,hi]:box('corner_joinery','bronze',x,z-.0325,z+.0325,w,.12,-.12)
  if x==0:
   for xx in [-.5,.5]:box('corner_joinery','bronze',xx,lo,hi,.055,.12,-.12)
  windows.append({'x':x,'width':w,'low':lo,'high':hi,'panes':3 if x==0 else 1})
for x in [-1.69,1.69]:box('portal_projecting_piers','trim',x,8.0,18.43,.36,.75,.10)
box('portal_projecting_lintel','trim',0,18.26,18.6,3.74,.9,.16)
box('portal_lower_stone_ledge','trim',0,8.04,8.3,3.78,.95,.19)
# Broad three-light window over the portal and the upper three narrow lights.
plain_row(18.6,22.2,19.25,21.72,[(0,3.0,3)])
plain_row(22.2,25.8,23.32,24.65,[(-1.05,.52,1),(0,.62,1),(1.05,.52,1)])
for g in groups.values():
 obj=g.finish();obj.name=obj.name.replace('61A_D5_NEXT_','61A_NEXT_');obj.data.name=obj.name
 for mod in list(obj.modifiers):obj.modifiers.remove(mod)
 owned.append(obj)
owned_names=[o.name for o in owned]
for layer in bpy.context.scene.view_layers:layer.update()
def probes():
 trees=[(o.name,BVHTree.FromPolygons([o.matrix_world@v.co for v in o.data.vertices],[tuple(f.vertices)for f in o.data.polygons],all_triangles=False))for o in bpy.data.collections['61A_EXTERIOR'].all_objects if o.type=='MESH'and not o.hide_render and len(o.data.polygons)]
 checks=[]
 samples=[(w['x']+w['width']*.21,(w['low']+w['high'])/2,'61A_NEXT_corner_glass_glass')for w in windows]
 samples.extend([(x,13.2,'61A_NEXT_portal_projecting_piers_trim')for x in [-1.69,1.69]])
 samples.extend([(0,11.45,'61A_NEXT_portal_metal_spandrel_spandrel'),(0,22.7,'61A_NEXT_corner_masonry_stone')])
 for x,z,expected in samples:
  start=world(x,z,2);best=None
  for name,tree in trees:
   hit=tree.ray_cast(start,-normal,4)
   if hit[0]is not None and(best is None or hit[3]<best[0]):best=(hit[3],name)
  assert best and best[1]==expected,(x,z,expected,best)
  checks.append({'localX':x,'height':z,'firstSurface':best[1],'distance':best[0]})
 return checks
checks=probes();assert all(fingerprint(bpy.data.objects[n])==v for n,v in originals.items())
component=OUT/'aldwych-facade-component.blend';bpy.data.libraries.write(str(component),set(owned),fake_user=True)
photo=ROOT/'data/documents/61aldwych_brochure_2021.pdf'
audit={'baseline':str(BASE),'baselineSha256':hashlib.sha256(BASE.read_bytes()).hexdigest(),'originalFingerprints':originals,'originalVisibility':visibility,'ownedObjects':owned_names,'archivedObjects':archives,'changeSummary':['Replaced the two repeated central windows by the photographed continuous three-storey recessed portal, its stone piers, dark metal spandrels and differentiated central/side lights.','Reconstructed the rows below and above the portal and the upper three narrow lights, confined to the existing6.769m street-corner segment.','Retained original entrance, surrounding street wings, roof pavilion, footprint, glass shaders and all original meshes; no speculative internal walls or alpha changes.'],'removedComponents':removed,'reference':{'file':str(photo),'sha256':hashlib.sha256(photo.read_bytes()).hexdigest(),'pdfPages':[1,9],'printedPage':18,'issue':'2021 letting brochure; PDF creation2021-07-15; image capture dates unknown','coverage':'Day street-corner photograph includes entire portal, upper three-light row, entrance and flanking street wings; cover evening photo corroborates the central recess.','url':None},'registration':{'centre':list(centre),'axis':list(axis),'outward':list(normal),'cornerSegmentLength':width,'boundarySource':'Original native segment anchored by OSM way/181939023; unlabelled61A provisional aggregate envelope.','scale':'Existing storey datums and6.769m segment preserved. Opening widths, pier sizes and projected relief are visual estimates, not measured dimensions.'},'wholeBuildingReview':{'massing':'Long Kingsway envelope and roof geometry remain provisional. Brochure plan is indicative and has no metric dimensions; exact property boundary not registered.','streetWings':'Existing side-wing3-storey belts preserved; Aldwych-side/party-wall allocation requires surveyed boundary registration.','centralFacade':'Previously missed distinguishing monumental portal corrected across six central levels.','entrance':'Existing recessed broad glazing preserved; day photo supports general portal arrangement but detailed ground-floor offsets require dedicated entrance registration.','materials':'Pale masonry and dark joinery roles match photographs. Night photo warm light is illumination evidence, not justification for yellow glass. Current opaque glass retained because local room enclosure is not verified.'},'limitations':['2021 source does not independently verify present-day LSE conversion exterior.','Central datum and opening sizes estimated; sculpted balcony and ornamental relief simplified, not exact reproductions.','Roof central stepped parapet and long-wing dormer count still differ; cannot faithfully correct before resolving combined footprint and front/side orientation.','No unseen rear elevation or interior constructed.'],'firstSurfaceChecks':checks}
audit['changes']=[{'source':source,'owned':'61A_NEXT_retained_'+source.removeprefix('61A_D5_'),'action':'Retain all geometry outside the registered central street-corner segment; remove only the superseded six-level central components from this independent copy.'}for source in archives]+[{'source':None,'owned':name,'action':'Add the photo-supported central street-corner component; metric dimensions remain estimates.'}for name in owned_names if not name.startswith('61A_NEXT_retained_')]
(OUT/'audit.json').write_text(json.dumps(audit,indent=2)+'\n')
open_baseline();col=bpy.data.collections['61A_EXTERIOR']
with bpy.data.libraries.load(str(component),link=False)as(src,dst):dst.objects=src.objects
for o in dst.objects:col.objects.link(o)
for name in archives:bpy.data.objects[name].hide_render=True;bpy.data.objects[name].hide_set(True)
for layer in bpy.context.scene.view_layers:layer.update()
checks2=probes();assert all(fingerprint(bpy.data.objects[n])==v for n,v in originals.items())
scene=bpy.context.scene;visible={o.name for o in col.all_objects}
for o in scene.objects:
 if o.type in {'MESH','FONT','CURVE','SURFACE'}and o.name not in visible:o.hide_render=True
focus=world(0,19,-1);cam=bpy.data.objects.new('ALDWYCH_REVIEW',bpy.data.cameras.new('ALDWYCH_REVIEW'));scene.collection.objects.link(cam);cam.location=focus+normal*85+axis*8+Vector((0,0,8));cam.rotation_euler=(focus-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=55;scene.camera=cam;scene.render.engine='BLENDER_EEVEE';scene.render.resolution_x=1300;scene.render.resolution_y=1100;scene.render.resolution_percentage=100;scene.render.filepath=str(OUT/'reloaded-street-corner.png');bpy.ops.render.render(write_still=True)
proof={'componentSha256':hashlib.sha256(component.read_bytes()).hexdigest(),'savedComponentReopened':True,'originalGeometryPreserved':True,'originalObjectCount':len(originals),'fullModelSaved':False,'firstSurfaceChecks':checks2,'allOriginalGlassMaterialsPreserved':True}
(OUT/'verification.json').write_text(json.dumps(proof,indent=2)+'\n');print('ALDWYCH_REOPENED',len(originals),len(owned_names),len(archives),len(checks2));bpy.ops.wm.quit_blender()
