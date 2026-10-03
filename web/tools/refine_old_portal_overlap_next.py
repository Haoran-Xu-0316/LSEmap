"""Clear stone-course overlap at the registered OLD entrance side windows.

Run in Blender's Text Editor. Only inner course edges change; physical clearances remain estimates.
"""
from pathlib import Path
import array, hashlib, json, sys, math
import bpy, bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'result/blender/old_portal_overlap_next'
OUT.mkdir(parents=True,exist_ok=True)
BASE = ROOT/'result/blender/LSE_campus_detailed_v133.blend'
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
collection=bpy.data.collections['OLD_EXTERIOR']
review=json.loads((ROOT/'result/blender/old_review133/inspection.json').read_text())
origin=Vector(review['origin']);axis=Vector(review['right']);normal=Vector(review['outward'])
source=bpy.data.objects['OLD_V112_entry_V97_Entrance_rusticated_blocks'];assert not source.hide_render
frame=bpy.data.objects['OLD_V112_entry_D5_portal78_frame_blue'];reveal=bpy.data.objects['OLD_V112_entry_D5_portal78_reveal_stone'];glass=bpy.data.objects['OLD_V112_entry_D5_portal78_pane_glass']
def local(p):
 d=p-origin;return Vector((d.dot(axis),d.dot(normal),p.z))
def world(x,d,z):return origin+axis*x+normal*d+Vector((0,0,z))
bounds={}
for obj in [frame,reveal,glass]:
 pts=[local(obj.matrix_world@v.co) for v in obj.data.vertices]
 bounds[obj.name]=[[min(p[i] for p in pts),max(p[i] for p in pts)] for i in range(3)]
# The native reveals are the widest registered window trim. Keep a small
# explicitly estimated clearance so course edges never cover that trim.
clearance=.004
left_limit=min(bounds[frame.name][0][0],bounds[reveal.name][0][0])-clearance
right_limit=max(bounds[frame.name][0][1],bounds[reveal.name][0][1])+clearance
owned=source.copy();owned.data=source.data.copy();owned.name='OLD_NEXT_PORTAL_clear_rusticated_blocks';owned.data.name=owned.name;collection.objects.link(owned)
bm=bmesh.new();bm.from_mesh(owned.data);seen=set();changes=[];untouched=[];modified=[]
for seed in bm.verts:
 if seed in seen:continue
 chunk=[];todo=[seed];seen.add(seed)
 while todo:
  v=todo.pop();chunk.append(v)
  for edge in v.link_edges:
   other=edge.other_vert(v)
   if other not in seen:seen.add(other);todo.append(other)
 ps=[local(owned.matrix_world@v.co) for v in chunk];avg=sum(ps,Vector())/len(ps);lo=min(p.x for p in ps);hi=max(p.x for p in ps)
 assert len(chunk)==8 and (hi<0 or lo>0)
 limit=left_limit if avg.x<0 else right_limit;old_inner=hi if avg.x<0 else lo;count=0
 inner=set(sorted(chunk,key=lambda v:local(owned.matrix_world@v.co).x,reverse=avg.x<0)[:4])
 for v,p in zip(chunk,ps):
  if v in inner:
   v.co+=owned.matrix_world.inverted().to_3x3()@(axis*(limit-p.x));modified.append(v);count+=1
  else:untouched.append(tuple(owned.matrix_world@v.co))
 assert count==4
 changes.append({'side':'left' if avg.x<0 else 'right','oldInnerEdgeX':old_inner,'newInnerEdgeX':limit,'zBounds':[min(p.z for p in ps),max(p.z for p in ps)],'changedVertices':count})
assert len(changes)==12 and len(modified)==48 and len(untouched)==48
assert all(tuple(owned.matrix_world@v.co) in untouched for v in bm.verts if v not in modified)
bm.to_mesh(owned.data);bm.free();owned.data.update()
def mesh_structure(obj):
 digest=hashlib.sha256()
 for data,field,kind,width in ((obj.data.loops,'vertex_index','i',1),(obj.data.polygons,'material_index','i',1)):
  values=array.array(kind,[0])*(len(data)*width);data.foreach_get(field,values);digest.update(values.tobytes())
 for layer in obj.data.uv_layers:
  values=array.array('f',[0])*(len(layer.data)*2);layer.data.foreach_get('uv',values);digest.update(values.tobytes())
 digest.update(str([m.name for m in obj.data.materials]).encode());return digest.hexdigest()
assert mesh_structure(source)==mesh_structure(owned)
def cast(objects,points):
 vertices=[];faces=[];names=[]
 for o in objects:
  k=len(vertices);vertices.extend(o.matrix_world@v.co for v in o.data.vertices);faces.extend(tuple(k+i for i in p.vertices) for p in o.data.polygons);names.extend([o.name]*len(o.data.polygons))
 tree=BVHTree.FromPolygons(vertices,faces);records=[]
 for label,x,z in points:
  hit=tree.ray_cast(world(x,.8,z),-normal,5);records.append({'label':label,'x':x,'z':z,'firstObject':names[hit[2]] if hit[2] is not None else None,'hitDepth':local(hit[0]).y if hit[0] else None})
 return records
visible=lambda:[o for o in collection.all_objects if o.type=='MESH' and not o.hide_render]
window_points=[('window-'+str(i),r['x'],r['z']) for i,r in enumerate(review['narrowWindowFirstHitProbes'])]
wall_points=[('outer-'+str(i),x,z) for i,(x,z) in enumerate([(x,z) for x in (-4.95,3.1) for z in (2.055,2.572,3.089,3.605)])]
before=cast([o for o in visible() if o!=owned],window_points+wall_points)
assert sum(r['firstObject']==source.name for r in before[:40])==16
source.hide_render=True;source.hide_set(True)
after=cast(visible(),window_points+wall_points)
assert all(r['firstObject'] in [glass.name,'OLD_V112_entry_D5_portal78_muntin_blue'] for r in after[:40]),after
assert all(r['firstObject']==owned.name for r in after[40:]),after[40:]
assert all(r['firstObject']==source.name for r in before[40:])
assert all(fingerprint(bpy.data.objects[n])==v for n,v in originals.items())
component=OUT/'old-portal-stone-clearance-component.blend';bpy.data.libraries.write(str(component),{owned},fake_user=True,compress=True)
ref=ROOT/'data/collections/old-user-reference/houghton-user-entrance-additional-20261002.png'
audit={'baselineSha256':hashlib.sha256(BASE.read_bytes()).hexdigest(),'originalFingerprints':originals,'originalVisibility':visibility,'ownedObjects':[owned.name],'archivedObjects':[source.name],'changedVertices':48,'unchangedOuterVertices':48,'sourceCourseCount':12,'changes':[{'source':source.name,'owned':owned.name,'changedVertices':48,'unchangedOuterVertices':48}],'courseChanges':changes,'registeredWindowBounds':bounds,'registration':{'origin':list(origin),'right':list(axis),'outward':list(normal),'leftCourseLimit':left_limit,'rightCourseLimit':right_limit,'estimatedClearance':clearance},'beforeProbes':before,'afterProbes':after,'references':[{'local':str(ref.relative_to(ROOT)),'sha256':hashlib.sha256(ref.read_bytes()).hexdigest(),'origin':'User supplied entrance photograph','captureDate':'unknown','evidence':'Visible upper left narrow window clear of projecting stone teeth; lower left is obscured by text and right window is outside view.'}],'scope':'Trim inner edges of one retained course family against registered native side-window frame/reveal extents; no window, arch, relief, plaque, step or material changes.','limitations':['Native frame/reveal boundaries are inherited estimates, not surveyed dimensions.','4mm margin is a small estimated model clearance, not a physical construction measurement.','Left correction is corroborated by photograph; right correction removes native collision only and does not claim independent photographic fidelity.','All12 course inner edges follow continuous registered jamb lines, including portions above/below the narrow glass; course height, depth and external edges remain unchanged.','Complete OLD exterior and interiors remain outside scope.']}
(OUT/'audit.json').write_text(json.dumps(audit,indent=2)+'\n');print('OLD_PORTAL_OVERLAP_COMPONENT_SAVED',flush=True)
open_baseline();collection=bpy.data.collections['OLD_EXTERIOR'];source=bpy.data.objects[audit['archivedObjects'][0]]
with bpy.data.libraries.load(str(component),link=False) as (src,dst):dst.objects=audit['ownedObjects']
owned=dst.objects[0];collection.objects.link(owned)
for i,m in enumerate(source.data.materials):owned.data.materials[i]=m
source.hide_render=True;source.hide_set(True)
for sc in bpy.data.scenes:
 for layer in sc.view_layers:layer.update()
assert all(fingerprint(bpy.data.objects[n])==v for n,v in originals.items())
reloaded=cast(visible(),window_points+wall_points);assert reloaded==after
scene=bpy.data.scenes['00_CAMPUS_COMPLETE']
for obj in scene.objects:
 if obj.type=='MESH' and obj.name not in {o.name for o in collection.all_objects}:obj.hide_render=True
focus=origin+Vector((0,0,5));camdata=bpy.data.cameras.new('OLD_NEXT_portal_preview');cam=bpy.data.objects.new(camdata.name,camdata);scene.collection.objects.link(cam);cam.location=focus+normal*24;cam.rotation_euler=(focus-cam.location).to_track_quat('-Z','Y').to_euler();camdata.type='ORTHO';camdata.ortho_scale=14.5;scene.camera=cam
scene.render.engine='BLENDER_EEVEE';scene.render.resolution_x=1350;scene.render.resolution_y=1050;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG';scene.render.filepath=str(OUT/'reloaded-clear-portal.png');bpy.ops.render.render(write_still=True)
verification={'componentSha256':hashlib.sha256(component.read_bytes()).hexdigest(),'baselineUnchanged':hashlib.sha256(BASE.read_bytes()).hexdigest()==audit['baselineSha256'],'originalGeometryPreserved':True,'originalObjectCount':len(originals),'savedComponentReopened':True,'originalStoneFacesLoopsUVAndMaterialSlotsRetained':True,'unchangedOuterVertices':48,'reloadedProbes':reloaded,'stoneFirstWindowHitsBefore':16,'stoneFirstWindowHitsAfter':0,'nativeRender':'reloaded-clear-portal.png'}
(OUT/'verification.json').write_text(json.dumps(verification,indent=2)+'\n');print('OLD_PORTAL_OVERLAP_COMPONENT_RELOADED_VERIFIED',flush=True)
