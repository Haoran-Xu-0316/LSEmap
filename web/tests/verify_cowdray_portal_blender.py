"""Verify the saved Cowdray entry, original meshes and actual glazing apertures."""
from pathlib import Path
import array
import hashlib
import json
import math
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'result/blender/stage118'
model=ROOT/'result/blender/LSE_campus_detailed_v118.blend'
audit=json.loads((OUT/'cow-portal-audit.json').read_text())
bpy.ops.wm.open_mainfile(filepath=str(model))
for scene in bpy.data.scenes:
    for layer in scene.view_layers:layer.update()
scene=bpy.data.scenes['00_CAMPUS_COMPLETE'];bpy.context.window.scene=scene

def fingerprint(obj):
    h=hashlib.sha256(str([list(r) for r in obj.matrix_world]).encode())
    if obj.type=='MESH':
        verts=array.array('f',[0])*(3*len(obj.data.vertices));loops=array.array('i',[0])*len(obj.data.loops)
        obj.data.vertices.foreach_get('co',verts);obj.data.loops.foreach_get('vertex_index',loops)
        h.update(verts.tobytes());h.update(loops.tobytes())
    h.update(str([m.name if m else None for m in getattr(obj.data,'materials',[])]).encode())
    return h.hexdigest()
for name,digest in audit['originalFingerprints'].items():
    obj=bpy.data.objects[name]
    assert fingerprint(obj)==digest,name
    assert obj.hide_render==(True if name in audit['archivedObjects'] else audit['originalVisibility'][name]),name
assert len(audit['archivedObjects'])==20
origin=Vector(audit['origin']);axis=Vector(audit['axis']);normal=Vector(audit['normal'])
def point(x,d,z):return origin+axis*x+normal*d+Vector((0,0,z))
trees=[]
for obj in bpy.data.collections['COW_EXTERIOR'].all_objects:
    if obj.type!='MESH' or obj.hide_render:continue
    trees.append((obj.name,BVHTree.FromPolygons([obj.matrix_world@v.co for v in obj.data.vertices],[list(p.vertices) for p in obj.data.polygons],all_triangles=False)))
def cast(ray,direction,length):
    result=[]
    for name,tree in trees:
        hit,hitnormal,index,distance=tree.ray_cast(ray,direction,length)
        if hit is not None:result.append((distance,name,list(hit),list(hitnormal)))
    return sorted(result)
probes=[]
for x,z in [(-.48,1.52),(-.32,2.32),(.25,1.52),(.49,2.32),(-.23,3.24),(.18,3.37),(.62,3.15)]:
    hits=cast(point(x,.8,z),-normal,1.4)
    assert hits and 'portal118_glass' in hits[0][1],(x,z,hits[:5])
    assert not [(d,n) for d,n,*_ in hits if 'portal118_glass' not in n and d<1.25],(x,z,hits)
    probes.append(dict(x=x,z=z,first=hits[0][1],clear=True))
for x,z in [(1.60,2.6),(0,3.78),(.75,3.78)]:
    hits=cast(point(x,.8,z),-normal,1.4)
    assert hits and 'portal118_' in hits[0][1] and 'glass' not in hits[0][1],(x,z,hits)
steps=[]
for step in audit['steps']:
    hits=cast(point(0,step['probeDepth'],1),Vector((0,0,-1)),1.2)
    assert hits and 'portal118_stone' in hits[0][1],hits
    assert abs(hits[0][2][2]-step['top'])<1e-5,(step,hits[0])
    steps.append(hits[0][2][2])
for name in audit['addedObjects']:
    obj=bpy.data.objects[name]
    assert obj.data.uv_layers and not obj.modifiers,name
    assert all(math.isfinite(c) for v in obj.data.vertices for c in v.co),name
    assert all(math.isfinite(c) for uv in obj.data.uv_layers.active.data for c in uv.uv),name
# Sample an actual front-facing stone arch segment, off its joints and frame.
x=.72;z=audit['spring']+audit['archRise']*.62+.16
hits=cast(point(x,.8,z),-normal,1.4)
assert hits and 'portal118_stone' in hits[0][1],hits
assert Vector(hits[0][3]).dot(normal)>.9,('Inward arch front face',hits)
result=dict(version=118,sourceModelSha256=hashlib.sha256(model.read_bytes()).hexdigest(),
    retainedObjects=len(audit['originalFingerprints']),originalGeometryRetained=True,originalVisibilityPreserved=True,
    retainedRoofAndUpperJoinery=True,archivedPortalObjects=20,addedMaterialBatches=len(audit['addedObjects']),
    apertureProbes=probes,clearApertures=len(probes),stepTops=steps,sourceUrls=audit['sourceUrls'],limits=audit['limits'])
(OUT/'saved-verification.json').write_text(json.dumps(result,indent=2)+'\n')
print('COWDRAY_SAVED_VERIFICATION_PASSED',len(probes),steps,flush=True)
# Isolated preview only; the original saved scene is not altered.
for obj in scene.objects:
    if obj.type in {'MESH','CURVE','FONT','SURFACE'} and not any(c.name=='COW_EXTERIOR' for c in obj.users_collection):obj.hide_render=True
camera_data=bpy.data.cameras.new('VERIFY_Cowdray');camera=bpy.data.objects.new('VERIFY_Cowdray',camera_data);scene.collection.objects.link(camera)
centre=origin+Vector((0,0,2.6));camera.location=centre+normal*11+axis*.3+Vector((0,0,1.5))
camera.rotation_euler=(centre-camera.location).to_track_quat('-Z','Y').to_euler()
camera_data.type='ORTHO';camera_data.ortho_scale=6.7;scene.camera=camera
scene.render.engine='BLENDER_EEVEE';scene.render.resolution_x=1440;scene.render.resolution_y=1200;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.render.filepath=str(OUT/'cow-portal-native.png')
bpy.ops.render.render(write_still=True)
print('COWDRAY_NATIVE_PREVIEW_RENDERED',flush=True)
