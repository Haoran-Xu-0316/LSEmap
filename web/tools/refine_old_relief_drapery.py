"""Refine OLD stone relief silhouettes and drapery from the supplied entrance photo.
Run in Blender Text Editor. This is authored shallow sculpture, not a scan.
"""
from pathlib import Path
import bpy, json, math, hashlib, array, sys
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'result/blender/stage71';OUT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(Path(__file__).resolve().parent))
from facade_geometry import Geometry,materials
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v70.blend'))
bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE']
collection=bpy.data.collections['OLD_EXTERIOR']
def digest(obj):
 h=hashlib.sha256(str([list(row) for row in obj.matrix_world]).encode())
 if obj.type=='MESH':
  h.update(array.array('f',[c for v in obj.data.vertices for c in v.co]).tobytes())
  h.update(array.array('i',[l.vertex_index for l in obj.data.loops]).tobytes())
 h.update(str([m.name if m else None for m in getattr(obj.data,'materials',[])]).encode())
 return h.hexdigest()
before={o.name:digest(o) for o in bpy.data.objects}
frame=json.loads((ROOT/'result/blender/stage52/old-houghton-audit.json').read_text())
origin,right,outward=[Vector(frame[k]) for k in ['origin','right','outward']]
def point(x,d,z):return origin+right*x+outward*d+Vector((0,0,z))
hidden=['OLD_V56_Entry_'+k for k in ['stone','shelf','book','basket']]
for name in hidden:
 obj=bpy.data.objects[name];obj.hide_render=True;obj.hide_set(True)
materials.clear()
for key,color in {'stone':(.58,.57,.535),'shelf':(.445,.44,.415),'basket':(.55,.545,.51),'book':(.515,.51,.475)}.items():
 mat=bpy.data.materials.new('OLD_V71_'+key);mat.use_nodes=True;mat.diffuse_color=(*color,1)
 shader=mat.node_tree.nodes['Principled BSDF'];shader.inputs['Base Color'].default_value=mat.diffuse_color;shader.inputs['Roughness'].default_value=.86
 materials[key]=mat
batches={}
def batch(key):
 if key not in batches:
  batches[key]=Geometry('OLD','relief71_'+key,key)
 return batches[key]
def box(key,x,d,z,w,t,h):batch(key).box(point(x,d,z),(w,t,h),math.atan2(right.y,right.x))
def limb(key,a,b,r0,r1=None):
 a,b=Vector(a),Vector(b);axis=(b-a).normalized();u=axis.cross(Vector((0,0,1)))
 if u.length<.01:u=Vector((1,0,0))
 u.normalize();v=axis.cross(u).normalized();r1=r0 if r1 is None else r1
 vs=[point(*(p+r*(u*math.cos(i*math.tau/12)+v*math.sin(i*math.tau/12))))for p,r in [(a,r0),(b,r1)]for i in range(12)]
 batch(key).add(vs,[(i,(i+1)%12,(i+1)%12+12,i+12)for i in range(12)]+[tuple(reversed(range(12))),tuple(range(12,24))])
def ellipsoid(x,d,z,rx,ry,rz):
 vs=[point(x+rx*math.cos(phi)*math.cos(theta),d+ry*math.cos(phi)*math.sin(theta),z+rz*math.sin(phi))for phi in [-math.pi/2+math.pi*j/12 for j in range(13)]for theta in [math.tau*i/20 for i in range(20)]]
 batch('stone').add(vs,[(j*20+i,j*20+(i+1)%20,(j+1)*20+(i+1)%20,(j+1)*20+i)for j in range(12)for i in range(20)])
# Shelving and irregular books remain behind the sculptural figures.
for x in [-2.37,-1.02,.62,2.38]:
 top=4.8+math.sqrt(2.80**2-x*x);box('shelf',x,-.51,(4.25+top)/2,.045,.065,top-4.25)
for row,z in enumerate([4.50,5.13,5.79,6.48,7.13]):
 half=min(2.76,math.sqrt(max(0,2.80**2-max(0,z-4.8)**2)));box('shelf',0,-.51,z,2*half,.07,.05)
 for k in range(int(2*half/.16)):
  x=-half+.09+k*.16;height=.18+.052*((k*7+row*3)%7)
  if z+height>4.8+math.sqrt(max(0,2.75**2-x*x)):continue
  if (k+row)%7==0:
   for stack in range(3):box('book',x,-.46,z+.043+stack*.055,.14,.10,.035)
  else:box('book',x,-.46,z+.03+height/2,.055+.012*(k%3),.10,height)
# Each figure has its own posture, asymmetrical cloth silhouette and head turn.
figures=[{'x':-2.05,'foot':4.28,'head':5.78,'lean':-.13,'turn':1,'pose':'walking'},
 {'x':-1.20,'foot':4.28,'head':5.98,'lean':.03,'turn':1,'pose':'basket'},
 {'x':-.18,'foot':4.40,'head':6.20,'lean':.19,'turn':1,'pose':'reaching'},
 {'x':1.03,'foot':4.69,'head':6.77,'lean':-.02,'turn':-1,'pose':'raised'},
 {'x':2.12,'foot':4.30,'head':6.07,'lean':-.10,'turn':-1,'pose':'basket'}]
basket_count=0
for index,figure in enumerate(figures):
 x,foot,head,lean=figure['x'],figure['foot'],figure['head'],figure['lean'];hx=x+lean
 ellipsoid(hx,-.30,head,.108,.073,.153)
 ellipsoid(hx-figure['turn']*.017,-.34,head+.063,.113,.057,.103)
 # Small facial profile and ears are relief volumes, not portraits.
 ellipsoid(hx+figure['turn']*.095,-.268,head-.015,.021,.025,.030)
 ellipsoid(hx-figure['turn']*.09,-.27,head-.008,.025,.04,.045)
 limb('stone',(hx,-.33,head-.13),(hx-.025,-.33,head-.28),.057)
 ellipsoid(hx-.025,-.34,head-.36,.22,.085,.14)
 # A full shoulder-to-hem surface with curved, asymmetric folds replaces
 # the isolated narrow torso and cylindrical diagonal mantle.
 vertices=[];levels=30;sides=36
 for j in range(levels):
  t=j/(levels-1);z=foot+.18+t*(head-foot-.40)
  cx=x+lean*t+.045*math.sin(t*math.pi+index)
  # Hem, knees, waist and shoulder widths are interpolated continuously.
  knots=[(0,.265),(.20,.24),(.48,.22),(.70,.175),(.88,.225),(.94,.210),(1,.064)]
  lo,hi=next((a,b) for a,b in zip(knots,knots[1:]) if a[0]<=t<=b[0])
  width=lo[1]+(hi[1]-lo[1])*(t-lo[0])/(hi[0]-lo[0])
  for k in range(sides):
   angle=k*math.tau/sides
   fold=1+.09*math.cos(7*angle+3*t+index)+.035*math.cos(13*angle-2*t)
   vertices.append(point(cx+width*math.cos(angle)*fold,-.35+.105*math.sin(angle)*fold,z))
 batch('stone').add(vertices,[(j*sides+k,j*sides+(k+1)%sides,(j+1)*sides+(k+1)%sides,(j+1)*sides+k) for j in range(levels-1) for k in range(sides)])
 # Thin overlapping draped bands cross the chest, then broaden over the skirt.
 for band in range(3):
  cloth=[]
  for j in range(25):
   t=j/24;z=head-.36-t*(head-foot-.64)
   cx=hx-.18+(.30+.025*band)*t+.035*math.sin(math.pi*t)
   width=.043+.043*t
   for side in [-1,1]:cloth.append(point(cx+side*width,-.216+.017*math.sin(3*math.pi*t+band),z-.035*band))
  batch('stone').add(cloth,[(2*j,2*j+1,2*j+3,2*j+2) for j in range(24)])
 for side in [-1,1]:
  step=.13 if figure['pose']=='walking' and side==1 else -.04
  limb('stone',(x+side*.10,-.33,foot+.32),(x+side*.16+step,-.29,foot+.05),.045)
  ellipsoid(x+side*.16+step,-.22,foot+.045,.11,.065,.04)
 shoulder=head-.36
 if figure['pose']=='raised':
  arms=[[(hx-.17,-.28,shoulder),(hx-.34,-.23,shoulder+.42),(hx-.30,-.20,shoulder+.85)],[(hx+.17,-.28,shoulder),(hx+.47,-.23,shoulder+.40),(hx+.34,-.20,shoulder+.83)]]
 elif figure['pose']=='reaching':
  arms=[[(hx-.17,-.28,shoulder),(hx-.38,-.21,shoulder-.22),(hx-.51,-.17,shoulder-.08)],[(hx+.17,-.28,shoulder),(hx+.38,-.20,shoulder+.29),(hx+.54,-.18,shoulder+.42)]]
 elif figure['pose']=='walking':
  arms=[[(hx-.17,-.28,shoulder),(hx-.24,-.21,shoulder-.31),(hx-.36,-.19,shoulder-.55)],[(hx+.17,-.28,shoulder),(hx+.28,-.22,shoulder-.22),(hx+.18,-.18,shoulder-.45)]]
 else:
  arms=[[(hx-.17,-.28,shoulder),(hx-.31,-.20,shoulder-.26),(x-.20,-.10,foot+.82)],[(hx+.17,-.28,shoulder),(hx+.30,-.20,shoulder-.24),(x+.23,-.10,foot+.81)]]
 for arm in arms:
  limb('stone',arm[0],arm[1],.095,.071);ellipsoid(*arm[1],.074,.055,.078);limb('stone',arm[1],arm[2],.069,.043);ellipsoid(*arm[-1],.054,.038,.065)
 if figure['pose']=='basket':
  basket_count+=1;z=foot+.76;box('basket',x,-.12,z-.17,.48,.15,.055)
  for zz in [z-.17,z+.12]:box('basket',x,-.035,zz,.55,.025,.025)
  for j in range(8):box('basket',x-.25+j*.0714,-.035+.03*abs(j-3.5)/3.5,z-.025,.012,.020,.29)
  for j in range(3):box('basket',x,-.032,z-.10+j*.10,.52,.022,.014)
  for side in [-1,1]:limb('basket',(x+side*.27,-.12,z-.15),(x+side*.27,-.04,z+.12),.014)
# The raised figure rests on a small stack visible against the shelves.
for layer in range(3):box('book',1.03,-.31,4.30+layer*.12,.56,.20,.11)
# Leaning ladder near the left figures; short rungs avoid obscuring their bodies.
for side in [-1,1]:limb('shelf',(-1.43+side*.16,-.15,4.30),(-.67+side*.16,-.17,5.88),.023)
for j in range(7):
 t=j/6;limb('shelf',(-1.43+.76*t-.16,-.15,4.30+1.58*t),(-1.43+.76*t+.16,-.15,4.30+1.58*t),.017)
added=[]
for key,g in batches.items():
 obj=g.finish();added.append(obj.name)
 for modifier in list(obj.modifiers):obj.modifiers.remove(modifier)
 if key=='stone':
  for poly in obj.data.polygons:poly.use_smooth=True
changed=[name for name,prior in before.items() if digest(bpy.data.objects[name])!=prior]
assert not changed,changed
for filename in ['room-studies.json','room-spaces.json','building-review.json']:
 (OUT/filename).write_bytes((ROOT/'result/blender/stage70'/filename).read_bytes())
audit={'version':71,'baseline':70,'frame':frame,'figureCount':len(figures),'basketCount':basket_count,'addedObjects':added,'hiddenPreviousObjects':hidden,'changedExistingGeometry':changed,'reference':'User supplied OLD entrance photograph, date unknown','limitations':['Photo-estimated relief silhouettes and shallow drapery, not an exact scan or carved portrait','Heraldic device, other elevations, roof and complete interior remain unresolved']}
(OUT/'old-relief-drapery-audit.json').write_text(json.dumps(audit,indent=2)+'\n')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v71.blend'))
print('OLD_RELIEF_DRAPERY_SAVED',len(added))
