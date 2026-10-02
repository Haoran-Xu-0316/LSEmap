"""Refine OLD's plastic mesh figure silhouettes without photographic textures.
Run directly in Blender Text Editor. Anatomy and weave spacing remain estimates.
"""
from pathlib import Path
import bpy, bmesh, json, math, hashlib, array, shutil, sys
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'result/blender/stage106';OUT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(Path(__file__).resolve().parent))
from facade_geometry import Geometry, materials
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v104.blend'))
bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE']
def digest(obj):
    h=hashlib.sha256(str([list(row) for row in obj.matrix_world]).encode())
    if obj.type=='MESH':
        h.update(array.array('f',[c for v in obj.data.vertices for c in v.co]).tobytes())
        h.update(array.array('i',[l.vertex_index for l in obj.data.loops]).tobytes())
    h.update(str([m.name if m else None for m in getattr(obj.data,'materials',[])]).encode())
    return h.hexdigest()
before={o.name:digest(o) for o in bpy.data.objects}
source=bpy.data.objects['OLD_D5_finalsale84_figures'];assert not source.hide_render
frame=json.loads((ROOT/'result/blender/stage52/old-houghton-audit.json').read_text())
origin,right,outward=[Vector(frame[k]) for k in ['origin','right','outward']]
depth_offset=0.0
def point(x,d,z):return origin+right*x+outward*(d+depth_offset)+Vector((0,0,z))
materials.clear();materials['figures']=source.data.materials[0]
geometry=Geometry('OLD','finalsale106_figures','figures')
def batch(key):
    assert key=='figures'
    return geometry
def limb(key,a,b,r0,r1=None):
 a,b=Vector(a),Vector(b);axis=(b-a).normalized();u=axis.cross(Vector((0,0,1)))
 if u.length<.01:u=Vector((1,0,0))
 u.normalize();v=axis.cross(u).normalized();r1=r0 if r1 is None else r1
 rings=max(2,math.ceil((b-a).length/.025));vs=[]
 for j in range(rings+1):
  t=j/rings;p=a.lerp(b,t);r=r0+(r1-r0)*t
  vs.extend(point(*(p+r*(u*math.cos(i*math.tau/24)+v*math.sin(i*math.tau/24))))for i in range(24))
 batch(key).add(vs,[(j*24+i,j*24+(i+1)%24,(j+1)*24+(i+1)%24,(j+1)*24+i)for j in range(rings)for i in range(24)])

def ellipsoid(x,d,z,rx,ry,rz):
    sides, levels = 48, 24
    vertices = [point(x+rx*math.cos(phi)*math.cos(theta), d+ry*math.cos(phi)*math.sin(theta), z+rz*math.sin(phi))
                for phi in [-math.pi/2+math.pi*j/levels for j in range(levels+1)]
                for theta in [math.tau*i/sides for i in range(sides)]]
    batch('figures').add(vertices, [(j*sides+i,j*sides+(i+1)%sides,(j+1)*sides+(i+1)%sides,(j+1)*sides+i)
                                   for j in range(levels) for i in range(sides)])
# Each figure has its own posture, asymmetrical cloth silhouette and head turn.
figures=[{'x':-2.05,'foot':4.28,'head':5.78,'lean':-.13,'turn':1,'pose':'walking'},
 {'x':-1.20,'foot':4.28,'head':5.98,'lean':.03,'turn':1,'pose':'basket'},
 {'x':-.73,'foot':5.19,'head':6.06,'lean':.015,'turn':1,'pose':'occluded'},
 {'x':-.18,'foot':4.40,'head':6.20,'lean':.19,'turn':1,'pose':'reaching'},
 {'x':1.03,'foot':4.93,'head':6.77,'lean':-.02,'turn':-1,'pose':'raised'},
 {'x':2.12,'foot':4.30,'head':6.07,'lean':-.10,'turn':-1,'pose':'basket'}]
basket_count=0
for index,figure in enumerate(figures):
 depth_offset=-.135 if figure['pose']=='occluded' else 0
 x,foot,head,lean=figure['x'],figure['foot'],figure['head'],figure['lean'];hx=x+lean
 ellipsoid(hx,-.30,head,.108,.073,.153)
 ellipsoid(hx-figure['turn']*.017,-.34,head+.063,.113,.057,.103)
 # Small facial profile and ears are relief volumes, not portraits.
 ellipsoid(hx+figure['turn']*.095,-.268,head-.015,.021,.025,.030)
 ellipsoid(hx-figure['turn']*.09,-.27,head-.008,.025,.04,.045)
 limb('figures',(hx,-.33,head-.13),(hx-.025,-.33,head-.28),.057)
 ellipsoid(hx-.025,-.34,head-.36,.22,.085,.14)
 # A full shoulder-to-hem surface with curved, asymmetric folds replaces
 # the isolated narrow torso and cylindrical diagonal mantle.
 vertices=[];levels=72;sides=64
 for j in range(levels):
  t=j/(levels-1);z=foot+.18+t*(head-foot-.40)
  sway={'walking':-.14,'basket':.11,'occluded':.04,'reaching':.13,'raised':-.09}[figure['pose']]
  cx=x+lean*t+sway*math.sin(t*math.pi)
  # Hem, knees, waist and shoulder widths are interpolated continuously.
  profiles={
   'walking':[(0,.29),(.20,.30),(.48,.33),(.70,.20),(.88,.24),(.94,.21),(1,.064)],
   'basket':[(0,.31),(.20,.27),(.48,.25),(.70,.17),(.88,.235),(.94,.21),(1,.064)],
   'occluded':[(0,.23),(.20,.23),(.48,.21),(.70,.17),(.88,.225),(.94,.21),(1,.064)],
   'reaching':[(0,.29),(.20,.26),(.48,.24),(.70,.175),(.88,.23),(.94,.21),(1,.064)],
   'raised':[(0,.25),(.20,.29),(.48,.28),(.70,.155),(.88,.225),(.94,.21),(1,.064)]}
  knots=profiles[figure['pose']]
  lo,hi=next((a,b) for a,b in zip(knots,knots[1:]) if a[0]<=t<=b[0])
  s=(t-lo[0])/(hi[0]-lo[0]); s=s*s*(3-2*s)
  width=lo[1]+(hi[1]-lo[1])*s
  for k in range(sides):
   angle=k*math.tau/sides
   fold=1+.14*math.cos(7*angle+5*t+index)+.045*math.cos(13*angle-2*t)
   vertices.append(point(cx+width*math.cos(angle)*fold,-.35+.105*math.sin(angle)*fold,z))
 batch('figures').add(vertices,[(j*sides+k,j*sides+(k+1)%sides,(j+1)*sides+(k+1)%sides,(j+1)*sides+k) for j in range(levels-1) for k in range(sides)])
 # Thin overlapping draped bands cross the chest, then broaden over the skirt.
 for band in range(3):
  cloth=[]
  for j in range(65):
   t=j/64;z=head-.36-t*(head-foot-.64)
   cx=hx-.20+(.38+.025*band)*t+.07*math.sin(math.pi*t)
   width=.043+.043*t
   for side in [-1,1]:cloth.append(point(cx+side*width,-.216+.017*math.sin(3*math.pi*t+band),z-.035*band))
  batch('figures').add(cloth,[(2*j,2*j+1,2*j+3,2*j+2) for j in range(64)])
 for side in ([] if figure['pose']=='occluded' else [-1,1]):
  step=.13 if figure['pose']=='walking' and side==1 else -.04
  limb('figures',(x+side*.10,-.33,foot+.32),(x+side*.16+step,-.29,foot+.05),.045)
  ellipsoid(x+side*.16+step,-.22,foot+.045,.11,.065,.04)
 shoulder=head-.36
 if figure['pose']=='raised':
  arms=[[(hx-.17,-.28,shoulder),(hx-.34,-.23,shoulder+.42),(hx-.30,-.20,shoulder+.85)],[(hx+.17,-.28,shoulder),(hx+.47,-.23,shoulder+.40),(hx+.34,-.20,shoulder+.83)]]
 elif figure['pose']=='reaching':
  arms=[[(hx-.17,-.28,shoulder),(hx-.38,-.21,shoulder-.22),(hx-.51,-.17,shoulder-.08)],[(hx+.17,-.28,shoulder),(hx+.38,-.20,shoulder+.29),(hx+.54,-.18,shoulder+.42)]]
 elif figure['pose']=='walking':
  arms=[[(hx-.17,-.28,shoulder),(hx-.24,-.21,shoulder-.31),(hx-.36,-.19,shoulder-.55)],[(hx+.17,-.28,shoulder),(hx+.28,-.22,shoulder-.22),(hx+.18,-.18,shoulder-.45)]]
 elif figure['pose']=='occluded':
  arms=[]
 else:
  arms=[[(hx-.17,-.28,shoulder),(hx-.31,-.20,shoulder-.26),(x-.20,-.10,foot+.82)],[(hx+.17,-.28,shoulder),(hx+.30,-.20,shoulder-.24),(x+.23,-.10,foot+.81)]]
 for arm in arms:
  limb('figures',arm[0],arm[1],.095,.071);ellipsoid(*arm[1],.074,.055,.078);limb('figures',arm[1],arm[2],.069,.043);ellipsoid(*arm[-1],.054,.038,.065)

depth_offset=0
# The two trolley wheels belonged to the figure batch; retain their positions.
for side in [-1,1]:ellipsoid(-1.87+side*.21,-.15,4.32,.054,.020,.054)
obj=geometry.finish()
for modifier in list(obj.modifiers):obj.modifiers.remove(modifier)
bm=bmesh.new();bm.from_mesh(obj.data)
bad=[f for f in bm.faces if f.calc_area()<1e-10]
if bad:bmesh.ops.delete(bm,geom=bad,context='FACES')
bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.00001)
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
bm.to_mesh(obj.data);bm.free()
faces_before=len(obj.data.polygons)
# Thin physical strands use shared-edge ribbons instead of bulky hollow tubes.
# Their 3.8mm width is retained; unresolvable strand cross sections are omitted.
mesh=obj.data
mesh.update()
vertices,faces=[],[]
for edge in mesh.edges:
    a,b=[mesh.vertices[index] for index in edge.vertices]
    tangent=(b.co-a.co).normalized()
    normal=(a.normal+b.normal).normalized()
    lateral=tangent.cross(normal)
    if lateral.length<1e-8:continue
    lateral.normalize();lateral*=.0019
    start=len(vertices)
    vertices.extend([a.co-lateral,b.co-lateral,b.co+lateral,a.co+lateral])
    faces.append((start,start+1,start+2,start+3))
ribbon=bpy.data.meshes.new('OLD_V106_open_plastic_strands')
ribbon.from_pydata(vertices,[],faces);ribbon.update()
material=source.data.materials[0].copy();material.name='OLD_V106_double_sided_plastic'
material.use_backface_culling=False
ribbon.materials.append(material)
obj.data=ribbon
for poly in obj.data.polygons:poly.use_smooth=True
source.hide_render=True;source.hide_set(True)
obj['artwork']='Final Sale';obj['artist']='Recycle Group'
obj['scope']='Open plastic mesh with finer heads, arms and smooth interpolated robe outlines; estimated weave and anatomy'
assert all(digest(bpy.data.objects[n])==h for n,h in before.items())
for name in ['room-studies.json','room-spaces.json','building-review.json']:
    shutil.copyfile(ROOT/'result/blender/stage104'/name,OUT/name)
shutil.copyfile(ROOT/'web/public/models/catalogue.json',OUT/'catalogue-before.json')
audit={'version':106,'baselineNative':104,'baselineRelease':105,'source':source.name,'copy':obj.name,
       'originalFingerprints':before,'frame':frame,'figureCount':6,'surfaceFaces':faces_before,
       'latticeThickness':.0038,'finalFaces':len(obj.data.polygons),'finalVertices':len(obj.data.vertices),
       'reference':'Artist front photograph and user entrance photograph, capture dates unknown',
       'limits':['Not a sculpture scan; anatomy, cloth and lattice spacing estimated','Other exteriors and complete interiors remain unverified']}
(OUT/'old-figure-silhouettes-audit.json').write_text(json.dumps(audit,indent=2)+'\n')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v106.blend'))
print('OLD_FIGURE_SILHOUETTES_SAVED',faces_before,len(obj.data.polygons),flush=True)
