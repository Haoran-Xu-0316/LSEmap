"""Cut real openings through St Clement's photographed setback attic.

Run in Blender's Text Editor. Derive every bay, wall and opening from the
current native model; retain the photographed street massing and materials.
Attic depths and all existing unmeasured dimensions remain estimates.
"""
from pathlib import Path
import array, hashlib, json, math, sys
import bpy, bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'result/blender/stc_next';OUT.mkdir(parents=True,exist_ok=True)
BASE=ROOT/'result/blender/LSE_campus_detailed_v122.blend'
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
collection=bpy.data.collections['STC_EXTERIOR']
source=bpy.data.objects['STC_D5_top_floor_backwall_terracotta'];glass=bpy.data.objects['STC_D5_attic_glass_glass']
assert not source.hide_render and not glass.hide_render
# Original families contain independent eight-vertex metric cuboids. Read
# their actual geometry instead of reconstructing a historical stage profile.
def cuboids(obj):
 assert len(obj.data.vertices)%8==0
 return [[obj.matrix_world@v.co for v in obj.data.vertices[i:i+8]] for i in range(0,len(obj.data.vertices),8)]
walls=[]
for vertices in cuboids(source):
 u=(vertices[4]-vertices[0]).normalized();n=(vertices[2]-vertices[0]).normalized()
 assert abs(u.z)<1e-6 and abs(n.z)<1e-6
 walls.append({'u':u,'n':n,'x0':min(v.dot(u) for v in vertices),'x1':max(v.dot(u) for v in vertices),'d0':min(v.dot(n) for v in vertices),'d1':max(v.dot(n) for v in vertices),'z0':min(v.z for v in vertices),'z1':max(v.z for v in vertices),'openings':[]})
windows=[]
for vertices in cuboids(glass):
 candidates=[]
 for index,wall in enumerate(walls):
  x0,x1=min(v.dot(wall['u']) for v in vertices),max(v.dot(wall['u']) for v in vertices)
  d=sum(v.dot(wall['n']) for v in vertices)/8
  if x0>=wall['x0']-.001 and x1<=wall['x1']+.001 and abs(d-wall['d1'])<.20:
   candidates.append((abs(d-wall['d1']),index,x0,x1))
 assert candidates
 _,index,x0,x1=min(candidates);wall=walls[index]
 opening={'x0':x0-.006,'x1':x1+.006,'z0':min(v.z for v in vertices)-.006,'z1':max(v.z for v in vertices)+.006,'center':sum(vertices,Vector())/8,'normal':wall['n'],'wallIndex':index}
 wall['openings'].append(opening);windows.append(opening)
assert len(walls)==7 and len(windows)==35
sys.path.insert(0,str(Path(__file__).resolve().parent));from facade_geometry import Geometry,materials
materials.clear();materials['terracotta']=source.data.materials[0];batch=Geometry('STC','attic_aperture_walls','terracotta')
def box(wall,left,right,bottom,top):
 if right-left<1e-7 or top-bottom<1e-7:return
 u,n=wall['u'],wall['n'];d0,d1=wall['d0'],wall['d1']
 vertices=[u*x+n*d+Vector((0,0,z)) for x,d,z in ((left,d0,bottom),(left,d0,top),(left,d1,bottom),(left,d1,top),(right,d0,bottom),(right,d0,top),(right,d1,bottom),(right,d1,top))]
 batch.add(vertices,[(0,4,6,2),(1,3,7,5),(0,1,5,4),(2,6,7,3),(0,2,3,1),(4,5,7,6)])
for wall in walls:
 openings=sorted(wall['openings'],key=lambda v:v['x0']);cursor=wall['x0']
 for opening in openings:
  assert opening['x0']>=cursor-.001
  box(wall,cursor,opening['x0'],wall['z0'],wall['z1'])
  box(wall,opening['x0'],opening['x1'],wall['z0'],opening['z0'])
  box(wall,opening['x0'],opening['x1'],opening['z1'],wall['z1'])
  cursor=opening['x1']
 box(wall,cursor,wall['x1'],wall['z0'],wall['z1'])
owned=batch.finish();owned.name='STC_NEXT_attic_opening_walls';owned.data.name=owned.name
for modifier in list(owned.modifiers):owned.modifiers.remove(modifier)
bm=bmesh.new();bm.from_mesh(owned.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(owned.data);bm.free()
assert all(math.isfinite(c) for vertex in owned.data.vertices for c in vertex.co)
assert all(poly.area>1e-10 for poly in owned.data.polygons)
def ray_tree(objects):
 vertices=[];faces=[];owners=[]
 for obj in objects:
  start=len(vertices);vertices.extend(obj.matrix_world@v.co for v in obj.data.vertices)
  faces.extend(tuple(start+i for i in p.vertices) for p in obj.data.polygons);owners.extend([obj.name]*len(obj.data.polygons))
 return BVHTree.FromPolygons(vertices,faces),owners
def probes(objects):
 tree,names=ray_tree(objects);results=[]
 for index,window in enumerate(windows):
  wall=walls[window['wallIndex']];u,n=wall['u'],wall['n'];x=(window['x0']+window['x1'])/2
  # Test both lights away from mullions, within the actual wall thickness.
  for side in (-1,1):
   point=u*(x+side*(window['x1']-window['x0'])*.22)+n*(wall['d1']+.02)+Vector((0,0,(window['z0']+window['z1'])/2))
   hit=tree.ray_cast(point,-n,wall['d1']-wall['d0']+.04)
   results.append({'window':index,'side':side,'opaqueHit':names[hit[2]] if hit[2] is not None else None})
 return results
def opaque_objects(exclude=()):
 return [obj for obj in collection.all_objects if obj.type=='MESH' and not obj.hide_render and obj not in exclude and 'glass' not in obj.name.lower()]
before=probes(opaque_objects((owned,)));assert all(p['opaqueHit']==source.name for p in before)
source.hide_render=True;source.hide_set(True)
after=probes(opaque_objects());assert all(p['opaqueHit'] is None for p in after)
assert all(fingerprint(bpy.data.objects[n])==v for n,v in originals.items())
component=OUT/'stc-attic-component.blend';bpy.data.libraries.write(str(component),{owned},fake_user=True,compress=True)
index=json.loads((ROOT/'data/建筑图片/STC_St Clement_s/图片索引.json').read_text())
records=[]
for record in index['images']:
 if record['file'].endswith('campus_photos_round2_STC_geograph_7222785_01.jpg'):
  assert hashlib.sha256((ROOT/'data/建筑图片/STC_St Clement_s'/record['file']).read_bytes()).hexdigest()==record['sha256']
  records.append({'local':'data/建筑图片/STC_St Clement_s/'+record['file'],'sha256':record['sha256'],'sources':record['sources']})
audit={'baselineSha256':hashlib.sha256(BASE.read_bytes()).hexdigest(),'originalFingerprints':originals,'originalVisibility':visibility,'ownedObjects':[owned.name],'archivedObjects':[source.name],'sources':records,'atticWindowsRetained':35,'wallSegments':7,'opaqueBeforeProbes':before,'clearAfterProbes':after,'limitations':['Street image supports setback storey with ribbon glazing; existing bay counts and dimensions retained rather than claimed surveyed','Unseen back wall and chamfer retain original solid geometry','Roof footprint, coping, height, murals, ground entrance and interiors unchanged','Only actual attic apertures corrected; no claim of full exterior accuracy']}
(OUT/'audit.json').write_text(json.dumps(audit,indent=2)+'\n');print('STC_COMPONENT_SAVED',component.stat().st_size,flush=True)
bpy.ops.wm.open_mainfile(filepath=str(BASE));scene=bpy.data.scenes['00_CAMPUS_COMPLETE'];bpy.context.window.scene=scene
with bpy.data.libraries.load(str(component),link=False) as (src,dst):dst.objects=audit['ownedObjects']
collection=bpy.data.collections['STC_EXTERIOR'];owned=dst.objects[0];collection.objects.link(owned)
# Remap imported material onto unchanged native ID, preventing suffix drift.
owned.data.materials[0]=bpy.data.objects[audit['archivedObjects'][0]].data.materials[0]
for name in audit['archivedObjects']:bpy.data.objects[name].hide_render=True;bpy.data.objects[name].hide_set(True)
assert all(fingerprint(bpy.data.objects[n])==v for n,v in originals.items())
after=probes(opaque_objects());assert all(p['opaqueHit'] is None for p in after)
for obj in scene.objects:
 if obj.type=='MESH' and obj.name not in {o.name for o in collection.all_objects}:obj.hide_render=True
corner=sum((window['center'] for window in windows),Vector())/len(windows)
# Show long street facade and setback glazing in one actual native view.
front=max(walls,key=lambda w:len(w['openings']));focus=front['u']*((front['x0']+front['x1'])/2)+front['n']*front['d1']+Vector((0,0,17.8))
camdata=bpy.data.cameras.new('STC_NEXT_preview_camera');cam=bpy.data.objects.new(camdata.name,camdata);scene.collection.objects.link(cam)
cam.location=focus+front['n']*35-front['u']*8+Vector((0,0,4));cam.rotation_euler=(focus-cam.location).to_track_quat('-Z','Y').to_euler();camdata.type='ORTHO';camdata.ortho_scale=front['x1']-front['x0']+2;scene.camera=cam
scene.render.engine='BLENDER_EEVEE';scene.render.resolution_x=1400;scene.render.resolution_y=600;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG';scene.render.filepath=str(OUT/'reloaded-attic.png');bpy.ops.render.render(write_still=True)
verification={'componentSha256':hashlib.sha256(component.read_bytes()).hexdigest(),'baselineUnchanged':hashlib.sha256(BASE.read_bytes()).hexdigest()==audit['baselineSha256'],'savedComponentReopened':True,'originalGeometryPreserved':True,'blockedBeforeProbes':len(before),'clearAfterProbes':len(after),'nativeRender':'reloaded-attic.png'}
(OUT/'verification.json').write_text(json.dumps(verification,indent=2)+'\n');print('STC_COMPONENT_RELOADED_VERIFIED',flush=True)
