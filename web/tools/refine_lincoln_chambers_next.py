"""Expose Lincoln Chambers' photographed glazed porch doors.

Run in Blender's Text Editor. Three opaque backing slabs are reduced to their
existing lower timber panels. Source geometry and all unverified upper facade
and roof geometry remain untouched; no interior layout is inferred.
"""
from pathlib import Path
import array, hashlib, json, math, sys
import bpy, bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'result/blender/lch_next';OUT.mkdir(parents=True,exist_ok=True)
BASE=ROOT/'result/blender/LSE_campus_detailed_v122.blend'
if not BASE.exists():BASE=max((ROOT/'result/blender').glob('LSE_campus_detailed_v[0-9]*.blend'),key=lambda p:int(p.stem.rsplit('v',1)[1]))
bpy.ops.wm.open_mainfile(filepath=str(BASE));scene=bpy.data.scenes['00_CAMPUS_COMPLETE'];bpy.context.window.scene=scene
previous=json.loads((OUT/'audit.json').read_text()) if (OUT/'audit.json').exists() else None
def remove_previous():
 if not previous:return
 for name in previous['ownedObjects']:
  obj=bpy.data.objects.get(name)
  if obj:
   data=obj.data;bpy.data.objects.remove(obj,do_unlink=True);data.use_fake_user=False
   if not data.users:bpy.data.meshes.remove(data)
 for name in previous['archivedObjects']:
  if name in bpy.data.objects:
   obj=bpy.data.objects[name];state=previous['originalVisibility'][name]
   obj.hide_render,obj.hide_viewport=state[:2];obj.hide_set(state[2])
remove_previous()
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

collection=bpy.data.collections['LCH_EXTERIOR']
source=bpy.data.objects['LCH_D5_door_leaf_back_wood_dark']
assert not source.hide_render
# The three old whole-height backing slabs cover the upper glazed lights.
# Retain their original x/y, thickness, material and UV; reduce only the top
# vertices to the existing lower midrail. No building dimension is inferred.
copy=source.copy();copy.data=source.data.copy();copy.name='LCH_NEXT_lower_timber_backing';copy.data.name=copy.name;collection.objects.link(copy)
old_top=max((source.matrix_world@v.co).z for v in source.data.vertices)
new_top=1.345
changed=0
for v in copy.data.vertices:
 world=copy.matrix_world@v.co
 if world.z>new_top:
  world.z=new_top;v.co=copy.matrix_world.inverted()@world;changed+=1
copy.data.update();assert changed==12
owned=[copy];archived=[source.name]
def islands(obj):
 bm=bmesh.new();bm.from_mesh(obj.data);seen=set();result=[]
 for seed in bm.verts:
  if seed in seen:continue
  part=[];pending=[seed];seen.add(seed)
  while pending:
   v=pending.pop();part.append(obj.matrix_world@v.co)
   for edge in v.link_edges:
    q=edge.other_vert(v)
    if q not in seen:seen.add(q);pending.append(q)
  result.append(part)
 bm.free();return result
# Recover pane orientation from the saved source glass, independent of deleted
# historical layout files. Each pane is an eight-vertex thin cuboid.
glass=bpy.data.objects['LCH_D5_door_glazed_panel_glass'];panes=islands(glass);assert len(panes)==4
header=bpy.data.objects['LCH_D5_porch_header_stone_stone'];approach=sum((header.matrix_world@v.co for v in header.data.vertices),Vector())/len(header.data.vertices)
probe_frames=[]
for points in panes:
 center=sum(points,Vector())/len(points)
 # Longest horizontal edge is the window width, not its thin glass depth.
 horizontal=[q-p for p in points for q in points if abs(q.z-p.z)<1e-5 and (q-p).length>.01]
 tangent=max(horizontal,key=lambda q:q.length);tangent.z=0;tangent.normalize()
 normal=Vector((-tangent.y,tangent.x,0))
 if normal.dot(approach-center)<0:normal=-normal
 probe_frames.append((center,tangent,normal))
def aperture_results():
 vertices=[];faces=[];owners=[]
 for obj in collection.all_objects:
  if obj.type!='MESH' or obj.hide_render or 'glass' in obj.name.lower():continue
  start=len(vertices);vertices.extend(obj.matrix_world@v.co for v in obj.data.vertices)
  faces.extend(tuple(start+i for i in p.vertices) for p in obj.data.polygons);owners.extend([obj.name]*len(obj.data.polygons))
 tree=BVHTree.FromPolygons(vertices,faces);results=[]
 for index,(center,tangent,normal) in enumerate(probe_frames):
  for dx in (-.12,.12):
   for z in (1.60,1.97,2.35):
    location=center+tangent*dx;location.z=z
    hit=tree.ray_cast(location+normal*.075,-normal,.21)
    results.append({'pane':index,'height':z,'offset':dx,'opaqueBacking':owners[hit[2]] if hit[2] is not None else None})
 return results
def lower_panel_results():
 results=[]
 for index,(center,tangent,normal) in enumerate(probe_frames):
  point=center.copy();point.z=.70
  # Test the reduced copied backing itself, so raised decorative panels cannot
  # accidentally make an absent lower backing look complete.
  mesh=copy.data;vertices=[copy.matrix_world@v.co for v in mesh.vertices]
  tree=BVHTree.FromPolygons(vertices,[tuple(p.vertices) for p in mesh.polygons])
  hit=tree.ray_cast(point+normal*.075,-normal,.21)
  results.append({'pane':index,'lowerBackingPresent':hit[2] is not None})
 assert all(p['lowerBackingPresent'] for p in results)
 return results
lower=lower_panel_results()
before=aperture_results();assert len(before)==24 and all(p['opaqueBacking']==source.name for p in before),before
source.hide_render=True;source.hide_set(True)
after=aperture_results();assert all(p['opaqueBacking'] is None for p in after),after
assert all(fingerprint(bpy.data.objects[n])==v for n,v in originals.items())
component=OUT/'lincoln-chambers-component.blend';bpy.data.libraries.write(str(component),set(owned),fake_user=True,compress=True)
audit={'baselineSha256':hashlib.sha256(BASE.read_bytes()).hexdigest(),'originalFingerprints':originals,'originalVisibility':visibility,'archivedObjects':archived,'ownedObjects':[o.name for o in owned],'backingSlabs':3,'glazedLights':4,'originalTopM':old_top,'lowerBackingTopM':new_top,'modifiedVertices':changed,'lowerBackingChecks':lower,'blockedBefore':before,'clearAfter':after,'sources':[{'local':'data/建筑图片/LCH_Lincoln Chambers/01_建筑实拍/exteriors_lse_estate_011.jpg','url':'https://info.lse.ac.uk/staff/divisions/estates-division/lse-estate/LSE-Estate','sha256':'bc27b36bcb580ccb73bb2bb8a61575c09e09217fefca0c26754e6022eef13cae','captureDate':None},{'local':'data/建筑图片/LCH_Lincoln Chambers/01_建筑实拍/exterior_photos_round4_LCH_geograph_2726383.jpg','url':'https://www.geograph.org.uk/photo/2726383','sha256':'a82340936aa12d5101444c3eb0983414f958d92703f4649849fbcbce8fb7a648','captureDate':'2011-12-10'}],'limitations':['Only opaque backing behind photographed glazed porch doors corrected','Upper facade, roof and unseen rear remain previous estimates','Existing dimensions and joinery retained; no measured survey or interior layout claimed','Official entrance photo capture date unknown; historical closeup does not establish present condition']}
(OUT/'audit.json').write_text(json.dumps(audit,indent=2)+'\n');print('LCH_COMPONENT_SAVED',component.stat().st_size,flush=True)
bpy.ops.wm.open_mainfile(filepath=str(BASE));scene=bpy.data.scenes['00_CAMPUS_COMPLETE'];bpy.context.window.scene=scene
remove_previous()
with bpy.data.libraries.load(str(component),link=False) as (src,dst):dst.objects=audit['ownedObjects']
collection=bpy.data.collections['LCH_EXTERIOR']
for obj in dst.objects:collection.objects.link(obj)
copy=dst.objects[0]
bpy.context.view_layer.update()
for name in archived:bpy.data.objects[name].hide_render=True;bpy.data.objects[name].hide_set(True)
assert all(fingerprint(bpy.data.objects[n])==v for n,v in originals.items())
lower=lower_panel_results()
reloaded=aperture_results();assert all(p['opaqueBacking'] is None for p in reloaded)
# Isolate the entrance for an actual native reload render, without saving preview
# visibility changes to either the source native or the component library.
for obj in scene.objects:
 if obj.type=='MESH' and obj.name not in {o.name for o in collection.all_objects}:obj.hide_render=True
main=probe_frames[0];focus=sum((f[0] for f in probe_frames),Vector())/len(probe_frames);focus.z=2.0
normal=(approach-focus);normal.z=0;normal.normalize()
camdata=bpy.data.cameras.new('LCH_NEXT_preview_camera');cam=bpy.data.objects.new(camdata.name,camdata);scene.collection.objects.link(cam)
cam.location=focus+normal*10+Vector((0,0,1));cam.rotation_euler=(focus-cam.location).to_track_quat('-Z','Y').to_euler();camdata.type='ORTHO';camdata.ortho_scale=5.7;scene.camera=cam
scene.render.engine='BLENDER_EEVEE';scene.render.resolution_x=1000;scene.render.resolution_y=900;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG';scene.render.filepath=str(OUT/'reloaded-entrance.png');bpy.ops.render.render(write_still=True)
verification={'componentSha256':hashlib.sha256(component.read_bytes()).hexdigest(),'baselineUnchanged':hashlib.sha256(BASE.read_bytes()).hexdigest()==audit['baselineSha256'],'originalGeometryPreserved':True,'savedComponentReopened':True,'blockedBefore':24,'reloadedClearProbes':len(reloaded),'reloadedLowerBackingChecks':lower,'nativeRender':'reloaded-entrance.png'}
(OUT/'verification.json').write_text(json.dumps(verification,indent=2)+'\n');print('LCH_COMPONENT_RELOADED_VERIFIED',flush=True)
