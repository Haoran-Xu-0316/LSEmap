"""Correct No.50's photographed tripartite sash and recessed stone arch.

Run in Blender's Text Editor. This saves a compact owned component, preserving
all original geometry, matrices, material slots and UVs. The upper window shown
in the official photo is the only window whose pattern is newly calibrated.
"""
from pathlib import Path
import array, hashlib, json, math, sys
import bpy, bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'result/blender/lincoln50_next';OUT.mkdir(parents=True,exist_ok=True)
BASE=ROOT/'result/blender/LSE_campus_detailed_v121.blend'
if not BASE.exists():BASE=max((ROOT/'result/blender').glob('LSE_campus_detailed_v[0-9]*.blend'),key=lambda p:int(p.stem.rsplit('v',1)[1]))
bpy.ops.wm.open_mainfile(filepath=str(BASE))
bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE']
collection=bpy.data.collections['50L_EXTERIOR']
previous=json.loads((OUT/'audit.json').read_text()) if (OUT/'audit.json').exists() else None
if previous:
    for name in previous['ownedObjects']:
        obj=bpy.data.objects.get(name)
        if obj:
            mesh=obj.data;bpy.data.objects.remove(obj,do_unlink=True);mesh.use_fake_user=False
            if not mesh.users:bpy.data.meshes.remove(mesh)
    for name in previous['archivedObjects']:
        obj=bpy.data.objects.get(name)
        if obj:
            state=previous['originalVisibility'][name]
            obj.hide_render,obj.hide_viewport=state[:2];obj.hide_set(state[2])
def fingerprint(obj):
    h=hashlib.sha256(str([list(r)for r in obj.matrix_world]).encode())
    if obj.type=='MESH':
        for data,field,kind,count in ((obj.data.vertices,'co','f',3),(obj.data.loops,'vertex_index','i',1),(obj.data.polygons,'material_index','i',1)):
            values=array.array(kind,[0])*(len(data)*count);data.foreach_get(field,values);h.update(values.tobytes())
        for layer in obj.data.uv_layers:
            values=array.array('f',[0])*(len(layer.data)*2);layer.data.foreach_get('uv',values);h.update(values.tobytes())
    h.update(str([m.name if m else None for m in getattr(obj.data,'materials',[])]).encode());return h.hexdigest()
originals={o.name:fingerprint(o)for o in bpy.data.objects}
visibility={o.name:[o.hide_render,o.hide_viewport,o.hide_get()]for o in bpy.data.objects}
# Registered No.50 portal basis, verified against the current native glass.
# Keep these stable coordinates independent of historical working directories.
PORTAL_ORIGIN=(-50.66649627685547,50.34284591674805,0.0)
PORTAL_RIGHT=(0.44621801376342773,-0.8949243426322937,0.0)
PORTAL_OUTWARD=(-0.8949243426322937,-0.44621801376342773,0.0)
origin,right,normal=map(Vector,(PORTAL_ORIGIN,PORTAL_RIGHT,PORTAL_OUTWARD))
def point(x,d,z):return origin+right*x+normal*d+Vector((0,0,z))
def local(p):
    delta=p-origin;return Vector((delta.dot(right),delta.dot(normal),p.z))
source=bpy.data.objects['50L_D5_vertical_mullion_white']
bm=bmesh.new();bm.from_mesh(source.data);bm.verts.ensure_lookup_table();seen=set();remove=[]
for seed in bm.verts:
    if seed in seen:continue
    pending=[seed];island=[];seen.add(seed)
    while pending:
        v=pending.pop();island.append(v)
        for edge in v.link_edges:
            other=edge.other_vert(v)
            if other not in seen:seen.add(other);pending.append(other)
    center=sum((local(source.matrix_world@v.co)for v in island),Vector())/len(island)
    if abs(center.x)<.05 and abs(center.z-5.31)<.05:remove.extend(island)
assert len(remove)==8,'Expected exactly the one photographed window mullion'
retained=source.copy();retained.data=source.data.copy();retained.name='50L_NEXT_retained_mullions';retained.data.name=retained.name;collection.objects.link(retained)
bmesh.ops.delete(bm,geom=remove,context='VERTS');bm.to_mesh(retained.data);bm.free()
owned=[retained];archived=[source.name]
source.hide_render=True;source.hide_set(True)
sys.path.insert(0,str(Path(__file__).resolve().parent))
from facade_geometry import Geometry,materials
materials.clear();materials['frame']=bpy.data.materials['COOPERS_white'];materials['stone']=bpy.data.materials['50L_V72_stone']
groups={}
def batch(key):
    if key not in groups:groups[key]=Geometry('50L','next_'+key,key)
    return groups[key]
def box(key,x,d,z,w,t,h):batch(key).box(point(x,d,z),(w,t,h),math.atan2(right.y,right.x))
# Locate the photographed sash's real bounds from its existing glass vertices.
glass=bpy.data.objects['50L_D5_window_glass']
points=[local(glass.matrix_world@v.co)for v in glass.data.vertices]
window=[p for p in points if abs(p.x)<1.20 and 4.29<p.z<6.33]
assert len(window)==8,window
left,right_edge=min(p.x for p in window),max(p.x for p in window)
width=right_edge-left;bottom,top=min(p.z for p in window),max(p.z for p in window)
for j in (1,2):box('frame',left+width*j/3,-.01,(bottom+top)/2,.085,.13,top-bottom)
# Continuous barrel returns stop behind the existing timber arch and do not
# project into the clear fanlight. Photographic dimensions remain estimates.
radius=.775;spring=2.70
for j in range(64):
    a,b=j*math.pi/64,(j+1)*math.pi/64
    inner,outer=radius,radius+.050
    vertices=[point(r*math.cos(t),d,spring+r*math.sin(t))for d in (-.105,.285)for r,t in ((inner,a),(outer,a),(outer,b),(inner,b))]
    batch('stone').add(vertices,[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)])
for group in groups.values():
    obj=group.finish();obj.name='50L_NEXT_'+obj.name.removeprefix('50L_D5_');obj.data.name=obj.name
    for modifier in list(obj.modifiers):obj.modifiers.remove(modifier)
    owned.append(obj)
def aperture_proof():
    vertices,faces,owners=[],[],[]
    for obj in collection.all_objects:
        if obj.type!='MESH' or obj.hide_render:continue
        # Glass is the receiving surface, so its name remains in the ray report.
        base=len(vertices);vertices.extend(obj.matrix_world@v.co for v in obj.data.vertices)
        faces.extend(tuple(base+i for i in p.vertices)for p in obj.data.polygons);owners.extend([obj.name]*len(obj.data.polygons))
    tree=BVHTree.FromPolygons(vertices,faces);result=[]
    probes=[('window',left+width*(i+.5)/3,z)for i in range(3)for z in (4.78,5.82)]
    probes += [('fanlight',x,z)for x,z in ((-.35,2.95),(0,3.10),(.35,2.95),(0,3.35))]
    for kind,x,z in probes:
        hit=tree.ray_cast(point(x,.60,z),-normal,1.00)
        name=owners[hit[2]] if hit[2] is not None else None
        assert name and 'glass' in name,(kind,x,z,name)
        result.append({'kind':kind,'x':x,'z':z,'firstSurface':name})
    return result
proof=aperture_proof();assert all(fingerprint(bpy.data.objects[n])==v for n,v in originals.items())
component=OUT/'lincoln50-component.blend';bpy.data.libraries.write(str(component),set(owned),fake_user=True,compress=True)
audit={'baselineSha256':hashlib.sha256(BASE.read_bytes()).hexdigest(),'ownedObjects':[o.name for o in owned],'archivedObjects':archived,'originalFingerprints':originals,'originalVisibility':visibility,'correctedWindowCount':1,'windowColumns':3,'windowRows':2,'archReturnSegments':64,'apertureProbes':proof,'sources':[{'local':'data/建筑图片/50L_50 Lincoln_s Inn Fields/01_建筑实拍/exteriors_lse_estate_014.jpg','url':'https://info.lse.ac.uk/staff/divisions/estates-division/lse-estate/LSE-Estate','date':'Official photograph, capture date unknown','sha256':'48df53fabdefca628e6ea2e5f59f6de84123d521729f4cc490b76d9b84499f04'},{'local':'data/建筑图片/50L_50 Lincoln_s Inn Fields/01_建筑实拍/small_round5_50L_handbook-000.png','url':'https://info.lse.ac.uk/staff/divisions/estates-division/Assets/Documents/Property-and-Space/LSE-Property-Handbook.pdf','date':'2025/26 handbook, photograph date unspecified','page':28}],'limitations':['Only one fully visible sash pattern calibrated; total bay count and full building massing remain unverified','Existing window positions, dimensions and unseen elevations retained','Arch reveal dimensions estimated from photographs','Existing stone and timber material colors retained; photographic weathering is not a measured color survey','No new interior reconstruction']}
(OUT/'audit.json').write_text(json.dumps(audit,indent=2)+'\n');print('LINCOLN50_COMPONENT_SAVED',component.stat().st_size,flush=True)
bpy.ops.wm.open_mainfile(filepath=str(BASE));bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE'];collection=bpy.data.collections['50L_EXTERIOR']
with bpy.data.libraries.load(str(component),link=False)as (library,target):target.objects=audit['ownedObjects']
for obj in target.objects:collection.objects.link(obj)
for name in archived:bpy.data.objects[name].hide_render=True;bpy.data.objects[name].hide_set(True)
assert all(fingerprint(bpy.data.objects[n])==v for n,v in originals.items())
reloaded=aperture_proof()
# Native close rendering verifies the actual appended component in context.
scene=bpy.context.scene
for obj in scene.objects:
    if obj.type=='MESH' and obj.name not in collection.all_objects:obj.hide_render=True
camera_data=bpy.data.cameras.new('50L_NEXT_verify_camera');camera=bpy.data.objects.new(camera_data.name,camera_data);scene.collection.objects.link(camera)
camera.location=point(0,15,7);target_point=point(0,0,3.8);camera.rotation_euler=(target_point-camera.location).to_track_quat('-Z','Y').to_euler();camera_data.type='ORTHO';camera_data.ortho_scale=8;scene.camera=camera
scene.render.engine='BLENDER_EEVEE';scene.render.resolution_x=900;scene.render.resolution_y=900;scene.render.resolution_percentage=100;scene.render.filepath=str(OUT/'native-window-portal.png');bpy.ops.render.render(write_still=True)
verification={'componentSha256':hashlib.sha256(component.read_bytes()).hexdigest(),'baselineUnchanged':hashlib.sha256(BASE.read_bytes()).hexdigest()==audit['baselineSha256'],'originalGeometryPreserved':True,'savedComponentReopened':True,'reloadedApertureProbes':reloaded,'render':'native-window-portal.png'}
(OUT/'verification.json').write_text(json.dumps(verification,indent=2)+'\n');print('LINCOLN50_COMPONENT_RELOADED_VERIFIED',flush=True)
