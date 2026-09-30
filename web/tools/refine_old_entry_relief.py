"""OLD Houghton concave stone reveal and photo-guided five-figure relief.
Run in Blender Text Editor; native55 and other buildings are preserved.
This authored interpretation is not a scan or an exact carving reproduction.
"""
from pathlib import Path
import bpy,bmesh,json,math,hashlib,array,sys
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'result/blender/stage56';OUT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(Path(__file__).resolve().parent))
from facade_geometry import Geometry,materials
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v55.blend'))
bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE']
collection=bpy.data.collections['OLD_EXTERIOR']
def digest(obj):
 h=hashlib.sha256(str([list(row)for row in obj.matrix_world]).encode())
 if obj.type=='MESH':h.update(array.array('f',[c for v in obj.data.vertices for c in v.co]).tobytes());h.update(array.array('i',[l.vertex_index for l in obj.data.loops]).tobytes())
 return h.hexdigest()
before={o.name:digest(o)for o in bpy.data.objects}
frame=json.loads((ROOT/'result/blender/stage52/old-houghton-audit.json').read_text());origin=Vector(frame['origin']);right=Vector(frame['right']);outward=Vector(frame['outward'])
def point(x,d,z):return origin+right*x+outward*d+Vector((0,0,z))
def local(p):
 v=p-origin;return Vector((v.dot(right),v.dot(outward),v.z))
hidden=[]
for name in ['OLD_Massive_entrance_arch','OLD_Rusticated_arch_voussoirs','OLD_V52_Houghton_stone','OLD_Photographic_relief_panel']:
 obj=bpy.data.objects[name];obj.hide_render=True;obj.hide_set(True);hidden.append(name)
# Remove the old fine rings and shelf/book batches without touching ashlar walls.
removed={}
for obj in list(collection.all_objects):
 if obj.type!='MESH' or obj.hide_render or not obj.name.startswith('OLD_V52_Houghton_ashlar_'):continue
 bm=bmesh.new();bm.from_mesh(obj.data);faces=[]
 for face in bm.faces:
  pts=[local(obj.matrix_world@v.co)for v in face.verts]
  shelf=all(abs(p.x)<2.81 and -.57<p.y<-.37 and 4.43<p.z<7.65 for p in pts)
  ring=all(2.875<math.hypot(p.x,p.z-4.8)<2.915 and p.z>=4.79 for p in pts)
  if shelf or ring:faces.append(face)
 if faces:removed[obj.name]=len(faces);bmesh.ops.delete(bm,geom=faces,context='FACES');bm.to_mesh(obj.data);obj.data.update()
 bm.free()
materials.clear()
for key,color in {'stone':(.61,.595,.55),'reveal':(.59,.575,.53),'shelf':(.46,.455,.43),'basket':(.57,.565,.53),'book':(.53,.525,.49),'rim':(.61,.595,.55),'backing':(.39,.395,.38),'joint':(.43,.425,.40)}.items():
 mat=bpy.data.materials.new('OLD_V56_'+key);mat.use_nodes=True;mat.diffuse_color=(*color,1);shader=mat.node_tree.nodes['Principled BSDF'];shader.inputs['Base Color'].default_value=mat.diffuse_color;shader.inputs['Roughness'].default_value=.83;materials[key]=mat
batches={}
def batch(key):
 if key not in batches:
  batches[key]=Geometry('OLD','entry_'+key,key);batches[key].name='OLD_V56_Entry_'+key
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
# A smoothly recessed intrados replaces the flat face and raised outer border.
# Radius/depth samples define a concave section registered to the existing opening.
radial=[(2.90+1.30*j/12,-.63+.85*(j/12)**.65)for j in range(13)]
for segment in range(32):
 a=segment*math.pi/32+.0014;b=(segment+1)*math.pi/32-.0014
 for (r0,d0),(r1,d1) in zip(radial,radial[1:]):
  vs=[point(r*math.cos(t),d,4.8+r*math.sin(t))for t in [a,b]for r,d in [(r0,d0),(r1,d1)]]
  batch('reveal').add(vs,[(0,1,3,2)])
 # Recessed continuous backing prevents angular joints looking through the wall.
 for (r0,d0),(r1,d1) in zip(radial,radial[1:]):
  vs=[point(r*math.cos(t),d-.014,4.8+r*math.sin(t))for t in [segment*math.pi/32,(segment+1)*math.pi/32]for r,d in [(r0,d0),(r1,d1)]]
  batch('joint').add(vs,[(0,1,3,2)])
 # Extend the radial ashlar joint treatment into the surrounding outer face.
 for j in range(2):
  r0=4.20+j*.28;r1=r0+.28
  vs=[point(r*math.cos(t),.224,4.8+r*math.sin(t))for r,t in [(r0,a),(r1,a),(r1,b),(r0,b)]]
  batch('reveal').add(vs,[(0,1,2,3)])
# Dressed inner ring follows the recessed rim rather than the front wall plane.
for segment in range(48):
 a=segment*math.pi/48+.001;b=(segment+1)*math.pi/48-.001
 vs=[point(r*math.cos(t),d,4.8+r*math.sin(t))for d in [-.65,-.58]for r,t in [(2.84,a),(2.92,a),(2.92,b),(2.84,b)]]
 batch('rim').add(vs,[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)])
# Plain stone backdrop replaces the private photographic projection.
outline=[(-2.90,4.16),(2.90,4.16)]+[(2.90*math.cos(k*math.pi/64),4.8+2.90*math.sin(k*math.pi/64))for k in range(65)]
batch('backing').add([point(x,-.579,z)for x,z in outline],[tuple(range(len(outline)))])
# Shelving and irregular books remain behind the sculptural figures.
for x in [-2.37,-1.02,.62,2.38]:
 top=4.8+math.sqrt(2.80**2-x*x);box('shelf',x,-.51,(4.25+top)/2,.045,.065,top-4.25)
for row,z in enumerate([4.50,5.13,5.79,6.48,7.13]):
 half=min(2.76,math.sqrt(max(0,2.80**2-max(0,z-4.8)**2)));box('shelf',0,-.51,z,2*half,.07,.05)
 for k in range(int(2*half/.16)):
  x=-half+.09+k*.16;height=.10+.055*((k*7+row*3)%5)
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
 ellipsoid(hx,-.29,head,.115,.095,.15)
 # Small facial profile and ears are relief volumes, not portraits.
 ellipsoid(hx+figure['turn']*.095,-.21,head-.025,.045,.04,.035)
 ellipsoid(hx-figure['turn']*.09,-.27,head-.008,.025,.04,.045)
 limb('stone',(hx,-.33,head-.13),(hx-.025,-.33,head-.28),.057)
 ellipsoid(hx-.025,-.34,head-.36,.22,.085,.14)
 vertices=[];levels=18;sides=28
 for j in range(levels):
  t=j/(levels-1);z=foot+.18+t*(head-foot-.64);cx=x+lean*t+.09*math.sin(t*math.pi+index)
  width=.20+.07*math.sin(math.pi*t)-.06*t
  for k in range(sides):
   angle=k*math.tau/sides;fold=1+.16*math.cos(6*angle+4*t+index)
   vertices.append(point(cx+width*math.cos(angle)*fold,-.35+.075*math.sin(angle)*fold,z))
 batch('stone').add(vertices,[(j*sides+k,j*sides+(k+1)%sides,(j+1)*sides+(k+1)%sides,(j+1)*sides+k)for j in range(levels-1)for k in range(sides)])
 # A visible diagonal mantle adds the observed drapery instead of a plain cone.
 limb('stone',(hx-.19,-.24,head-.32),(x+.18,-.23,foot+.40),.065,.09)
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
  limb('stone',arm[0],arm[1],.085,.067);limb('stone',arm[1],arm[2],.065,.045);ellipsoid(*arm[-1],.06,.05,.055)
 if figure['pose']=='basket':
  basket_count+=1;z=foot+.76;box('basket',x,-.12,z-.17,.48,.15,.055)
  for zz in [z-.17,z+.12]:box('basket',x,-.035,zz,.55,.025,.025)
  for j in range(8):box('basket',x-.25+j*.0714,-.035,z-.025,.014,.025,.29)
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
reveal=bpy.data.objects['OLD_V56_Entry_reveal']
depths=[local(reveal.matrix_world@v.co).y for v in reveal.data.vertices]
assert min(depths)<-.62 and max(depths)>.21,(min(depths),max(depths))
for layer in bpy.context.scene.view_layers:layer.update()
changed=[name for name,prior in before.items()if digest(bpy.data.objects[name])!=prior]
assert all(name.startswith('OLD_')for name in changed),changed
for filename in ['room-studies.json','room-spaces.json','building-review.json']:(OUT/filename).write_bytes((ROOT/'result/blender/stage55'/filename).read_bytes())
audit={'version':56,'baseline':55,'changedExistingObjects':changed,'changedOtherObjects':[n for n in changed if not n.startswith('OLD_')],'hiddenPreviousObjects':hidden,'removedObsoleteFaces':removed,'figureCount':len(figures),'basketCount':basket_count,'figures':figures,'revealSection':radial,'savedRevealDepthRange':[min(depths),max(depths)],'addedObjects':added,'reference':'data/collections/old-exterior-2026/user-references/houghton-entrance-close.png','limitations':['User supplied photograph capture date unknown; dimensions estimated','Relief is a photo-guided sculptural interpretation, not a scan or exact reproduction','Heraldic carving, other elevations, roof and full interiors remain unresolved']}
(OUT/'old-entry-relief-audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v56.blend'));print('OLD_ENTRY_SAVED',len(changed),len(figures),basket_count)
