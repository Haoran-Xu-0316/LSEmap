"""Build eight verified archive-based room samples as an isolated edition-20 batch.
Run in Blender's Text Editor. Room dimensions and floor levels are estimates;
these independent cutaways are not a surveyed whole-building interior.
"""
from pathlib import Path
import hashlib, json, math, sys, array
import bpy
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).resolve().parent))
from facade_geometry import Geometry, materials
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'result/blender/stage20/interiors-b';OUT.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v19.blend'))
def geometry_digest(objects):
 digest=hashlib.sha256()
 for obj in sorted(objects,key=lambda o:o.name):
  if obj.type!='MESH':continue
  digest.update(obj.name.encode());digest.update(array.array('f',[v for row in obj.matrix_world for v in row]).tobytes())
  values=array.array('f',[0])*(len(obj.data.vertices)*3);obj.data.vertices.foreach_get('co',values);digest.update(values.tobytes())
  digest.update('|'.join(m.name if m else '' for m in obj.data.materials).encode())
 return digest.hexdigest()
original_objects=list(bpy.data.objects)
original_geometry_sha256=geometry_digest(original_objects)
PALETTE={'plaster':(.79,.78,.72),'wood':(.32,.14,.047),'oak':(.48,.29,.13),
 'white':(.78,.79,.73),'blue':(.025,.13,.23),'black':(.018,.024,.024),
 'red':(.48,.035,.035),'yellow':(.62,.43,.13),'brick':(.29,.11,.06),'burgundy':(.18,.026,.035),'purple':(.21,.19,.25),'cream':(.71,.62,.41),'steel':(.28,.32,.33),'carpet':(.21,.23,.22),'carpet_light':(.34,.39,.40),
 'carpet_dark':(.11,.17,.19),'glass':(.28,.46,.52),'light':(.95,.90,.70)}
for name,color in PALETTE.items():
 mat=bpy.data.materials.new('V20_INTB_'+name);mat.use_nodes=True;mat.diffuse_color=(*color,1)
 shader=mat.node_tree.nodes['Principled BSDF'];shader.inputs['Base Color'].default_value=mat.diffuse_color
 shader.inputs['Roughness'].default_value=.38 if name in {'wood','oak','steel','glass'} else .72
 shader.inputs['Metallic'].default_value=.65 if name=='steel' else 0
 if name=='light':shader.inputs['Emission Color'].default_value=(*color,1);shader.inputs['Emission Strength'].default_value=.8
 materials[name]=mat
records=[]
rooms=[]
original_names=set(bpy.data.objects.keys())
original_campus_names=set(bpy.data.scenes['00_CAMPUS_COMPLETE'].objects.keys())
class Room:
 def __init__(self,code,label,photo,plan,camera,target):
  self.code=code;self.groups={};self.seats=0
  placeholder=bpy.data.collections.get(code+'_PUBLIC_INTERIOR_study')
  if placeholder:
   assert not placeholder.all_objects, 'Existing interior must not be replaced'
   bpy.data.collections.remove(placeholder)
  self.col=bpy.data.collections.new(code+'_PUBLIC_INTERIOR_study')
  self.col['roomSample']=True;self.col['roomLabel']=label
  self.scene=bpy.data.scenes.new('V20_INTB_'+code);self.scene.collection.children.link(self.col)
  bpy.context.window.scene=self.scene
  rooms.append(self)
  self.record={'code':code,'label':label,'photo':photo,'plan':plan,'dimensions':'Estimated from archived images and undimensioned room plan','scope':'One historical room sample, not a whole building or its current layout','camera':camera,'target':target}
 def group(self,family,material):
  key=family+'_'+material
  if key not in self.groups:
   g=Geometry(self.code,'V20_INTB_'+key,material);g.collection=self.col;g.name=self.code+'_V20_INTB_'+key;self.groups[key]=g
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
  cam=bpy.data.objects.new('V20_INTB_'+self.code+'_camera',bpy.data.cameras.new('V20_INTB_'+self.code+'_camera'));self.scene.collection.objects.link(cam)
  cam.location=self.record['camera'];cam.rotation_euler=(Vector(self.record['target'])-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.lens=36;self.scene.camera=cam
  self.record.update({'seats':self.seats,'components':sum(g.parts for g in self.groups.values()),'meshFamilies':len(self.groups)})
  self.record['addedObjects']=[{'name':g.name,'collection':self.col.name} for g in self.groups.values()]
  self.record['roomStudy']={k:self.record[k] for k in ['label','camera','target','scope']}
  self.record['status']='added'
  records.append(self.record)

# Coordinates are local to each cutaway, not inferred positions in the campus.
def shell(r,width,depth,height=3.1,floor='carpet',wall='plaster'):
 r.box('floor',floor,(0,0,-.10),(width,depth,.20))
 r.box('back_wall',wall,(0,depth/2,height/2),(width,.16,height))
 r.box('left_wall',wall,(-width/2,depth*.15,height/2),(.16,depth*.70,height))
 r.box('skirting','white',(0,depth/2-.11,.06),(width,.04,.12))
def roundtop(r,family,mat,x,y,z,radius,thickness=.06):
 r.prism(family,mat,[(x+radius*math.cos(i*math.tau/32),y+radius*math.sin(i*math.tau/32)) for i in range(32)],z,thickness)
def table_group(r,x,y,radius=.9,seats=6,seatmat='white'):
 # Rounded triangular teamwork table: three curved corners, following the plan.
 points=[]
 for i in range(3):
  a=math.pi/2+i*math.tau/3;cx=x+radius*.68*math.cos(a);cy=y+radius*.68*math.sin(a)
  for j in range(9):
   b=a-math.pi/3+j*math.pi/12;points.append((cx+radius*.45*math.cos(b),cy+radius*.45*math.sin(b)))
 r.prism('group_table','white',points,.74,.065)
 for a in [math.pi/2,7*math.pi/6,11*math.pi/6]:r.tube('table_legs','steel',(x+.42*math.cos(a),y+.42*math.sin(a),.03),(x+.42*math.cos(a),y+.42*math.sin(a),.74),.028)
 for i in range(seats):
  a=i*math.tau/seats;r.chair(x+1.12*radius*math.cos(a),y+1.12*radius*math.sin(a),angle=a-math.pi/2,mat=seatmat)
def dining_chair(r,x,y,angle):
 c,s=math.cos(angle),math.sin(angle)
 def p(dx,dy,z):return(x+c*dx-s*dy,y+s*dx+c*dy,z)
 r.seats+=1
 r.box('dining_seat','burgundy',p(0,0,.48),(.48,.46,.095),angle)
 for dx in [-.19,.19]:
  for dy in [-.16,.16]:r.tube('dining_chair_leg','wood',p(dx*1.12,dy*1.12,.025),p(dx,dy,.46),.025)
 outline=[(-.25,.52),(.25,.52),(.28,1.20),(.23,1.32),(.15,1.27),(0,1.24),(-.15,1.27),(-.23,1.32),(-.28,1.20)]
 vertices=[p(dx,depth,z) for depth in [.17,.26] for dx,z in outline];n=len(outline)
 faces=[tuple(reversed(range(n))),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
 r.group('high_upholstered_back','burgundy').add(vertices,faces)
def theatre_seat(r,x,y,z):
 r.seats+=1
 r.box('theatre_seat','burgundy',(x,y,z+.48),(.49,.48,.13))
 r.box('theatre_back','burgundy',(x,y+.21,z+.77),(.50,.12,.61))
 for dx in [-.27,.27]:
  r.box('seat_arm','black',(x+dx,y,z+.68),(.045,.48,.06))
  r.box('seat_pedestal','black',(x+dx*.75,y+.05,z+.25),(.04,.12,.49))

def teaching(r,x,y,blue=False):
 r.box('teaching_board','white',(x,y,1.6),(3.2,.05,1.4))
 r.equipment(x+2,y-.65)
 if blue:r.box('blue_accent','blue',(x+2,y+.03,1.55),(2.05,.08,3.1))
 r.box('teaching_display','black',(x-2.2,y-.03,1.9),(1.3,.10,.75))
def roof_lights(r,width,depth,height=3):
 # Only sparse lighting tracks are retained so the browser cutaway stays open.
 for x in [-width*.27,width*.27]:
  r.box('light_track','white',(x,depth*.33,height),(.065,depth*.55,.065))
  for y in [depth*.1,depth*.35]:r.box('light_panel','light',(x,y,height-.08),(.55,.55,.045))

r=Room('FAW','FAW.1.01小组教室','6055aee50b04_FAW.1.01.jpg','7d41fb5c4b15_FAW.1.01.GIF',(10,-10,9),(0,0,.7))
shell(r,9,6)
# Fawcett's clipped corner and four six-place tables are verified in the plan.
for ix in range(10):
 for iy in range(7):
  if (ix+iy)%2:r.box('carpet_tiles','carpet_light',(-4.05+ix*.81,-2.7+iy*.8,.008),(.8,.79,.012))
for x,y in [(-2.5,-1),(0,1),(2.5,1),(1,-1.4)]:table_group(r,x,y,.93,6,'black')
teaching(r,-1,2.89,True)
r.box('door','wood',(3.8,2.85,1.05),(.8,.08,2.1));roof_lights(r,9,6);r.finish()
r.record['changes']=['Four rounded triangular group tables with 24 chairs','Blue teaching accent, AV lectern, display and patterned carpet']
r.record['limitations']=['Archived plan states capacity 24. Perimeter size and ceiling height estimated. Clipped corner represented as an open cutaway.']

r=Room('PAN','PAN.1.01小组教室','ae44059862f6_PAN.1.01.jpg','4efb3d848fec_PAN.1.01.GIF',(10,-10,9),(0,0,.7))
shell(r,9,7)
for ix in range(11):
 for iy in range(8):
  if (ix*3+iy)%3==0:r.box('carpet_tiles','carpet_light',(-4.1+ix*.8,-3.1+iy*.8,.008),(.78,.78,.012))
for x,y in [(-2.4,1.2),(.9,1.2),(-2.5,-1.5),(.2,-1.5),(2.9,-1.5)]:table_group(r,x,y,.85,6,'white')
for x in [-2.8,-.9,1,2.9]:r.window(x,3.38,2.53,1.55,.77)
teaching(r,-1,3.23)
# Portable boards have visible feet, matching the furniture on the room plan.
for x in [-3.7,3.7]:
 r.box('portable_board','white',(x,.8,1.6),(.045,1.5,1.15));r.box('board_foot','steel',(x,.8,.08),(.65,1.15,.07))
 for y in [.3,1.3]:r.tube('board_support','steel',(x,y,.10),(x,y,1.10),.022)
roof_lights(r,9,7);r.finish();r.record['changes']=['Five six-seat teaching islands','High windows, portable boards and lecture equipment'];r.record['limitations']=['Room identity and five table locations checked against plan. Dimensions and exact chair spacing estimated.']

r=Room('PAR','PAR.1.02小组教室','7388b9be0058_PAR.1.02.jpg','8065f2ad7b43_PAR.1.02.GIF',(15,-13,12),(0,0,.7))
shell(r,14,8,3.65)
for x in [-5.4,-2.7,0,2.7,5.4]:
 for y in [-1.8,1.25]:table_group(r,x,y,.84,6,'white')
for x in [-5.2,-1.7,1.7,5.2]:r.window(x,3.86,2.1,2.4,2.5)
# Retained perimeter beam portions and linear lights communicate the hall height.
for x in [-5,0,5]:
 r.box('ceiling_beam','plaster',(x,3.35,3.5),(.32,1.3,.35));r.box('beam_light','light',(x,3.25,3.28),(.13,1.0,.05))
r.equipment(0,3.08);r.box('projection_screen','white',(-3.0,3.70,2.30),(2.1,.06,1.25))
r.finish();r.record['changes']=['Ten group tables and 60 chairs matching the plan capacity','Tall windows, retained beams, projection screen and teaching station'];r.record['limitations']=['Plan explicitly identifies PAR.1.02 and capacity 60. Cutaway omits roof and two walls; dimensions estimated.']

# PEL roof studio: documented 45 sq m project, with a filmed interview corner.
# The separate control room is deliberately not welded into this unknown plan.
r=Room('PEL','Tower3屋顶媒体演播室访谈区','2014-LSE-Media-Studio.pdf',None,(8,-8,6),(0,0,1))
shell(r,6.8,5.3,3.2,'black','yellow')
r.box('brick_pier','brick',(-.5,2.54,1.6),(1.0,.17,3.2))
for row in range(34):
 for col in range(4):r.box('brick_face','oak',(-.85+col*.22+(row%2)*.05,2.43,.08+row*.09),(.205,.018,.075))
for x,angle in [(-1,math.pi/2),(1,-math.pi/2)]:r.chair(x,.5,angle=angle,mat='black',arms=True)
for x,y in [(-2.5,-1.3),(2.4,-1.4)]:
 r.tube('camera_column','black',(x,y,.2),(x,y,1.4),.045)
 for a in [0,math.tau/3,2*math.tau/3]:r.tube('tripod','black',(x+.52*math.cos(a),y+.52*math.sin(a),.04),(x,y,1.05),.029)
 r.box('camera_body','black',(x,y,1.50),(.33,.45,.28));r.box('camera_lens','black',(x,y+.28,1.5),(.21,.19,.20));r.box('camera_monitor','steel',(x,y-.14,1.74),(.34,.05,.21))
for y in [.3,2.0]:
 r.tube('lighting_grid','steel',(-3.3,y,3.12),(3.3,y,3.12),.035)
 for x in [-2,0,2]:
  r.box('studio_light','black',(x,y,2.89),(.40,.30,.23));r.box('studio_diffuser','light',(x,y-.16,2.89),(.31,.03,.17))
r.finish();r.record['changes']=['Interview chairs, cameras on tripods, overhead lighting grid and warm studio backdrop','Visible brick pier reconstructed without copying source photographs'];r.record['limitations']=['The 2014 project sheet establishes location and use; only the photographed studio corner is modeled. Studio/control-room partition and equipment positions are approximate.']

# SAR tea point: project sheet's lower-right image, never an invented room number.
r=Room('SAR','2015改造茶水间样本','2015-Sardinia-House-Phase-34.pdf',None,(8,-7,6.4),(0,0,.9))
shell(r,6.6,5.4,3.25)
for x in [-2,1.7]:r.window(x,2.58,2.1,1.65,2.0)
r.box('kitchen_base','white',(-2.5,.65,.45),(1.25,2.6,.9));r.box('countertop','black',(-2.5,.65,.93),(1.34,2.7,.08))
r.box('red_backsplash','red',(-3.20,.65,1.36),(.035,2.7,.70))
for y in [-.4,.3,1.0,1.7]:r.box('tile_grout','plaster',(-3.17,y,1.36),(.02,.018,.7))
for z in [1.12,1.35,1.58]:r.box('tile_grout','plaster',(-3.17,.65,z),(.02,2.7,.018))
r.box('sink','steel',(-2.5,.25,.976),(.70,.50,.023));r.tube('tap','steel',(-2.85,.25,.97),(-2.85,.25,1.25),.019);r.tube('tap_spout','steel',(-2.85,.25,1.25),(-2.64,.25,1.25),.019)
r.box('kettle','red',(-2.5,1.45,1.15),(.25,.23,.35))
r.box('window_counter','white',(.8,2.35,1.10),(3.9,.55,.08))
for i,x in enumerate([-.7,.65,2]):
 r.chair(x,1.68,.27,0,mat='red' if i==0 else 'white')
 for dx in [-.19,.19]:
  for dy in [-.16,.16]:r.tube('stool_leg_extension','steel',(x+dx,1.68+dy,.03),(x+dx,1.68+dy,.31),.016)
for x,y in [(-.25,-1.15),(1.75,-.45)]:
 roundtop(r,'cafe_table','white',x,y,.75,.62);r.tube('table_pedestal','steel',(x,y,.05),(x,y,.75),.055);roundtop(r,'table_base','steel',x,y,.03,.33,.04)
 r.chair(x,y-.86,angle=math.pi,mat='red');r.chair(x+.85,y,angle=-math.pi/2,mat='white')
r.finish();r.record['changes']=['Red tiled kitchen counter, sink and window counter','Round café tables and mixed red/white chairs'];r.record['limitations']=['Photo identified within Sardinia House 2015 refurbishment sheet. Room number, dimensions and unseen perimeter unknown.']

# 5LF official faculty accommodation gallery: bedroom-only spatial sample.
r=Room('5LF','教职工公寓双人卧室样本','5LF_01.jpg / 5LF_02.jpg / 5LF_03.jpg',None,(0,-9,6.5),(0,0,.8))
shell(r,5.7,4.8,2.7,'purple')
r.window(0,2.28,1.6,1.65,1.9)
for x in [-1.2,1.2]:
 for i in range(9):r.box('curtain_folds','cream',(x+(i-4)*.055,2.13,1.50),(.035,.11,2.35))
r.box('bed_base','white',(1.67,.10,.30),(2.10,1.75,.50));r.box('mattress','white',(1.67,.08,.59),(2.08,1.77,.18))
r.box('duvet','plaster',(1.50,.08,.72),(1.64,1.80,.16))
for y in [-.35,.50]:r.box('pillow','white',(2.39,y,.78),(.40,.72,.19))
r.box('folding_bed_panel','white',(2.76,.10,1.25),(.12,1.97,2.5))
# Workstation on the opposite wall, camera view keeps the two zone relationship.
r.box('desk_top','white',(-1.9,.5,.76),(1.38,.66,.06))
for x in [-2.48,-1.32]:r.tube('desk_leg','steel',(x,.5,.02),(x,.5,.74),.027)
r.box('desktop_monitor','white',(-1.9,.65,1.08),(.56,.06,.36));r.box('monitor_screen','glass',(-1.9,.61,1.08),(.49,.016,.28));r.tube('monitor_foot','steel',(-1.9,.65,.79),(-1.9,.65,.94),.022)
r.chair(-1.9,-.2,angle=math.pi,mat='black',arms=True)
r.box('wardrobe','white',(-2.48,1.52,1.12),(.62,1.2,2.24));r.finish();r.record['changes']=['Double bed with bedding, foldaway-bed wall panel, workstation and wardrobe','Sash window and paired curtain folds'];r.record['limitations']=['Official faculty-accommodation gallery confirms bedroom views. Room number and dimensions unavailable; kitchen/bathroom not inferred into a joined floor plan.']

# Coopers' official restaurant photograph supplies a clearly attributed dining area.
r=Room('49L','Coopers餐厅用餐区样本','49L_food_outlets_07.jpg',None,(9,-9,7),(0,0,1))
shell(r,8,7,3.2,'oak','red')
for x in [-2.4,1.25]:r.window(x,3.38,1.87,1.2,2.2)
# The exposed brick upper wall and irregular plaster edge are photo-informed.
r.box('side_wall','cream',(-3.86,.3,1.6),(.18,6.2,3.2))
for row in range(11):
 for col in range(22):
  y=-2.6+col*.27;z=2.1+row*.092
  if z>2.00+.20*math.sin(y*1.5):r.box('brick_reveal','brick',(-3.75,y,z),(.025,.255,.079))
for i in range(20):r.box('floor_plank_joint','wood',(-3.8+i*.40,0,.008),(.012,7,.015))
r.tube('yellow_column','yellow',(-.7,1.25,.0),(-.7,1.25,3.15),.10)
for x in [-2.4,0,2.25]:
 for y in [-1.9,.1,2.1]:
  r.box('dining_table','oak',(x,y,.79),(1.35,.75,.08));r.tube('dining_table_leg','black',(x,y,.06),(x,y,.76),.05)
  for sign in [-1,1]:
   dining_chair(r,x,y+sign*.66,0 if sign==1 else math.pi)
   roundtop(r,'plate','white',x,y+sign*.20,.835,.12,.012)
   r.tube('glass_stem','glass',(x+.25,y+sign*.24,.84),(x+.25,y+sign*.24,.96),.012)
   roundtop(r,'glass_bowl','glass',x+.25,y+sign*.24,.97,.045,.085)
r.finish();r.record['changes']=['Nine timber dining tables, upholstered chairs and place settings','Red window wall, exposed brick strip, yellow support column and wood floor'];r.record['limitations']=['Official LSE catering photograph identifies Coopers. Table spacing and partial perimeter estimated; no full restaurant floorplan claimed.']

# Peacock theatre: verified proscenium dimensions, stage plan and section.
# This is a bounded stage/front-stalls sample, not 999 invented seat positions.
r=Room('PEA','Peacock舞台与前排观众席','baeeae18f5a2_PT.jpg','Stage-Plan-stage-only.pdf / Stage-section.pdf',(23,22,18),(0,-1,2.6))
r.box('auditorium_floor','carpet',(0,4.25,-.15),(16,8.5,.20))
r.box('stage_floor','black',(0,-5.35,.40),(19.5,10.7,.8))
r.box('stage_backwall','black',(0,-10.7,3.75),(19.5,.20,7.5))
for x in [-8.125,8.125]:r.box('proscenium_pier','black',(x,0,3.75),(3.25,.50,7.5))
r.box('proscenium_header','black',(0,0,7.10),(13,.5,.8))
r.box('projection_screen','white',(0,-3,4.5),(9.8,.07,3.2))
for x in [-6.7,6.7]:
 for i in range(13):r.box('stage_curtain_folds','burgundy',(x+(i-6)*.08,-.24,3.75),(.075,.16,5.9))
# Photographed red front valance and shallow orchestra apron.
r.box('stage_valance','burgundy',(0,.50,.40),(13,.06,.8))
r.prism('forestage','black',[(-5.64,0),(5.64,0),(5.64,1),(3.2,1.6),(0,2),(-3.2,1.6),(-5.64,1)],.3,.18)
for row in range(6):
 y=3+row*.90;z=row*.13
 r.box('stalls_riser','carpet',(0,y,z/2-.1),(15.5,.90,z+.20))
 for bank in [-1,0,1]:
  for col in range(6):theatre_seat(r,bank*4.8+(col-2.5)*.56,y,z)
# Cut side-wall ribbing and aisle lights identify the technical-section character.
for side in [-1]:
 r.box('auditorium_side','black',(side*8,4,2.5),(.20,8,5))
 for i in range(30):r.box('acoustic_ribs','steel',(side*7.86,i*.26,.0+3.4),(.05,.06,2.5))
 for y in [2.6,4.4,6.2]:r.box('aisle_light','light',(side*7.6,y,.22),(.18,.10,.035))
r.equipment(-4,-1.4)
r.finish();r.record['changes']=['13m by 5.9m proscenium and 10.7m stage depth from operator specification','Projection screen, side curtains, apron and six sample stalls rows with aisle gaps'];r.record['limitations']=['Only stage/front-stalls cutaway. The 108 modeled seats are a visible sample, not the venue capacity or exact seating chart. Balcony/backstage/dressing rooms and camera-side wall omitted. Operator PDF version signals differ: header November 2022, filename February 2023, index January 2024. Dimensions outside operator specification estimated.']

# Provenance resolves archive filenames to exact local paths and source URLs.
archive=json.loads((ROOT/'data/collections/interiors/sources.json').read_text())['sources']
for record in records:
 tokens=[t.strip() for text in [record.get('photo'),record.get('plan')] if text for t in text.split(' / ')]
 sources=[]
 for token in tokens:
  match=next((s for s in archive if Path(s.get('local_path','')).name==token),None)
  if match:sources.append({'path':match['local_path'],'url':match['url'],'title':match['title']})
  elif token.startswith('5LF_'):
   source=next(s for s in json.loads((ROOT/'data/collections/small_buildings_round3/sources.json').read_text())['sources'] if Path(s.get('local_file','')).name==token)
   sources.append({'path':source['local_file'],'url':source['url'],'title':source['title']})
  elif token=='49L_food_outlets_07.jpg':sources.append({'path':'data/collections/campus_photos_round2/images/49L/49L_food_outlets_07.jpg','url':'https://campuslife-browzer-platform.s3.eu-west-2.amazonaws.com/images/517f52dce7f47c33117be7024078abcd','title':'Official Coopers Restaurant photograph'})
 record['sources']=sources
 if record['code']=='PEA':
  source=next(s for s in archive if Path(s.get('local_path','')).name=='Peacock-Theatre-Technical-Specification-Feb-2023.pdf');record['sources'].append({'path':source['local_path'],'url':source['url'],'title':source['title']})
 record['roomStudy']['scope']='历史室内局部样本；非整栋内部，未确认现时布局。'+('舞台口尺寸来自运营方技术规格，其余估算。' if record['code']=='PEA' else '尺寸和未显示部分均为估算。')
for code,reason in {
 '50L':'No attributed interior photograph or usable room plan in the inspected archives.',
 '51L':'No attributed interior photograph or usable room plan in the inspected archives.',
 '61A':'Building attribution remains provisional; no verified LSE interior.',
 'POR':'2015 retail project sheet covers Lincoln Chambers and Portsmouth Street together; individual interior photos cannot be safely assigned to POR.',
 'SHF':'No attributed interior photograph or usable room plan in the inspected archives.',
 'OCS':'No verified interior layout in the inspected archives.',
 '35L':'Construction-only representation. No completed interior is inferred.'}.items():
 records.append({'code':code,'status':'evidence-gap','changes':[],'sources':[],'limitations':[reason],'addedObjects':[]})
 if code=='POR':
  source=next(s for s in archive if Path(s.get('local_path','')).name=='2015-SU-Shop.pdf');records[-1]['sources']=[{'path':source['local_path'],'url':source['url'],'title':source['title']}]
assert geometry_digest(original_objects)==original_geometry_sha256,'Existing geometry changed'
assert all(all(math.isfinite(v) for p in o.data.vertices for v in p.co) for r in rooms for o in r.col.all_objects if o.type=='MESH'),'Nonfinite new vertices'
assert set(bpy.data.scenes['00_CAMPUS_COMPLETE'].objects.keys())==original_campus_names,'Room sample leaked into campus'
bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE'];bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'refined.blend'))
manifest={'sourceModel':'result/blender/LSE_campus_detailed_v19.blend','buildings':records,'verification':{'campusObjectMembershipUnchanged':True,'originalGeometryUnchanged':True,'originalGeometrySha256':original_geometry_sha256,'newVerticesFinite':True}}
(OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
for r in rooms:
 scene=r.scene;bpy.context.window.scene=scene
 scene.world=bpy.data.worlds.new('V20_INTB_'+r.code+'_world');scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.62,.66,.72,1);scene.world.node_tree.nodes['Background'].inputs[1].default_value=.8
 for x,y,z,power in [(0,-3,8,1000),(-4,1,6,800)]:
  light=bpy.data.objects.new('V20_INTB_'+r.code+'_light',bpy.data.lights.new('V20_INTB_review','AREA'));scene.collection.objects.link(light);light.location=(x,y,z);light.data.energy=power;light.data.shape='DISK';light.data.size=7;light.rotation_euler=(Vector((0,0,0))-light.location).to_track_quat('-Z','Y').to_euler()
 scene.render.engine='CYCLES';scene.cycles.samples=12;scene.cycles.use_denoising=True;scene.render.resolution_x=1000;scene.render.resolution_y=800;scene.render.resolution_percentage=100;scene.view_settings.view_transform='AgX';scene.render.image_settings.file_format='PNG';scene.render.filepath=str(OUT/(r.code.lower()+'-interior.png'));bpy.context.view_layer.update();bpy.ops.render.render(write_still=True)
 print('INTERIOR_B_RENDERED',r.code,flush=True)
print('INTERIORS_B_COMPLETE',[(r['code'],r.get('seats')) for r in records if r['addedObjects']],flush=True)
