"""Add photo-guided stone heraldry to OLD's reserved shield.
Run in Blender Text Editor. Dimensions and carving are estimates, not a scan.
"""
from pathlib import Path
import array
import hashlib
import json
import math
import sys
import bpy
import bmesh
from functools import lru_cache
from mathutils import Vector
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'result/blender/stage74'
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(Path(__file__).resolve().parent))
from facade_geometry import Geometry, materials
bpy.ops.wm.open_mainfile(filepath=str(ROOT / 'result/blender/LSE_campus_detailed_v73.blend'))
bpy.context.window.scene = bpy.data.scenes['00_CAMPUS_COMPLETE']
frame = json.loads((ROOT / 'result/blender/stage52/old-houghton-audit.json').read_text())
origin, right, outward = [Vector(frame[k]) for k in ['origin', 'right', 'outward']]
def point(x, depth, z):
    return origin + right*x + outward*depth + Vector((0, 0, z))
def fingerprint(obj):
    h = hashlib.sha256(str([list(row) for row in obj.matrix_world]).encode())
    if obj.type == 'MESH':
        h.update(array.array('f', [c for v in obj.data.vertices for c in v.co]).tobytes())
        h.update(array.array('i', [l.vertex_index for l in obj.data.loops]).tobytes())
    h.update(str([m.name if m else None for m in getattr(obj.data, 'materials', [])]).encode())
    return h.hexdigest()
before = {o.name: fingerprint(o) for o in bpy.data.objects}
materials.clear()
for key, color in [('stone', (.59, .575, .54)), ('incision', (.465, .455, .425)), ('field', (.50, .49, .46))]:
    mat = bpy.data.materials.new('OLD_V74_' + key)
    mat.use_nodes = True
    mat.diffuse_color = (*color, 1)
    bsdf = mat.node_tree.nodes['Principled BSDF']
    bsdf.inputs['Base Color'].default_value = mat.diffuse_color
    bsdf.inputs['Roughness'].default_value = .9
    materials[key] = mat
batches = {}
def batch(key):
    if key not in batches:
        batches[key] = Geometry('OLD', 'arms74_' + key, key)
    return batches[key]
def box(key, x, d, z, w, t, h):
    batch(key).box(point(x, d, z), (w, t, h), math.atan2(right.y, right.x))
def face(key, points):
    vs = [point(*p) for p in points]
    if (vs[1]-vs[0]).cross(vs[-1]-vs[0]).dot(outward) < 0:
        vs.reverse()
    batch(key).add(vs, [tuple(range(len(vs)))])
def line(key, a, b, width, d):
    dx, dz = b[0]-a[0], b[1]-a[1]
    length = math.hypot(dx, dz)
    nx, nz = -dz/length*width/2, dx/length*width/2
    face(key, [(a[0]-nx, d, a[1]-nz), (b[0]-nx, d, b[1]-nz),
               (b[0]+nx, d, b[1]+nz), (a[0]+nx, d, a[1]+nz)])
def relief_outline(points, depth=.84, thickness=.025):
    # A thin solid silhouette gives feet and paddle tail a carved edge.
    face('stone', [(x, depth+thickness, z) for x,z in points])
    for a,b in zip(points, points[1:]+points[:1]):
        face('stone', [(a[0],depth,a[1]), (b[0],depth,b[1]),
                       (b[0],depth+thickness,b[1]), (a[0],depth+thickness,a[1])])
# The lower field has fine square heraldic hatching in the official close photo.
for i in range(23):
    z=9.49+i*.035
    half=min(.58, max(.08, .24+(z-9.49)*.75))
    line('field',(-half,z),(half,z),.003,.800)
for i in range(33):
    x=-.56+i*.035
    bottom=9.46+max(0,abs(x)-.17)*1.08
    line('field',(x,bottom),(x,10.28),.003,.801)
line('incision',(-.575,10.28),(.575,10.28),.016,.815)
# Two closed books, with stone page edges, inset borders and clasp details.
for x in [-.285,.285]:
    box('stone',x,.832,10.445,.31,.052,.34)
    for z in [10.293,10.596]:
        line('incision',(x-.137,z),(x+.137,z),.009,.862)
    for xx in [x-.132,x+.132]:
        line('incision',(xx,10.305),(xx,10.583),.009,.862)
    diamond=[(x,10.52),(x+.078,10.448),(x,10.376),(x-.078,10.448)]
    for a,b in zip(diamond,diamond[1:]+diamond[:1]):
        line('incision',a,b,.009,.865)
    for z in [10.37,10.52]:
        box('stone',x+.139,.868,z,.040,.018,.031)
    for z in [10.282,10.293]:
        line('incision',(x-.14,z),(x+.14,z),.003,.86)
# Fill the reserved shield behind its border; the original outline stays intact.
shield=[(-.60,10.76),(.60,10.76),(.69,10.14),(.57,9.62),(.27,9.39),(0,9.28),(-.27,9.39),(-.57,9.62),(-.69,10.14)]
face('field',[(x*1.12,.779,10.05+(z-10.05)*1.12) for x,z in shield])
# One continuous shallow silhouette avoids separate ellipsoidal body parts.
outline=[(-.41,10.035),(-.393,10.07),(-.34,10.092),(-.30,10.105),(-.282,10.135),(-.26,10.14),(-.241,10.117),(-.206,10.107),(-.17,10.115),(-.12,10.139),(-.055,10.146),(.035,10.134),(.117,10.10),(.185,10.058),(.218,10.01),(.267,9.978),(.365,9.988),(.468,9.981),(.524,9.953),(.505,9.925),(.433,9.916),(.30,9.923),(.257,9.923),(.282,9.893),(.280,9.851),(.228,9.819),(.179,9.811),(.16,9.828),(.20,9.85),(.24,9.873),(.222,9.884),(.194,9.857),(.109,9.807),(.055,9.799),(.042,9.817),(.088,9.837),(.153,9.878),(.103,9.913),(.018,9.934),(-.071,9.943),(-.142,9.936),(-.166,9.882),(-.222,9.84),(-.264,9.836),(-.272,9.85),(-.227,9.874),(-.205,9.909),(-.235,9.929),(-.267,9.888),(-.316,9.863),(-.343,9.868),(-.345,9.884),(-.301,9.903),(-.284,9.959),(-.309,9.989),(-.363,9.997),(-.40,10.01)]
relief_outline(outline,.828,.012)
def inside(x,z):
    result=False
    for a,b in zip(outline,outline[1:]+outline[:1]):
        if (a[1]>z)!=(b[1]>z) and x<(b[0]-a[0])*(z-a[1])/(b[1]-a[1])+a[0]:
            result=not result
    return result
def edge_distance(x,z):
    distances=[]
    for a,b in zip(outline,outline[1:]+outline[:1]):
        dx,dz=b[0]-a[0],b[1]-a[1]
        t=max(0,min(1,((x-a[0])*dx+(z-a[1])*dz)/(dx*dx+dz*dz)))
        distances.append(math.hypot(x-a[0]-t*dx,z-a[1]-t*dz))
    return min(distances)
@lru_cache(maxsize=None)
def carved_depth(x,z):
    edge=min(1,edge_distance(x,z)/.037)
    fullness=math.exp(-((x-.00)/.24)**2-((z-10.015)/.125)**2)
    fur=.0004*math.sin(110*x+35*z)*math.sin(62*z-20*x)
    return .84+math.sqrt(edge)*(.028+.020*fullness)+fur
# Clipped grid triangles share a single anatomical surface and fine stone grain.
step=.004
for ix in range(236):
    for iz in range(88):
        x,z=-.412+ix*step,9.796+iz*step
        for triangle in [[(x,z),(x+step,z),(x+step,z+step)],[(x,z),(x+step,z+step),(x,z+step)]]:
            if all(inside(xx,zz) for xx,zz in triangle):
                face('stone',[(xx,carved_depth(xx,zz),zz) for xx,zz in triangle])
# Short shallow engraved fur marks follow the long body instead of a round blob.
for i in range(38):
    x=-.16+i*.009;z=10.045+.041*math.sin(i*.075)
    if inside(x,z) and inside(x+.015,z-.023):
        line('incision',(x,z),(x+.015,z-.023),.0018,max(carved_depth(x,z),carved_depth(x+.015,z-.023))+.001)
line('incision',(-.335,10.064),(-.325,10.066),.005,carved_depth(-.33,10.065)+.001)
for i in range(5):
    x=.365+i*.027
    line('incision',(x,9.933),(x-.015,9.972),.0025,.854)

added=[]
for key,g in batches.items():
    obj=g.finish();added.append(obj.name)
    for modifier in list(obj.modifiers):
        obj.modifiers.remove(modifier)
    if key=='stone':
        mesh=bmesh.new();mesh.from_mesh(obj.data)
        bmesh.ops.remove_doubles(mesh,verts=list(mesh.verts),dist=.000001)
        mesh.to_mesh(obj.data);mesh.free();obj.data.update()
        for p in obj.data.polygons:
            p.use_smooth=len(p.vertices)==3 or len(p.vertices)==4 and p.area<.003
changed=[name for name,value in before.items() if fingerprint(bpy.data.objects[name])!=value]
assert not changed,changed
for filename in ['room-studies.json','room-spaces.json','building-review.json']:
    (OUT/filename).write_bytes((ROOT/'result/blender/stage73'/filename).read_bytes())
audit={'version':74,'baseline':73,'bookCount':2,'beaverCount':1,'addedObjects':added,'changedExistingGeometry':changed,'reference':'LSE History: Devising the LSE coat of arms, Nigel Stead stone close photograph; corroborated by latest user entrance image','referenceUrl':'https://blogs.lse.ac.uk/lsehistory/2017/06/20/cheerful-nonsense-with-brains-behind-it-devising-the-lse-coat-of-arms/','limitations':['Carving dimensions and shallow relief profiles estimated, not a scan','Source capture date unknown; official article published 2017','Other elevations, roof and complete interiors remain under review']}
(OUT/'old-heraldic-device-audit.json').write_text(json.dumps(audit,indent=2)+'\n')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v74.blend'))
print('OLD_HERALDIC_DEVICE_SAVED',len(added))
