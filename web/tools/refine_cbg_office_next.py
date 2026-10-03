"""Rebuild CBG square-facing academic glazing as documented office modules.
Run in Blender Text Editor. Existing footprint, levels and stair-strip registration
remain estimates; this is a reference-guided architectural study, not a survey.
"""
from pathlib import Path
import array,hashlib,json,math
import bpy,bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'result/blender/cbg_office_next';OUT.mkdir(parents=True,exist_ok=True)
BASE=ROOT/'result/blender/LSE_campus_detailed_v129.blend'
if not BASE.exists():BASE=max((ROOT/'result/blender').glob('LSE_campus_detailed_v[0-9]*.blend'),key=lambda p:int(p.stem.rsplit('v',1)[1]))
previous=json.loads((OUT/'audit.json').read_text())if(OUT/'audit.json').exists()else None
def open_baseline():
 bpy.ops.wm.open_mainfile(filepath=str(BASE));scene=bpy.data.scenes['00_CAMPUS_COMPLETE'];bpy.context.window.scene=scene
 if previous:
  for name in previous['ownedObjects']:
   obj=bpy.data.objects.get(name)
   if obj:
    mesh=obj.data;bpy.data.objects.remove(obj,do_unlink=True);mesh.use_fake_user=False
    if not mesh.users:bpy.data.meshes.remove(mesh)
  for name in previous['archivedObjects']:
   obj=bpy.data.objects[name];v=previous['originalVisibility'][name];obj.hide_render,obj.hide_viewport=v[:2];obj.hide_set(v[2])
 for mat in list(bpy.data.materials):
  if mat.name.startswith('CBG_NEXT_')and mat.users==int(mat.use_fake_user):mat.use_fake_user=False;bpy.data.materials.remove(mat)
 for layer in scene.view_layers:layer.update()
 return scene
scene=open_baseline();collection=bpy.data.collections['CBG_EXTERIOR']
def fingerprint(o):
 h=hashlib.sha256(str([list(r)for r in o.matrix_world]).encode())
 if o.type=='MESH':
  for data,field,kind,n in [(o.data.vertices,'co','f',3),(o.data.loops,'vertex_index','i',1),(o.data.polygons,'material_index','i',1)]:
   values=array.array(kind,[0])*(len(data)*n);data.foreach_get(field,values);h.update(values.tobytes())
  for layer in o.data.uv_layers:
   values=array.array('f',[0])*(len(layer.data)*2);layer.data.foreach_get('uv',values);h.update(values.tobytes())
 h.update(str([m.name if m else None for m in getattr(o.data,'materials',[])]).encode());return h.hexdigest()
original={o.name:fingerprint(o)for o in bpy.data.objects};visibility={o.name:[o.hide_render,o.hide_viewport,o.hide_get()]for o in bpy.data.objects}
site=json.loads((ROOT/'result/blender/site_geometry.json').read_text());cx,cy=next(b for b in site['buildings']if b['code']=='CBG')['center'];a=math.radians(58);c,s=math.cos(a),math.sin(a)
def world(x,y,z):return Vector((cx+c*x-s*y,cy+s*x+c*y,z))
def local(v):return Vector((c*(v.x-cx)+s*(v.y-cy),-s*(v.x-cx)+c*(v.y-cy),v.z))
STEP=52.2/13;CLEAR=[None,-9,-9,-1,-1,-9,-17,-25,-25,-17,-9,-1,-1]
modules=[]
# Sixteen 3m office units fit the existing estimated49m tower frontage, leaving
# half-metre edge glazing. Never put an office panel in the meandering stair strip.
for floor in range(3,13):
 for i in range(16):
  x0=-41.5+i*3;x1=x0+3;void=(CLEAR[floor]-7.8,CLEAR[floor]+7.8)
  if x1<=void[0]-.10 or x0>=void[1]+.10:modules.append({'floor':floor,'x0':x0,'x1':x1,'solidStart':x0+2})
assert len(modules)>80,len(modules)
intervals={f:[(m['x0'],m['x1'])for m in modules if m['floor']==f]for f in range(3,13)}
BOX_FACES=[(0,4,6,2),(1,3,7,5),(0,1,5,4),(2,6,7,3),(0,2,3,1),(4,5,7,6)]
def box_mesh(vertices,faces,lo,hi):
 n=len(vertices)
 for u,v,w in [(0,0,0),(0,0,1),(0,1,0),(0,1,1),(1,0,0),(1,0,1),(1,1,0),(1,1,1)]:vertices.append(world((lo[0],hi[0])[u],(lo[1],hi[1])[v],(lo[2],hi[2])[w]))
 faces.extend(tuple(n+i for i in f)for f in BOX_FACES)
def make(name,vertices,faces,material):
 mesh=bpy.data.meshes.new(name);mesh.from_pydata(vertices,[],faces);mesh.update();mesh.materials.append(material);obj=bpy.data.objects.new(name,mesh);collection.objects.link(obj);return obj
owned=[];archived=[];removal_counts={}
source_names=['CBG_NEXT_neutral_curtain_wall_glazing','CBG_D_window_mullions','CBG_D_window_transoms']+[o.name for o in collection.all_objects if not o.hide_render and o.name.startswith(('CBG_D5_V16_','CBG_D5_V17_'))]
for name in source_names:
 old=bpy.data.objects[name];assert not old.hide_render and len(old.data.materials)==1
 new=old.copy();new.data=old.data.copy();new.name='CBG_NEXT_office_retained_'+name;new.data.name=new.name;collection.objects.link(new)
 # Remove the same decorative bevels as the existing overview; these replacement
 # groups keep their geometry at both scales instead of restoring detail-only bevels.
 for mod in list(new.modifiers):
  if mod.type=='BEVEL':new.modifiers.remove(mod)
 bm=bmesh.new();bm.from_mesh(new.data);seen=set();delete=[];remainder_boxes=[];count=0
 for vertex in bm.verts:
  if vertex in seen:continue
  seen.add(vertex);stack=[vertex];part=[]
  while stack:
   v=stack.pop();part.append(v)
   for e in v.link_edges:
    other=e.other_vert(v)
    if other not in seen:seen.add(other);stack.append(other)
  points=[local(new.matrix_world@v.co)for v in part];lo=[min(p[k]for p in points)for k in range(3)];hi=[max(p[k]for p in points)for k in range(3)];floor=int(((lo[2]+hi[2])/2+.001)//STEP)
  if floor not in intervals or abs((lo[1]+hi[1])/2+2)>.60:continue
  spans=[(x0,x1)for x0,x1 in intervals[floor]if x1>lo[0]+.001 and x0<hi[0]-.001]
  if not spans:continue
  # Glass is a disconnected rectangular solid. Clip just its office overlap,
  # keeping genuine glass in the stair strip and all unaffected rows/faces.
  if name=='CBG_NEXT_neutral_curtain_wall_glazing':
   assert len(part)==8,len(part);remaining=[(lo[0],hi[0])]
   for x0,x1 in spans:
    next_ranges=[]
    for left,right in remaining:
     if x1<=left or x0>=right:next_ranges.append((left,right))
     else:
      if x0>left+.001:next_ranges.append((left,x0))
      if x1<right-.001:next_ranges.append((x1,right))
    remaining=next_ranges
   remainder_boxes.extend(([left,lo[1],lo[2]],[right,hi[1],hi[2]])for left,right in remaining)
  elif not any(x0+.001<(lo[0]+hi[0])/2<x1-.001 for x0,x1 in spans):continue
  delete.extend(part);count+=1
 if not count:
  mesh=new.data;bpy.data.objects.remove(new,do_unlink=True);bpy.data.meshes.remove(mesh);bm.free();continue
 bmesh.ops.delete(bm,geom=delete,context='VERTS');bm.to_mesh(new.data);bm.free();new.data.update()
 if remainder_boxes:
  vertices=[new.matrix_world@v.co for v in new.data.vertices];faces=[tuple(p.vertices)for p in new.data.polygons]
  for lo,hi in remainder_boxes:box_mesh(vertices,faces,lo,hi)
  mat=new.data.materials[0];old_mesh=new.data;new.data=bpy.data.meshes.new(new.name);new.data.from_pydata(vertices,[],faces);new.data.update();new.data.materials.append(mat);new.matrix_world.identity();bpy.data.meshes.remove(old_mesh)
 old.hide_render=True;old.hide_set(True);owned.append(new);archived.append(name);removal_counts[name]=count
# Closed office leaves, high-level glass vents and thin recessed perimeter frames.
materials={'glass':bpy.data.objects['CBG_NEXT_neutral_curtain_wall_glazing'].data.materials[0],'silver':bpy.data.materials['CBG_D_silver_aluminium'],'frame':bpy.data.materials['CBG_D_charcoal_thermal_frames']}
leaf=materials['silver'].copy();leaf.name='CBG_NEXT_office_pale_solid_leaf';leaf.diffuse_color=(.57,.585,.58,1)
shader=leaf.node_tree.nodes.get('Principled BSDF');shader.inputs['Base Color'].default_value=(.57,.585,.58,1);shader.inputs['Metallic'].default_value=.15;shader.inputs['Roughness'].default_value=.45
materials['solid']=leaf
geometry={key:([],[])for key in ['glass','solid','frames','grooves']}
def add(key,x0,x1,y0,y1,z0,z1):box_mesh(*geometry[key],[x0,y0,z0],[x1,y1,z1])
for m in modules:
 x=m['x0'];z0=m['floor']*STEP+.08;z1=(m['floor']+1)*STEP-.08;vent=z1-.50
 add('glass',x+.035,x+1.965,-2.018,-1.983,z0,z1)
 add('solid',x+2.035,x+2.965,-2.105,-2.025,z0,z1)
 for xx in [x,x+2,x+3]:add('frames',xx-.025,xx+.025,-2.145,-2.025,z0,z1)
 for zz in [z0,z1]:add('frames',x,x+3,-2.145,-2.025,zz-.025,zz+.025)
 add('frames',x,x+2,-2.145,-2.025,vent-.022,vent+.022)
 # Thin horizontal reveals distinguish the opaque leaf from transparent glass.
 for k in range(1,10):
  z=z0+(z1-z0)*k/10;add('grooves',x+2.07,x+2.93,-2.108,-2.105,z-.004,z+.004)
for key,(vertices,faces)in geometry.items():
 name='CBG_NEXT_office_'+key;material=materials['glass']if key=='glass'else materials['solid']if key=='solid'else materials['frame'];owned.append(make(name,vertices,faces,material))
assert all(fingerprint(bpy.data.objects[n])==v for n,v in original.items())
def probes():
 trees=[]
 for o in collection.all_objects:
  if o.type=='MESH'and not o.hide_render:trees.append((o,BVHTree.FromPolygons([o.matrix_world@v.co for v in o.data.vertices],[tuple(p.vertices)for p in o.data.polygons])))
 rows=[]
 for m in modules:
  floor=m['floor'];z0=floor*STEP+.08;z1=(floor+1)*STEP-.08
  for kind,offsets,z,target in [('glass',[.45,.8,1.25,1.6],z0+.65,'CBG_NEXT_office_glass'),('solid',[2.20,2.40,2.65,2.80],z0+.65,'CBG_NEXT_office_solid'),('vent',[.45,.8,1.25,1.6],z1-.50,'CBG_NEXT_office_frames')]:
   found=None;attempts=[]
   for offset in offsets:
    start=world(m['x0']+offset,-2.22,z);best=None
    for o,t in trees:
     hit=t.ray_cast(start,Vector((-s,c,0)),.8)
     if hit[0]is not None and(best is None or hit[3]<best[0]):best=(hit[3],o.name)
    attempts.append(best)
    if best and best[1]==target:found=(start,best);break
   assert found,(m,kind,attempts)
   rows.append({'floor':floor,'moduleX':m['x0'],'kind':kind,'point':list(found[0]),'firstSurface':found[1][1]})
 # Every clear stair strip must still expose retained neutral glass.
 for floor in range(3,13):
  bvh_rows=[]
  for x in [CLEAR[floor]-.6,CLEAR[floor]+.6]:
   start=world(x,-2.1,floor*STEP+1.1);best=None
   for o,t in trees:
    hit=t.ray_cast(start,Vector((-s,c,0)),.5)
    if hit[0]is not None and(best is None or hit[3]<best[0]):best=(hit[3],o.name)
   if best and best[1].startswith('CBG_NEXT_office_retained_CBG_NEXT_neutral_curtain'):bvh_rows.append(best)
  assert bvh_rows,('stair strip',floor)
 return rows
rows=probes();component=OUT/'cbg-office-component.blend';bpy.data.libraries.write(str(component),set(owned),fake_user=True,compress=True)
photo=ROOT/'data/collections/cbg_facade_contractor/photo-6.jpg'
audit={'baselineSha256':hashlib.sha256(BASE.read_bytes()).hexdigest(),'ownedObjects':[o.name for o in owned],'archivedObjects':archived,'originalVisibility':visibility,'retainedOriginalObjects':len(original),'officeModules':modules,'moduleCount':len(modules),'removedSolidCounts':removal_counts,'source':{'url':'https://rshp.com/projects/education/lse-centre-building/','specification':'Each academic office:2m glazing with high-level vent plus1m solid inward-opening panel','photo':str(photo.relative_to(ROOT)),'photoSha256':hashlib.sha256(photo.read_bytes()).hexdigest(),'captureDate':'unknown'},'registration':{'face':'square-facing tower','localY':-2,'academicFloors':list(range(3,13)),'officeUnitPitch':3,'glazedNominalWidth':2,'solidNominalWidth':1,'stairClearCentres':CLEAR,'stairHalfWidth':7.8},'limitations':['Current campus footprint, floor heights and stair-strip positions remain photo/GIS estimates.','Exact office counts and individual module offsets are a reference-guided reconstruction, not a registered as-built elevation.','Only square-facing academic tower strips are reconstructed; teaching floors, stairs, back face, low wing and end faces retained.','Opening leaves are shown closed; no unsupported opening animation or fabricated room allocation.'],'surfaceProbes':rows}
(OUT/'audit.json').write_text(json.dumps(audit,indent=2)+'\n')
scene=open_baseline();collection=bpy.data.collections['CBG_EXTERIOR']
with bpy.data.libraries.load(str(component),link=False)as(src,dst):dst.objects=audit['ownedObjects']
for o in dst.objects:
 collection.objects.link(o)
 for i,m in enumerate(list(o.data.materials)):
  if m and m.name[-4:-3]=='.':o.data.materials[i]=bpy.data.materials[m.name.rsplit('.',1)[0]]
for name in archived:bpy.data.objects[name].hide_render=True;bpy.data.objects[name].hide_set(True)
for layer in scene.view_layers:layer.update()
reloaded=probes();assert reloaded==rows;assert all(fingerprint(bpy.data.objects[n])==v for n,v in original.items())
proof={'componentSha256':hashlib.sha256(component.read_bytes()).hexdigest(),'savedComponentReopened':True,'originalGeometryPreserved':True,'retainedOriginalObjects':len(original),'moduleCount':len(modules),'visibleSurfaceChecks':len(rows),'stairStripsRetained':10,'fullModelSaved':False}
(OUT/'verification.json').write_text(json.dumps(proof,indent=2)+'\n')
visible={o.name for o in collection.all_objects}
for o in scene.objects:
 if o.type=='MESH'and o.name not in visible:o.hide_render=True
focus=world(-25,-2,31);cd=bpy.data.cameras.new('CBG_OFFICE_REVIEW');cam=bpy.data.objects.new(cd.name,cd);scene.collection.objects.link(cam);cam.location=focus+Vector((s,-c,.04))*40;cam.rotation_euler=(focus-cam.location).to_track_quat('-Z','Y').to_euler();cd.type='ORTHO';cd.ortho_scale=24;scene.camera=cam;scene.render.engine='BLENDER_EEVEE';scene.render.resolution_x=1050;scene.render.resolution_y=1050;scene.render.resolution_percentage=100;scene.render.filepath=str(OUT/'reloaded-offices.png');bpy.ops.render.render(write_still=True)
print('CBG_OFFICE_COMPONENT_RELOADED',len(modules),len(rows),len(original),flush=True);bpy.ops.wm.quit_blender()
