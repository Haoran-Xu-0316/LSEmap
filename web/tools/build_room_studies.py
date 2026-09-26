"""Build three archive-based interior samples in a separate edition-18 model.
Run in Blender's Text Editor. Room dimensions and floor levels are estimates;
these independent cutaways are not a surveyed whole-building interior.
"""
from pathlib import Path
import hashlib, json, math, sys
import bpy
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).resolve().parent))
from facade_geometry import Geometry, materials
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'result/blender/stage18';OUT.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v17.blend'))
PALETTE={'plaster':(.79,.78,.72),'wood':(.32,.14,.047),'oak':(.48,.29,.13),
 'white':(.78,.79,.73),'blue':(.025,.13,.23),'black':(.018,.024,.024),
 'steel':(.28,.32,.33),'carpet':(.21,.23,.22),'carpet_light':(.34,.39,.40),
 'carpet_dark':(.11,.17,.19),'glass':(.28,.46,.52),'light':(.95,.90,.70)}
for name,color in PALETTE.items():
 mat=bpy.data.materials.new('ROOM18_'+name);mat.use_nodes=True;mat.diffuse_color=(*color,1)
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
  self.scene=bpy.data.scenes.new('ROOM18_'+code);self.scene.collection.children.link(self.col)
  bpy.context.window.scene=self.scene
  self.record={'code':code,'label':label,'photo':photo,'plan':plan,'dimensions':'Estimated from archived images and undimensioned room plan','scope':'One historical room sample, not a whole building or its current layout','camera':camera,'target':target}
 def group(self,family,material):
  key=family+'_'+material
  if key not in self.groups:
   g=Geometry(self.code,'ROOM18_'+key,material);g.collection=self.col;self.groups[key]=g
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
  cam=bpy.data.objects.new('ROOM18_'+self.code+'_camera',bpy.data.cameras.new('ROOM18_'+self.code+'_camera'));self.scene.collection.objects.link(cam)
  cam.location=self.record['camera'];cam.rotation_euler=(Vector(self.record['target'])-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.lens=36;self.scene.camera=cam
  self.record.update({'seats':self.seats,'components':sum(g.parts for g in self.groups.values()),'meshFamilies':len(self.groups)})
  records.append(self.record)
# OLD.4.10: three seating banks, central straight benches and angled side banks.
r=Room('OLD','OLD.4.10阶梯教室','8608c74c666d_OLD.4.10.jpg','fc4876049d62_OLD.4.10.gif',(17,1,12),(0,0,.7))
r.box('floor','carpet',(0,0,-.13),(16,8.6,.26))
r.box('teaching_wall','plaster',(0,-4.3,1.7),(16,.18,3.4))
r.box('window_wall_base','plaster',(0,4.3,.42),(16,.18,.84))
r.box('window_wall_header','plaster',(0,4.3,3.13),(16,.18,.54))
for x in [-6.4,-3.2,0,3.2,6.4]:
 r.window(x,4.3,1.85,2.8,2.02)
 r.box('window_pier','plaster',(x+1.55,4.3,1.85),(.22,.25,2.02))
for bx,count,rows,angle in [(-5.15,4,6,-.14),(0,6,4,0),(5.15,4,6,.14)]:
 for row in range(rows):
  y=-2.0+row*.98 if rows==6 else .0+row*.98;z=row*.13
  r.box('seating_riser','carpet',(bx,y,z/2),(count*.53+.28,.99,max(.035,z)),angle)
  r.desk(bx,y-.19,z,count*.53+.2,angle=angle)
  for i in range(count):
   dx=(i-(count-1)/2)*.53;r.chair(bx+dx*math.cos(angle),y+.32+dx*math.sin(angle),z,angle)
for x in [-4.8,3.5]:
 r.box('whiteboard_frame','steel',(x,-4.16,1.84),(4.7,.075,1.4));r.box('whiteboard','white',(x,-4.10,1.84),(4.58,.035,1.28))
r.equipment(-1.25,-2.9)
r.box('door','white',(7.02,-4.15,1.07),(1.05,.075,2.14));r.box('door_vision','black',(7.02,-4.1,1.55),(.14,.03,.71))
r.box('projection_screen','white',(-.6,-4.07,2.47),(2.4,.055,1.25))
for x in [-4,0,4]:r.box('ceiling_light','light',(x,-2.6,3.25),(2.5,.24,.065))
r.box('projector','white',(-.6,-1.7,2.95),(.4,.36,.15));r.finish()
# CLM.1.01: irregular perimeter, four five-seat group tables, dark timber wall panels.
r=Room('CLM','CLM.1.01小组教室','1af9f3e45428_CLM.1.01.jpg','c96587d61319_CLM.1.01.GIF',(8,-8,6.8),(0,0,.6))
outline=[(-4.2,-3.2),(4.2,-3.2),(4.2,3.1),(.3,3.1),(.3,2.5),(-1.0,2.5),(-1.6,3.35),(-3.3,2.95),(-3.25,2.0),(-4.2,1.6)]
r.prism('room_floor','carpet',outline,-.15,.15)
# Inset triangular carpet field, leaving the irregular perimeter intact.
for ix in range(8):
 for iy in range(5):
  x=-3.6+ix*.9;y=-2.5+iy*.9
  r.prism('carpet_triangles','carpet_light' if (ix+iy)%2 else 'carpet_dark',[(x,y),(x+.88,y),(x,y+.88)],.002,.003)
r.panel_wall(8.4,3.1,1.10)
r.box('upper_wall','plaster',(1.8,3.1,2.15),(4.8,.17,2.1))
r.box('wall_dado','wood',(1.8,3.0,2.6),(4.8,.09,.28))
r.window(-2.1,3.1,2.05,3.6,1.65)
for x,y in [(-2.1,-1.5),(1.55,-1.5),(-2.1,1.0),(1.55,1.0)]:
 points=[(x+1.0*math.cos(a),y+1.0*math.sin(a)) for a in [math.pi/2,math.pi/2+2*math.pi/3,math.pi/2+4*math.pi/3]]
 r.prism('group_table','white',points,.74,.065)
 for dx,dy in [(-.4,-.25),(.4,-.25),(0,.5)]:r.tube('table_leg','steel',(x+dx,y+dy,.03),(x+dx,y+dy,.74),.03)
 for i in range(5):
  a=-math.pi/2+i*2*math.pi/5;r.chair(x+1.18*math.cos(a),y+1.18*math.sin(a),0,a-math.pi/2,mat='white')
r.box('teaching_whiteboard','white',(2.8,2.72,1.36),(2.35,.065,1.27));r.equipment(.6,2.5)
for x in [-2,1.5]:r.box('suspended_light','light',(x,2.55,3.07),(2.25,.17,.065))
r.box('timber_door','wood',(3.75,3.0,1.05),(.75,.09,2.1));r.finish()
# CON.7.04: eight seats around a boat-shaped conference table, timber wall panels.
r=Room('CON','CON.7.04会议室','73b7be2bc2de_CON.7.04.jpg','11f7e4c56390_CON.7.04.GIF',(7,-6,5.7),(0,0,.75))
r.box('floor','carpet',(0,0,-.12),(6.4,4.2,.24))
r.panel_wall(6.4,2.1,.85)
r.box('window_header','wood',(0,2.1,2.85),(6.4,.16,.3))
for x in [-2.75,2.75]:r.box('side_window_panel','wood',(x,2.1,1.8),(.9,.16,1.9))
r.window(0,2.1,1.82,4.45,1.88)
r.box('left_wall','wood',(-3.2,.55,1.45),(.16,3.1,2.9))
for y in [-.95,-.05,.85,1.75]:
 for z in [.13,.84,2.75]:r.box('panel_moulding','oak',(-3.08,y,z),(.065,.83,.055))
 r.box('panel_stile','oak',(-3.08,y+.4,1.45),(.065,.055,2.7))
outline=[(-2.2,-.48),(-1.65,-.85),(1.65,-.85),(2.2,-.48),(2.2,.48),(1.65,.85),(-1.65,.85),(-2.2,.48)]
r.prism('conference_table','oak',outline,.76,.075)
for x in [-1.35,1.35]:r.box('table_pedestal','wood',(x,0,.38),(.55,.85,.76))
for x in [-1.2,0,1.2]:
 r.chair(x,1.25,mat='black',arms=True);r.chair(x,-1.25,angle=math.pi,mat='black',arms=True)
r.chair(-2.65,0,angle=math.pi/2,mat='black',arms=True);r.chair(2.65,0,angle=-math.pi/2,mat='black',arms=True)
for x in [-.95,.95]:r.box('table_cable_lid','black',(x,0,.805),(.25,.08,.012))
r.box('display','black',(-1.7,1.85,1.77),(1.35,.09,.79));r.tube('display_stand','steel',(-1.7,1.88,.3),(-1.7,1.88,1.75),.045)
r.finish()
bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE']
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v18.blend'))
(OUT/'room-studies.json').write_text(json.dumps({'version':18,'buildings':records},ensure_ascii=False,indent=2)+'\n')
print('ROOM_STUDIES_COMPLETE',[(r['code'],r['seats'],r['components']) for r in records],flush=True)
