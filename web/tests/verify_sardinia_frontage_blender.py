"""Reopen SAR's saved five-bay facade and verify real openings and preservation."""
from pathlib import Path
import array
import hashlib
import json
import math
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'result/blender/stage119'
model=ROOT/'result/blender/LSE_campus_detailed_v119.blend'
audit=json.loads((OUT/'sardinia-frontage-audit.json').read_text())
additional_archives=set()
if not model.exists():
    candidates=list((ROOT/'result/blender').glob('LSE_campus_detailed_v[0-9]*.blend'))
    model=max(candidates,key=lambda path:int(path.stem.rsplit('v',1)[1]))
    merged=json.loads((ROOT/'result/blender/stage120/saved-verification.json').read_text())
    assert hashlib.sha256(model.read_bytes()).hexdigest()==merged['sourceModelSha256']
    additional_archives=set(merged['archivedObjects'])
    OUT=ROOT/'result/blender/stage120/sardinia';OUT.mkdir(exist_ok=True)
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
    obj=bpy.data.objects[name];assert fingerprint(obj)==digest,name
    assert obj.hide_render==(True if name in set(audit['archivedObjects'])|additional_archives else audit['originalVisibility'][name]),name
origin=Vector(audit['origin']);axis=Vector(audit['axis']);normal=Vector(audit['normal'])
def point(x,d,z):return origin+axis*x+normal*d+Vector((0,0,z))
trees=[]
for obj in bpy.data.collections['SAR_EXTERIOR'].all_objects:
    if obj.type!='MESH' or obj.hide_render:continue
    trees.append((obj.name,BVHTree.FromPolygons([obj.matrix_world@v.co for v in obj.data.vertices],[list(p.vertices) for p in obj.data.polygons],all_triangles=False)))
def hits(x,z):
    result=[]
    for name,tree in trees:
        hit,_,_,distance=tree.ray_cast(point(x,.80,z),-normal,1.40)
        if hit is not None:result.append((distance,name))
    return sorted(result)
probes=[]
for opening in audit['openings']:
    # Sample inside a pane, avoiding intentional mullions and lower iron grilles.
    if opening['kind']=='entry':x=opening['x']-.22;z=1.72
    else:x=opening['x']-opening['width']*.40;z=opening['low']+(opening['high']-opening['low'])*.17
    found=hits(x,z);assert found and 'front119_glass' in found[0][1],(opening,found[:5])
    assert not [(d,n) for d,n in found if 'front119_glass' not in n and d<1.20],(opening,found)
    probes.append(dict(floor=opening['floor'],bay=opening['bay'],kind=opening['kind'],first=found[0][1]))
assert len(probes)==30 and sum(p['kind']=='entry' for p in probes)==1
entry=next(o for o in audit['openings'] if o['kind']=='entry')
assert entry['bay']==2 and abs(entry['x']-audit['frontLength']/2)<1e-8
assert audit['externalStepsAdded']==0
for name in audit['addedObjects']:
    obj=bpy.data.objects[name];assert obj.data.uv_layers and not obj.modifiers,name
    assert all(math.isfinite(c) for v in obj.data.vertices for c in v.co),name
    assert all(math.isfinite(c) for uv in obj.data.uv_layers.active.data for c in uv.uv),name
    if name.endswith('_brick'):
        for poly in obj.data.polygons:
            for index in poly.loop_indices:
                p=obj.matrix_world@obj.data.vertices[obj.data.loops[index].vertex_index].co-origin
                uv=obj.data.uv_layers.active.data[index].uv
                assert abs(uv.x-p.dot(axis))<1e-4 and abs(uv.y-p.z)<1e-4
result=dict(version=int(model.stem.rsplit('v',1)[1]),sourceModelSha256=hashlib.sha256(model.read_bytes()).hexdigest(),
    originalGeometryRetained=True,originalVisibilityPreserved=True,retainedObjects=len(audit['originalFingerprints']),
    bayCount=5,centralEntry=True,clearApertures=len(probes),apertureProbes=probes,
    metricBrickUVs=True,roofGeometryRetained=True,sourceUrls=audit['sourceUrls'],limits=audit['limits'])
(OUT/'saved-verification.json').write_text(json.dumps(result,indent=2)+'\n')
print('SARDINIA_SAVED_VERIFICATION_PASSED',len(probes),flush=True)
for obj in scene.objects:
    if obj.type in {'MESH','CURVE','FONT','SURFACE'} and not any(c.name=='SAR_EXTERIOR' for c in obj.users_collection):obj.hide_render=True
camera_data=bpy.data.cameras.new('VERIFY_Sardinia');camera=bpy.data.objects.new('VERIFY_Sardinia',camera_data);scene.collection.objects.link(camera)
centre=origin+axis*audit['frontLength']/2+Vector((0,0,11.5));camera.location=centre+normal*38+axis*1.8+Vector((0,0,1.8))
camera.rotation_euler=(centre-camera.location).to_track_quat('-Z','Y').to_euler();camera_data.type='ORTHO';camera_data.ortho_scale=27;scene.camera=camera
scene.render.engine='BLENDER_EEVEE';scene.render.resolution_x=1200;scene.render.resolution_y=1400;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.render.filepath=str(OUT/'sardinia-native.png')
bpy.ops.render.render(write_still=True)
print('SARDINIA_NATIVE_PREVIEW_RENDERED',flush=True)
