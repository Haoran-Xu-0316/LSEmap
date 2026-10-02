"""Reopen the saved LRB model; verify preservation, clear apertures and roof join."""
from pathlib import Path
import array
import bisect
import hashlib
import json
import math
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'result/blender/stage117'
model = ROOT/'result/blender/LSE_campus_detailed_v117.blend'
audit = json.loads((OUT/'carey-frontage-audit.json').read_text())
plan = json.loads((OUT/'street-survey-geometry.json').read_text())
bpy.ops.wm.open_mainfile(filepath=str(model))
for scene in bpy.data.scenes:
    for layer in scene.view_layers: layer.update()
scene = bpy.data.scenes['00_CAMPUS_COMPLETE']
bpy.context.window.scene = scene

def fingerprint(obj):
    h=hashlib.sha256(str([list(r) for r in obj.matrix_world]).encode())
    if obj.type=='MESH':
        vertices=array.array('f',[0])*(3*len(obj.data.vertices))
        indices=array.array('i',[0])*len(obj.data.loops)
        obj.data.vertices.foreach_get('co',vertices);obj.data.loops.foreach_get('vertex_index',indices)
        h.update(vertices.tobytes());h.update(indices.tobytes())
    h.update(str([m.name if m else None for m in getattr(obj.data,'materials',[])]).encode())
    return h.hexdigest()
for name, digest in audit['originalFingerprints'].items():
    obj=bpy.data.objects[name]
    assert fingerprint(obj)==digest, name
    assert obj.hide_render==(True if name in audit['archivedObjects'] else audit['originalVisibility'][name]),name

origin=Vector((*plan['careyOrigin'],0));axis=Vector((*plan['careyAxis'],0));normal=Vector((*plan['careyNormal'],0))
corner=[Vector((*p,0)) for p in plan['cornerCurve']]
def basis(x, curved):
    if not curved:return origin+axis*x,normal
    ds=plan['cornerDistances'];i=min(47,max(0,bisect.bisect_right(ds,x)-1))
    u=(corner[i+1]-corner[i]).normalized()
    return corner[i]+u*(x-ds[i]),Vector((-u.y,u.x,0))

trees=[]
for obj in bpy.data.collections['LRB_EXTERIOR'].all_objects:
    if obj.hide_render or obj.type!='MESH':continue
    pts=[obj.matrix_world@v.co for v in obj.data.vertices]
    trees.append((obj.name,BVHTree.FromPolygons(pts,[list(p.vertices) for p in obj.data.polygons],all_triangles=False)))
def hits(x,z,curved=False):
    p,n=basis(x,curved);ray=p+n*.8+Vector((0,0,z));result=[]
    for name,tree in trees:
        point,_,_,distance=tree.ray_cast(ray,-n,1.5)
        if point is not None:result.append((distance,name))
    return sorted(result)
probes=[]
for opening in plan['openings']:
    # Sample inside a pane, avoiding its deliberately solid metal mullions.
    x=opening['x']-opening['width']/2+opening['width']*.37/opening['columns']
    z=opening['low']+(opening['high']-opening['low'])*.43/opening['rows']
    found=hits(x,z,opening['curved'])
    assert found and 'carey117_glass' in found[0][1],(opening,found[:4])
    blockers=[(d,name) for d,name in found if 'carey117_glass' not in name and d<1.12]
    assert not blockers,(opening,blockers)
    probes.append(dict(kind=opening['kind'],x=x,z=z,first=found[0][1]))
for arch in plan['arches']:
    x=arch['x']+arch['radius']*.137;z=arch['spring']+arch['radius']*.77
    found=hits(x,z)
    assert found and 'carey117_glass' in found[0][1],(arch,found[:4])
    assert not [(d,n) for d,n in found if 'carey117_glass' not in n and d<1.12],(arch,found)
    probes.append(dict(kind='arch',x=x,z=z,first=found[0][1]))
    solid=hits(arch['x']+arch['radius']*.75,arch['spring']+arch['radius']*.87)
    assert solid and 'carey117_glass' not in solid[0][1],('arch-spandrel',solid)
for name in audit['addedObjects']:
    obj=bpy.data.objects[name]
    assert obj.data.uv_layers,name
    assert all(math.isfinite(c) for v in obj.data.vertices for c in v.co),name
    assert all(math.isfinite(c) for uv in obj.data.uv_layers.active.data for c in uv.uv),name
# The replacement perimeter must not move the retained raised roof geometry.
original=bpy.data.objects['LRB_D5_roof109_roof']
current=bpy.data.objects['LRB_V117_current_perimeter_roof']
def upper_points(obj):
    return sorted(tuple(round(c,5) for c in obj.matrix_world@v.co)
                  for v in obj.data.vertices if (obj.matrix_world@v.co).z>20.25)
assert upper_points(original)==upper_points(current), 'Raised roof geometry changed'
assert (corner[-1]-origin).length<1e-6
start=(corner[1]-corner[0]).normalized()
nw=(Vector((*plan['ring'][2],0))-Vector((*plan['ring'][1],0))).normalized()
assert start.dot(nw)>.995
assert (corner[-1]-corner[-2]).normalized().dot(axis)>.995
result=dict(version=117,sourceModelSha256=hashlib.sha256(model.read_bytes()).hexdigest(),
            originalGeometryRetained=True,originalVisibilityPreserved=True,
            retainedObjects=len(audit['originalFingerprints']),originalPortugalStreetPreserved=True,
            apertureProbes=probes,clearApertures=len(probes),archCount=len(plan['arches']),
            tangentContinuity=True,raisedRoofGeometryPreserved=True,source=plan['source'],limits=plan['limits'])
(OUT/'saved-verification.json').write_text(json.dumps(result,indent=2)+'\n')
print('LIBRARY_CAREY_SAVED_VERIFICATION_PASSED',len(probes),flush=True)
# A native preview isolates this exterior without altering the saved file.
for obj in scene.objects:
    if obj.type in {'MESH','CURVE','FONT','SURFACE'} and not any(c.name=='LRB_EXTERIOR' for c in obj.users_collection): obj.hide_render=True
camera_data=bpy.data.cameras.new('VERIFY_Carey');camera=bpy.data.objects.new('VERIFY_Carey',camera_data);scene.collection.objects.link(camera)
centre=origin+axis*(plan['careyLength']/2)+Vector((0,0,12))
camera.location=centre+normal*59+axis*(-12)+Vector((0,0,15))
camera.rotation_euler=(centre-camera.location).to_track_quat('-Z','Y').to_euler();camera_data.type='ORTHO';camera_data.ortho_scale=61;scene.camera=camera
scene.render.engine='BLENDER_EEVEE';scene.render.resolution_x=1440;scene.render.resolution_y=960;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.render.filepath=str(OUT/'carey-native.png')
bpy.ops.render.render(write_still=True)
print('LIBRARY_CAREY_NATIVE_PREVIEW_RENDERED',flush=True)
