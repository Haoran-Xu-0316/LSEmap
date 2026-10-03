"""Correct the two photographed CKK wing segmental pediments.

Run in Blender's Text Editor. Only the two upper hood caps are replaced. Curve and stone-section dimensions remain estimates.
"""
from pathlib import Path
import array, hashlib, json, sys, math
import bpy, bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'result/blender/ckk_pediment_next'
OUT.mkdir(parents=True,exist_ok=True)
BASE = ROOT/'result/blender/LSE_campus_detailed_v130.blend'
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
collection=bpy.data.collections['CKK_EXTERIOR'];source=bpy.data.objects['CKK_NEXT_WING_window_hoods'];assert not source.hide_render
centre=Vector((-110.49102024587766,77.56014819690478,0));angle=math.radians(22);normal=Vector((math.cos(angle),math.sin(angle),0));axis=Vector((-math.sin(angle),math.cos(angle),0))
def local(p):
 q=p-centre;return Vector((q.dot(normal),q.dot(axis),p.z))
def world(p):return centre+normal*p[0]+axis*p[1]+Vector((0,0,p[2]))
retained=source.copy();retained.data=source.data.copy();retained.name='CKK_NEXT_PEDIMENT_retained_hood_bases';retained.data.name=retained.name;collection.objects.link(retained)
bm=bmesh.new();bm.from_mesh(retained.data);seen=set();remove=[];caps=[]
for seed in bm.verts:
 if seed in seen:continue
 part=[];todo=[seed];seen.add(seed)
 while todo:
  v=todo.pop();part.append(v)
  for edge in v.link_edges:
   other=edge.other_vert(v)
   if other not in seen:seen.add(other);todo.append(other)
 points=[local(retained.matrix_world@v.co) for v in part];mean=sum(points,Vector())/len(points)
 if abs(abs(mean.y)-12.65)<.01 and min(p.z for p in points)>12.775:
  caps.append({'x0':min(p.x for p in points),'x1':max(p.x for p in points),'y0':min(p.y for p in points),'y1':max(p.y for p in points),'z0':min(p.z for p in points),'z1':max(p.z for p in points)});remove.extend(part)
assert len(caps)==2 and len(remove)==16
bmesh.ops.delete(bm,geom=remove,context='VERTS');bm.to_mesh(retained.data);bm.free();assert len(retained.data.vertices)==96
verts=[];faces=[]
def solid(profile,x0,x1):
 count=len(profile);offset=len(verts);verts.extend(world((x,y,z)) for x in (x0,x1) for y,z in profile)
 faces.extend([tuple(offset+i for i in reversed(range(count))),tuple(offset+count+i for i in range(count))]);faces.extend((offset+i,offset+(i+1)%count,offset+count+(i+1)%count,offset+count+i) for i in range(count))
base=12.77;rise=.50;thickness=.08;segments=32
for cap in caps:
 ycenter=(cap['y0']+cap['y1'])/2;half=(cap['y1']-cap['y0'])/2;radius=(half*half+rise*rise)/(2*rise);cz=base+rise-radius
 curve=lambda y:cz+math.sqrt(max(0,radius*radius-y*y))
 for i in range(segments):
  y0=-half+2*half*i/segments;y1=-half+2*half*(i+1)/segments;z0=curve(y0);z1=curve(y1)
  solid([(ycenter+y0,z0),(ycenter+y1,z1),(ycenter+y1,z1-thickness),(ycenter+y0,z0-thickness)],cap['x0'],cap['x1'])
 # Plain recessed tympanum inside the moulding. No unverified carving or grille.
 inner_half=math.sqrt(radius*radius-(base+thickness-cz)**2)
 contour=[(ycenter-inner_half,base),(ycenter+inner_half,base)]
 contour.extend((ycenter+y,curve(y)-thickness) for y in [inner_half-2*inner_half*i/segments for i in range(1,segments)])
 solid(contour,cap['x0'],cap['x1']-.07)
mesh=bpy.data.meshes.new('CKK_NEXT_PEDIMENT_curved_stone');mesh.from_pydata(verts,[],faces);mesh.materials.append(source.data.materials[0]);mesh.update();new=bpy.data.objects.new(mesh.name,mesh);collection.objects.link(new)
bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free();mesh.update()
assert all(p.area>1e-9 for p in mesh.polygons)
uv=mesh.uv_layers.new(name='SurfaceUV')
for p in mesh.polygons:
 u=Vector((0,0,1)).cross(p.normal)
 if u.length<1e-6:u=Vector((1,0,0))
 u.normalize();v=p.normal.cross(u).normalized()
 for loop in p.loop_indices:
  point=mesh.vertices[mesh.loops[loop].vertex_index].co;uv.data[loop].uv=(point.dot(u),point.dot(v))
owned=[retained.name,new.name];archived=[source.name]
def tree(objects):
 vertices=[];polygons=[];owners=[]
 for o in objects:
  offset=len(vertices);vertices.extend(o.matrix_world@v.co for v in o.data.vertices);polygons.extend(tuple(offset+i for i in p.vertices) for p in o.data.polygons);owners.extend([o.name]*len(o.data.polygons))
 return BVHTree.FromPolygons(vertices,polygons),owners
probes=[]
for lo,hi in [(9.3,12.5),(13.8,16.5),(17.9,20.5)]:
 for yc in [-12.65,12.65]:
  for side in [-1,1]:probes.append({'y':yc+side*.55,'z':lo+(hi-lo)*.7})
def cast(objects):
 bvh,names=tree(objects);results=[]
 for p in probes:
  hit=bvh.ray_cast(world((26,p['y'],p['z'])),-normal,5);results.append({**p,'firstObject':names[hit[2]] if hit[2] is not None else None})
 return results
before=cast([o for o in collection.all_objects if o.type=='MESH' and not o.hide_render and o.name not in owned]);assert all(p['firstObject']=='CKK_NEXT_WING_recessed_glass' for p in before)
source.hide_render=True;source.hide_set(True);after=cast([o for o in collection.all_objects if o.type=='MESH' and not o.hide_render]);assert after==before
assert all(fingerprint(bpy.data.objects[n])==v for n,v in originals.items())
component=OUT/'ckk-pediment-component.blend';bpy.data.libraries.write(str(component),{retained,new},fake_user=True,compress=True)
ref=ROOT/'data/建筑图片/CKK_Cheng Kin Ku Building/01_建筑实拍/exteriors_ckk_grimshaw_010.jpg'
audit={'baselineSha256':hashlib.sha256(BASE.read_bytes()).hexdigest(),'originalFingerprints':originals,'originalVisibility':visibility,'ownedObjects':owned,'archivedObjects':archived,'replacedUpperCaps':caps,'retainedHoodCuboids':12,'newCurvedPediments':2,'glassFirstBeforeProbes':before,'glassFirstAfterProbes':after,'references':[{'local':str(ref.relative_to(ROOT)),'sha256':hashlib.sha256(ref.read_bytes()).hexdigest(),'url':'https://grimshaw.global/projects/education-and-science/london-school-of-economics-new-academic-building/','date':'2008 project; photograph capture date unknown'}],'estimatedDimensions':{'baseZ':base,'rise':rise,'mouldingVerticalThickness':thickness,'span':'Inherited widths of removed hood caps','tympanumFrontRecess':.07},'limitations':['Only curved form of two wing principal-storey upper hood caps is photo-confirmed; rise, section, depth and exact curve remain estimates','Plain tympana omit unmeasured decorative carving and vent grilles','Central five straight hoods, all lower bases, existing window widths/mullions, roof apertures, entry and interior unchanged']}
(OUT/'audit.json').write_text(json.dumps(audit,indent=2)+'\n');print('CKK_PEDIMENT_COMPONENT_SAVED',component.stat().st_size,flush=True)
bpy.ops.wm.open_mainfile(filepath=str(BASE));scene=bpy.data.scenes['00_CAMPUS_COMPLETE'];bpy.context.window.scene=scene;collection=bpy.data.collections['CKK_EXTERIOR'];source=bpy.data.objects[archived[0]]
with bpy.data.libraries.load(str(component),link=False) as (src,dst):dst.objects=owned
for obj in dst.objects:
 collection.objects.link(obj)
 for i,mat in enumerate(source.data.materials):obj.data.materials[i]=mat
source.hide_render=True;source.hide_set(True)
for sc in bpy.data.scenes:
 for layer in sc.view_layers:layer.update()
assert all(fingerprint(bpy.data.objects[n])==v for n,v in originals.items());reloaded=cast([o for o in collection.all_objects if o.type=='MESH' and not o.hide_render]);assert reloaded==before
for obj in scene.objects:
 if obj.type=='MESH' and obj.name not in {o.name for o in collection.all_objects}:obj.hide_render=True
focus=world((23,0,12.5));camdata=bpy.data.cameras.new('CKK_NEXT_PEDIMENT_preview_camera');cam=bpy.data.objects.new(camdata.name,camdata);scene.collection.objects.link(cam);cam.location=focus+normal*40+Vector((0,0,.5));cam.rotation_euler=(focus-cam.location).to_track_quat('-Z','Y').to_euler();camdata.type='ORTHO';camdata.ortho_scale=36;scene.camera=cam
scene.render.engine='BLENDER_EEVEE';scene.render.resolution_x=1600;scene.render.resolution_y=800;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG';scene.render.filepath=str(OUT/'reloaded-pediments.png');bpy.ops.render.render(write_still=True)
verification={'componentSha256':hashlib.sha256(component.read_bytes()).hexdigest(),'baselineUnchanged':hashlib.sha256(BASE.read_bytes()).hexdigest()==audit['baselineSha256'],'savedComponentReopened':True,'originalGeometryPreserved':True,'reloadedGlassFirstProbes':reloaded,'nativeRender':'reloaded-pediments.png'}
(OUT/'verification.json').write_text(json.dumps(verification,indent=2)+'\n');print('CKK_PEDIMENT_COMPONENT_RELOADED_VERIFIED',flush=True)
