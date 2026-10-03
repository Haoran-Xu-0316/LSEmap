"""Restore photographed four-column OLD roof casements without moving openings.
Run in Blender Text Editor. Only the ten clearly photographed dormers change;
the two far-left openings and every measured/estimated roof datum are retained.
"""
from pathlib import Path
import array,hashlib,json,math,sys
import bpy,bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'result/blender/old_mansard_next';OUT.mkdir(parents=True,exist_ok=True)
BASE=ROOT/'result/blender/LSE_campus_detailed_v124.blend'
if not BASE.exists():BASE=max((ROOT/'result/blender').glob('LSE_campus_detailed_v[0-9]*.blend'),key=lambda p:int(p.stem.rsplit('v',1)[1]))
bpy.ops.wm.open_mainfile(filepath=str(BASE));scene=bpy.data.scenes['00_CAMPUS_COMPLETE'];bpy.context.window.scene=scene
for layer in scene.view_layers:layer.update()
previous=json.loads((OUT/'audit.json').read_text())if (OUT/'audit.json').exists()else None
if previous:
 for name in previous['ownedObjects']:
  obj=bpy.data.objects.get(name)
  if obj:
   mesh=obj.data;bpy.data.objects.remove(obj,do_unlink=True)
   if not mesh.users:bpy.data.meshes.remove(mesh)
 for name in previous['archivedObjects']:
  obj=bpy.data.objects[name];state=previous['originalVisibility'][name];obj.hide_render,obj.hide_viewport=state[:2];obj.hide_set(state[2])
def fingerprint(obj):
 h=hashlib.sha256(str([list(row)for row in obj.matrix_world]).encode())
 if obj.type=='MESH':
  for data,field,kind,count in ((obj.data.vertices,'co','f',3),(obj.data.loops,'vertex_index','i',1),(obj.data.polygons,'material_index','i',1)):
   values=array.array(kind,[0])*(len(data)*count);data.foreach_get(field,values);h.update(values.tobytes())
  for layer in obj.data.uv_layers:
   values=array.array('f',[0])*(len(layer.data)*2);layer.data.foreach_get('uv',values);h.update(values.tobytes())
 h.update(str([m.name if m else None for m in getattr(obj.data,'materials',[])]).encode());return h.hexdigest()
originals={obj.name:fingerprint(obj)for obj in bpy.data.objects};visibility={obj.name:[obj.hide_render,obj.hide_viewport,obj.hide_get()]for obj in bpy.data.objects}
frame=json.loads((ROOT/'result/blender/stage52/old-houghton-audit.json').read_text());origin,right,normal=[Vector(frame[k])for k in ('origin','right','outward')]
def point(x,d,z):return origin+right*x+normal*d+Vector((0,0,z))
def local(p):
 d=p-origin;return Vector((d.dot(right),d.dot(normal),d.z))
collection=bpy.data.collections['OLD_EXTERIOR'];source=bpy.data.objects['OLD_D5_houghton112_mansard_blue'];glass=bpy.data.objects['OLD_D5_houghton112_mansard_glass']
assert not source.hide_render and len(glass.data.vertices)==96
windows=[]
for start in range(0,len(glass.data.vertices),8):
 pts=[local(glass.matrix_world@v.co)for v in glass.data.vertices[start:start+8]];lo=[min(p[i]for p in pts)for i in range(3)];hi=[max(p[i]for p in pts)for i in range(3)]
 windows.append({'index':start//8,'x':(lo[0]+hi[0])/2,'d':(lo[1]+hi[1])/2,'z':(lo[2]+hi[2])/2,'width':hi[0]-lo[0],'height':hi[2]-lo[2],'rows':4 if start//8<6 else 5,'columns':4,'photoSupported':start//8%6!=0})
selected=[w for w in windows if w['photoSupported']];assert len(selected)==10
retained=source.copy();retained.data=source.data.copy();retained.name='OLD_NEXT_mansard_retained_blue';collection.objects.link(retained)
bm=bmesh.new();bm.from_mesh(retained.data);seen=set();delete=[];removed=0
for vertex in bm.verts:
 if vertex in seen:continue
 stack=[vertex];seen.add(vertex);part=[]
 while stack:
  v=stack.pop();part.append(v)
  for edge in v.link_edges:
   other=edge.other_vert(v)
   if other not in seen:seen.add(other);stack.append(other)
 pts=[local(retained.matrix_world@v.co)for v in part];lo=[min(p[i]for p in pts)for i in range(3)];hi=[max(p[i]for p in pts)for i in range(3)];x=(lo[0]+hi[0])/2;z=(lo[2]+hi[2])/2
 for w in selected:
  if abs((lo[1]+hi[1])/2-w['d']-.075)>.04:continue
  if (abs(x-w['x'])<.01 and hi[0]-lo[0]<.08 and abs(z-w['z'])<.01)or(abs(z-w['z'])<.01 and hi[2]-lo[2]<.08 and abs(x-w['x'])<.01):
   delete.extend(part);removed+=1;break
assert removed==20,removed
bmesh.ops.delete(bm,geom=delete,context='VERTS');bm.to_mesh(retained.data);bm.free();retained.data.update()
sys.path.insert(0,str(Path(__file__).resolve().parent));from facade_geometry import Geometry,materials
materials.clear();materials['blue']=source.data.materials[0];bars=Geometry('OLD','mansard_next_casements','blue');members=[];angle=math.atan2(right.y,right.x)
for w in selected:
 for fraction,width in [(-.25,.025),(0,.048),(.25,.025)]:
  x=w['x']+fraction*w['width'];size=(width,.08,w['height']-.08);bars.box(point(x,w['d']+.075,w['z']),size,angle);members.append({'window':w['index'],'axis':'vertical','fraction':fraction,'size':size})
 for j in range(1,w['rows']):
  fraction=j/w['rows'];z=w['z']-w['height']/2+w['height']*fraction;heavy=.75 if w['rows']==4 else .6;size=(w['width']-.08,.08,.065 if abs(fraction-heavy)<1e-6 else .025)
  bars.box(point(w['x'],w['d']+.075,z),size,angle);members.append({'window':w['index'],'axis':'horizontal','fraction':fraction,'size':size})
new=bars.finish();new.name='OLD_NEXT_mansard_four_column_blue'
for modifier in list(new.modifiers):new.modifiers.remove(modifier)
assert len(members)==65
source.hide_render=True;source.hide_set(True)
def probes():
 vertices=[];faces=[];owners=[]
 for obj in collection.all_objects:
  if obj.type!='MESH'or obj.hide_render:continue
  offset=len(vertices);vertices.extend(obj.matrix_world@v.co for v in obj.data.vertices)
  for poly in obj.data.polygons:faces.append(tuple(offset+i for i in poly.vertices));owners.append(obj.name)
 tree=BVHTree.FromPolygons(vertices,faces);results=[]
 for w in selected:
  for xfraction in (-.125,.125):
   p=point(w['x']+xfraction*w['width'],w['d']+.65,w['z']+.07*w['height']);hit=tree.ray_cast(p,-normal,1);name=owners[hit[2]]if hit[2]is not None else None
   assert name==glass.name,(w['index'],xfraction,name)
   results.append({'window':w['index'],'columnOffset':xfraction,'firstSurface':name})
 return results
clearance=probes();assert all(fingerprint(bpy.data.objects[k])==v for k,v in originals.items())
component=OUT/'old-mansard-component.blend';owned=[retained,new];bpy.data.libraries.write(str(component),set(owned),fake_user=True,compress=True)
ref=ROOT/'data/collections/campus_photos_round2/images/OLD/OLD_old_webbyates_06.jpg'
audit={'baselineSha256':hashlib.sha256(BASE.read_bytes()).hexdigest(),'originalFingerprints':originals,'originalVisibility':visibility,'ownedObjects':[o.name for o in owned],'archivedObjects':[source.name],'windows':windows,'members':members,'removedInnerMembers':removed,'glassFirstSurfaceProbes':clearance,'sources':[{'local':str(ref.relative_to(ROOT)),'sha256':hashlib.sha256(ref.read_bytes()).hexdigest(),'url':'https://webbyates.com/projects/the-old-building/','projectCompletion':2024,'captureDate':'unknown'}],'limitations':['Only ten front dormers clearly visible in the full engineer photograph adopt four columns and photographed row hierarchy','Two far-left windows retain existing divisions because the adjoining silhouette prevents unambiguous photographic attribution','All window openings, heights, roof contours, materials and unseen elevations retained as prior estimates','This is a joinery correction, not a surveyed roof or complete OLD interior reconstruction']}
(OUT/'audit.json').write_text(json.dumps(audit,indent=2)+'\n')
bpy.ops.wm.open_mainfile(filepath=str(BASE));scene=bpy.data.scenes['00_CAMPUS_COMPLETE'];bpy.context.window.scene=scene
for layer in scene.view_layers:layer.update()
collection=bpy.data.collections['OLD_EXTERIOR'];source=bpy.data.objects[audit['archivedObjects'][0]];glass=bpy.data.objects['OLD_D5_houghton112_mansard_glass']
with bpy.data.libraries.load(str(component),link=False)as(src,dst):dst.objects=audit['ownedObjects']
for obj in dst.objects:
 collection.objects.link(obj);obj.data.materials[0]=source.data.materials[0]
source.hide_render=True;source.hide_set(True)
assert all(fingerprint(bpy.data.objects[k])==v for k,v in originals.items());reloaded=probes()
names={o.name for o in collection.all_objects}
for obj in scene.objects:
 if obj.type=='MESH'and obj.name not in names:obj.hide_render=True
focus=point(sum(w['x']for w in selected)/10,-1.7,23.8);camera_data=bpy.data.cameras.new('OLD_NEXT_preview_camera');camera=bpy.data.objects.new(camera_data.name,camera_data);scene.collection.objects.link(camera);camera.location=focus+normal*24+Vector((0,0,1));camera.rotation_euler=(focus-camera.location).to_track_quat('-Z','Y').to_euler();camera_data.type='ORTHO';camera_data.ortho_scale=17;scene.camera=camera
scene.render.engine='BLENDER_EEVEE';scene.render.resolution_x=1400;scene.render.resolution_y=850;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG';scene.render.filepath=str(OUT/'reloaded-casements.png');bpy.ops.render.render(write_still=True)
verification={'componentSha256':hashlib.sha256(component.read_bytes()).hexdigest(),'baselineUnchanged':hashlib.sha256(BASE.read_bytes()).hexdigest()==audit['baselineSha256'],'savedComponentReopened':True,'originalGeometryPreserved':True,'correctedPhotographedWindows':10,'retainedUnclearWindows':2,'newInnerMembers':65,'glassFirstSurfaceProbes':len(reloaded),'nativeRender':'reloaded-casements.png'}
(OUT/'verification.json').write_text(json.dumps(verification,indent=2)+'\n');print('OLD_MANSARD_COMPONENT_RELOADED',len(members),len(reloaded),flush=True)
