"""Remove roof surfaces that incorrectly seal Lakatos' estimated dormer windows.

Run in Blender's Text Editor. Export only this component, never a full campus.
Official photos establish projecting dormers; roof contour, positions and counts
are retained estimates, not a surveyed architectural reconstruction.
"""
from pathlib import Path
import array
import hashlib
import json
import sys
import bpy
import bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'result/blender/lak_next'
OUT.mkdir(parents=True, exist_ok=True)
BASELINE = ROOT/'result/blender/LSE_campus_detailed_v120.blend'
previous = json.loads((OUT/'audit.json').read_text()) if (OUT/'audit.json').exists() else None
if not BASELINE.exists():
    BASELINE = max((ROOT/'result/blender').glob('LSE_campus_detailed_v[0-9]*.blend'), key=lambda p: int(p.stem.rsplit('v',1)[1]))
bpy.ops.wm.open_mainfile(filepath=str(BASELINE))
def restore():
    if previous:
        for name in previous['ownedObjects']:
            obj = bpy.data.objects.get(name)
            if obj:
                mesh = obj.data
                bpy.data.objects.remove(obj, do_unlink=True)
                if mesh.users == 0:
                    bpy.data.meshes.remove(mesh)
        for name in previous['archivedObjects']:
            state = previous['originalVisibility'][name]
            obj = bpy.data.objects[name]
            obj.hide_render, obj.hide_viewport = state['hideRender'], state['hideViewport']
            obj.hide_set(state['hideSet'])
restore()
collection = bpy.data.collections['LAK_EXTERIOR']
bpy.context.window.scene = bpy.data.scenes['00_CAMPUS_COMPLETE']
def fingerprint(obj):
    digest = hashlib.sha256(str([list(row) for row in obj.matrix_world]).encode())
    if obj.type == 'MESH':
        digest.update(array.array('f',[c for v in obj.data.vertices for c in v.co]).tobytes())
        digest.update(array.array('i',[loop.vertex_index for loop in obj.data.loops]).tobytes())
        for layer in obj.data.uv_layers:
            digest.update(array.array('f',[c for uv in layer.data for c in uv.uv]).tobytes())
    digest.update(str([m.name if m else None for m in getattr(obj.data,'materials',[])]).encode())
    return digest.hexdigest()
originals = list(bpy.data.objects)
before = {o.name:fingerprint(o) for o in originals}
visibility = {o.name:{'hideRender':o.hide_render,'hideViewport':o.hide_viewport,'hideSet':o.hide_get()} for o in originals}
ring = next(b for b in json.loads((ROOT/'result/blender/site_geometry.json').read_text())['buildings'] if b['code']=='LAK')['rings'][0]
roof = bpy.data.objects['LAK_D5_hipped_slate_roof']
faces = [[roof.matrix_world@roof.data.vertices[i].co for i in polygon.vertices] for polygon in roof.data.polygons]
facades = []
for wall,count in ((0,2),(1,4)):
    p,q = Vector((*ring[wall],0)), Vector((*ring[wall+1],0))
    axis = (q-p).normalized()
    normal = Vector((-axis.y,axis.x,0))
    # Original outer/inner roof corners determine the retained roof slope.
    outer, inner = faces[wall][0], faces[wall][-1]
    slope = (inner.z-outer.z)/((inner-outer).dot(normal))
    facades.append({'wall':wall,'p':p,'axis':axis,'normal':normal,'length':(q-p).length,'count':count,'slope':slope,'backDepth':(16.95-15.72)/slope})
def point(f,x,z,d):
    return f['p']+f['axis']*x+f['normal']*d+Vector((0,0,z))
def tree():
    vertices, polygons, owners = [],[],[]
    for obj in collection.all_objects:
        if obj.type!='MESH' or obj.hide_render:
            continue
        base=len(vertices)
        vertices.extend(obj.matrix_world@v.co for v in obj.data.vertices)
        polygons.extend(tuple(base+i for i in poly.vertices) for poly in obj.data.polygons)
        owners.extend([obj.name]*len(obj.data.polygons))
    return BVHTree.FromPolygons(vertices,polygons),owners
probes = [(f,bay,z,(bay+.5)*f['length']/f['count']+.12) for f in facades for bay in range(f['count']) for z in (15.95,16.15,16.45,16.7)]
def aperture_results():
    t,owners=tree()
    result=[]
    for f,bay,z,x in probes:
        location,n,index,distance=t.ray_cast(point(f,x,z,2),-f['normal'],4)
        assert index is not None
        result.append({'wall':f['wall'],'bay':bay,'height':z,'firstSurface':owners[index],'distance':distance,'clear':'glass' in owners[index]})
    return result
apertures_before = aperture_results()
assert sum(not p['clear'] for p in apertures_before)==14
# Subtract each dormer volume from each original planar roof polygon. This
# preserves every roof surface outside the openings instead of lowering it.
def clip(poly, signed_distance, inside):
    if not poly:
        return []
    result=[]
    for a,b in zip(poly,poly[1:]+poly[:1]):
        da,db=signed_distance(a),signed_distance(b)
        ina,inb=(da>=-1e-8,db>=-1e-8) if inside else (da<=1e-8,db<=1e-8)
        if ina:
            result.append(a)
        if ina!=inb and abs(da-db)>1e-12:
            result.append(a+(b-a)*(da/(da-db)))
    return result
for f in facades:
    for bay in range(f['count']):
        center=(bay+.5)*f['length']/f['count']
        def x(v): return (v-f['p']).dot(f['axis'])
        def d(v): return (v-f['p']).dot(f['normal'])
        planes=[lambda v:x(v)-(center-.49),lambda v:(center+.49)-x(v),lambda v:d(v)-f['backDepth']+.015,lambda v:.10-d(v),lambda v:16.95-v.z]
        retained=[]
        for poly in faces:
            remaining=poly
            for plane in planes:
                outside=clip(remaining,plane,False)
                if len(outside)>=3:
                    retained.append(outside)
                remaining=clip(remaining,plane,True)
                if len(remaining)<3:
                    break
        faces=retained
owned=[]
def mesh_object(name,polygons,material):
    vertices,indices=[],[]
    for poly in polygons:
        base=len(vertices);vertices.extend(poly);indices.append(tuple(range(base,base+len(poly))))
    mesh=bpy.data.meshes.new('LAK_NEXT_'+name)
    mesh.from_pydata(vertices,[],indices);mesh.materials.append(material)
    bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=bm.faces);bm.to_mesh(mesh);bm.free();mesh.update()
    uv=mesh.uv_layers.new(name='SurfaceUV')
    for polygon in mesh.polygons:
        coords=[mesh.vertices[i].co for i in polygon.vertices]
        origin=coords[0];axis=(coords[1]-origin).normalized();normal=polygon.normal;up=normal.cross(axis)
        for loop in polygon.loop_indices:
            v=mesh.vertices[mesh.loops[loop].vertex_index].co-origin
            uv.data[loop].uv=(v.dot(axis),v.dot(up))
    obj=bpy.data.objects.new(mesh.name,mesh);collection.objects.link(obj);owned.append(obj)
    return obj
slate=roof.data.materials[0]
mesh_object('roof_with_dormer_openings',faces,slate)
cheeks,caps,aprons=[],[],[]
def box_faces(f,x,z,w,h,d,offset):
    vertices=[point(f,x+sx*w/2,z+sz*h/2,offset+sd*d/2) for sx,sd,sz in ((-1,-1,-1),(-1,-1,1),(-1,1,-1),(-1,1,1),(1,-1,-1),(1,-1,1),(1,1,-1),(1,1,1))]
    return [[vertices[i] for i in face] for face in ((0,4,6,2),(1,3,7,5),(0,1,5,4),(2,6,7,3),(0,2,3,1),(4,5,7,6))]
for f in facades:
    for bay in range(f['count']):
        x=(bay+.5)*f['length']/f['count'];back=f['backDepth']
        for side in (-1,1):
            profile=[(.02,15.72),(-.55,15.70),(-.55,16.95),(back,16.95)]
            vertices=[point(f,x+side*.50+dx,z,d) for dx in (-.025,.025) for d,z in profile]
            cheeks.extend([[vertices[i] for i in face] for face in ((0,1,2,3),(4,7,6,5),(0,4,5,1),(1,5,6,2),(2,6,7,3),(3,7,4,0))])
        caps.extend(box_faces(f,x,16.96,1.14,.10,abs(back+.30)+.08,(back-.30)/2))
        aprons.extend(box_faces(f,x,15.725,.98,.03,.60,-.27))
mesh_object('dormer_closed_cheeks',cheeks,slate)
mesh_object('dormer_roof_caps',caps,slate)
mesh_object('dormer_lower_aprons',aprons,slate)
archived=['LAK_D5_hipped_slate_roof','LAK_D5_dormer_cap_slate']
for name in archived:
    bpy.data.objects[name].hide_render=True;bpy.data.objects[name].hide_set(True)
assert all(fingerprint(o)==before[o.name] for o in originals)
apertures_after=aperture_results()
assert all(p['clear'] for p in apertures_after),apertures_after
component=OUT/'lakatos-roof-component.blend'
bpy.data.libraries.write(str(component),set(owned),fake_user=True,compress=True)
sources=[{'url':'https://info.lse.ac.uk/staff/divisions/estates-division/lse-estate/LSE-Estate','local':'data/建筑图片/LAK_Lakatos Building/01_建筑实拍/exteriors_lse_estate_010.jpg','date':'Undated official photograph'}, {'url':'https://www.lse.ac.uk/philosophy','local':'data/建筑图片/LAK_Lakatos Building/01_建筑实拍/small_buildings_round3_small3_008.webp','date':'Official photograph available September 2026; capture date unspecified'}, {'url':'https://www.geograph.org.uk/photo/668683','date':'23 January 2008','author':'Nigel Cox','local':'data/建筑图片/LAK_Lakatos Building/01_建筑实拍/campus_photos_round3_LRB_LAK_geograph_668683.jpg'}]
limits=['Existing 3/7 facade bays, 2/4 dormer counts, roof outline and heights remain estimates, not independently confirmed','Official photographs establish projecting roof windows, not exact cheek depth or finish','No transplant of unlocated 2006 central pediment','No new site survey; no claim to complete current interior or hidden elevations','Roof cuts and dormer cheeks follow the existing estimated window positions']
audit={'baseline':str(BASELINE),'baselineSha256':hashlib.sha256(BASELINE.read_bytes()).hexdigest(),'reference120Sha256':previous.get('reference120Sha256',previous['baselineSha256']) if previous else hashlib.sha256(BASELINE.read_bytes()).hexdigest(),'originalFingerprints':before,'originalVisibility':visibility,'archivedObjects':archived,'ownedObjects':[o.name for o in owned],'componentBytes':component.stat().st_size,'aperturesBefore':apertures_before,'aperturesAfter':apertures_after,'previousBlockedProbes':14,'nowClearProbes':24,'facades':[{key:list(value) if isinstance(value,Vector) else value for key,value in f.items()} for f in facades],'sources':sources,'limitations':limits}
(OUT/'audit.json').write_text(json.dumps(audit,indent=2)+'\n')
assert component.stat().st_size<10*1024*1024
print('LAK_COMPONENT_SAVED',component.stat().st_size,flush=True)
bpy.ops.wm.open_mainfile(filepath=str(BASELINE));restore();collection=bpy.data.collections['LAK_EXTERIOR']
with bpy.data.libraries.load(str(component),link=False) as (source,target):
    target.objects=audit['ownedObjects']
for obj in target.objects:
    assert obj is not None;collection.objects.link(obj)
for name in archived:
    bpy.data.objects[name].hide_render=True;bpy.data.objects[name].hide_set(True)
assert all(fingerprint(bpy.data.objects[name])==value for name,value in before.items())
assert all(p['clear'] for p in aperture_results())
print('LAK_RELOADED_APERTURES_VERIFIED',24,flush=True)
scene=bpy.data.scenes.new('LAK_NEXT_NATIVE_PREVIEW');scene.collection.children.link(collection);bpy.context.window.scene=scene
center=Vector((13,5,10));direction=(facades[0]['normal']+facades[1]['normal']).normalized()
camera_data=bpy.data.cameras.new('LAK_NEXT_preview_camera');camera=bpy.data.objects.new(camera_data.name,camera_data);scene.collection.objects.link(camera)
camera.location=center+direction*35+Vector((0,0,17));camera.rotation_euler=(center-camera.location).to_track_quat('-Z','Y').to_euler();camera_data.type='ORTHO';camera_data.ortho_scale=28;scene.camera=camera
scene.world=bpy.data.worlds.new('LAK_NEXT_preview_world');scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.55,.63,.70,1);scene.world.node_tree.nodes['Background'].inputs[1].default_value=.65
sun=bpy.data.lights.new('LAK_NEXT_preview_sun','SUN');sun.energy=2;sun.angle=.15;light=bpy.data.objects.new(sun.name,sun);scene.collection.objects.link(light);light.rotation_euler=(.5,-.45,-.5)
scene.render.engine='CYCLES';scene.cycles.samples=16;scene.cycles.use_denoising=True;scene.render.resolution_x=1400;scene.render.resolution_y=1100;scene.render.resolution_percentage=100;scene.view_settings.view_transform='AgX';scene.render.image_settings.file_format='PNG';scene.render.filepath=str(OUT/'lakatos-native.png');bpy.ops.render.render(write_still=True)
verification={'componentSha256':hashlib.sha256(component.read_bytes()).hexdigest(),'baselineUnchanged':hashlib.sha256(BASELINE.read_bytes()).hexdigest()==audit['baselineSha256'],'originalGeometryPreserved':True,'reloadedClearApertures':aperture_results(),'render':scene.render.filepath}
(OUT/'verification.json').write_text(json.dumps(verification,indent=2)+'\n')
print('LAK_NATIVE_COMPONENT_VERIFIED',flush=True)
