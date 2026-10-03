"""Correct the two photographed storeys above CBG's braced entrance.
Run in Blender Text Editor. Keep other end faces and unphotographed rows intact.
"""
from pathlib import Path
import array,hashlib,json,math
import bpy,bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'result/blender/cbg_frontage_next';OUT.mkdir(parents=True,exist_ok=True)
BASE=ROOT/'result/blender/LSE_campus_detailed_v128.blend'
if not BASE.exists():BASE=max((ROOT/'result/blender').glob('LSE_campus_detailed_v[0-9]*.blend'),key=lambda p:int(p.stem.rsplit('v',1)[1]))
bpy.ops.wm.open_mainfile(filepath=str(BASE));scene=bpy.data.scenes['00_CAMPUS_COMPLETE'];bpy.context.window.scene=scene
previous=json.loads((OUT/'audit.json').read_text())if (OUT/'audit.json').exists()else None
def restore_component_baseline():
 if previous:
  for name in previous['ownedObjects']:
   obj=bpy.data.objects.get(name)
   if obj:
    mesh=obj.data;bpy.data.objects.remove(obj,do_unlink=True);mesh.use_fake_user=False
    if not mesh.users:bpy.data.meshes.remove(mesh)
  for name in previous['archivedObjects']:
   if name in bpy.data.objects:
    obj=bpy.data.objects[name];state=previous['originalVisibility'][name];obj.hide_render,obj.hide_viewport=state[:2];obj.hide_set(state[2])
 for mat in list(bpy.data.materials):
  if mat.name.startswith(('CBG_NEXT_',)) and mat.users==int(mat.use_fake_user):
   mat.use_fake_user=False;bpy.data.materials.remove(mat)
restore_component_baseline()
for layer in scene.view_layers:layer.update()
def fingerprint(obj):
 h=hashlib.sha256(str([list(r)for r in obj.matrix_world]).encode())
 if obj.type=='MESH':
  for rows,field,kind,count in [(obj.data.vertices,'co','f',3),(obj.data.loops,'vertex_index','i',1),(obj.data.polygons,'material_index','i',1)]:
   values=array.array(kind,[0])*(len(rows)*count);rows.foreach_get(field,values);h.update(values.tobytes())
  for uv in obj.data.uv_layers:
   values=array.array('f',[0])*(len(uv.data)*2);uv.data.foreach_get('uv',values);h.update(values.tobytes())
 h.update(str([m.name if m else None for m in getattr(obj.data,'materials',[])]).encode());return h.hexdigest()
original={o.name:fingerprint(o)for o in bpy.data.objects};visibility={o.name:[o.hide_render,o.hide_viewport,o.hide_get()]for o in bpy.data.objects}
site=json.loads((ROOT/'result/blender/site_geometry.json').read_text());cx,cy=next(b for b in site['buildings']if b['code']=='CBG')['center'];angle=math.radians(58);c,s=math.cos(angle),math.sin(angle)
def world(x,y,z):return Vector((cx+c*x-s*y,cy+s*x+c*y,z))
def local(v):return Vector((c*(v.x-cx)+s*(v.y-cy),-s*(v.x-cx)+c*(v.y-cy),v.z))
collection=bpy.data.collections['CBG_EXTERIOR'];source=bpy.data.objects['CBG_D_end_wall_mullions'];assert not source.hide_render
retained=source.copy();retained.data=source.data.copy();retained.name='CBG_NEXT_entrance_retained_mullions';retained.data.name=retained.name;collection.objects.link(retained)
step=25/6;removed=[];bm=bmesh.new();bm.from_mesh(retained.data);seen=set();delete=[]
for vertex in bm.verts:
 if vertex in seen:continue
 stack=[vertex];seen.add(vertex);part=[]
 while stack:
  v=stack.pop();part.append(v)
  for edge in v.link_edges:
   n=edge.other_vert(v)
   if n not in seen:seen.add(n);stack.append(n)
 coords=[local(retained.matrix_world@v.co)for v in part];lo=[min(v[k]for v in coords)for k in range(3)];hi=[max(v[k]for v in coords)for k in range(3)];centre=[(lo[k]+hi[k])/2 for k in range(3)]
 floor=round(centre[2]/step-.5);division=round((centre[1]+14)/16*6)
 if abs(centre[0]-7)<.001 and floor in (1,2) and division in (1,3,5) and abs(centre[1]-(-14+division*16/6))<.001:
  delete.extend(part);removed.append({'floor':floor,'division':division,'bounds':[lo,hi]})
assert len(removed)==6,removed
bmesh.ops.delete(bm,geom=delete,context='VERTS');bm.to_mesh(retained.data);bm.free();retained.data.update();source.hide_render=True;source.hide_set(True)
verts=[];faces=[]
for floor in (1,2):
 x,y,z=6.94,-6,(floor+1)*step-.85;sizes=(.14,16,.055);offset=len(verts)
 for a,b,d in [(-1,-1,-1),(-1,-1,1),(-1,1,-1),(-1,1,1),(1,-1,-1),(1,-1,1),(1,1,-1),(1,1,1)]:verts.append(world(x+a*sizes[0]/2,y+b*sizes[1]/2,z+d*sizes[2]/2))
 faces.extend(tuple(offset+i for i in f)for f in [(0,4,6,2),(1,3,7,5),(0,1,5,4),(2,6,7,3),(0,2,3,1),(4,5,7,6)])
mesh=bpy.data.meshes.new('CBG_NEXT_entrance_high_level_transoms');mesh.from_pydata(verts,[],faces);mesh.update();mesh.materials.append(bpy.data.materials['CBG_D_silver_aluminium']);transom=bpy.data.objects.new(mesh.name,mesh);collection.objects.link(transom)
bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free();owned=[retained,transom]
def tree():
 verts=[];faces=[];owners=[]
 for obj in collection.all_objects:
  if obj.type!='MESH' or obj.hide_render:continue
  offset=len(verts);verts.extend(obj.matrix_world@v.co for v in obj.data.vertices);faces.extend(tuple(offset+i for i in f.vertices)for f in obj.data.polygons);owners.extend([obj.name]*len(obj.data.polygons))
 return BVHTree.FromPolygons(verts,faces),owners
def probe(bvh,owners,label,y,z):
 hit=bvh.ray_cast(world(5.8,y,z),Vector((c,s,0)),2)
 return {'label':label,'local':[5.8,y,z],'firstSurface':owners[hit[2]]if hit[2]is not None else None}
def checks():
 bvh,owners=tree();rows=[]
 # Outside the tower overlap y>=-2, test actual visible glass at removed bars.
 for floor in (1,2):
  for div in (1,3):
   y=-14+div*16/6
   candidates=[probe(bvh,owners,'removed-bar-glass',y,floor*step+t)for t in (.6,1.2,1.8,2.4)]
   found=next((r for r in candidates if r['firstSurface']=='CBG_NEXT_neutral_end_wall_glazing'),None);assert found,candidates;rows.append(found)
  for div in (2,4):
   y=-14+div*16/6
   candidates=[probe(bvh,owners,'retained-vertical',y,floor*step+t)for t in (.6,1.2,1.8,2.4)]
   found=next((r for r in candidates if r['firstSurface']==retained.name),None);assert found,candidates;rows.append(found)
  z=(floor+1)*step-.85
  candidates=[probe(bvh,owners,'new-high-transom',y,z)for y in (-12,-10,-7,-5,-3)]
  found=next((r for r in candidates if r['firstSurface']==transom.name),None);assert found,candidates;rows.append(found)
 return rows
rows=checks();assert all(fingerprint(bpy.data.objects[n])==v for n,v in original.items())
component=OUT/'cbg-frontage-component.blend';bpy.data.libraries.write(str(component),set(owned),fake_user=True,compress=True)
photo=ROOT/'data/collections/cbg_facade_contractor/photo-5.jpg'
audit={'baselineSha256':hashlib.sha256(BASE.read_bytes()).hexdigest(),'ownedObjects':[o.name for o in owned],'archivedObjects':[source.name],'originalVisibility':visibility,'removedSolids':removed,'retainedOriginalObjects':len(original),'photo':{'file':str(photo.relative_to(ROOT)),'sha256':hashlib.sha256(photo.read_bytes()).hexdigest(),'url':'https://www.dobler-metallbau.com/wp-content/uploads/2020/11/55_LSE_1174x684px5.jpg','captureDate':'unknown'},'registration':{'wing':'low wing','planeX':7,'yRange':[-14,2],'zRange':[step,3*step],'columns':3,'upperTransomOffset':.85,'localAngle':58,'towerOverlap':[-2,2]},'surfaceProbes':rows,'limitations':['Only two complete photographed storeys above the entrance are corrected.','Wing dimensions, frame thickness and transom offset remain estimates.','The existing tower/low-wing overlap is retained; visible-surface probes exclude the shared four-metre region.','Other end walls, ground entrance, upper unphotographed floors and office panels are unchanged.']}
(OUT/'audit.json').write_text(json.dumps(audit,indent=2)+'\n')
bpy.ops.wm.open_mainfile(filepath=str(BASE));scene=bpy.data.scenes['00_CAMPUS_COMPLETE'];bpy.context.window.scene=scene
restore_component_baseline();collection=bpy.data.collections['CBG_EXTERIOR']
with bpy.data.libraries.load(str(component),link=False)as(src,dst):dst.objects=audit['ownedObjects']
for obj in dst.objects:
 collection.objects.link(obj)
 for i,mat in enumerate(list(obj.data.materials)):
  if mat and mat.name[-4:-3]=='.':obj.data.materials[i]=bpy.data.materials[mat.name.rsplit('.',1)[0]]
retained,transom=dst.objects;source=bpy.data.objects[audit['archivedObjects'][0]];source.hide_render=True;source.hide_set(True)
for layer in scene.view_layers:layer.update()
reopened=checks();assert reopened==rows;assert all(fingerprint(bpy.data.objects[n])==v for n,v in original.items())
proof={'componentSha256':hashlib.sha256(component.read_bytes()).hexdigest(),'savedComponentReopened':True,'originalGeometryPreserved':True,'retainedOriginalObjects':len(original),'removedSolids':6,'visibleGlassProbeCount':4,'retainedVerticalProbeCount':4,'newHighTransomProbeCount':2,'reopenedSurfaceProbes':reopened,'fullModelSaved':False}
(OUT/'verification.json').write_text(json.dumps(proof,indent=2)+'\n')
# Inspect the braced frontage in a reloaded scene, without saving a full copy.
for obj in scene.objects:
 if obj.type=='MESH'and obj.name not in {o.name for o in collection.all_objects}:obj.hide_render=True
focus=world(7,-7,8.1);camdata=bpy.data.cameras.new('CBG_FRONTAGE_preview');cam=bpy.data.objects.new(camdata.name,camdata);scene.collection.objects.link(cam);cam.location=focus+Vector((-c,-s,.01))*26;cam.rotation_euler=(focus-cam.location).to_track_quat('-Z','Y').to_euler();camdata.type='ORTHO';camdata.ortho_scale=20;scene.camera=cam
scene.render.engine='BLENDER_EEVEE';scene.render.resolution_x=1000;scene.render.resolution_y=950;scene.render.resolution_percentage=100;scene.render.filepath=str(OUT/'reloaded-frontage.png');bpy.ops.render.render(write_still=True)
print('CBG_FRONTAGE_COMPONENT_RELOADED',len(original),len(reopened),flush=True);bpy.ops.wm.quit_blender()
