"""Correct the photographed three-column window over the Columbia House portal.

Run in Blender's Text Editor. Only this window divider changes; widths and frame sections remain estimates.
"""
from pathlib import Path
import array, hashlib, json, sys, math
import bpy, bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'result/blender/col_transoms_next'
OUT.mkdir(parents=True,exist_ok=True)
BASE = ROOT/'result/blender/LSE_campus_detailed_v131.blend'
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
collection=bpy.data.collections['COL_EXTERIOR'];source=bpy.data.objects['COL_V99_retained_D4_window_frames'];glass=bpy.data.objects['COL_V99_retained_D4_recessed_glass'];assert not source.hide_render and not glass.hide_render
origin=Vector((16.679906845092773,-127.4544677734375,0));axis=Vector((-.999708354473114,.024150928482413292,0));normal=Vector((-.024150928482413292,-.999708354473114,0))
def local(p):
 d=p-origin;return Vector((d.dot(axis),d.dot(normal),p.z))
def world(x,d,z):return origin+axis*x+normal*d+Vector((0,0,z))
owned=source.copy();owned.data=source.data.copy();owned.name='COL_NEXT_portal_window_three_columns';owned.data.name=owned.name;collection.objects.link(owned)
bm=bmesh.new();bm.from_mesh(owned.data);seen=set();selected=[];original_other=[]
for seed in bm.verts:
 if seed in seen:continue
 part=[];todo=[seed];seen.add(seed)
 while todo:
  v=todo.pop();part.append(v)
  for e in v.link_edges:
   other=e.other_vert(v)
   if other not in seen:seen.add(other);todo.append(other)
 ps=[local(owned.matrix_world@v.co) for v in part];avg=sum(ps,Vector())/len(ps)
 if abs(avg.x)<.01 and -.4<avg.y<-.2 and abs(min(p.z for p in ps)-5.6)<.01 and abs(max(p.z for p in ps)-7.95)<.01:selected.append(part)
 else:original_other.extend(tuple(owned.matrix_world@v.co) for v in part)
assert len(selected)==1 and len(selected[0])==8
part=selected[0];edges={e for v in part for e in v.link_edges};faces={f for v in part for f in v.link_faces};geom=list(part)+list(edges)+list(faces);offset=1.88/6;new_vertices=[]
for side in (-1,1):
 duplicate=bmesh.ops.duplicate(bm,geom=geom);verts=[v for v in duplicate['geom'] if isinstance(v,bmesh.types.BMVert)];assert len(verts)==8
 for v in verts:v.co+=owned.matrix_world.inverted().to_3x3()@(axis*side*offset)
 new_vertices.extend(verts)
bmesh.ops.delete(bm,geom=part,context='VERTS');retained_world=[tuple(owned.matrix_world@v.co) for v in bm.verts if v not in new_vertices];assert sorted(retained_world)==sorted(original_other)
bm.to_mesh(owned.data);bm.free();owned.data.update();assert len(owned.data.vertices)==len(source.data.vertices)+8
# All visible COL meshes participate, so original deep reveals and ornate entry
# can never masquerade as a light behind an unregistered decorative overlay.
def cast(objects,points):
 vertices=[];faces=[];names=[]
 for o in objects:
  off=len(vertices);vertices.extend(o.matrix_world@v.co for v in o.data.vertices);faces.extend(tuple(off+i for i in p.vertices) for p in o.data.polygons);names.extend([o.name]*len(o.data.polygons))
 bvh=BVHTree.FromPolygons(vertices,faces);result=[]
 for x,z in points:
  h=bvh.ray_cast(world(x,.8,z),-normal,2);result.append({'x':x,'z':z,'firstObject':names[h[2]] if h[2] is not None else None})
 return result
lights=[(x,z) for z in (6.3,7.6) for x in (-.60,0,.60)];divider_points=[(x,6.3) for x in (-offset,offset)]
visible=lambda:[o for o in collection.all_objects if o.type=='MESH' and not o.hide_render]
before=cast([o for o in visible() if o!=owned],lights);assert [p['firstObject'] for p in before]==[glass.name,source.name,glass.name]*2
source.hide_render=True;source.hide_set(True);after=cast(visible(),lights);assert all(p['firstObject']==glass.name for p in after)
bars=cast(visible(),divider_points);assert all(p['firstObject']==owned.name for p in bars)
assert all(fingerprint(bpy.data.objects[n])==v for n,v in originals.items())
component=OUT/'col-three-column-window-component.blend';bpy.data.libraries.write(str(component),{owned},fake_user=True,compress=True)
ref=ROOT/'data/建筑图片/COL_Columbia House/01_建筑实拍/small_round5_COL_handbook-000.png'
audit={'baselineSha256':hashlib.sha256(BASE.read_bytes()).hexdigest(),'originalFingerprints':originals,'originalVisibility':visibility,'ownedObjects':[owned.name],'archivedObjects':[source.name],'unchangedOtherFrameVertices':len(original_other),'removedCentralDividerVertices':8,'newDividerVertices':16,'glassObjectUnchanged':glass.name,'windowRegistration':{'origin':list(origin),'right':list(axis),'outward':list(normal),'existingNominalWidth':1.88,'existingGlassWidth':1.8,'newDividerOffsets':[-offset,offset],'frameZ':[5.6,7.95]},'lightBeforeProbes':before,'lightAfterProbes':after,'dividerAfterProbes':bars,'references':[{'local':str(ref.relative_to(ROOT)),'sha256':hashlib.sha256(ref.read_bytes()).hexdigest(),'url':'https://info.lse.ac.uk/staff/divisions/estates-division/Assets/Documents/Property-and-Space/LSE-Property-Handbook.pdf','date':'2025/26 handbook; photograph capture date unknown'}],'limitations':['Photograph supports three columns and upper transom in this single portal-adjacent window; equal thirds spacing and retained width/sections remain estimates','Existing upper transom, perimeter frames, glass, stone wall/reveals and sill unchanged','All other windows and67 ornate entry/99 Garrick corner details unchanged','No claim of complete facade or interior accuracy']}
(OUT/'audit.json').write_text(json.dumps(audit,indent=2)+'\n');print('COL_WINDOW_COMPONENT_SAVED',component.stat().st_size,flush=True)
open_baseline();scene=bpy.data.scenes['00_CAMPUS_COMPLETE'];collection=bpy.data.collections['COL_EXTERIOR'];source=bpy.data.objects[audit['archivedObjects'][0]];glass=bpy.data.objects[audit['glassObjectUnchanged']]
with bpy.data.libraries.load(str(component),link=False) as (src,dst):dst.objects=audit['ownedObjects']
owned=dst.objects[0];collection.objects.link(owned)
for i,m in enumerate(source.data.materials):owned.data.materials[i]=m
source.hide_render=True;source.hide_set(True)
for sc in bpy.data.scenes:
 for layer in sc.view_layers:layer.update()
assert all(fingerprint(bpy.data.objects[n])==v for n,v in originals.items());reloaded_lights=cast(visible(),lights);assert reloaded_lights==after;assert cast(visible(),divider_points)==bars
for o in scene.objects:
 if o.type=='MESH' and o.name not in {o.name for o in collection.all_objects}:o.hide_render=True
focus=world(0,0,5.2);camdata=bpy.data.cameras.new('COL_NEXT_preview_camera');cam=bpy.data.objects.new(camdata.name,camdata);scene.collection.objects.link(cam);cam.location=focus+normal*18+axis*.8+Vector((0,0,1));cam.rotation_euler=(focus-cam.location).to_track_quat('-Z','Y').to_euler();camdata.type='ORTHO';camdata.ortho_scale=9;scene.camera=cam
scene.render.engine='BLENDER_EEVEE';scene.render.resolution_x=1000;scene.render.resolution_y=1100;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG';scene.render.filepath=str(OUT/'reloaded-portal-window.png');bpy.ops.render.render(write_still=True)
verification={'componentSha256':hashlib.sha256(component.read_bytes()).hexdigest(),'baselineUnchanged':hashlib.sha256(BASE.read_bytes()).hexdigest()==audit['baselineSha256'],'savedComponentReopened':True,'originalGeometryPreserved':True,'reloadedLightProbes':reloaded_lights,'nativeRender':'reloaded-portal-window.png'}
(OUT/'verification.json').write_text(json.dumps(verification,indent=2)+'\n');print('COL_WINDOW_COMPONENT_RELOADED_VERIFIED',flush=True)
