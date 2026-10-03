"""Open CKK's photographed dormer windows through the solid mansard volume.

Run in Blender's Text Editor. Derive every bay, wall and opening from the
current native model; retain all existing roof datums and materials.
Attic depths and all existing unmeasured dimensions remain estimates.
"""
from pathlib import Path
import array, hashlib, json, math, sys
import bpy, bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'result/blender/ckk_next';OUT.mkdir(parents=True,exist_ok=True)
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
   obj=bpy.data.objects[name];state=previous['originalVisibility'][name]
   obj.hide_render,obj.hide_viewport=state[:2];obj.hide_set(state[2])
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
collection=bpy.data.collections['CKK_EXTERIOR'];source=bpy.data.objects['CKK_V32_front_mansard'];glass=bpy.data.objects['CKK_V32_dormer_glazing']
centre=Vector((-110.49102024587766,77.56014819690478,0));angle=math.radians(22);u=Vector((math.cos(angle),math.sin(angle),0));n=Vector((-math.sin(angle),math.cos(angle),0))
def local(p):
 p=p-centre;return Vector((p.dot(u),p.dot(n),p.z))
def world(p):return centre+u*p[0]+n*p[1]+Vector((0,0,p[2]))
windows=[]
for i in range(0,len(glass.data.vertices),8):
 pts=[local(glass.matrix_world@v.co) for v in glass.data.vertices[i:i+8]]
 windows.append({'y0':min(p.y for p in pts),'y1':max(p.y for p in pts),'z0':min(p.z for p in pts),'z1':max(p.z for p in pts),'x':sum(p.x for p in pts)/8})
assert len(windows)==18
verts=[];faces=[]
def piece(y0,y1,z0,z1):
 if y1-y0<1e-6 or z1-z0<1e-6:return
 x0=14.5;front=lambda z:22-(z-25)*4/7
 ps=[(x0,y0,z0),(x0,y0,z1),(x0,y1,z0),(x0,y1,z1),(front(z0),y0,z0),(front(z1),y0,z1),(front(z0),y1,z0),(front(z1),y1,z1)]
 offset=len(verts);verts.extend(world(p) for p in ps);faces.extend(tuple(offset+i for i in f) for f in ((0,2,6,4),(1,5,7,3),(0,4,5,1),(2,3,7,6),(0,1,3,2),(4,6,7,5)))
edges=sorted({-16.1,16.1,*[w[k] for w in windows for k in ('y0','y1')]})
for left,right in zip(edges,edges[1:]):
 openings=sorted([w for w in windows if w['y0']-1e-5<=(left+right)/2<=w['y1']+1e-5],key=lambda w:w['z0']);cursor=25
 for w in openings:piece(left,right,cursor,w['z0']);cursor=w['z1']
 piece(left,right,cursor,32)
mesh=bpy.data.meshes.new('CKK_NEXT_mansard_openings');mesh.from_pydata(verts,[],faces);mesh.materials.append(source.data.materials[0]);mesh.update()
owned=bpy.data.objects.new(mesh.name,mesh);collection.objects.link(owned)
bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free()
# Use the same metric face projection as the preserved source mansard.
uv=mesh.uv_layers.new(name='SurfaceUV')
for face in mesh.polygons:
 normal=face.normal.normalized();axis=Vector((0,0,1)).cross(normal)
 if axis.length<1e-6:axis=Vector((1,0,0))
 axis.normalize();vertical=normal.cross(axis).normalized()
 for loop in face.loop_indices:
  point=mesh.vertices[mesh.loops[loop].vertex_index].co;uv.data[loop].uv=(point.dot(axis),point.dot(vertical))
from mathutils.bvhtree import BVHTree
def roof_probes(obj):
 tree=BVHTree.FromPolygons([obj.matrix_world@v.co for v in obj.data.vertices],[list(p.vertices) for p in obj.data.polygons]);results=[]
 for i,w in enumerate(windows):
  for side in (-1,1):
   origin=world((w['x']+.03,(w['y0']+w['y1'])/2+side*(w['y1']-w['y0'])*.25,(w['z0']+w['z1'])/2));hit=tree.ray_cast(origin,-u,9)
   results.append({'window':i,'side':side,'opaqueRoofHit':hit[2] is not None})
 return results
before=roof_probes(source);after=roof_probes(owned);assert all(p['opaqueRoofHit'] for p in before);assert all(not p['opaqueRoofHit'] for p in after)
source.hide_render=True;source.hide_set(True);assert all(fingerprint(bpy.data.objects[k])==v for k,v in originals.items())
component=OUT/'cheng-kin-ku-component.blend';bpy.data.libraries.write(str(component),{owned},fake_user=True,compress=True)
ref=ROOT/'data/建筑图片/CKK_Cheng Kin Ku Building/01_建筑实拍/library_round5_library_round5_CKK_8f06506667f1.jpg'
audit={'baselineSha256':hashlib.sha256(BASE.read_bytes()).hexdigest(),'originalFingerprints':originals,'originalVisibility':visibility,'ownedObjects':[owned.name],'archivedObjects':[source.name],'sources':[{'local':str(ref.relative_to(ROOT)),'sha256':hashlib.sha256(ref.read_bytes()).hexdigest(),'url':'https://www.willebrand.com/en/projects/lse-london-school-of-economics-grimshaw-architects.398','captureDate':'unknown; historical project photograph'}],'opaqueBeforeProbes':before,'clearAfterProbes':after,'limitations':['Photograph confirms two dormer rows and real glazing; existing 18 windows, positions, 25m roof base and 32m top retained as estimates','Only solid mansard volume behind glass replaced by actual openings; roof silhouette, materials, frames, cheek returns and roof caps retained','Other elevations, current cafe layout and interiors remain incomplete; no claim of full exterior accuracy']}
(OUT/'audit.json').write_text(json.dumps(audit,indent=2)+'\n');print('CKK_COMPONENT_SAVED',component.stat().st_size,flush=True)
bpy.ops.wm.open_mainfile(filepath=str(BASE));scene=bpy.data.scenes['00_CAMPUS_COMPLETE'];bpy.context.window.scene=scene
with bpy.data.libraries.load(str(component),link=False) as (src,dst):dst.objects=audit['ownedObjects']
owned=dst.objects[0];collection=bpy.data.collections['CKK_EXTERIOR'];collection.objects.link(owned);source=bpy.data.objects[audit['archivedObjects'][0]];owned.data.materials[0]=source.data.materials[0];source.hide_render=True;source.hide_set(True)
assert all(fingerprint(bpy.data.objects[k])==v for k,v in originals.items());assert all(not p['opaqueRoofHit'] for p in roof_probes(owned))
for obj in scene.objects:
 if obj.type=='MESH' and obj.name not in {o.name for o in collection.all_objects}:obj.hide_render=True
focus=world((20,0,27));camdata=bpy.data.cameras.new('CKK_NEXT_preview_camera');cam=bpy.data.objects.new(camdata.name,camdata);scene.collection.objects.link(cam);cam.location=focus+u*44+n*10+Vector((0,0,10));cam.rotation_euler=(focus-cam.location).to_track_quat('-Z','Y').to_euler();camdata.type='ORTHO';camdata.ortho_scale=38;scene.camera=cam
scene.render.engine='BLENDER_EEVEE';scene.render.resolution_x=1400;scene.render.resolution_y=700;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG';scene.render.filepath=str(OUT/'reloaded-mansard.png');bpy.ops.render.render(write_still=True)
verification={'componentSha256':hashlib.sha256(component.read_bytes()).hexdigest(),'baselineUnchanged':hashlib.sha256(BASE.read_bytes()).hexdigest()==audit['baselineSha256'],'savedComponentReopened':True,'originalGeometryPreserved':True,'blockedBeforeProbes':len(before),'clearAfterProbes':len(after),'nativeRender':'reloaded-mansard.png'}
(OUT/'verification.json').write_text(json.dumps(verification,indent=2)+'\n');print('CKK_COMPONENT_RELOADED_VERIFIED',flush=True)
