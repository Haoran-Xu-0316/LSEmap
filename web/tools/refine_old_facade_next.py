"""Close unsupported gaps between Clare Market blue window heads and stone.

Run in Blender's Text Editor. Only five retained stone spandrel bottom edges change; all window geometry remains intact.
"""
from pathlib import Path
import array, hashlib, json, sys, math
import bpy, bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'result/blender/old_facade_next'
OUT.mkdir(parents=True,exist_ok=True)
BASE = ROOT/'result/blender/LSE_campus_detailed_v135.blend'
if not BASE.exists():
    BASE = max((ROOT/'result/blender').glob('LSE_campus_detailed_v[0-9]*.blend'),key=lambda p:int(p.stem.rsplit('v',1)[1]))
def open_baseline():
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE']
    previous=json.loads((OUT/'audit.json').read_text()) if (OUT/'audit.json').exists() else None
    if previous:
        for name in previous.get('ownedObjects',[]):
            obj=bpy.data.objects.get(name)
            if obj:
                mesh=obj.data;bpy.data.objects.remove(obj,do_unlink=True);mesh.use_fake_user=False
                if not mesh.users:bpy.data.meshes.remove(mesh)
        for name in previous.get('archivedObjects',[]):
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
collection=bpy.data.collections['OLD_EXTERIOR'];review=json.loads((OUT/'inspection.json').read_text())
origin=Vector(review['frame']['origin']);axis=Vector(review['frame']['right']);normal=Vector(review['frame']['outward'])
source=bpy.data.objects[review['stoneSource']];assert not source.hide_render
parts=review['upperSpandrels'];assert len(parts)==5
def local(p):
 d=p-origin;return Vector((d.dot(axis),d.dot(normal),p.z))
def world(x,d,z):return origin+axis*x+normal*d+Vector((0,0,z))
# Read actual visible perimeter caps, not nominal openings. Filling to9.60m
# would wrongly cover the upper half of the existing95mm blue frame.
cap_records=[]
for o in collection.all_objects:
 if o.type!='MESH' or o.hide_render or not any('blue' in m.name.lower() for m in o.data.materials):continue
 bm=bmesh.new();bm.from_mesh(o.data);seen=set()
 for seed in bm.verts:
  if seed in seen:continue
  chunk=[];todo=[seed];seen.add(seed)
  while todo:
   v=todo.pop();chunk.append(v)
   for e in v.link_edges:
    other=e.other_vert(v)
    if other not in seen:seen.add(other);todo.append(other)
  ps=[local(o.matrix_world@v.co) for v in chunk];lo=[min(p[i] for p in ps) for i in range(3)];hi=[max(p[i] for p in ps) for i in range(3)];cx=(lo[0]+hi[0])/2
  if 9.5<lo[2]<9.7 and hi[2]<9.8 and hi[2]-lo[2]<.12 and hi[0]-lo[0]>2.3:
   cap_records.append({'source':o.name,'centerX':cx,'bounds':[lo,hi]})
 bm.free()
assert len(cap_records)==5,cap_records
owned=source.copy();owned.data=source.data.copy();owned.name='OLD_NEXT_CLARE_sealed_window_head_stone';owned.data.name=owned.name;collection.objects.link(owned)
changed=[];caps=[]
for part in parts:
 cx=(part['bounds'][0][0]+part['bounds'][1][0])/2;cap=next(c for c in cap_records if abs(c['centerX']-cx)<.02);top=cap['bounds'][1][2];assert abs(top-9.6475)<.001
 targets=[i for i in part['vertexIndices'] if abs((source.matrix_world@source.data.vertices[i].co).z-9.8)<.001];assert len(targets)==4
 for i in targets:
  point=owned.matrix_world@owned.data.vertices[i].co;point.z=top;owned.data.vertices[i].co=owned.matrix_world.inverted()@point;changed.append(i)
 caps.append(cap)
assert len(changed)==20;owned.data.update()
assert all(tuple(v.co)==tuple(owned.data.vertices[i].co) for i,v in enumerate(source.data.vertices) if i not in changed)
def structure(o):
 h=hashlib.sha256()
 for data,field,kind,w in ((o.data.loops,'vertex_index','i',1),(o.data.polygons,'material_index','i',1)):
  a=array.array(kind,[0])*(len(data)*w);data.foreach_get(field,a);h.update(a.tobytes())
 for layer in o.data.uv_layers:
  a=array.array('f',[0])*(len(layer.data)*2);layer.data.foreach_get('uv',a);h.update(a.tobytes())
 h.update(str([m.name for m in o.data.materials]).encode());return h.hexdigest()
assert structure(owned)==structure(source)
def cast(objects,points):
 vertices=[];faces=[];names=[]
 for o in objects:
  k=len(vertices);vertices.extend(o.matrix_world@v.co for v in o.data.vertices);faces.extend(tuple(k+i for i in p.vertices) for p in o.data.polygons);names.extend([o.name]*len(o.data.polygons))
 tree=BVHTree.FromPolygons(vertices,faces);records=[]
 for label,x,z in points:
  hit=tree.ray_cast(world(x,.85,z),-normal,1.4);records.append({'label':label,'x':x,'z':z,'firstObject':names[hit[2]] if hit[2] is not None else None})
 return records
visible=lambda:[o for o in collection.all_objects if o.type=='MESH' and not o.hide_render]
fill=[('gap-'+str(i),r['x'],r['z']) for i,r in enumerate(review['gapProbes'])]
kept=[('kept-'+str(i)+'-'+str(z),r['x'],z) for i,r in enumerate(review['gapProbes']) for z in (9.3,9.6,9.9)]
before=cast([o for o in visible() if o!=owned],fill+kept);assert all(r['firstObject'] is None for r in before[:10])
source.hide_render=True;source.hide_set(True);after=cast(visible(),fill+kept);assert all(r['firstObject']==owned.name for r in after[:10])
assert [r['firstObject'].replace(owned.name,source.name) if r['firstObject'] else None for r in after[10:]]==[r['firstObject'] for r in before[10:]]
assert all(fingerprint(bpy.data.objects[n])==h for n,h in originals.items())
component=OUT/'old-clare-window-head-component.blend';bpy.data.libraries.write(str(component),{owned},fake_user=True,compress=True)
ref=ROOT/'result/blender/stage89/frith-front-study.png';pdf=ROOT/'data/collections/old-clare-reference/architectural-sculpture-2010.pdf';user=ROOT/'data/collections/public-realm-2026/user-references/reference-08.png'
audit={'baselineSha256':hashlib.sha256(BASE.read_bytes()).hexdigest(),'originalFingerprints':originals,'originalVisibility':visibility,'ownedObjects':[owned.name],'archivedObjects':[source.name],'archiveObjects':[source.name],'changes':[{'source':source.name,'owned':owned.name,'changedVertices':20,'unchangedVertices':len(source.data.vertices)-20}],'windowCaps':caps,'registration':review['frame'],'oldStoneBottom':9.8,'newStoneBottom':caps[0]['bounds'][1][2],'beforeProbes':before,'afterProbes':after,'references':[{'local':str(ref.relative_to(ROOT)),'sha256':hashlib.sha256(ref.read_bytes()).hexdigest(),'underlyingPdf':str(pdf.relative_to(ROOT)),'underlyingPdfSha256':hashlib.sha256(pdf.read_bytes()).hexdigest(),'url':'https://jeremyhaslam.wordpress.com/wp-content/uploads/2010/01/architectural-sculpture-part-2-8-pdf.pdf','date':'Published2010; photograph capture date unknown','evidence':'Study photographC registers the complete five-bay frontage: upper blue heads meet continuous stone above, with no open checkerboard strips.'},{'local':str(user.relative_to(ROOT)),'sha256':hashlib.sha256(user.read_bytes()).hexdigest(),'date':'User photograph capture date unknown','evidence':'Corroborates five blue bays and stone pier registration; cropped uppermost heads are not treated as independent measured evidence.'}],'limitations':['All metre levels are inherited model estimates; the change closes a native defect against existing frame geometry, not a measured facade dimension.','No colour, glazing, divisions, relief, entrance, roof or other elevation changes.','Study is historical and not a current refurbishment survey.','Original wall UVs/material slots retained; continuous upper spandrel only extends downward0.1525m.']}
(OUT/'audit.json').write_text(json.dumps(audit,indent=2)+'\n');print('OLD_CLARE_HEAD_COMPONENT_SAVED',flush=True)
open_baseline();collection=bpy.data.collections['OLD_EXTERIOR'];source=bpy.data.objects[audit['archivedObjects'][0]]
with bpy.data.libraries.load(str(component),link=False) as (src,dst):dst.objects=audit['ownedObjects']
owned=dst.objects[0];collection.objects.link(owned)
for i,m in enumerate(source.data.materials):owned.data.materials[i]=m
source.hide_render=True;source.hide_set(True)
for sc in bpy.data.scenes:
 for layer in sc.view_layers:layer.update()
assert all(fingerprint(bpy.data.objects[n])==h for n,h in originals.items());assert structure(owned)==structure(source);assert cast(visible(),fill+kept)==after
scene=bpy.data.scenes['00_CAMPUS_COMPLETE']
for o in scene.objects:
 if o.type=='MESH' and o.name not in {obj.name for obj in collection.all_objects}:o.hide_render=True
focus=world(0,0,8);camera_data=bpy.data.cameras.new('OLD_NEXT_CLARE_preview');camera=bpy.data.objects.new(camera_data.name,camera_data);scene.collection.objects.link(camera);camera.location=focus+normal*25;camera.rotation_euler=(focus-camera.location).to_track_quat('-Z','Y').to_euler();camera_data.type='ORTHO';camera_data.ortho_scale=18;scene.camera=camera
scene.render.engine='BLENDER_EEVEE';scene.render.resolution_x=1200;scene.render.resolution_y=700;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG';scene.render.filepath=str(OUT/'reloaded-clare-window-heads.png');bpy.ops.render.render(write_still=True)
v={'componentSha256':hashlib.sha256(component.read_bytes()).hexdigest(),'baselineUnchanged':hashlib.sha256(BASE.read_bytes()).hexdigest()==audit['baselineSha256'],'savedComponentReopened':True,'originalGeometryPreserved':True,'originalObjectCount':len(originals),'ownedTopologyUVMaterialSlotsMatchOriginal':True,'reloadedProbes':after,'nativeRender':'reloaded-clare-window-heads.png'}
(OUT/'verification.json').write_text(json.dumps(v,indent=2)+'\n');print('OLD_CLARE_HEAD_COMPONENT_RELOADED_VERIFIED',flush=True)
