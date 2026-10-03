"""Correct CKK wing middle-window widths and single-light flanking windows.

Run in Blender's Text Editor. Only three photographed storeys are corrected; native dimensions are estimates.
"""
from pathlib import Path
import array, hashlib, json, sys, math
import bpy, bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'result/blender/ckk_wing_next'
OUT.mkdir(parents=True,exist_ok=True)
BASE = ROOT/'result/blender/LSE_campus_detailed_v125.blend'
if not BASE.exists():
    BASE = max((ROOT/'result/blender').glob('LSE_campus_detailed_v[0-9]*.blend'),key=lambda p:int(p.stem.rsplit('v',1)[1]))
bpy.ops.wm.open_mainfile(filepath=str(BASE))
bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE']
previous=json.loads((OUT/'audit.json').read_text()) if (OUT/'audit.json').exists() else None
if previous:
    for name in previous['ownedObjects']:
        obj=bpy.data.objects.get(name)
        if obj:
            mesh=obj.data;bpy.data.objects.remove(obj,do_unlink=True);mesh.use_fake_user=False
            if not mesh.users:bpy.data.meshes.remove(mesh)
    for name in previous['archivedObjects']:
        obj=bpy.data.objects[name];state=previous['originalVisibility'][name]
        obj.hide_render,obj.hide_viewport=state[:2];obj.hide_set(state[2])
for scene in bpy.data.scenes:
    for layer in scene.view_layers:layer.update()
def fingerprint(obj):
    digest=hashlib.sha256(str([list(row) for row in obj.matrix_world]).encode())
    if obj.type=='MESH':
        for data,field,kind,width in ((obj.data.vertices,'co','f',3),(obj.data.loops,'vertex_index','i',1),(obj.data.polygons,'material_index','i',1)):
            values=array.array(kind,[0])*(len(data)*width);data.foreach_get(field,values);digest.update(values.tobytes())
        for layer in obj.data.uv_layers:
            values=array.array('f',[0])*(len(layer.data)*2);layer.data.foreach_get('uv',values);digest.update(values.tobytes())
    digest.update(str([m.name if m else None for m in getattr(obj.data,'materials',[])]).encode())
    return digest.hexdigest()
originals={o.name:fingerprint(o) for o in bpy.data.objects}
visibility={o.name:[o.hide_render,o.hide_viewport,o.hide_get()] for o in bpy.data.objects}
collection=bpy.data.collections['CKK_EXTERIOR'];centre=Vector((-110.49102024587766,77.56014819690478,0));angle=math.radians(22);outward=Vector((math.cos(angle),math.sin(angle),0));axis=Vector((-math.sin(angle),math.cos(angle),0))
def local(p):
 q=p-centre;return Vector((q.dot(outward),q.dot(axis),p.z))
def world(p):return centre+outward*p.x+axis*p.y+Vector((0,0,p.z))
rows=[(9.3,12.5),(13.8,16.5),(17.9,20.5)];middle=(-12.65,12.65);flanks=(-14.65,-10.65,10.65,14.65);old_width=.92;new_width=1.60;expansion=(new_width-old_width)/2
families=['masonry','recessed_glass','window_frames','stone_reveals','centre_mullions','projecting_sills','window_hoods'];owned=[];archived=[];counts={}
for family in families:
 source=bpy.data.objects['CKK_V33_'+family];assert not source.hide_render
 copy=source.copy();copy.data=source.data.copy();copy.name='CKK_NEXT_WING_'+family;copy.data.name=copy.name;collection.objects.link(copy)
 changed=0;removed=0
 if family=='masonry':
  for vertex in copy.data.vertices:
   p=local(copy.matrix_world@vertex.co)
   if not 22.69<p.x<23.21:continue
   if not any(lo-.001<=p.z<=hi+.001 for lo,hi in rows):continue
   for y in middle:
    if abs(abs(p.y-y)-old_width/2)<.001:
     p.y+=expansion*(1 if p.y>y else -1);vertex.co=copy.matrix_world.inverted()@world(p);changed+=1;break
  assert changed==48,changed
 else:
  bm=bmesh.new();bm.from_mesh(copy.data);seen=set();delete=[]
  for seed in bm.verts:
   if seed in seen:continue
   part=[];todo=[seed];seen.add(seed)
   while todo:
    v=todo.pop();part.append(v)
    for edge in v.link_edges:
     other=edge.other_vert(v)
     if other not in seen:seen.add(other);todo.append(other)
   ps=[local(copy.matrix_world@v.co) for v in part];avg=sum(ps,Vector())/len(ps)
   if not any(lo-.22<=min(p.z for p in ps) and max(p.z for p in ps)<=hi+.50 for lo,hi in rows):continue
   if family=='centre_mullions' and any(abs(avg.y-y)<.01 for y in flanks):delete.extend(part);removed+=1;continue
   if family=='centre_mullions':continue
   target=next((y for y in middle if abs(avg.y-y)<1.0),None)
   if target is None:continue
   for vertex,p in zip(part,ps):
    if abs(p.y-target)>.08:p.y+=expansion*(1 if p.y>target else -1)
    vertex.co=copy.matrix_world.inverted()@world(p)
   changed+=1
  if delete:bmesh.ops.delete(bm,geom=delete,context='VERTS')
  bm.to_mesh(copy.data);bm.free()
  if family=='centre_mullions':assert removed==12,removed
 copy.data.update();owned.append(copy.name);archived.append(source.name);counts[family]={'changedPartsOrVertices':changed,'removedParts':removed}
# Glass must be encountered before ANY overlapping stone/old return, including
# the newly widened strips on both sides, across the complete native elevation.
def tree(objects):
 vertices=[];faces=[];names=[]
 for obj in objects:
  offset=len(vertices);vertices.extend(obj.matrix_world@v.co for v in obj.data.vertices);faces.extend(tuple(offset+i for i in p.vertices) for p in obj.data.polygons);names.extend([obj.name]*len(obj.data.polygons))
 return BVHTree.FromPolygons(vertices,faces),names
probes=[]
for lo,hi in rows:
 for y in middle:
  for side in (-1,1):
   for height in (.30,.70):probes.append({'type':'newlyWidenedLight','y':y+side*.65,'z':lo+(hi-lo)*height})
 for y in flanks:probes.append({'type':'singleFlankingLight','y':y,'z':(lo+hi)/2})
def cast(objects):
 bvh,names=tree(objects);out=[]
 for p in probes:
  hit=bvh.ray_cast(world(Vector((26,p['y'],p['z']))),-outward,5)
  out.append({**p,'firstObject':names[hit[2]] if hit[2] is not None else None})
 return out
original_visible=[o for o in collection.all_objects if o.type=='MESH' and not o.hide_render and o.name not in owned];before=cast(original_visible)
assert all(p['firstObject']=='CKK_V33_masonry' for p in before if p['type']=='newlyWidenedLight')
assert all(p['firstObject']=='CKK_V33_centre_mullions' for p in before if p['type']=='singleFlankingLight')
for name in archived:bpy.data.objects[name].hide_render=True;bpy.data.objects[name].hide_set(True)
after=cast([o for o in collection.all_objects if o.type=='MESH' and not o.hide_render]);assert all(p['firstObject']=='CKK_NEXT_WING_recessed_glass' for p in after),after
assert all(fingerprint(bpy.data.objects[n])==v for n,v in originals.items())
component=OUT/'ckk-wing-window-component.blend';bpy.data.libraries.write(str(component),{bpy.data.objects[n] for n in owned},fake_user=True,compress=True)
ref=ROOT/'data/建筑图片/CKK_Cheng Kin Ku Building/01_建筑实拍/exteriors_ckk_grimshaw_010.jpg'
audit={'baselineSha256':hashlib.sha256(BASE.read_bytes()).hexdigest(),'originalFingerprints':originals,'originalVisibility':visibility,'ownedObjects':owned,'archivedObjects':archived,'componentChanges':counts,'windowCounts':{'widenedMiddle':6,'singleLightFlanks':12},'sources':[{'local':str(ref.relative_to(ROOT)),'sha256':hashlib.sha256(ref.read_bytes()).hexdigest(),'url':'https://grimshaw.global/projects/education-and-science/london-school-of-economics-new-academic-building/','photoDate':'Unknown; 2008 project archive'}],'firstBeforeProbes':before,'glassFirstAfterProbes':after,'estimatedDimensions':{'oldWidth':old_width,'newMiddleWidth':new_width,'retainedFlankWidth':old_width,'middleToFlankRatio':new_width/old_width,'retainedRows':rows},'limitations':['Photograph confirms wider double-light wing centres and single-light flanks, but exact widths and frame sections are not surveyed','Only principal storey and two above corrected; bottom two storeys and short top-floor band unchanged','Roof, whole facade outline, central five bays, entrance, material properties, window level datums and interiors unchanged','Existing flat principal-storey hoods retain their simplification; curved pediments and current Cafe54 remain unresolved']}
(OUT/'audit.json').write_text(json.dumps(audit,indent=2)+'\n');print('CKK_WING_COMPONENT_SAVED',component.stat().st_size,flush=True)
bpy.ops.wm.open_mainfile(filepath=str(BASE));scene=bpy.data.scenes['00_CAMPUS_COMPLETE'];bpy.context.window.scene=scene;collection=bpy.data.collections['CKK_EXTERIOR']
with bpy.data.libraries.load(str(component),link=False) as (src,dst):dst.objects=owned
for obj in dst.objects:
 collection.objects.link(obj);original=bpy.data.objects['CKK_V33_'+obj.name.removeprefix('CKK_NEXT_WING_')]
 for i,mat in enumerate(original.data.materials):obj.data.materials[i]=mat
for name in archived:bpy.data.objects[name].hide_render=True;bpy.data.objects[name].hide_set(True)
for scene_update in bpy.data.scenes:
 for layer in scene_update.view_layers:layer.update()
assert all(fingerprint(bpy.data.objects[n])==v for n,v in originals.items());reloaded=cast([o for o in collection.all_objects if o.type=='MESH' and not o.hide_render]);assert all(p['firstObject']=='CKK_NEXT_WING_recessed_glass' for p in reloaded)
for obj in scene.objects:
 if obj.type=='MESH' and obj.name not in {o.name for o in collection.all_objects}:obj.hide_render=True
focus=world(Vector((23,0,14.7)));camdata=bpy.data.cameras.new('CKK_NEXT_WING_preview_camera');cam=bpy.data.objects.new(camdata.name,camdata);scene.collection.objects.link(cam);cam.location=focus+outward*42+Vector((0,0,1));cam.rotation_euler=(focus-cam.location).to_track_quat('-Z','Y').to_euler();camdata.type='ORTHO';camdata.ortho_scale=36;scene.camera=cam
scene.render.engine='BLENDER_EEVEE';scene.render.resolution_x=1440;scene.render.resolution_y=1000;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG';scene.render.filepath=str(OUT/'reloaded-wing-windows.png');bpy.ops.render.render(write_still=True)
verification={'componentSha256':hashlib.sha256(component.read_bytes()).hexdigest(),'baselineUnchanged':hashlib.sha256(BASE.read_bytes()).hexdigest()==audit['baselineSha256'],'savedComponentReopened':True,'originalGeometryPreserved':True,'glassFirstProbeCount':len(after),'reloadedGlassFirstProbes':reloaded,'nativeRender':'reloaded-wing-windows.png'}
(OUT/'verification.json').write_text(json.dumps(verification,indent=2)+'\n');print('CKK_WING_COMPONENT_RELOADED_VERIFIED',flush=True)
