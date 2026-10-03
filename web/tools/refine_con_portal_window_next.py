"""Correct the compact four-light window above the Connaught House entrance.

Run in Blender's Text Editor. Only this opening changes; relative height is photo-guided, absolute dimensions remain estimates.
"""
from pathlib import Path
import array, hashlib, json, sys, math
import bpy, bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'result/blender/con_portal_window_next'
OUT.mkdir(parents=True,exist_ok=True)
BASE = ROOT/'result/blender/LSE_campus_detailed_v132.blend'
if not BASE.exists():
    BASE = max((ROOT/'result/blender').glob('LSE_campus_detailed_v[0-9]*.blend'),key=lambda p:int(p.stem.rsplit('v',1)[1]))
def open_baseline():
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
open_baseline()
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
collection=bpy.data.collections['CON_EXTERIOR']
origin=Vector((-16.17835807800293,-130.22201538085938,0))
axis=Vector((-.9859890937805176,-.16680996119976044,0))
normal=Vector((.16680996119976044,-.9859890937805176,0))
def local(p):
 d=p-origin;return Vector((d.dot(axis),d.dot(normal),p.z))
def world(x,d,z):return origin+axis*x+normal*d+Vector((0,0,z))
old_sill,old_head,new_sill,new_head=5.6,7.95,6.1,7.6
parts=['stone_spandrels','window_reveals','recessed_glass','window_frames','projecting_sills','sill_drip_edges','lintel_mouldings']
owned=[];sources=[];changes=[]
for part_name in parts:
 source=bpy.data.objects['CON_D4_'+part_name];assert not source.hide_render
 obj=source.copy();obj.data=source.data.copy();obj.name='CON_NEXT_PORTAL_WINDOW_'+part_name;obj.data.name=obj.name;collection.objects.link(obj)
 bm=bmesh.new();bm.from_mesh(obj.data);seen=set();changed=0;unchanged=[]
 for seed in bm.verts:
  if seed in seen:continue
  chunk=[];todo=[seed];seen.add(seed)
  while todo:
   v=todo.pop();chunk.append(v)
   for e in v.link_edges:
    other=e.other_vert(v)
    if other not in seen:seen.add(other);todo.append(other)
  pts=[local(obj.matrix_world@v.co) for v in chunk];avg=sum(pts,Vector())/len(pts);low=min(p.z for p in pts);high=max(p.z for p in pts)
  selected=abs(avg.x)<1.1 and ((4.7<avg.z<8.7) if part_name=="stone_spandrels" else (5.25<avg.z<8.35))
  mode=None
  if selected:
   if part_name=='stone_spandrels':
    if abs(low-4.8)<.01 and abs(high-old_sill)<.01:mode='lower_wall'
    elif abs(low-old_head)<.01 and abs(high-8.6)<.01:mode='upper_wall'
   elif part_name in ['window_reveals','recessed_glass','window_frames']:mode='window'
   elif part_name in ['projecting_sills','sill_drip_edges']:mode='sill'
   elif part_name=='lintel_mouldings':mode='head'
  if not mode:
   unchanged.extend(tuple(obj.matrix_world@v.co) for v in chunk);continue
  for v,p in zip(chunk,pts):
   if mode=='lower_wall':z=new_sill if abs(p.z-old_sill)<.01 else p.z
   elif mode=='upper_wall':z=new_head if abs(p.z-old_head)<.01 else p.z
   elif mode=='window':z=new_sill+(p.z-old_sill)*(new_head-new_sill)/(old_head-old_sill)
   elif mode=='sill':z=p.z+new_sill-old_sill
   else:z=p.z+new_head-old_head
   v.co+=obj.matrix_world.inverted().to_3x3()@Vector((0,0,z-p.z))
  changed+=len(chunk)
 bm.to_mesh(obj.data);bm.free();obj.data.update();assert changed>0
 # Changes are confined to the registered center opening; all other vertices stay exact.
 copied=[tuple(obj.matrix_world@v.co) for v in obj.data.vertices]
 from collections import Counter
 assert not Counter(unchanged)-Counter(copied)
 owned.append(obj);sources.append(source);changes.append({'source':source.name,'owned':obj.name,'changedVertices':changed,'unchangedVertices':len(unchanged)})
def cast(objects,points):
 vertices=[];faces=[];names=[]
 for o in objects:
  off=len(vertices);vertices.extend(o.matrix_world@v.co for v in o.data.vertices);faces.extend(tuple(off+i for i in p.vertices) for p in o.data.polygons);names.extend([o.name]*len(o.data.polygons))
 bvh=BVHTree.FromPolygons(vertices,faces);result=[]
 for x,z in points:
  h=bvh.ray_cast(world(x,.8,z),-normal,2);result.append({'x':x,'z':z,'firstObject':names[h[2]] if h[2] is not None else None})
 return result
visible=lambda:[o for o in collection.all_objects if o.type=='MESH' and not o.hide_render]
lights=[(x,z) for z in (6.45,7.40) for x in (-.5,.5)]
filled=[(x,z) for z in (5.85,7.80) for x in (-.5,.5)]
neighbors=[(x,z) for x in (-3.90,3.90) for z in (6.3,7.6)]
before=cast([o for o in visible() if o not in owned],lights+filled+neighbors)
for source in sources:source.hide_render=True;source.hide_set(True)
after=cast(visible(),lights+filled+neighbors)
assert all(p['firstObject']=='CON_NEXT_PORTAL_WINDOW_recessed_glass' for p in after[:4]),after
assert all(p['firstObject']=='CON_NEXT_PORTAL_WINDOW_stone_spandrels' for p in after[4:8]),after
assert [p["firstObject"].replace("CON_NEXT_PORTAL_WINDOW_","CON_D4_") for p in after[8:]]==[p["firstObject"] for p in before[8:]]
assert all(fingerprint(bpy.data.objects[n])==v for n,v in originals.items())
component=OUT/'con-compact-portal-window-component.blend';bpy.data.libraries.write(str(component),set(owned),fake_user=True,compress=True)
ref=ROOT/'data/建筑图片/CON_Connaught House/01_建筑实拍/exteriors_lse_estate_005.jpg'
audit={'baselineSha256':hashlib.sha256(BASE.read_bytes()).hexdigest(),'originalFingerprints':originals,'originalVisibility':visibility,'ownedObjects':[o.name for o in owned],'archivedObjects':[o.name for o in sources],'changes':changes,'windowRegistration':{'origin':list(origin),'right':list(axis),'outward':list(normal),'oldSill':old_sill,'oldHead':old_head,'newSill':new_sill,'newHead':new_head,'oldHeight':2.35,'newHeight':1.5,'heightRatio':1.5/2.35,'widthUnchanged':1.88,'fourLightTransomFractionUnchanged':.69},'beforeProbes':before,'afterProbes':after,'references':[{'local':str(ref.relative_to(ROOT)),'sha256':hashlib.sha256(ref.read_bytes()).hexdigest(),'url':'https://info.lse.ac.uk/staff/divisions/estates-division/lse-estate/LSE-Estate','date':'Photograph capture date unknown','pixelRegistration':{'centerBounds':[113,55,179,94],'leftVisibleBounds':[0,49,60,109],'rightVisibleBounds':[238,44,300,101],'neighborHeightAtCenterApprox':60,'centerHeightApprox':39,'relativeHeightApprox':.65},'observation':'The compact portal window head lies below adjacent heads and its sill above adjacent sills. Window-to-window ratios are used, not an assumed common head.'}],'limitations':['Metre dimensions, head shift0.35m and sill shift0.50m are photo-guided estimates from the inherited2.35m neighboring opening, not survey measurements.','Photo is300x400px and oblique; approximate bounds carry several-pixel uncertainty. Side window extents partly meet image boundary.','Nominal width, four-light transom proportion, depths, sections, color and materials retained.','Only one center first-upper-storey opening changes; neighboring windows, entrance, crest and other elevations are preserved.','No claim of full-building exterior or interior completion.']}
(OUT/'audit.json').write_text(json.dumps(audit,indent=2)+'\n');print('CON_COMPACT_WINDOW_COMPONENT_SAVED',flush=True)
open_baseline();collection=bpy.data.collections['CON_EXTERIOR']
with bpy.data.libraries.load(str(component),link=False) as (src,dst):dst.objects=audit['ownedObjects']
for obj in dst.objects:
 collection.objects.link(obj)
 source=bpy.data.objects['CON_D4_'+obj.name.removeprefix('CON_NEXT_PORTAL_WINDOW_')]
 for i,mat in enumerate(source.data.materials):obj.data.materials[i]=mat
for name in audit['archivedObjects']:bpy.data.objects[name].hide_render=True;bpy.data.objects[name].hide_set(True)
for sc in bpy.data.scenes:
 for layer in sc.view_layers:layer.update()
assert all(fingerprint(bpy.data.objects[n])==v for n,v in originals.items())
reloaded=cast(visible(),lights+filled+neighbors);assert reloaded==after
scene=bpy.data.scenes['00_CAMPUS_COMPLETE']
for o in scene.objects:
 if o.type=='MESH' and o.name not in {o.name for o in collection.all_objects}:o.hide_render=True
focus=world(0,0,4.7);camdata=bpy.data.cameras.new('CON_NEXT_preview_camera');cam=bpy.data.objects.new(camdata.name,camdata);scene.collection.objects.link(cam);cam.location=focus+normal*18+axis*.8+Vector((0,0,.4));cam.rotation_euler=(focus-cam.location).to_track_quat('-Z','Y').to_euler();camdata.type='ORTHO';camdata.ortho_scale=9.4;scene.camera=cam
scene.render.engine='BLENDER_EEVEE';scene.render.resolution_x=900;scene.render.resolution_y=1000;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG';scene.render.filepath=str(OUT/'reloaded-compact-window.png');bpy.ops.render.render(write_still=True)
verification={'componentSha256':hashlib.sha256(component.read_bytes()).hexdigest(),'baselineUnchanged':hashlib.sha256(BASE.read_bytes()).hexdigest()==audit['baselineSha256'],'savedComponentReopened':True,'originalGeometryPreserved':True,'originalObjectCount':len(originals),'ownedCount':len(owned),'archivedCount':len(sources),'reloadedProbes':reloaded,'nativeRender':'reloaded-compact-window.png'}
(OUT/'verification.json').write_text(json.dumps(verification,indent=2)+'\n');print('CON_COMPACT_WINDOW_COMPONENT_RELOADED_VERIFIED',flush=True)
