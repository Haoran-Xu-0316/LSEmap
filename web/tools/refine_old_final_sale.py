"""Refine OLD Final Sale plastic-mesh figures and supermarket shelves from the supplied entrance photo.
Run in Blender Text Editor. This is photo-guided mesh interpretation, not a scan.
"""
from pathlib import Path
import bpy, bmesh, json, math, hashlib, array, sys
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'result/blender/stage84';OUT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(Path(__file__).resolve().parent))
from facade_geometry import Geometry,materials
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v83.blend'))
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
depth_offset=0.0
def point(x,d,z):return origin+right*x+outward*(d+depth_offset)+Vector((0,0,z))
hidden=['OLD_D5_relief71_'+k for k in ['stone','shelf','book','basket']]
hidden.append('OLD_V56_Entry_backing')
for name in hidden:
 obj=bpy.data.objects[name];obj.hide_render=True;obj.hide_set(True)
materials.clear()
for key,color in {'figures':(.66,.66,.635),'display_frame':(.59,.60,.58),'containers':(.63,.64,.615),'products':(.64,.65,.625)}.items():
 mat=bpy.data.materials.new('OLD_V84_FinalSale_'+key);mat.use_nodes=True;mat.diffuse_color=(*color,1)
 shader=mat.node_tree.nodes['Principled BSDF'];shader.inputs['Base Color'].default_value=mat.diffuse_color;shader.inputs['Roughness'].default_value=.86
 materials[key]=mat
batches={}
def batch(key):
 if key not in batches:
  batches[key]=Geometry('OLD','finalsale84_'+key,key)
 return batches[key]
def box(key,x,d,z,w,t,h):batch(key).box(point(x,d,z),(w,t,h),math.atan2(right.y,right.x))
def limb(key,a,b,r0,r1=None):
 a,b=Vector(a),Vector(b);axis=(b-a).normalized();u=axis.cross(Vector((0,0,1)))
 if u.length<.01:u=Vector((1,0,0))
 u.normalize();v=axis.cross(u).normalized();r1=r0 if r1 is None else r1
 rings=max(2,math.ceil((b-a).length/.07));vs=[]
 for j in range(rings+1):
  t=j/rings;p=a.lerp(b,t);r=r0+(r1-r0)*t
  vs.extend(point(*(p+r*(u*math.cos(i*math.tau/12)+v*math.sin(i*math.tau/12))))for i in range(12))
 batch(key).add(vs,[(j*12+i,j*12+(i+1)%12,(j+1)*12+(i+1)%12,(j+1)*12+i)for j in range(rings)for i in range(12)])

def ellipsoid(x,d,z,rx,ry,rz):
 vs=[point(x+rx*math.cos(phi)*math.cos(theta),d+ry*math.cos(phi)*math.sin(theta),z+rz*math.sin(phi))for phi in [-math.pi/2+math.pi*j/12 for j in range(13)]for theta in [math.tau*i/20 for i in range(20)]]
 batch('figures').add(vs,[(j*20+i,j*20+(i+1)%20,(j+1)*20+(i+1)%20,(j+1)*20+i)for j in range(12)for i in range(20)])
# Shelving and irregular books remain behind the sculptural figures.
for x in [-2.37,-1.02,.62,2.38]:
 top=4.8+math.sqrt(2.80**2-x*x);box('display_frame',x,-.51,(4.25+top)/2,.045,.065,top-4.25)
for row,z in enumerate([4.50,5.13,5.79,6.48,7.13]):
 half=min(2.76,math.sqrt(max(0,2.80**2-max(0,z-4.8)**2)));box('display_frame',0,-.51,z,2*half,.07,.05)
 for k in range(int(2*half/.24)):
  x=-half+.14+k*.24;height=.20+.044*((k*5+row*3)%7)
  if z+height>4.8+math.sqrt(max(0,2.75**2-x*x)):continue
  if (k+row)%3==0:
   # Thin-necked bottle, body and shoulder rings.
   profile=[(0,.066),(.68,.066),(.78,.036),(1,.029)]
   vs=[point(x+r*math.cos(t),-.465+r*.60*math.sin(t),z+.035+f*height)for f,r in profile for t in [i*math.tau/10 for i in range(10)]]
   batch('products').add(vs,[(j*10+i,j*10+(i+1)%10,(j+1)*10+(i+1)%10,(j+1)*10+i)for j in range(3)for i in range(10)])
  else:
   # Supermarket packets and bags taper to a gathered top.
   vs=[]
   for j in range(7):
    t=j/6;width=.07*(.62+.38*math.sin(math.pi*t))
    for k in range(10):
     angle=k*math.tau/10
     vs.append(point(x+width*math.cos(angle),-.47+.035*math.sin(angle),z+.035+t*height))
   batch('products').add(vs,[(j*10+i,j*10+(i+1)%10,(j+1)*10+(i+1)%10,(j+1)*10+i)for j in range(6)for i in range(10)])
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
 batch('figures').add(vertices,[(j*sides+k,j*sides+(k+1)%sides,(j+1)*sides+(k+1)%sides,(j+1)*sides+k) for j in range(levels-1) for k in range(sides)])
 # Thin overlapping draped bands cross the chest, then broaden over the skirt.
 for band in range(3):
  cloth=[]
  for j in range(25):
   t=j/24;z=head-.36-t*(head-foot-.64)
   cx=hx-.18+(.30+.025*band)*t+.035*math.sin(math.pi*t)
   width=.043+.043*t
   for side in [-1,1]:cloth.append(point(cx+side*width,-.216+.017*math.sin(3*math.pi*t+band),z-.035*band))
  batch('figures').add(cloth,[(2*j,2*j+1,2*j+3,2*j+2) for j in range(24)])
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
 if figure['pose']=='basket':
  basket_count+=1;z=foot+.76;box('containers',x,-.12,z-.17,.48,.15,.055)
  for zz in [z-.17,z+.12]:box('containers',x,-.035,zz,.55,.025,.025)
  for j in range(8):box('containers',x-.25+j*.0714,-.035+.03*abs(j-3.5)/3.5,z-.025,.012,.020,.29)
  for j in range(3):box('containers',x,-.032,z-.10+j*.10,.52,.022,.014)
  for side in [-1,1]:limb('containers',(x+side*.27,-.12,z-.15),(x+side*.27,-.04,z+.12),.014)
depth_offset=0
# Boxed products form a short raised pedestal under the reaching shopper.
for layer in range(3):box('products',1.03,-.31,4.57+layer*.12,.56,.20,.11)
# The left diagonal members belong to a shopping trolley, not a ladder.
z=5.12;x=-1.87;basket_count+=1
for j in range(10):box('containers',x-.34+j*.075,-.12,z,.009,.016,.40)
for height in [-.20,-.07,.07,.20]:box('containers',x,-.12,z+height,.71,.016,.009)
for side in [-1,1]:
 limb('display_frame',(x+side*.35,-.13,z-.20),(x-side*.20,-.13,4.36),.014)
 limb('display_frame',(x+side*.35,-.13,z+.20),(x+side*.37,-.13,z+.29),.014)
 # The small solid wheels stay legible without multiplying mesh holes.
 ellipsoid(x+side*.21,-.15,4.32,.054,.020,.054)
# Rear arched glazing reveals the mesh openings rather than a stone backing.
glass=bpy.data.materials.new('OLD_V84_FinalSale_glazing');glass.use_nodes=True
glass.diffuse_color=(.15,.18,.18,.58)
shader=glass.node_tree.nodes['Principled BSDF'];shader.inputs['Base Color'].default_value=(.15,.18,.18,1)
shader.inputs['Roughness'].default_value=.2;shader.inputs['Alpha'].default_value=.58
shader.inputs['Transmission Weight'].default_value=.12;glass['webOpacity']=.58
materials['glazing']=glass
outline=[(-2.90,4.16),(2.90,4.16)]+[(2.90*math.cos(k*math.pi/64),4.8+2.90*math.sin(k*math.pi/64))for k in range(65)]
batch('glazing').add([point(x,-.579,z)for x,z in outline],[tuple(range(len(outline)))])
added=[]
for key,g in batches.items():
 obj=g.finish();added.append(obj.name)
 for modifier in list(obj.modifiers):obj.modifiers.remove(modifier)
 bm=bmesh.new();bm.from_mesh(obj.data)
 bad=[f for f in bm.faces if f.calc_area()<1e-10]
 if bad:bmesh.ops.delete(bm,geom=bad,context='FACES')
 bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.00001)
 bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
 if key=='glazing':
  bm.normal_update()
  for face in bm.faces:
   if face.normal.dot(outward)<0:face.normal_flip()
 bm.to_mesh(obj.data);bm.free()
 if key in ['figures','products']:
  bpy.context.view_layer.objects.active=obj
  mod=obj.modifiers.new('Open plastic lattice','WIREFRAME');mod.thickness=.0075
  mod.use_replace=True;mod.use_boundary=True;mod.use_even_offset=True
  bpy.ops.object.modifier_apply(modifier=mod.name)
  for poly in obj.data.polygons:poly.use_smooth=True
 obj['artwork']='Final Sale';obj['artist']='Recycle Group'
 obj['materialEvidence']='Plastic mesh; Gazelli Art House and artist portfolio'
changed=[name for name,prior in before.items() if digest(bpy.data.objects[name])!=prior]
assert not changed,changed
for filename in ['room-studies.json','room-spaces.json','building-review.json']:
 (OUT/filename).write_bytes((ROOT/'result/blender/stage83'/filename).read_bytes())
audit={'version':84,'baseline':83,'frame':frame,'figureCount':len(figures),'figures':figures,'basketCount':basket_count,'addedObjects':added,'hiddenPreviousObjects':hidden,'baselineFingerprint':before,'changedExistingGeometry':changed,'referenceUrls':['https://gazell.io/collections/recycle-group/products/final-sale','https://recyclegroup.fr/portfolio/final-sale/'],'reference':'User Houghton photo plus artist front and side photographs, capture dates unknown','limitations':['Six figure relationships, trolley and product silhouettes guided by photos; exact anatomy and mesh spacing are estimates','Artwork catalogue dimensions 330x480x30cm guide proportions, but installation alignment remains inherited and estimated','No photographic texture or exact sculpture scan; unseen exterior, roof and complete interior remain unresolved']}
(OUT/'old-final-sale-audit.json').write_text(json.dumps(audit,indent=2)+'\n')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v84.blend'))
print('OLD_FINAL_SALE_SAVED',len(added),len(figures),basket_count,flush=True)
