"""Restore photographed ashlar joints on 51 Lincoln's Inn Fields' front base.

Run in Blender's Text Editor. The existing three arches and all upper facade,
roof, rounded corner and interior geometry remain unchanged. Joint dimensions
are photo estimates; no measured survey is claimed.
"""
from pathlib import Path
import array, hashlib, json, math, sys
import bpy, bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'result/blender/lincoln51_next';OUT.mkdir(parents=True,exist_ok=True)
BASE=ROOT/'result/blender/LSE_campus_detailed_v121.blend'
if not BASE.exists():BASE=max((ROOT/'result/blender').glob('LSE_campus_detailed_v[0-9]*.blend'),key=lambda p:int(p.stem.rsplit('v',1)[1]))
bpy.ops.wm.open_mainfile(filepath=str(BASE));scene=bpy.data.scenes['00_CAMPUS_COMPLETE'];bpy.context.window.scene=scene
previous=json.loads((OUT/'audit.json').read_text()) if (OUT/'audit.json').exists() else None
if previous:
 for name in previous['ownedObjects']:
  obj=bpy.data.objects.get(name)
  if obj:
   data=obj.data;bpy.data.objects.remove(obj,do_unlink=True);data.use_fake_user=False
   if not data.users:bpy.data.meshes.remove(data)
 for name in previous['archivedObjects']:
  if name in bpy.data.objects:
   obj=bpy.data.objects[name];state=previous['originalVisibility'][name]
   obj.hide_render,obj.hide_viewport=state[:2];obj.hide_set(state[2])
def fingerprint(o):
 h=hashlib.sha256(str([list(r) for r in o.matrix_world]).encode())
 if o.type=='MESH':
  for data,field,kind,n in ((o.data.vertices,'co','f',3),(o.data.loops,'vertex_index','i',1),(o.data.polygons,'material_index','i',1)):
   values=array.array(kind,[0])*(len(data)*n);data.foreach_get(field,values);h.update(values.tobytes())
  for layer in o.data.uv_layers:
   values=array.array('f',[0])*(len(layer.data)*2);layer.data.foreach_get('uv',values);h.update(values.tobytes())
 h.update(str([m.name if m else None for m in getattr(o.data,'materials',[])]).encode());return h.hexdigest()
originals={o.name:fingerprint(o) for o in bpy.data.objects}
visibility={o.name:[o.hide_render,o.hide_viewport,o.hide_get()] for o in bpy.data.objects}
ring=next(p for p in json.loads((ROOT/'result/blender/site_geometry.json').read_text())['buildings'] if p['code']=='51L')['rings'][0]
a=Vector((*ring[1],0));u=Vector((*ring[2],0))-a;length=u.length;u.normalize();normal=Vector((-u.y,u.x,0))
center=sum((Vector((*p,0)) for p in ring),Vector())/len(ring)
if normal.dot(a+u*length/2-center)<0:normal=-normal
height=max((bpy.data.objects['51L_D5_threebay92_brick'].matrix_world@v.co).z for v in bpy.data.objects['51L_D5_threebay92_brick'].data.vertices)
floor=height/6;pitch=length/3;width=pitch*.58;radius=width/2;spring=2.30
collection=bpy.data.collections['51L_EXTERIOR'];source=bpy.data.objects['51L_D5_threebay92_stone']
assert not source.hide_render
copy=source.copy();copy.data=source.data.copy();copy.name='51L_NEXT_recessed_ashlar_backing';copy.data.name=copy.name;collection.objects.link(copy)
# Recess only original ground-storey disconnected components. Every upper
# cornice, sill, lintel and quoin remains at its existing coordinates.
bm=bmesh.new();bm.from_mesh(copy.data);seen=set();recessed=0
for seed in bm.verts:
 if seed in seen:continue
 part=[];pending=[seed];seen.add(seed)
 while pending:
  vertex=pending.pop();part.append(vertex)
  for edge in vertex.link_edges:
   other=edge.other_vert(vertex)
   if other not in seen:seen.add(other);pending.append(other)
 if max((source.matrix_world@v.co).z for v in part)<floor+.001:
  for v in part:v.co-=source.matrix_world.to_3x3().inverted()@normal*.025
  recessed+=1
bm.to_mesh(copy.data);bm.free();copy.data.update();assert recessed>0
source.hide_render=True;source.hide_set(True)
sys.path.insert(0,str(Path(__file__).resolve().parent));from facade_geometry import Geometry,materials
materials.clear();materials['stone']=source.data.materials[0];batch=Geometry('51L','ashlar_courses','stone')
def point(x,d,z):return a+u*x+normal*d+Vector((0,0,z))
def clip(poly,axis,value,sign):
 result=[]
 for p,q in zip(poly,poly[1:]+poly[:1]):
  pv=sign*(p[axis]-value);qv=sign*(q[axis]-value)
  if pv>=-1e-9:result.append(p)
  if (pv>=0)!=(qv>=0):
   t=pv/(pv-qv);result.append((p[0]+t*(q[0]-p[0]),p[1]+t*(q[1]-p[1])))
 return result
outlines=[]
for bay in range(3):
 x=(bay+.5)*pitch
 outlines.extend([[(bay*pitch,0),(x-radius,0),(x-radius,floor),(bay*pitch,floor)],[(x+radius,0),((bay+1)*pitch,0),((bay+1)*pitch,floor),(x+radius,floor)],[(x-radius,0),(x+radius,0),(x+radius,.40),(x-radius,.40)]])
 for j in range(24):
  t0,t1=math.pi*j/24,math.pi*(j+1)/24
  x0,x1=x+radius*math.cos(t0),x+radius*math.cos(t1);z0,z1=spring+radius*math.sin(t0),spring+radius*math.sin(t1)
  outlines.append([(x1,z1),(x0,z0),(x0,floor),(x1,floor)])
# Seven photographed horizontal divisions; staggered head joints. Faces
# are separated by real open rebates backed by the recessed original stone.
courses=8;joint=.012;block=pitch/3;parts=0
for row in range(courses):
 bottom=row*floor/courses+joint/2;top=(row+1)*floor/courses-joint/2
 offset=-block/2 if row%2 else 0
 for index in range(-1,math.ceil(length/block)+2):
  left=max(0,offset+index*block)+joint/2;right=min(length,offset+(index+1)*block)-joint/2
  if right<=left:continue
  for poly in outlines:
   for axis,value,sign in ((0,left,1),(0,right,-1),(1,bottom,1),(1,top,-1)):
    poly=clip(poly,axis,value,sign) if poly else []
   if len(poly)<3:continue
   area=abs(sum(p[0]*q[1]-q[0]*p[1] for p,q in zip(poly,poly[1:]+poly[:1])))/2
   if area<1e-6:continue
   count=len(poly);vertices=[point(x,d,z) for d in (-.005,.033) for x,z in poly]
   faces=[tuple(reversed(range(count))),tuple(range(count,2*count))]+[(j,(j+1)%count,(j+1)%count+count,j+count) for j in range(count)]
   batch.add(vertices,faces);parts+=1
ashlar=batch.finish();ashlar.name='51L_NEXT_ashlar_courses';ashlar.data.name=ashlar.name
for modifier in list(ashlar.modifiers):ashlar.modifiers.remove(modifier)
for obj in (copy,ashlar):
 bm=bmesh.new();bm.from_mesh(obj.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(obj.data);bm.free()
owned=[copy,ashlar];archived=[source.name]
assert all(fingerprint(bpy.data.objects[n])==v for n,v in originals.items())
def aperture_results():
 vertices=[];faces=[];owners=[]
 for o in collection.all_objects:
  if o.type!='MESH' or o.hide_render or 'glass' in o.name or 'wood' in o.name or 'brass' in o.name or 'metal' in o.name:continue
  start=len(vertices);vertices.extend(o.matrix_world@v.co for v in o.data.vertices)
  faces.extend(tuple(start+i for i in p.vertices) for p in o.data.polygons);owners.extend([o.name]*len(o.data.polygons))
 tree=BVHTree.FromPolygons(vertices,faces);results=[]
 for bay in range(3):
  x=(bay+.5)*pitch
  for dx,z in ((-.15,1.70),(.15,1.70),(0,spring+radius*.60)):
   hit=tree.ray_cast(point(x+dx,.25,z),-normal,.65);results.append({'bay':bay,'x':x+dx,'z':z,'opaqueMasonry':owners[hit[2]] if hit[2] is not None else None})
 assert all(r['opaqueMasonry'] is None for r in results),results
 return results
probes=aperture_results();component=OUT/'lincoln51-ashlar-component.blend';bpy.data.libraries.write(str(component),set(owned),fake_user=True,compress=True)
audit={'baselineSha256':hashlib.sha256(BASE.read_bytes()).hexdigest(),'originalFingerprints':originals,'originalVisibility':visibility,'archivedObjects':archived,'ownedObjects':[o.name for o in owned],'recessedGroundParts':recessed,'ashlarPieces':parts,'horizontalCourses':courses,'jointWidthEstimateM':joint,'apertureChecks':probes,'sources':[{'local':'data/collections/lincolns-frontage-review/51l-gsos-2025.jpg','url':'https://www.lse.ac.uk/global-school-of-sustainability/news/2025/first-recipients-Global-Sustainability-Research-Fund','published':'2025-07-31','captureDate':None,'sha256':'0619940f9fb3f241108f346ee6f771dbdf45d7d8400de27133c83ef041c82217'},{'local':'data/建筑图片/51L_51 Lincoln_s Inn Fields/01_建筑实拍/exteriors_lse_estate_015.jpg','url':'https://info.lse.ac.uk/staff/divisions/estates-division/lse-estate/LSE-Estate','captureDate':None,'sha256':'138df01636cc35098af46a5b2b468bce7c65f61e23a74dfc028b58d1d3308f72'}],'limitations':['Stone course, block length and joint depth are photograph-guided estimates','Only Lincoln frontage ground-storey stone corrected; curved entrance and side retain earlier geometry','Brick, roof, window counts and interiors unchanged','Published 2025 photograph does not establish capture date']}
(OUT/'audit.json').write_text(json.dumps(audit,indent=2)+'\n');print('LINCOLN51_COMPONENT_SAVED',component.stat().st_size,flush=True)
bpy.ops.wm.open_mainfile(filepath=str(BASE));scene=bpy.data.scenes['00_CAMPUS_COMPLETE'];bpy.context.window.scene=scene
with bpy.data.libraries.load(str(component),link=False) as (src,dst):dst.objects=audit['ownedObjects']
collection=bpy.data.collections['51L_EXTERIOR']
for o in dst.objects:collection.objects.link(o)
for name in archived:bpy.data.objects[name].hide_render=True;bpy.data.objects[name].hide_set(True)
assert all(fingerprint(bpy.data.objects[n])==v for n,v in originals.items());probes=aperture_results()
# Native reload render isolates this building with neutral illumination.
for o in scene.objects:
 if o.type=='MESH' and o.name not in {v.name for v in collection.all_objects}:o.hide_render=True
camdata=bpy.data.cameras.new('51L_NEXT_preview_camera');cam=bpy.data.objects.new(camdata.name,camdata);scene.collection.objects.link(cam)
focus=point(length/2,0,floor/2);cam.location=focus+normal*15-u*2+Vector((0,0,3));cam.rotation_euler=(focus-cam.location).to_track_quat('-Z','Y').to_euler();camdata.type='ORTHO';camdata.ortho_scale=length+2;scene.camera=cam
scene.render.engine='BLENDER_EEVEE';scene.render.resolution_x=1100;scene.render.resolution_y=650;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG';scene.render.filepath=str(OUT/'reloaded-frontage.png');bpy.ops.render.render(write_still=True)
verification={'componentSha256':hashlib.sha256(component.read_bytes()).hexdigest(),'baselineUnchanged':hashlib.sha256(BASE.read_bytes()).hexdigest()==audit['baselineSha256'],'originalGeometryPreserved':True,'savedComponentReopened':True,'reloadedMasonryClearProbes':len(probes),'nativeRender':'reloaded-frontage.png'}
(OUT/'verification.json').write_text(json.dumps(verification,indent=2)+'\n');print('LINCOLN51_COMPONENT_RELOADED_VERIFIED',flush=True)
