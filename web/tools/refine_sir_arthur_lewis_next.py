"""Restore SAL's photographed semicircular historical entrance.

Run in Blender's Text Editor. Photograph establishes the arch form, not metric
measurements. Existing column positions, entrance width and entablature stay.
"""
from pathlib import Path
import array, hashlib, json, math, sys
import bpy,bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'result/blender/sal_next';OUT.mkdir(parents=True,exist_ok=True)
BASE=ROOT/'result/blender/LSE_campus_detailed_v123.blend'
if not BASE.exists():BASE=max((ROOT/'result/blender').glob('LSE_campus_detailed_v[0-9]*.blend'),key=lambda p:int(p.stem.rsplit('v',1)[1]))
bpy.ops.wm.open_mainfile(filepath=str(BASE));scene=bpy.data.scenes['00_CAMPUS_COMPLETE'];bpy.context.window.scene=scene
previous=json.loads((OUT/'audit.json').read_text()) if (OUT/'audit.json').exists() else None
if previous:
 for name in previous['ownedObjects']:
  obj=bpy.data.objects.get(name)
  if obj:
   mesh=obj.data;bpy.data.objects.remove(obj,do_unlink=True);mesh.use_fake_user=False
   if not mesh.users:bpy.data.meshes.remove(mesh)
 for name in previous['archivedObjects']:
  if name in bpy.data.objects:
   obj=bpy.data.objects[name];state=previous['originalVisibility'][name];obj.hide_render,obj.hide_viewport=state[:2];obj.hide_set(state[2])
for layer in scene.view_layers:layer.update()
def fingerprint(obj):
 digest=hashlib.sha256(str([list(row) for row in obj.matrix_world]).encode())
 if obj.type=='MESH':
  for data,field,kind,count in ((obj.data.vertices,'co','f',3),(obj.data.loops,'vertex_index','i',1),(obj.data.polygons,'material_index','i',1)):
   values=array.array(kind,[0])*(len(data)*count);data.foreach_get(field,values);digest.update(values.tobytes())
  for layer in obj.data.uv_layers:
   values=array.array('f',[0])*(len(layer.data)*2);layer.data.foreach_get('uv',values);digest.update(values.tobytes())
 digest.update(str([m.name if m else None for m in getattr(obj.data,'materials',[])]).encode());return digest.hexdigest()
originals={obj.name:fingerprint(obj) for obj in bpy.data.objects};visibility={obj.name:[obj.hide_render,obj.hide_viewport,obj.hide_get()] for obj in bpy.data.objects}
collection=bpy.data.collections['SAL_EXTERIOR'];source=bpy.data.objects['SAL_Central_door_recess'];assert not source.hide_render
angle=math.radians(24.35);u=Vector((-math.cos(angle),-math.sin(angle),0));n=Vector((-math.sin(angle),math.cos(angle),0));vs=[source.matrix_world@v.co for v in source.data.vertices]
xc=(min(v.dot(u) for v in vs)+max(v.dot(u) for v in vs))/2;half=(max(v.dot(u) for v in vs)-min(v.dot(u) for v in vs))/2;floor=min(v.z for v in vs)
# The frame and column registration remain native. Arc radius/spring line are
# photographic estimates constrained beneath the retained stone entablature.
radius=1.48;spring=2.80;top=4.53;steps=48
sys.path.insert(0,str(Path(__file__).resolve().parent));from facade_geometry import Geometry,materials
materials.clear();materials['dark']=source.data.materials[0];materials['stone']=bpy.data.materials['SAL_Cut_stone_edges']
batches={key:Geometry('SAL','entrance_arch_'+key,key) for key in materials}
def prism(key,outline,d0,d1):
 points=[u*(xc+x)+n*d+Vector((0,0,z)) for d in (d0,d1) for x,z in outline];k=len(outline)
 batches[key].add(points,[tuple(reversed(range(k))),tuple(range(k,2*k))]+[(i,(i+1)%k,(i+1)%k+k,i+k) for i in range(k)])
# Arched dark recess replaces the rectangular black placeholder. The new
# backplate covers the previous generic sash still stored behind this entrance.
outline=[(-radius,floor),(radius,floor),(radius,spring)]+[(radius*math.cos(i*math.pi/steps),spring+radius*math.sin(i*math.pi/steps)) for i in range(1,steps+1)]
prism('dark',outline,62.32,62.42)
# Continuous masonry outside the real semicircular boundary, not a flat arch
# decal. Each curved return has its own solid thickness, with no invented carving.
prism('stone',[(-half,floor),(-radius,floor),(-radius,spring),(-half,spring)],62.40,62.67)
prism('stone',[(radius,floor),(half,floor),(half,spring),(radius,spring)],62.40,62.67)
for i in range(steps):
 a0,a1=i*math.pi/steps,(i+1)*math.pi/steps;x0,x1=radius*math.cos(a0),radius*math.cos(a1);z0,z1=spring+radius*math.sin(a0),spring+radius*math.sin(a1)
 prism('stone',[(x0,z0),(x0,top),(x1,top),(x1,z1)],62.40,62.67)
# Fill the small outside shoulders up to the old opening boundary.
for sign in (-1,1):prism('stone',[(sign*radius,spring),(sign*half,spring),(sign*half,top),(sign*radius,top)],62.40,62.67)
owned=[]
for key,batch in batches.items():
 obj=batch.finish();obj.name='SAL_NEXT_historical_entrance_'+key;obj.data.name=obj.name
 for modifier in list(obj.modifiers):obj.modifiers.remove(modifier)
 bm=bmesh.new();bm.from_mesh(obj.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(obj.data);bm.free();owned.append(obj)
source.hide_render=True;source.hide_set(True)
assert all(fingerprint(bpy.data.objects[name])==v for name,v in originals.items())
def probes(objects):
 vertices=[];faces=[];owners=[]
 for obj in objects:
  start=len(vertices);vertices.extend(obj.matrix_world@v.co for v in obj.data.vertices);faces.extend(tuple(start+i for i in face.vertices) for face in obj.data.polygons);owners.extend([obj.name]*len(obj.data.polygons))
 tree=BVHTree.FromPolygons(vertices,faces);results=[]
 for i in range(1,16):
  a=i*math.pi/16;x=radius*math.cos(a);z=spring+radius*math.sin(a)
  for delta,expected in ((-.07,'dark'),(.07,'stone')):
   p=u*(xc+x)+n*63.1+Vector((0,0,z+delta));hit=tree.ray_cast(p,-n,1)
   name=owners[hit[2]] if hit[2] is not None else None
   assert name=='SAL_NEXT_historical_entrance_'+expected,(i,delta,name)
   results.append({'angleIndex':i,'heightOffset':delta,'firstSurface':name})
 return results
boundary=probes([obj for obj in collection.all_objects if obj.type=='MESH' and not obj.hide_render]);component=OUT/'sir-arthur-lewis-component.blend';bpy.data.libraries.write(str(component),set(owned),fake_user=True,compress=True)
index=json.loads((ROOT/'data/建筑图片/SAL_Sir Arthur Lewis Building/图片索引.json').read_text());record=next(r for r in index['images'] if r['file'].endswith('SAL_d0d696021ed0.jpg'));reference=ROOT/'data/建筑图片/SAL_Sir Arthur Lewis Building'/record['file'];assert hashlib.sha256(reference.read_bytes()).hexdigest()==record['sha256']
audit={'baselineSha256':hashlib.sha256(BASE.read_bytes()).hexdigest(),'originalFingerprints':originals,'originalVisibility':visibility,'ownedObjects':[obj.name for obj in owned],'archivedObjects':[source.name],'sources':[{'local':str(reference.relative_to(ROOT)),'sha256':record['sha256'],'sources':record['sources']}],'scope':'Historical central entrance only: actual semicircular stone aperture and dark arched recess; generic door-window behind the new opaque backplate is retained without changing its geometry','geometry':{'centerAxis':xc,'retainedHalfWidth':half,'estimatedArchRadius':radius,'estimatedSpringHeight':spring,'retainedEntablatureBottom':top,'recessDepth':[62.32,62.42],'stoneReturnDepth':[62.40,62.67]},'archBoundaryProbes':boundary,'limitations':['Arch existence is clearly visible in architect photograph; dimensions and return thickness are estimates','Existing doorway registration, columns, entablature and paving retained; no carved ornament invented','Dark historical door detail is not resolved in the photograph; no glass-door or leaf-panel inference added','Roof rear elevations, full flank opening counts and interiors remain unresolved; no claim of complete building accuracy']}
(OUT/'audit.json').write_text(json.dumps(audit,indent=2)+'\n');print('SAL_COMPONENT_SAVED',component.stat().st_size,flush=True)
bpy.ops.wm.open_mainfile(filepath=str(BASE));scene=bpy.data.scenes['00_CAMPUS_COMPLETE'];bpy.context.window.scene=scene
for layer in scene.view_layers:layer.update()
with bpy.data.libraries.load(str(component),link=False) as (src,dst):dst.objects=audit['ownedObjects']
collection=bpy.data.collections['SAL_EXTERIOR'];owned=dst.objects
for obj in owned:
 collection.objects.link(obj)
 for i,mat in enumerate(list(obj.data.materials)):
  original=bpy.data.materials.get(mat.name.rsplit('.',1)[0]) if mat.name[-4:-3]=='.' else mat
  if original:obj.data.materials[i]=original
for name in audit['archivedObjects']:bpy.data.objects[name].hide_render=True;bpy.data.objects[name].hide_set(True)
assert all(fingerprint(bpy.data.objects[name])==v for name,v in originals.items());boundary=probes([obj for obj in collection.all_objects if obj.type=='MESH' and not obj.hide_render])
names={o.name for o in collection.all_objects}
for obj in scene.objects:
 if obj.type=='MESH' and obj.name not in names:obj.hide_render=True
focus=u*xc+n*62.5+Vector((0,0,2.65));camdata=bpy.data.cameras.new('SAL_NEXT_preview_camera');cam=bpy.data.objects.new(camdata.name,camdata);scene.collection.objects.link(cam);cam.location=focus+n*13+u*1.8+Vector((0,0,1));cam.rotation_euler=(focus-cam.location).to_track_quat('-Z','Y').to_euler();camdata.type='ORTHO';camdata.ortho_scale=7;scene.camera=cam
scene.render.engine='BLENDER_EEVEE';scene.render.resolution_x=1000;scene.render.resolution_y=1050;scene.render.resolution_percentage=100;scene.render.filepath=str(OUT/'reloaded-entrance.png');bpy.ops.render.render(write_still=True)
verification={'componentSha256':hashlib.sha256(component.read_bytes()).hexdigest(),'baselineUnchanged':hashlib.sha256(BASE.read_bytes()).hexdigest()==audit['baselineSha256'],'savedComponentReopened':True,'originalGeometryPreserved':True,'archBoundaryProbes':len(boundary),'nativeRender':'reloaded-entrance.png'}
(OUT/'verification.json').write_text(json.dumps(verification,indent=2)+'\n');print('SAL_COMPONENT_RELOADED_VERIFIED',flush=True)
