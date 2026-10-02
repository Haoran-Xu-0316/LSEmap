"""Rebuild LRB's stepped roof from the 2025 survey and approved plant layout.

Run in Blender Text Editor. Preserve archived originals and all lower interiors.
Outline registration and some plant detail are estimates, documented in the audit.
"""
from pathlib import Path
import array,hashlib,json,math,shutil,sys
import bpy
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'result/blender/stage109'
sys.path.insert(0,str(Path(__file__).resolve().parent))
from facade_geometry import Geometry,materials
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v108.blend'))
bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE'];collection=bpy.data.collections['LRB_EXTERIOR']
plan=json.loads((OUT/'roof-survey-geometry.json').read_text())
def digest(obj):
 h=hashlib.sha256(str([list(r)for r in obj.matrix_world]).encode())
 if obj.type=='MESH':
  h.update(array.array('f',[c for v in obj.data.vertices for c in v.co]).tobytes())
  h.update(array.array('i',[l.vertex_index for l in obj.data.loops]).tobytes())
 h.update(str([m.name if m else None for m in getattr(obj.data,'materials',[])]).encode())
 return h.hexdigest()
before={o.name:digest(o)for o in bpy.data.objects}
visible=[o for o in collection.all_objects if not o.hide_render]
archived=[];copies={}
def archive(obj):
 obj.hide_render=True;obj.hide_set(True);archived.append(obj.name)
def copy(obj,name):
 new=obj.copy();new.data=obj.data.copy();new.name=name;collection.objects.link(new)
 archive(obj);new.hide_render=False;new.hide_set(False);copies[obj.name]=new.name
 return new
# Remove the generic continuous mansard and its 24 estimated dormers. The survey
# distinguishes the lower perimeter terrace from the raised setback office roof.
for obj in visible:
 if obj.name.startswith('LRB_D5_mansard60_') or obj.name=='LRB_V108_survey_deck_opening':archive(obj)
# Ground datum 19.76m from the southwest survey elevation. Existing facade rows
# are remapped monotonically; their bay rhythm still requires full reconstruction.
old_knots=[0,4.35,5.5,8.8,13.15,14.2,17.5,18.55,21.85,23.0]
new_knots=[0,4.35,5.66,8.81,12.43,13.72,16.58,17.59,19.55,plan['lowerRoofHeight']]
def remap(z):
 if z<=0:return z
 for a,b,c,d in zip(old_knots,old_knots[1:],new_knots,new_knots[1:]):
  if z<=b:return c+(z-a)*(d-c)/(b-a)
 return new_knots[-1]+z-old_knots[-1]
facade_copies=[]
for obj in visible:
 if obj.hide_render or obj.type!='MESH' or obj.name.startswith('LRB_V108_'):continue
 new=copy(obj,'LRB_V109_facade_'+obj.name.removeprefix('LRB_'))
 inv=new.matrix_world.inverted()
 for vertex in new.data.vertices:
  p=new.matrix_world@vertex.co;p.z=remap(p.z);vertex.co=inv@p
 new.data.update();facade_copies.append(new.name)
# The cap retains measured dimensions and centre; shift its local datum down to
# the same surveyed ground reference as the new main roof.
shift=plan['upperRoofHeight']-25.8
for obj in visible:
 if obj.hide_render or not obj.name.startswith('LRB_V108_'):continue
 new=copy(obj,obj.name.replace('V108','V109'))
 inv=new.matrix_world.inverted()
 for vertex in new.data.vertices:
  p=new.matrix_world@vertex.co
  if 'spring_collar' in obj.name:
   if p.z<=25.80001:p.z=plan['lowerRoofHeight']+(p.z-23)*(plan['upperRoofHeight']-plan['lowerRoofHeight'])/2.8
   else:p.z+=shift
  else:p.z+=shift
  vertex.co=inv@p
 new.data.update();new['sharedInteriorRoof']=True
materials.clear()
for key,color,rough,metal in [
 ('roof',(.37,.39,.39),.83,0),('cladding',(.62,.64,.625),.65,.08),
 ('glass',(.14,.19,.20),.17,.18),('frame',(.17,.19,.19),.52,.35),
 ('plant',(.60,.64,.64),.5,.30),('grille',(.15,.17,.17),.7,.3),
 ('panel',(.055,.10,.145),.23,.25),('rail',(.45,.48,.49),.45,.65)]:
 m=bpy.data.materials.new('LRB_V109_'+key);m.use_nodes=True;m.diffuse_color=(*color,1)
 p=m.node_tree.nodes['Principled BSDF'];p.inputs['Base Color'].default_value=m.diffuse_color
 p.inputs['Roughness'].default_value=rough;p.inputs['Metallic'].default_value=metal
 materials[key]=m
batches={}
def batch(key):
 if key not in batches:batches[key]=Geometry('LRB','roof109_'+key,key)
 return batches[key]
low,high=plan['lowerRoofHeight'],plan['upperRoofHeight']
for kind,height in [('lower',low),('upper',high)]:
 for triangle in plan[kind+'Triangles']:batch('roof').add([(*p,height)for p in triangle],[(0,1,2)])
boundary=[Vector(p)for p in plan['raisedBoundary']]
clerestory=[]
# The vertical riser is the setback office storey. Pane subdivisions are estimated
# from the elevation; the roof footprint and height follow the survey registration.
for a,b in zip(boundary,boundary[1:]+boundary[:1]):
 direction=(b-a).normalized();length=(b-a).length;normal=Vector((direction.y,-direction.x))
 angle=math.atan2(direction.y,direction.x)
 def point(x,d,z):return (*((a+direction*x)+normal*d),z)
 count=max(1,round(length/2.4));pitch=length/count
 for index in range(count):
  x=(index+.5)*pitch
  batch('cladding').box(point(x,-.10,(low+high)/2),(pitch,.20,high-low),angle)
  if length<2.5:continue
  lo,hi=low+.65,high-.48;width=min(1.35,pitch*.66)
  batch('glass').box(point(x,.022,(lo+hi)/2),(width,.035,hi-lo),angle)
  for z in [lo,hi,(lo+hi)/2]:batch('frame').box(point(x,.058,z),(width,.08,.035),angle)
  for sign in [-1,1]:batch('frame').box(point(x+sign*width/2,.058,(lo+hi)/2),(.035,.08,hi-lo),angle)
  clerestory.append([*point(x,.02,(lo+hi)/2),width,hi-lo])
 batch('cladding').box(point(length/2,-.04,high+.075),(length+.12,.35,.15),angle)
# One clearly drawn existing plant room east of the skylight. Its detailed joins,
# windows and hidden elevations are estimates. The other room will be reviewed.
room=[Vector(p)for p in plan['plant']['room']]
room_height=3.2
batch('roof').add([(*p,high+room_height)for p in room],[(0,1,2,3)])
for a,b in zip(room,room[1:]+room[:1]):
 batch('cladding').add([(*a,high),(*b,high),(*b,high+room_height),(*a,high+room_height)],[(0,1,2,3)])
# Three approved 5.2x2.2x2.5m air-source heat pump housings and access platform.
# Completion is confirmed by LSE; exact as-built placement/detail is unverified.
angle=plan['rotationRadians'];right=Vector((math.cos(angle),math.sin(angle)))
down=Vector((math.sin(angle),-math.cos(angle)))
unit_centres=[Vector(p)for p in plan['plant']['heatPumpCentres']]
platform_centre=sum(unit_centres,Vector((0,0)))/3
batch('rail').box((*platform_centre,high+.12),(14.7,8.2,.24),angle)
for centre in unit_centres:
 batch('plant').box((*centre,high+.24+1.25),(2.2,5.2,2.5),angle)
 for side in [-1,1]:
  for row in range(16):
   p=centre+right*side*1.108
   batch('grille').box((*p,high+.55+row*.115),(.025,4.85,.05),angle)
 # Top fan rings express the mechanism; number and enclosure detail estimated.
 for offset in [-1.65,0,1.65]:
  centre_fan=centre+down*offset
  for i in range(32):
   a,b=i*2*math.pi/32,(i+1)*2*math.pi/32
   verts=[(*((centre_fan+Vector((math.cos(t),math.sin(t)))*r)),high+2.755)for r,t in [(.44,a),(.44,b),(.51,b),(.51,a)]]
   batch('grille').add(verts,[(0,1,2,3)])
# Retained PV arrays on the approved plan. Broad array footprints are estimated;
# do not recreate the solar panels replaced by the three heat pumps.
pv_pixels=[(870,198,4.8,1.6),(986,192,3.3,1.6),(1075,183,3.3,1.6),
 (1193,177,3.3,1.6),(1310,169,3.3,1.6),(1437,166,3.3,1.6),
 (988,230,12.8,1.2),(990,278,12.5,1.2),(1280,218,5.4,1.4),
 (1404,210,5.4,1.4),(931,990,15.4,1.3),(812,1097,2.5,1.3),
 (749,1137,13.0,1.3)]
# Reuse the rigid registration prepared outside Blender; validate full panel
# polygons against the raised roof before adding them.
import subprocess
pv_outline=[]
for px,py,w,d in pv_pixels:
 delta=Vector((px-plan['sourcePixelCentre'][0],py-plan['sourcePixelCentre'][1]))
 centre=Vector(plan['centre'])+(right*delta.x+down*delta.y)*plan['metresPerPixel']
 pv_outline.append({'centre':list(centre),'dimensions':[w,d]})
(OUT/'pv-candidates.json').write_text(json.dumps(pv_outline))
subprocess.run(['/opt/anaconda3/envs/MachineLearning/bin/python',str(ROOT/'web/tools/validate_library_roof_panels.py')],check=True)
pv=json.loads((OUT/'pv-validated.json').read_text())
for item in pv:
 centre=Vector(item['centre']);w,d=item['dimensions'];z=high+.16
 batch('panel').box((*centre,z),(w,d,.055),angle)
 columns=max(1,round(w/1.1))
 for k in range(columns+1):
  p=centre+right*(k*w/columns-w/2)
  batch('rail').box((*p,z+.035),(.015,d,.015),angle)
 for side in [-1,1]:
  p=centre+down*side*d/2
  batch('rail').box((*p,z+.035),(w,.015,.015),angle)
added=[]
for g in batches.values():
 o=g.finish();o['sharedInteriorRoof']=True;o['scope']='2025 survey-guided roof architecture and approved plant layout; registration, window rhythm and enclosure details approximate'
 for modifier in list(o.modifiers):o.modifiers.remove(modifier)
 added.append(o.name)
assert all(digest(bpy.data.objects[n])==h for n,h in before.items())
for name in ['room-studies.json','room-spaces.json','building-review.json']:shutil.copyfile(ROOT/'result/blender/stage108'/name,OUT/name)
baseline_web_commit='5b51ada1a7425017de75c46a0213bfe2176d28aa'
(OUT/'catalogue-before.json').write_bytes(subprocess.check_output(['git','show',baseline_web_commit+':web/public/models/catalogue.json'],cwd=ROOT))
audit={'version':109,'baselineNative':108,'originalFingerprints':before,'archived':archived,'copies':copies,
       'newRoofObjects':added,'facadeCopies':facade_copies,'datum':19.76,'lowRoofHeight':low,'highRoofHeight':high,
       'capShift':shift,'clerestoryWindows':clerestory,'heatPumpCentres':[list(p)for p in unit_centres],
       'pumpDimensions':[2.2,5.2,2.5],'pvArrays':pv,'oldHeightKnots':old_knots,'newHeightKnots':new_knots,
       'sources':['4556-FBR-LR-ZZ-DR-A-110 P01 existing roof plan, 17 April 2025','4556-FBR-LR-ZZ-DR-A-111 P01 southwest elevation, 17 April 2025','4556-FBR-LR-ZZ-DR-A-115 P01 existing roof sections','4556-FBR-LR-ZZ-DR-A-310 P02 approved roof proposal, 8 May 2025'],
       'limits':plan['limits']+['Other plant room, remaining AHUs, full PV extent and historic mansard details require review','Facade bay subdivision and historical corner storey count still approximate','Interior floor levels and full floor plans remain unresolved']}
(OUT/'library-roof-survey-audit.json').write_text(json.dumps(audit,indent=2)+'\n')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v109.blend'))
print('LIBRARY_ROOF_SURVEY_SAVED',len(facade_copies),len(added),len(pv),flush=True)
