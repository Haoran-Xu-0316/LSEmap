"""Photo-supported Parish Hall brick arch joints and pale timber joinery.

Run in Blender's Text Editor. The campus stays readonly; export only the
owned component objects. Existing objects are archived by visibility only.
"""
from pathlib import Path
import array
import hashlib
import json
import math
import sys
import bpy
import bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'result/blender/par_next'
OUT.mkdir(parents=True, exist_ok=True)
BASELINE = ROOT / 'result/blender/LSE_campus_detailed_v119.blend'
previous_audit = json.loads((OUT/'audit.json').read_text()) if (OUT/'audit.json').exists() else None
if not BASELINE.exists():
    candidates = list((ROOT/'result/blender').glob('LSE_campus_detailed_v[0-9]*.blend'))
    BASELINE = max(candidates, key=lambda path: int(path.stem.rsplit('v',1)[1]))
bpy.ops.wm.open_mainfile(filepath=str(BASELINE))
def restore_previous_component():
    if previous_audit:
        for name in previous_audit['ownedObjects']:
            obj = bpy.data.objects.get(name)
            if obj:
                mesh = obj.data if obj.type == 'MESH' else None
                bpy.data.objects.remove(obj, do_unlink=True)
                if mesh is not None and mesh.users == 0:
                    bpy.data.meshes.remove(mesh)
        for name in previous_audit['archivedObjects']:
            obj = bpy.data.objects[name]
            state = previous_audit['originalVisibility'][name]
            obj.hide_render, obj.hide_viewport = state['hideRender'], state['hideViewport']
            obj.hide_set(state['hideSet'])
        for material in list(bpy.data.materials):
            if material.name.startswith('PAR_NEXT_') and material.users == 0:
                bpy.data.materials.remove(material)
restore_previous_component()
collection = bpy.data.collections['PAR_EXTERIOR']
bpy.context.window.scene = bpy.data.scenes['00_CAMPUS_COMPLETE']

def fingerprint(obj):
    digest = hashlib.sha256(str([list(row) for row in obj.matrix_world]).encode())
    if obj.type == 'MESH':
        digest.update(array.array('f', [c for v in obj.data.vertices for c in v.co]).tobytes())
        digest.update(array.array('i', [p.vertex_index for p in obj.data.loops]).tobytes())
        for layer in obj.data.uv_layers:
            digest.update(array.array('f', [c for uv in layer.data for c in uv.uv]).tobytes())
    digest.update(str([m.name if m else None for m in getattr(obj.data, 'materials', [])]).encode())
    return digest.hexdigest()
originals = list(bpy.data.objects)
before = {o.name: fingerprint(o) for o in originals}
visibility = {o.name: {'hideRender': o.hide_render, 'hideViewport': o.hide_viewport, 'hideSet': o.hide_get()} for o in originals}
site = json.loads((ROOT / 'result/blender/site_geometry.json').read_text())
ring = next(b['rings'][0] for b in site['buildings'] if b['code'] == 'PAR')
p, q = Vector((*ring[1], 0)), Vector((*ring[2], 0))
length = (q-p).length
axis = (q-p).normalized()
normal = Vector((-axis.y, axis.x, 0))
split = length - 4.7

def point(x, z, depth):
    return p + axis*x + normal*depth + Vector((0,0,z))

def visible_tree():
    vertices, faces, owners = [], [], []
    for obj in collection.all_objects:
        if obj.type != 'MESH' or obj.hide_render:
            continue
        start = len(vertices)
        vertices.extend(obj.matrix_world @ v.co for v in obj.data.vertices)
        faces.extend(tuple(start+i for i in poly.vertices) for poly in obj.data.polygons)
        owners.extend([obj.name]*len(obj.data.polygons))
    return BVHTree.FromPolygons(vertices, faces, all_triangles=False), owners

probes = [(i, z, (i+.5)*split/4-.31) for i in range(4) for z in (3.13, 7.26)]
def opening_results(tree_data):
    tree, owners = tree_data
    result=[]
    for bay,z,x in probes:
        location, face_normal, index, distance = tree.ray_cast(point(x,z,1), -normal, 2)
        assert location is not None, ('Missing glazed opening',bay,z)
        assert 'glass' in owners[index], ('Opaque first surface', bay, z, owners[index])
        result.append({'bay':bay,'height':z,'x':x,'firstSurface':owners[index],'firstSurfaceDistance':distance})
    return result
apertures_before = opening_results(visible_tree())
archived, owned, replacement_slots = [], [], {}
# The official photographs show pale painted timber, rather than dark tan joinery.
pale = bpy.data.materials['PAR_V66_frame'].copy()
pale.name = 'PAR_NEXT_pale_timber'
pale.diffuse_color = (.82,.80,.72,1)
pale.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = pale.diffuse_color
pale.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = .58
frame_materials = {'PAR_V66_frame','V16_PAR_finish','V17_PAR_finish'}
for obj in list(collection.all_objects):
    if obj.type != 'MESH' or obj.hide_render:
        continue
    slots = [i for i,m in enumerate(obj.data.materials) if m and m.name in frame_materials]
    if not slots:
        continue
    copied = obj.copy()
    copied.data = obj.data.copy()
    copied.name = 'PAR_NEXT_' + obj.name.removeprefix('PAR_')
    collection.objects.link(copied)
    for slot in slots:
        copied.data.materials[slot] = pale
    replacement_slots[obj.name] = slots
    owned.append(copied)
    obj.hide_render = True
    obj.hide_set(True)
    archived.append(obj.name)
# Replace continuous pointed bands with radial brick voussoirs and real joints.
old_arch = bpy.data.objects['PAR_D5_photo66_pointed_window_head_archbrick']
assert not old_arch.hide_render
old_arch.hide_render = True
old_arch.hide_set(True)
archived.append(old_arch.name)
brick = bpy.data.materials['PAR_V66_archbrick'].copy()
brick.name = 'PAR_NEXT_arch_brick'
brick.diffuse_color = (.35,.13,.067,1)
brick.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = brick.diffuse_color
# Use solid individual bricks; procedural horizontal bonding would conflict
# with their radial arrangement. Palette and joint width remain estimates.
for node in brick.node_tree.nodes:
    if node.type == 'BSDF_PRINCIPLED':
        for socket in ('Base Color','Normal'):
            for link in list(node.inputs[socket].links):
                brick.node_tree.links.remove(link)
brick.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = .89
vertices,faces=[],[]
brick_count=0
for bay in range(4):
    center_x = (bay+.5)*split/4
    half,rise,spring,thickness = 1.08,1.38,5.26,.16
    center = (rise*rise-half*half)/(2*half)
    radius = half+center
    end_angle = math.atan2(rise,-center)
    for side in (-1,1):
        for segment in range(19):
            joint_angle = .006/radius
            a = math.pi+(end_angle-math.pi)*segment/19-joint_angle/2
            b = math.pi+(end_angle-math.pi)*(segment+1)/19+joint_angle/2
            start=len(vertices)
            vertices.extend(point(center_x+side*(center+r*math.cos(t)),spring+r*math.sin(t),d)
                for d in (.016,.136) for r,t in ((radius,a),(radius,b),(radius+thickness,b),(radius+thickness,a)))
            faces.extend(tuple(start+i for i in f) for f in ((0,1,2,3),(4,7,6,5),(0,4,5,1),(3,2,6,7),(1,5,6,2),(0,3,7,4)))
            brick_count+=1
mesh=bpy.data.meshes.new('PAR_NEXT_radial_arch_bricks')
mesh.from_pydata(vertices,[],faces)
mesh.materials.append(brick)
bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=bm.faces);bm.to_mesh(mesh);bm.free()
mesh.update()
obj=bpy.data.objects.new(mesh.name,mesh)
collection.objects.link(obj)
owned.append(obj)
assert all(fingerprint(o)==before[o.name] for o in originals)
apertures_after = opening_results(visible_tree())
assert all(abs(a['firstSurfaceDistance']-b['firstSurfaceDistance'])<1e-5 for a,b in zip(apertures_before,apertures_after))
component = OUT/'parish-exterior-component.blend'
bpy.data.libraries.write(str(component),set(owned),fake_user=True,compress=True)
audit={'baseline':str(BASELINE),'baselineSha256':hashlib.sha256(BASELINE.read_bytes()).hexdigest(),
 'reference119Sha256':previous_audit.get('reference119Sha256',previous_audit['baselineSha256']) if previous_audit else hashlib.sha256(BASELINE.read_bytes()).hexdigest(),
 'originalFingerprints':before,'originalVisibility':visibility,'archivedObjects':archived,
 'ownedObjects':[o.name for o in owned],'replacementSlots':replacement_slots,'radialBrickCount':brick_count,
 'componentBytes':component.stat().st_size,'aperturesBefore':apertures_before,'aperturesAfter':apertures_after,
 'front':{'origin':list(p),'axis':list(axis),'normal':list(normal),'length':length,'entryStart':split},
 'sources':[{'url':'https://info.lse.ac.uk/staff/divisions/estates-division/Assets/Documents/Cap-Dev/2015-Parish-Hall.pdf','date':'2015 refurbishment; photograph capture date not specified','local':'data/建筑图片/PAR_Parish Hall/01_建筑实拍/small_round5_PAR-001.jpg'},
 {'url':'https://info.lse.ac.uk/staff/divisions/estates-division/Assets/Documents/Property-and-Space/LSE-Property-Handbook.pdf','date':'2025/26 handbook; photograph capture date not specified','local':'data/建筑图片/PAR_Parish Hall/01_建筑实拍/small_round5_PAR_handbook-000.png'}],
 'limitations':['Not a 2026 site survey','Photographs establish radial brick heads and pale joinery; exact pigment, joint width and dimensions estimated','Existing four-bay dimensions, roof and interior unchanged','No claim about unseen elevations or current interior']}
(OUT/'audit.json').write_text(json.dumps(audit,indent=2)+'\n')
assert component.stat().st_size < 10*1024*1024
print('PAR_COMPONENT_SAVED',len(owned),brick_count,component.stat().st_size,flush=True)
# Reopen the immutable campus and append the saved small component itself.
bpy.ops.wm.open_mainfile(filepath=str(BASELINE))
restore_previous_component()
collection=bpy.data.collections['PAR_EXTERIOR']
with bpy.data.libraries.load(str(component),link=False) as (source,target):
    target.objects=list(audit['ownedObjects'])
for obj in target.objects:
    assert obj is not None
    collection.objects.link(obj)
for name in archived:
    bpy.data.objects[name].hide_render=True
    bpy.data.objects[name].hide_set(True)
assert all(fingerprint(bpy.data.objects[name])==value for name,value in before.items())
assert all(abs(a['firstSurfaceDistance']-b['firstSurfaceDistance'])<1e-5 for a,b in zip(apertures_before,opening_results(visible_tree())))
print('PAR_RELOADED_APERTURES_VERIFIED',len(probes),flush=True)
scene=bpy.data.scenes.new('PAR_NEXT_NATIVE_PREVIEW')
scene.collection.children.link(collection)
bpy.context.window.scene=scene
center=point(length/2,6,-2)
camera_data=bpy.data.cameras.new('PAR_NEXT_preview_camera')
camera=bpy.data.objects.new(camera_data.name,camera_data);scene.collection.objects.link(camera)
camera.location=center+normal*34+axis*7+Vector((0,0,8))
camera.rotation_euler=(center-camera.location).to_track_quat('-Z','Y').to_euler()
camera_data.type='ORTHO';camera_data.ortho_scale=29;scene.camera=camera
scene.world=bpy.data.worlds.new('PAR_NEXT_preview_world');scene.world.use_nodes=True
scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.55,.63,.70,1)
scene.world.node_tree.nodes['Background'].inputs[1].default_value=.65
sun=bpy.data.lights.new('PAR_NEXT_preview_sun','SUN');sun.energy=2;sun.angle=.15
light=bpy.data.objects.new(sun.name,sun);scene.collection.objects.link(light);light.rotation_euler=(.5,-.45,-.5)
scene.render.engine='CYCLES';scene.cycles.samples=16;scene.cycles.use_denoising=True
scene.render.resolution_x=1400;scene.render.resolution_y=1000;scene.render.resolution_percentage=100
scene.view_settings.view_transform='AgX';scene.render.image_settings.file_format='PNG'
scene.render.filepath=str(OUT/'parish-native.png');bpy.ops.render.render(write_still=True)
verification={'componentSha256':hashlib.sha256(component.read_bytes()).hexdigest(),'baselineUnchanged':hashlib.sha256(BASELINE.read_bytes()).hexdigest()==audit['baselineSha256'],'reloadedObjects':len(owned),'clearApertureParity':len(probes),'originalGeometryPreserved':True,'render':scene.render.filepath}
(OUT/'verification.json').write_text(json.dumps(verification,indent=2)+'\n')
print('PAR_NATIVE_COMPONENT_VERIFIED',flush=True)
