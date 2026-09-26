"""Archive-supported room cutaways for seven buildings; no whole-building claim.
Run in Blender's Text Editor. All geometry stays in independent local scenes.
"""
from pathlib import Path
import array, hashlib, json, math, sys
import bpy
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).resolve().parent))
from facade_geometry import Geometry, materials
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'result/blender/stage20/interiors-a';OUT.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v19.blend'))
originals=list(bpy.data.objects)
def fingerprint(objects):
 h=hashlib.sha256()
 for o in sorted(objects,key=lambda o:o.name):
  h.update(o.name.encode());h.update(array.array('f',[v for row in o.matrix_world for v in row]).tobytes())
  if o.type=='MESH':
   a=array.array('f',[0])*(len(o.data.vertices)*3);o.data.vertices.foreach_get('co',a);h.update(a.tobytes())
 return h.hexdigest()
before=fingerprint(originals)
PALETTE={'plaster':(.79,.78,.72),'wood':(.32,.14,.047),'oak':(.48,.29,.13),'white':(.78,.79,.73),'blue':(.025,.13,.23),'black':(.018,.024,.024),'steel':(.28,.32,.33),'silver':(.53,.56,.56),'carpet':(.21,.23,.22),'carpet_light':(.34,.39,.40),'carpet_dark':(.11,.17,.19),'glass':(.28,.46,.52),'light':(.95,.90,.70),'grey':(.35,.39,.4),'red':(.45,.04,.035),'green':(.20,.37,.12),'yellow':(.65,.45,.04),'brick':(.36,.16,.065),'mint':(.35,.63,.55),'mortar':(.23,.21,.18),'blue_seat':(.27,.44,.47)}
materials.clear()
for name,color in PALETTE.items():
 mat=bpy.data.materials.new('V20_INTA_'+name);mat.use_nodes=True;mat.diffuse_color=(*color,1)
 shader=mat.node_tree.nodes['Principled BSDF'];shader.inputs['Base Color'].default_value=mat.diffuse_color
 shader.inputs['Roughness'].default_value=.38 if name in {'wood','oak','steel','glass'} else .72
 shader.inputs['Metallic'].default_value=.65 if name=='steel' else 0
 if name=='light':shader.inputs['Emission Color'].default_value=(*color,1);shader.inputs['Emission Strength'].default_value=.8
 materials[name]=mat
records=[]
class Room:
 def __init__(self,code,label,photo,plan,camera,target):
  self.code=code;self.groups={};self.seats=0
  placeholder=bpy.data.collections.get(code+'_PUBLIC_INTERIOR_study')
  if placeholder:
   assert not placeholder.all_objects, 'Existing interior must not be replaced'
   bpy.data.collections.remove(placeholder)
  self.col=bpy.data.collections.new(code+'_PUBLIC_INTERIOR_study')
  self.col['roomSample']=True;self.col['roomLabel']=label
  self.scene=bpy.data.scenes.new('V20_INTA_'+code);self.scene.collection.children.link(self.col)
  bpy.context.window.scene=self.scene
  self.record={'code':code,'label':label,'photo':photo,'plan':plan,'dimensions':'Estimated from archived images and undimensioned room plan','scope':'One historical room sample, not a whole building or its current layout','camera':camera,'target':target}
 def group(self,family,material):
  key=family+'_'+material
  if key not in self.groups:
   g=Geometry(self.code,'V20_INTA_'+key,material);g.collection=self.col;g.name=self.code+'_V20_INTA_'+key;self.groups[key]=g
  return self.groups[key]
 def box(self,family,mat,p,s,angle=0):self.group(family,mat).box(p,s,angle)
 def prism(self,family,mat,polygon,z,depth):
  n=len(polygon);v=[(x,y,h) for h in [z,z+depth] for x,y in polygon]
  f=[tuple(reversed(range(n))),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
  self.group(family,mat).add(v,f)
 def tube(self,family,mat,a,b,r=.023):
  a,b=Vector(a),Vector(b);d=(b-a).normalized();u=d.cross(Vector((0,0,1)))
  if u.length<.1:u=d.cross(Vector((0,1,0)))
  u.normalize();v=d.cross(u);count=10
  vertices=[p+r*(math.cos(i*2*math.pi/count)*u+math.sin(i*2*math.pi/count)*v) for p in [a,b] for i in range(count)]
  faces=[tuple(reversed(range(count))),tuple(range(count,2*count))]+[(i,(i+1)%count,(i+1)%count+count,i+count) for i in range(count)]
  self.group(family,mat).add(vertices,faces)
 def chair(self,x,y,z=0,angle=0,mat='blue',arms=False):
  self.seats+=1;c,s=math.cos(angle),math.sin(angle)
  def p(dx,dy,dz):return(x+c*dx-s*dy,y+s*dx+c*dy,z+dz)
  self.box('chair_seat',mat,p(0,0,.46),(.46,.45,.065),angle)
  self.box('chair_back',mat,p(0,.21,.73),(.46,.065,.49),angle)
  for side in [-1,1]:
   for front in [-1,1]:self.tube('chair_legs','steel',p(side*.19,front*.16,.03),p(side*.19,front*.18,.45),.016)
   if arms:
    self.box('armrests','black',p(side*.28,0,.67),(.055,.43,.035),angle)
    self.tube('arm_support','steel',p(side*.26,.1,.47),p(side*.26,.1,.67),.014)
 def desk(self,x,y,z,width,depth=.42,angle=0):
  self.box('desk_top','oak',(x,y,z+.76),(width,depth,.065),angle)
  for side in [-1,1]:
   dx=side*(width/2-.18);c,s=math.cos(angle),math.sin(angle)
   self.box('desk_support','black',(x+c*dx,y+s*dx,z+.38),(.06,.30,.73),angle)
   self.box('desk_foot','black',(x+c*dx,y+s*dx,z+.035),(.44,.42,.045),angle)
 def window(self,x,y,z,width,height):
  self.box('window_glass','glass',(x,y,z),(width,.035,height))
  for side in [-1,1]:
   self.box('window_stile','white',(x+side*width/2,y-.04,z),(.065,.11,height+.12))
   self.box('window_rail','white',(x,y-.04,z+side*height/2),(width-.065,.11,.065))
  for t in [-.25,0,.25]:self.box('window_mullion','white',(x+width*t,y-.05,z),(.035,.12,height-.065))
  self.box('window_sill','white',(x,y-.09,z-height/2-.04),(width+.18,.28,.07))
  self.box('roller_blind','plaster',(x,y-.1,z+height/2-.15),(width,.065,.28))
 def panel_wall(self,width,y,height=3):
  self.box('wood_wall','wood',(0,y,height/2),(width,.16,height))
  count=round(width/.85)
  for i in range(count+1):self.box('panel_stile','oak',(-width/2+width*i/count,y-.11,height/2),(.042,.065,height))
  for z in [.12,.82,height-.12]:self.box('panel_rail','oak',(0,y-.11,z),(width,.075,.065))
 def equipment(self,x,y):
  self.box('lectern','plaster',(x,y,.54),(1.05,.62,1.08))
  self.box('lectern_top','oak',(x,y,1.10),(1.16,.72,.055))
  self.box('monitor','black',(x,y+.08,1.39),(.54,.05,.34))
  self.box('monitor_stand','steel',(x,y+.08,1.20),(.10,.1,.18))
  self.box('keyboard','black',(x,y-.14,1.14),(.40,.13,.025))
 def finish(self):
  for g in self.groups.values():
   o=g.finish()
   o['scope']='Historical room sample; estimated dimensions, not a surveyed current interior'
   for mod in list(o.modifiers):
    if 'carpet_triangles' in o.name:
     o.modifiers.remove(mod)
    elif mod.type=='BEVEL':mod.width=.009;mod.segments=2
  cam=bpy.data.objects.new('V20_INTA_'+self.code+'_camera',bpy.data.cameras.new('V20_INTA_'+self.code+'_camera'));self.scene.collection.objects.link(cam)
  cam.location=self.record['camera'];cam.rotation_euler=(Vector(self.record['target'])-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.lens=36;self.scene.camera=cam
  self.record.update({'seats':self.seats,'components':sum(g.parts for g in self.groups.values()),'meshFamilies':len(self.groups)})
  self.record['addedObjects']=[{'name':g.name,'collection':self.col.name} for g in self.groups.values()]
  self.record['cameraName']=cam.name
  records.append(self.record)

# Shared fittings are dimensioned visual studies; furniture counts are stated
# only where the official room plan supplies them.
def shell(r,width,depth,mat='carpet',height=3.1,wallmat='plaster'):
 r.box('floor',mat,(0,0,-.09),(width,depth,.18))
 r.box('back_wall',wallmat,(0,depth/2,height/2),(width,.16,height))
 r.box('left_wall',wallmat,(-width/2,0,height/2),(.16,depth,height))
 r.box('back_skirting','white',(0,depth/2-.12,.11),(width,.045,.22))
 r.box('left_skirting','white',(-width/2+.12,0,.11),(.045,depth,.22))
def side_window(r,y,z,width,height,x):
 # Window helper rotated as a group through local coordinates, preserving
 # left-wall orientation rather than leaving every window facing one direction.
 start={k:len(g.vertices) for k,g in r.groups.items()}
 r.window(y,0,z,width,height)
 for key,g in r.groups.items():
  for i in range(start.get(key,0),len(g.vertices)):
   vx,vy,vz=g.vertices[i];g.vertices[i]=(x-vy,vx,vz)
def screen(r,x,y,z,width=1.3):
 r.box('display_frame','black',(x,y,z),(width,.09,width*.60))
 r.box('display_screen','carpet_dark',(x,y-.052,z),(width-.055,.025,width*.60-.055))
def board(r,x,y,z,width=2.8):
 r.box('board_frame','steel',(x,y,z),(width,.08,1.25))
 r.box('writing_surface','white',(x,y-.055,z),(width-.10,.025,1.15))
 r.box('pen_tray','steel',(x,y-.15,z-.62),(width,.18,.03))
def side_board(r,y,z,width,x):
 start={k:len(g.vertices) for k,g in r.groups.items()};board(r,y,0,z,width)
 for key,g in r.groups.items():
  for i in range(start.get(key,0),len(g.vertices)):
   vx,vy,vz=g.vertices[i];g.vertices[i]=(x-vy,vx,vz)
def ceiling_strip(r,x,y,width=2.8,z=3):
 r.box('suspended_light_body','steel',(x,y,z),(width,.10,.10))
 r.box('suspended_light_diffuser','light',(x,y,z-.061),(width-.06,.075,.025))
 for dx in [-width*.38,width*.38]:r.tube('light_suspension','steel',(x+dx,y,z+.05),(x+dx,y,z+.35),.009)
def table(r,x,y,width,depth,mat='white'):
 r.box('table_top',mat,(x,y,.76),(width,depth,.055))
 for dx in [-width/2+.12,width/2-.12]:
  for dy in [-depth/2+.12,depth/2-.12]:r.tube('table_legs','steel',(x+dx,y+dy,.04),(x+dx,y+dy,.73),.023)
def office_chair(r,x,y,angle=0,mat='black'):
 r.seats+=1;c,s=math.cos(angle),math.sin(angle)
 def p(dx,dy,z):return(x+c*dx-s*dy,y+s*dx+c*dy,z)
 r.box('office_seat',mat,p(0,0,.46),(.47,.45,.075),angle)
 r.box('office_back',mat,p(0,.20,.76),(.46,.075,.49),angle)
 r.tube('chair_height_post','steel',p(0,0,.10),p(0,0,.42),.043)
 for side in [-1,1]:
  r.box('office_armrests','black',p(side*.28,0,.68),(.06,.39,.035),angle)
  r.tube('office_arm_support','black',p(side*.26,.10,.49),p(side*.26,.10,.68),.016)
 for i in range(5):
  a=i*2*math.pi/5;dx,dy=.31*math.cos(a),.31*math.sin(a)
  r.tube('five_spoke_chair_base','black',p(0,0,.14),p(dx,dy,.08),.025)
  r.tube('caster_wheels','black',p(dx-.025*math.sin(a),dy+.025*math.cos(a),.045),p(dx+.025*math.sin(a),dy-.025*math.cos(a),.045),.039)
def desktop(r,x,y,angle=0):
 c,s=math.cos(angle),math.sin(angle)
 def p(dx,dy,z):return(x+c*dx-s*dy,y+s*dx+c*dy,z)
 r.box('computer_monitor','black',p(0,.05,1.14),(.51,.045,.32),angle)
 r.box('computer_screen','carpet_dark',p(0,.024,1.14),(.465,.015,.27),angle)
 r.box('monitor_foot','black',p(0,.08,.80),(.24,.17,.04),angle)
 r.box('monitor_post','black',p(0,.08,.91),(.055,.04,.22),angle)
 r.box('keyboard','black',p(0,-.16,.80),(.42,.14,.025),angle)
 r.box('mouse','black',p(.31,-.16,.80),(.055,.09,.032),angle)
def radiator(r,x,y,width=1.7):
 r.box('radiator_body','white',(x,y,.46),(width,.16,.57))
 for i in range(round(width/.085)):r.box('radiator_fins','plaster',(x-width/2+.055+i*.085,y-.095,.46),(.025,.02,.47))
def hex_table(r,x,y):
 vertices=[(x+1.1*math.cos(i*math.pi/3),y+1.1*math.sin(i*math.pi/3)) for i in range(6)]
 inner=[(x+.32,y),(x+.08,y+.13856),(x-.16,y+.27712),(x-.16,y),(x-.16,y-.27712),(x+.08,y-.13856)]
 for i in range(6):
  j=(i+1)%6;r.prism('hexagonal_group_top','white',[vertices[i],vertices[j],inner[j],inner[i]],.73,.06)
 for i in range(3):
  a=i*2*math.pi/3;r.tube('group_table_legs','steel',(x+.70*math.cos(a),y+.70*math.sin(a),.04),(x+.70*math.cos(a),y+.70*math.sin(a),.73),.025)
 # A triangular central opening and the three wedge seams follow the photo.
 for a in [0,2*math.pi/3,4*math.pi/3]:r.tube('table_segment_seams','grey',(x+.34*math.cos(a),y+.34*math.sin(a),.794),(x+1.08*math.cos(a),y+1.08*math.sin(a),.794),.008)
 for i in range(8):
  a=i*2*math.pi/8;r.chair(x+1.4*math.cos(a),y+1.4*math.sin(a),angle=a-math.pi/2,mat='white')

I='data/collections/interiors/images/'
# KGS: plan explicitly states24places, arranged as three eight-seat islands.
r=Room('KGS','KGS.1.02协作教室',I+'9949479964ed_KGS.1.02.jpg',I+'ce3e85e64f56_KGS.1.02.GIF',(10,-13,11),(0,0,.5))
shell(r,5.8,11.2,wallmat='grey')
for y in [-3.5,0,3.5]:hex_table(r,0,y)
r.window(0,5.47,1.9,3.8,1.9);radiator(r,0,5.25,3.3)
for y in [-2.8,2.8]:side_board(r,y,1.65,3,-2.78)
# Wall display on the retained long side; rotate it to face into the room.
start={k:len(g.vertices) for k,g in r.groups.items()};screen(r,0,0,1.95,1.9)
for key,g in r.groups.items():
 for i in range(start.get(key,0),len(g.vertices)):
  x,y,z=g.vertices[i];g.vertices[i]=(-2.76-y,x,z)
for x in [-2.1,2.1]:
 start={k:len(g.vertices) for k,g in r.groups.items()};ceiling_strip(r,0,0,10.5,2.95)
 for key,g in r.groups.items():
  for i in range(start.get(key,0),len(g.vertices)):
   vx,vy,vz=g.vertices[i];g.vertices[i]=(x-vy,vx,vz)
for y in [-4.5,0,4.5]:r.box('ceiling_crossbeam','plaster',(0,y,3.17),(5.8,.22,.26))
r.finish()

# KSW: five six-seat triangular tables, varied chair colours, teaching equipment.
r=Room('KSW','KSW.1.01小组教室',I+'afcb531c98b9_KSW.1.01.jpg',I+'d6d0161e1a3b_KSW.1.01.GIF',(11,-13,11),(0,0,.55))
shell(r,8,9.6)
for j,(x,y) in enumerate([(-1.9,-2.8),(1.8,-2.8),(0,0),(-1.9,2.8),(1.8,2.8)]):
 polygon=[(x+1.22*math.cos(a),y+1.22*math.sin(a)) for a in [math.pi/2,7*math.pi/6,11*math.pi/6]]
 r.prism('triangular_white_tables','white',polygon,.73,.065)
 for a in [math.pi/2,7*math.pi/6,11*math.pi/6]:r.tube('tripod_table_legs','steel',(x+.62*math.cos(a),y+.62*math.sin(a),.03),(x+.62*math.cos(a),y+.62*math.sin(a),.73),.025)
 for i in range(6):
  a=i*math.pi/3;r.chair(x+1.4*math.cos(a),y+1.4*math.sin(a),angle=a-math.pi/2,mat=['red','green','yellow','black'][((j*3)+i)%4])
r.window(1.8,4.67,1.83,2.6,2.10);radiator(r,1.8,4.44,2.5)
board(r,-1.8,4.67,1.8,2.6);r.equipment(-2.8,3.6)
side_board(r,0,1.7,5.1,-3.88)
for x in [-2.3,0,2.3]:
 for y in [-3,0,3]:r.box('ceiling_light_panels','light',(x,y,3.05),(.60,.60,.035))
r.finish()

# SAL: official plan has a three-sided table, 19student seats plus one teaching chair.
r=Room('SAL','SAL.G.01研讨教室',I+'32195c447bd2_SAL.G.01.jpg',I+'d3cbb566bd01_SAL.G.01.GIF',(12,-10,9),(0,0,.6))
shell(r,10,7,mat='carpet_light')
for x in [-2.5,2.5]:r.window(x,3.37,1.8,2.7,2.4);radiator(r,x,3.13,2.2)
for y in [-1.8,1.8]:
 table(r,.3,y,5.95,.58)
 for i in range(7):r.chair(-2.25+i*.85,y+(.60 if y>0 else -.60),angle=0 if y>0 else math.pi,mat='red')
table(r,3.53,0,.58,4.2)
for i in range(5):r.chair(4.14,-1.65+i*.82,angle=-math.pi/2,mat='red')
table(r,-3.55,0,.70,2);r.chair(-4.18,0,angle=math.pi/2,mat='black');r.equipment(-3.5,2.50)
side_board(r,0,1.75,4.3,-4.88)
for y in [-2.4,0,2.4]:ceiling_strip(r,0,y,5.8,3.1)
r.box('projector_body','white',(-1.9,0,2.90),(.39,.28,.14));r.box('projector_lens','black',(-2.10,0,2.9),(.035,.09,.07))
r.finish()

# STC plan is explicitly unavailable. Reconstruct only the visible computer
# island and teaching wall, with no claimed room boundary or official capacity.
r=Room('STC','STC.S018计算机学习区',I+'526a06ebc830_STC.S018.jpg',None,(9,-10,8),(0,0,.6))
shell(r,7,6.5,mat='carpet_light')
polygon=[(1.55*math.cos(i*math.pi/12),.92*math.sin(i*math.pi/12)) for i in range(24)]
r.prism('oval_computer_island','white',polygon,.73,.06)
r.box('island_service_pedestal','plaster',(0,0,.37),(1.7,.65,.70))
for i,(x,y,a) in enumerate([(-.9,-.35,0),(0,-.4,0),(.9,-.35,0),(-.9,.35,math.pi),(0,.4,math.pi),(.9,.35,math.pi)]):
 desktop(r,x,y,a);office_chair(r,x,y+(-.91 if y<0 else .91),angle=math.pi if y<0 else 0,mat='blue' if i%2 else 'black')
board(r,1.1,3.1,1.8,4.2);screen(r,-2.2,3.1,2.0,1.5)
table(r,1.6,-2.0,2.1,.75);office_chair(r,1.6,-2.65,angle=math.pi,mat='blue')
r.box('door_leaf','plaster',(-2.85,3.11,1.15),(.84,.08,2.3))
for x in [-1.8,1.8]:
 for y in [-1.7,1.7]:r.box('ceiling_light_panels','light',(x,y,3.0),(.65,.65,.035))
r.box('projector_body','white',(0,.4,2.84),(.43,.31,.15));r.box('projector_mount','steel',(0,.4,3.0),(.08,.08,.23))
r.finish()

# COW:2019project photos show an ornate meeting/seminar room. No room number
# or surveyed plan is available; chairs are representative of the visible rows.
COW='data/建筑图片/COW_Cowdray House/01_建筑实拍/campus_photos_round2_COW_cow_russell_02.jpg'
r=Room('COW','Cowdray研讨厅局部',COW,None,(13,-13,10),(0,0,1))
shell(r,9,10,mat='carpet_light',height=3.65)
# Individual floor strips and dado/cornice layers are geometry rather than a photo texture.
for i in range(30):r.box('carpet_linear_texture','carpet',(-4.35+i*.30,0,.009),(.008,10,.004))
side_window(r,0,2,1.8,2.8,-4.37)
for x in [-2.75,2.75]:r.window(x,4.87,2,1.8,2.8)
for y in [-4.7,-1.55,1.6,4.7]:
 r.box('ornamental_pilaster','plaster',(-4.33,y,1.75),(.21,.32,3.50))
 for z,w in [(.18,.46),(2.95,.50),(3.13,.58)]:r.box('pilaster_capital','white',(-4.29,y,z),(.28,w,.16))
for z,d,h in [(3.35,.12,.09),(3.46,.18,.08),(3.56,.25,.11)]:
 r.box('cornice_left','white',(-4.36,0,z),(d,10,h));r.box('cornice_back','white',(0,4.86,z),(9,d,h))
for i in range(36):r.box('cornice_dentils','white',(-4.31,-4.8+i*.27,3.28),(.19,.10,.14))
# Shelf bays flank the retained tall windows, matching the photo's white joinery.
for y in [-3.25,3.25]:
 for z in [.35,.9,1.45,2,2.55,3.1]:r.box('library_shelves','white',(-4.19,y,z),(.35,1.6,.045))
for side in [-1,1]:r.box('arched_niche_jamb','white',(side*.65,4.72,1.48),(.075,.11,1.54))
for i in range(32):
 a,b=i*math.pi/32,(i+1)*math.pi/32
 r.tube('arched_niche_head','white',(.65*math.cos(a),4.72,2.25+.65*math.sin(a)),(.65*math.cos(b),4.72,2.25+.65*math.sin(b)),.044)
for row in range(5):
 for seat in range(7):
  x=-2.6+seat*.86;y=-1.5+row*.98;r.chair(x,y,mat='blue_seat',arms=True)
  # The open dark mesh back is represented by a thin dark inner panel.
  r.box('chair_mesh_back','black',(x,y+.245,.74),(.39,.018,.37))
table(r,1.8,-3.75,2.8,.90,mat='oak')
for cy in [-1.9,2.1]:
 for i in range(72):
  a,b=i*2*math.pi/72,(i+1)*2*math.pi/72
  r.tube('ring_pendant','light',(.72*math.cos(a),cy+.72*math.sin(a),3.28),(.72*math.cos(b),cy+.72*math.sin(b),3.28),.047)
 for x,y in [(-.5,cy-.4),(.5,cy-.4),(0,cy+.6)]:r.tube('ring_pendant_wire','steel',(x,y,3.28),(x,y,3.7),.007)
r.finish()

# COL: the official catering image identifies the Garrick dining space. Model
# the visible dining bay, exposed service ceiling and short rear stair only.
COL='data/建筑图片/COL_Columbia House/01_建筑实拍/campus_photos_round2_COL_food_outlets_11.png'
r=Room('COL','Garrick咖啡厅用餐区',COL,None,(11,-14,11),(0,0,.8))
shell(r,7.6,11,mat='wood',height=3.8,wallmat='brick')
for row in range(45):
 z=.05+row*.08
 for col in range(26):
  y=-5.4+col*.42+(.21 if row%2 else 0)
  if y<5.5:r.box('brick_mortar_vertical','mortar',(-3.71,y,z),(.012,.010,.072))
 r.box('brick_mortar_horizontal','mortar',(-3.71,0,z),( .012,11,.009))
for y in [-3.6,-.3,3]:
 r.box('mint_wall_panel','mint',(-3.60,y,2.17),(.15,.78,2.72))
 r.box('wall_uplight','steel',(-3.38,y,2.0),(.25,.40,.19))
for y in [-3,-.4,2.2]:
 for x in [-1.8,1.55]:
  table(r,x,y,2.1,.90,mat='oak')
  for dx in [-.55,.55]:
   for side in [-1,1]:r.chair(x+dx,y+side*.77,angle=0 if side>0 else math.pi,mat='oak')
# Back stair behind the dining bay, cropped to the visible public fragment.
for i in range(9):r.box('rear_stair_treads','grey',(1.5,3.35+i*.22,(i+1)*.15/2),(1.45,.23,(i+1)*.15))
for side in [-1,1]:
 x=1.5+side*.79
 r.tube('rear_stair_handrail','steel',(x,3.3,1.05),(x,5.32,2.4),.024)
 for i in range(5):r.tube('rear_stair_balusters','steel',(x,3.4+i*.43,.15+i*.29),(x,3.4+i*.43,1.12+i*.29),.016)
r.box('service_counter','oak',(-3.27,-4.1,.55),(.76,2.5,1.10));r.box('countertop','black',(-3.27,-4.1,1.12),(.82,2.6,.065))
for y in [-3.7,0,3.7]:r.box('exposed_crossbeam','grey',(0,y,3.6),(7.6,.15,.26))
for x in [-2.4,2.4]:
 r.tube('exposed_service_duct','steel',(x,-5.2,3.42),(x,5.2,3.42),.13)
 for y in [-3.5,-1.2,1.2,3.5]:r.tube('track_spotlight','black',(x,y,3.25),(x+.15,y,3.0),.06)
for y in [-2,2]:ceiling_strip(r,0,y,3.1,3.25)
r.finish()

# LAK:2012project sheet gives40m2total reception area, but not a measured plan.
# This model is only the photographed short stair/entrance, not an invented lift layout.
LAK='data/collections/interiors/originals/2012-Lakatos-Entrance.pdf'
r=Room('LAK','Lakatos2012入口楼梯',LAK,None,(8,-9,7),(0,.6,.7))
shell(r,4.8,6.6,mat='carpet_dark',height=3.4)
for i in range(6):
 h=(i+1)*.17;r.box('entry_stair_treads','carpet_dark',(0,.35+i*.33,h/2),(3.15,.335,h))
 r.box('stair_nosing','silver',(0,.20+i*.33,h+.01),(3.15,.045,.025))
r.box('entry_landing','carpet_dark',(0,2.60,.51),(3.15,.85,1.02))
r.box('entrance_door_glass','glass',(0,3.16,2.06),(2.6,.045,2.04))
for x in [-1.34,0,1.34]:r.box('entrance_door_stiles','white',(x,3.10,2.06),(.065,.13,2.16))
for z in [1.02,2.95,3.14]:r.box('entrance_door_transom','white',(0,3.1,z),(2.7,.13,.065))
for side in [-1,1]:
 x=side*.14
 for i in range(24):
  a,b=i*2*math.pi/24,(i+1)*2*math.pi/24;r.tube('door_ring_pull','steel',(x+.1*math.cos(a),3.0,1.88+.1*math.sin(a)),(x+.1*math.cos(b),3.0,1.88+.1*math.sin(b)),.012)
# Central balustrade and a left handrail correspond to the source photograph.
for y,z in [(.1,.10),(1.13,.58),(2.18,1.02)]:r.tube('stair_balustrade_post','steel',(-.56,y,z),(-.56,y,z+1),.025)
r.tube('stair_balustrade_top','steel',(-.56,.05,1.08),(-.56,2.63,2.04),.03)
r.group('balustrade_glass_panel','glass').add([(x,y,z) for x in [-.57,-.55] for y,z in [(.18,.28),(2.30,1.12),(2.30,1.85),(.18,1.01)]],[(0,1,2,3),(4,7,6,5),(0,4,5,1),(1,5,6,2),(2,6,7,3),(3,7,4,0)])
for y,z in [(.05,1.06),(2.55,2.03)]:r.tube('wall_rail_bracket','black',(-2.28,y,z),(-2.1,y,z),.014)
r.tube('wall_handrail','black',(-2.10,.05,1.06),(-2.10,2.55,2.03),.027)
r.box('red_identity_panel','red',(-2.28,2.5,2.15),(.08,.43,2.50))
r.box('white_wall_feature_panel','white',(-2.28,-.65,1.65),(.08,2.6,2.35))
for y in [-1,1.4]:r.box('entry_downlight','light',(0,y,3.25),(.35,.35,.035))
r.finish()

# Review existing public interiors without overwriting layouts or prior meshes.
limits={
 'KGS':'官方历史平面标24席；几何尺寸、净高估算，非现状测绘。',
 'KSW':'历史平面为5组桌；每组6席按图建立，尺寸、颜色具体分布为照片近似。',
 'SAL':'保留历史U形桌布置；尺寸和设备位置估算，非当前排课场景。',
 'STC':'无可用平面，只有照片中的计算机岛和教学墙；围合边界、席位与尺寸均为示意。',
 'COW':'2019项目照片，无房间号或平面；仅研讨厅可见构件，座椅数量不代表核定容量。',
 'COL':'餐饮照片拍摄日期未知；仅可见用餐区，布局深度和后部楼梯关系为照片比例估计。',
 'LAK':'依据2012入口改造照片；只重建楼梯入口片段，不外推整栋40平方米接待区或电梯位置。',
}
changes={
 'KGS':['3组八人六边形桌、长条灯、白板、墙面显示屏和后窗。'],
 'KSW':['5组六人三角桌、彩色座椅、白板、讲台和后窗。'],
 'SAL':['U形连续桌、19个学员座位与教师位、窗户、散热器和教学设备。'],
 'STC':['椭圆计算机岛、显示器键盘、教学墙与投影设备。'],
 'COW':['成排座椅、白色书架、窗户、装饰柱头、檐口与环形吊灯。'],
 'COL':['木桌椅、砖墙、薄荷绿墙板、裸露风管、灯轨及后部楼梯片段。'],
 'LAK':['入口短梯、防滑鼻口、不锈钢栏杆、墙扶手、红色识别板和双扇玻璃门。'],
}
manifest={'baseline':'result/blender/LSE_campus_detailed_v19.blend','buildings':[]}
for record in records:
 code=record['code'];scope='历史资料支持的局部室内样本，非整栋完整内部。'+limits[code]
 manifest['buildings'].append({'code':code,'status':'room-sample-built','changes':changes[code],
  'sources':[s for s in [record['photo'],record['plan']] if s]+(['data/collections/interiors/originals/2019-Cowdray-House.pdf'] if code=='COW' else []), 'limitations':[limits[code],'保留档案年代边界，不代表2026现状。'],
  'addedObjects':record['addedObjects'],'roomStudy':{'label':record['label'],'camera':record['camera'],'target':record['target'],'cameraName':record['cameraName'],'scope':scope},
  'sourceSupport':'photo-and-matched-plan' if record['plan'] else 'photo-only-visible-fragment','modeledSeats':record['seats'],'components':record['components']})
manifest['buildings'].append({'code':'LCH','status':'insufficient-interior-evidence','changes':[],'sources':['data/建筑图片/LCH_Lincoln Chambers/图片索引.json'],'limitations':['可用索引只有外观照片，无可确认内部房间或平面；未凭空添加室内。'],'addedObjects':[]})
for code,note in [('CBG','已有结构梁柱、学术楼梯、灯具和座椅；全部办公室教室仍未知。'),('CKK','已有木阶、钢梁、玻璃栏板、回廊；本轮未发现足够资料支持的新增空间。'),('LRB','已有坡道、栏杆、书架、双升降机及屋顶；仍不是逐层完整藏书与房间复原。'),('MAR','已有大厅树形柱、公共楼梯、门禁、桌椅与灯具；体育馆和全部教室未建立。'),('SAW','v19已补楼梯黑色扶手；其余楼层只有楼板，不能称完整室内。')]:
 manifest['buildings'].append({'code':code,'status':'existing-public-space-reviewed','changes':[],'sources':['result/blender/stage19/modern/manifest.json'],'limitations':[note],'addedObjects':[]})
bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE'];bpy.context.view_layer.update()
assert fingerprint(originals)==before,'Existing objects changed'
manifest['originalGeometryUnchanged']=True;manifest['originalGeometrySha256']=before
(OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'refined.blend'))
print('INTERIORS_A_SAVED',[(r['code'],r['components']) for r in records],flush=True)
# Render the actual cutaway scenes with roof omitted intentionally for inspection.
for record in records:
 code=record['code'];scene=bpy.data.scenes['V20_INTA_'+code]
 scene.render.engine='CYCLES';scene.cycles.samples=12;scene.cycles.use_denoising=True
 scene.render.resolution_x=1100;scene.render.resolution_y=900;scene.render.resolution_percentage=100
 scene.world=bpy.data.worlds.new('V20_INTA_WORLD_'+code);scene.world.use_nodes=True
 scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.65,.69,.72,1)
 scene.world.node_tree.nodes['Background'].inputs[1].default_value=.8
 for j,(pos,power,size) in enumerate([((2,-3,9),1700,7),((-4,1,7),1100,5)]):
  d=bpy.data.lights.new('V20_INTA_QA_'+code+str(j),'AREA');d.energy=power;d.size=size
  o=bpy.data.objects.new(d.name,d);scene.collection.objects.link(o);o.location=pos
  o.rotation_euler=(Vector((0,0,.5))-o.location).to_track_quat('-Z','Y').to_euler()
 scene.render.filepath=str(OUT/(code.lower()+'-interior.png'))
 bpy.ops.render.render(write_still=True,scene=scene.name)
 print('INTERIORS_A_RENDERED',code,flush=True)
print('INTERIORS_A_COMPLETE',flush=True)
