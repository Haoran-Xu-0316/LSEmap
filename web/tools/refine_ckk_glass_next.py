"""Remove five unsupported radial spokes from the CKK entrance fanlight.

Run in Blender's Text Editor. Retain the arched rim, spring rail, glass and stone arch; no full model save.
"""
from pathlib import Path
import array, hashlib, json, sys, math
import bpy, bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'result/blender/ckk_glass_next'
OUT.mkdir(parents=True,exist_ok=True)
BASE = ROOT/'result/blender/LSE_campus_detailed_v134.blend'
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
collection=bpy.data.collections['CKK_EXTERIOR'];source=bpy.data.objects['CKK_V33_fanlight_frame'];assert not source.hide_render
centre=Vector((-110.49102024587766,77.56014819690478,0));angle=math.radians(22);normal=Vector((math.cos(angle),math.sin(angle),0));axis=Vector((-math.sin(angle),math.cos(angle),0))
def local(p):
 q=p-centre;return Vector((q.dot(normal),q.dot(axis),p.z))
def world(p):return centre+normal*p[0]+axis*p[1]+Vector((0,0,p[2]))
owned=source.copy();owned.data=source.data.copy();owned.name='CKK_NEXT_FANLIGHT_retained_arch_frame';owned.data.name=owned.name;collection.objects.link(owned);owned_name=owned.name;source_name=source.name
for mod in list(owned.modifiers):
 if mod.type=='BEVEL':owned.modifiers.remove(mod)
bm=bmesh.new();bm.from_mesh(owned.data);removed=[]
for face in bm.faces:
 pts=[local(owned.matrix_world@v.co)for v in face.verts];r=[math.hypot(p.y,p.z-6.55)for p in pts]
 if len(pts)==4 and min(r)<.031 and max(r)>1.34 and all(23.07<p.x<23.12 and 6.52<p.z<7.92 for p in pts):removed.append(face)
assert len(removed)==5,len(removed)
bmesh.ops.delete(bm,geom=removed,context='FACES');orphans=[v for v in bm.verts if not v.link_faces]
if orphans:bmesh.ops.delete(bm,geom=orphans,context='VERTS')
bm.to_mesh(owned.data);bm.free();owned.data.update();source.hide_render=True;source.hide_set(True)
for layer in bpy.context.scene.view_layers:layer.update()
def probes():
 trees=[(o.name,BVHTree.FromPolygons([o.matrix_world@v.co for v in o.data.vertices],[tuple(f.vertices)for f in o.data.polygons],all_triangles=False))for o in collection.all_objects if o.type=='MESH' and not o.hide_render and len(o.data.polygons)]
 samples=[]
 for i in range(1,6):
  t=i*math.pi/6
  for r in [.45,.9]:samples.append((r*math.cos(t),6.55+r*math.sin(t),'CKK_V33_fanlight_glass'))
 for t in [math.pi*.25,math.pi*.75]:samples.append((1.35*math.cos(t),6.55+1.35*math.sin(t),owned_name))
 samples.append((.75,6.55,owned_name));checks=[]
 for y,z,expected in samples:
  start=world((24,y,z));best=None
  for name,tree in trees:
   hit=tree.ray_cast(start,-normal,3)
   if hit[0]is not None and(best is None or hit[3]<best[0]):best=(hit[3],name)
  assert best and best[1]==expected,(y,z,best,expected);checks.append({'point':list(start),'firstSurface':best[1]})
 return checks
checks=probes();assert all(fingerprint(bpy.data.objects[n])==v for n,v in originals.items())
component=OUT/'ckk-fanlight-component.blend';bpy.data.libraries.write(str(component),{owned},fake_user=True)
photo=ROOT/'data/建筑图片/CKK_Cheng Kin Ku Building/01_建筑实拍/exteriors_ckk_grimshaw_010.jpg'
audit={'baseline':str(BASE),'baselineSha256':hashlib.sha256(BASE.read_bytes()).hexdigest(),'originalFingerprints':originals,'originalVisibility':visibility,'ownedObjects':[owned.name],'archivedObjects':[source.name],'originalGeometryPreserved':True,'removedSpokeFaces':5,'scope':'Only5 unsupported radial metal spokes removed from central entrance fanlight; rim and spring rail retained.','reference':{'file':str(photo.relative_to(ROOT)),'sha256':hashlib.sha256(photo.read_bytes()).hexdigest(),'url':'https://grimshaw.global/projects/education-and-science/london-school-of-economics-new-academic-building/','captureDate':'unknown'},'firstSurfaceChecks':checks,'limitations':['Photograph supports unsplit arched glass; exact reflected interior finish and present-day condition unverified.','Original opening position, rim radius1.35m and frame thickness retained as existing estimates.','Wing segmental pediments, window widths, roof apertures, stone arch and glass material unchanged.']}
(OUT/'audit.json').write_text(json.dumps(audit,indent=2)+'\n')
open_baseline();collection=bpy.data.collections['CKK_EXTERIOR']
with bpy.data.libraries.load(str(component),link=False)as(src,dst):dst.objects=src.objects
for o in dst.objects:collection.objects.link(o)
bpy.data.objects[source_name].hide_render=True;bpy.data.objects[source_name].hide_set(True)
for layer in bpy.context.scene.view_layers:layer.update()
reloaded=probes();assert reloaded==checks;assert all(fingerprint(bpy.data.objects[n])==v for n,v in originals.items())
scene=bpy.context.scene;visible={o.name for o in collection.all_objects}
for o in scene.objects:
 if o.type=='MESH'and o.name not in visible:o.hide_render=True
focus=world((23.1,0,6.6));cd=bpy.data.cameras.new('CKK_FANLIGHT_REVIEW');cam=bpy.data.objects.new(cd.name,cd);scene.collection.objects.link(cam);cam.location=focus+normal*15;cam.rotation_euler=(focus-cam.location).to_track_quat('-Z','Y').to_euler();cd.type='ORTHO';cd.ortho_scale=5.8;scene.camera=cam;scene.render.engine='BLENDER_EEVEE';scene.render.resolution_x=1000;scene.render.resolution_y=1000;scene.render.resolution_percentage=100;scene.render.filepath=str(OUT/'reloaded-fanlight.png');bpy.ops.render.render(write_still=True)
proof={'componentSha256':hashlib.sha256(component.read_bytes()).hexdigest(),'savedComponentReopened':True,'originalGeometryPreserved':True,'originalObjectCount':len(originals),'fullModelSaved':False,'firstSurfaceChecks':reloaded,'bevelRemovedFromCopy':True}
(OUT/'verification.json').write_text(json.dumps(proof,indent=2)+'\n');print('CKK_FANLIGHT_RELOADED',len(originals),len(reloaded));bpy.ops.wm.quit_blender()
