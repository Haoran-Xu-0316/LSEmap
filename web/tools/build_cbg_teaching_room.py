"""Independent CBG.1.02 room study from its official photo and 42-seat plan.

Run inside Blender. Seven six-seat groups follow the published plan. Metric
scale, unseen finishes and service routing remain explicit visual estimates.
The existing CBG atrium and every edition-22 object are preserved.
"""
from pathlib import Path
import array
import hashlib
import json
import math
import sys
import bpy
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'result/blender/stage23/cbg'
OUT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(Path(__file__).resolve().parent))
from facade_geometry import Geometry, materials
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v22.blend'))
originals=list(bpy.data.objects)
campus_names=set(bpy.data.scenes['00_CAMPUS_COMPLETE'].objects.keys())
def fingerprint(objects):
    digest=hashlib.sha256()
    for obj in sorted(objects,key=lambda item:item.name):
        digest.update(obj.name.encode())
        digest.update(array.array('f',[v for row in obj.matrix_world for v in row]).tobytes())
        if obj.type=='MESH':
            points=array.array('f',[0])*(len(obj.data.vertices)*3)
            obj.data.vertices.foreach_get('co',points);digest.update(points.tobytes())
            digest.update('|'.join(m.name if m else '' for m in obj.data.materials).encode())
    return digest.hexdigest()
protected=fingerprint(originals)
assert not bpy.data.collections.get('CBG_TEACHING_ROOM_study')
collection=bpy.data.collections.new('CBG_TEACHING_ROOM_study')
collection['roomSample']=True;collection['roomLabel']='CBG.1.02分组教学室，42座历史样本'
scene=bpy.data.scenes.new('ROOM23_CBG_TEACHING');scene.collection.children.link(collection)
bpy.context.window.scene=scene
palette={'white':(.79,.80,.75),'seat':(.75,.80,.79),'wall':(.76,.77,.72),
         'carpet':(.12,.14,.14),'carpet_alt':(.135,.15,.15),'steel':(.45,.48,.46),
         'dark':(.035,.047,.049),'duct':(.66,.69,.66),'baffle':(.027,.071,.11),
         'glass':(.38,.54,.57),'screen':(.10,.16,.18),'light':(.96,.93,.81),
         'curtain':(.063,.069,.065),'exit':(.015,.42,.12),'red':(.67,.025,.045)}
materials.clear()
for name,color in palette.items():
    mat=bpy.data.materials.new('CBG_V23_TEACH_'+name);mat.diffuse_color=(*color,1);mat.use_nodes=True
    shader=mat.node_tree.nodes['Principled BSDF'];shader.inputs['Base Color'].default_value=(*color,1)
    shader.inputs['Roughness'].default_value=.75
    if name=='steel':shader.inputs['Metallic'].default_value=.55
    if name in ['light','exit']:
        shader.inputs['Emission Color'].default_value=(*color,1);shader.inputs['Emission Strength'].default_value=.8
    if name=='glass':
        shader.inputs['Transmission Weight'].default_value=.35
        shader.inputs['Alpha'].default_value=.18;mat.diffuse_color=(*color,.18)
        mat.surface_render_method='DITHERED'
    materials[name]=mat
batches={}
def group(family,mat):
    key=(family,mat)
    if key not in batches:
        g=Geometry('CBG',family,mat);g.collection=collection
        g.name='CBG_V23_TEACH_'+family+'_'+mat;batches[key]=g
    return batches[key]
def box(family,mat,p,size,angle=0):group(family,mat).box(p,size,angle)
def prism(family,mat,outline,z,height):
    n=len(outline);points=[(x,y,h) for h in [z,z+height] for x,y in outline]
    group(family,mat).add(points,[tuple(reversed(range(n))),tuple(range(n,n*2))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)])
def tube(family,mat,a,b,r=.015,sides=10):
    a,b=Vector(a),Vector(b);direction=(b-a).normalized();u=direction.cross(Vector((0,0,1)))
    if u.length<.01:u=direction.cross(Vector((0,1,0)))
    u.normalize();v=direction.cross(u)
    points=[p+r*(u*math.cos(i*math.tau/sides)+v*math.sin(i*math.tau/sides)) for p in [a,b] for i in range(sides)]
    group(family,mat).add(points,[tuple(reversed(range(sides))),tuple(range(sides,sides*2))]+[(i,(i+1)%sides,(i+1)%sides+sides,i+sides) for i in range(sides)])
def plan_point(x,y):return((x-340)*.034,(y-450)*.034)
def transform(x,y,angle,p):
    c,s=math.cos(angle),math.sin(angle);return(x+c*p[0]-s*p[1],y+s*p[0]+c*p[1],p[2])

# Dark carpet and simple rectangular room follow the room-only official plan.
x0,x1=-5.58,5.68;y0,y1=-5.10,5.65
box('floor_base','carpet',((x0+x1)/2,(y0+y1)/2,-.09),(x1-x0,y1-y0,.18))
for ix in range(12):
    for iy in range(12):
        width=(x1-x0)/12;depth=(y1-y0)/12
        box('carpet_tiles','carpet' if (ix+iy)%3 else 'carpet_alt',
            (x0+(ix+.5)*width,y0+(iy+.5)*depth,.005),(width-.007,depth-.007,.009))
box('left_writing_wall','wall',(x0-.06,.275,1.82),(.12,10.75,3.64))
box('left_skirting','steel',(x0+.016,.275,.10),(.035,10.75,.20))
# Plan door at lower-left. Cut-open rear wall makes the room browsable.
box('rear_cutaway_wall','wall',(.05,y1+.05,.17),(11.26,.10,.34))
box('right_cutaway_wall','curtain',(x1+.05,.275,.17),(.10,10.75,.34))
for x in [-2.7,5.45]:
    box('front_structural_piers','wall',(x,y0+.12,1.84),(.32,.38,3.68))
box('front_head_beam','wall',(.05,y0-.025,3.55),(11.26,.24,.30))
# The matching photograph shows glazing beside the AV lectern and a dark blind.
for a,b in [(-5.40,-2.95),(-2.52,-.1),(.02,2.44),(2.56,5.25)]:
    box('front_glazing','glass',((a+b)/2,y0,1.84),(b-a,.035,3.3))
    for x in [a,b]:box('glazing_mullions','steel',(x,y0+.04,1.85),(.055,.075,3.4))
    box('glazing_sills','steel',((a+b)/2,y0+.025,.19),(b-a+.06,.16,.085))
    box('roller_blind_cassette','steel',((a+b)/2,y0+.075,3.29),(b-a+.04,.14,.15))
box('dark_roller_blind','curtain',(4.0,y0+.10,1.97),(2.35,.035,2.60))
# Rear glazing has been cut down to its sill line rather than concealing tables.
for x in [-2.77,.02,2.81,5.40]:
    box('rear_window_cut_frame','steel',(x,y1,.48),(.055,.095,.80))
box('rear_window_sill','steel',(.05,y1-.02,.15),(11.18,.18,.07))
# Door leaf is shown open at the position in the floor plan; no corridor added.
box('door_leaf','wall',(-3.64,5.20,1.15),(1.08,.065,2.3),math.radians(-53))
tube('door_handle','steel',(-3.28,4.80,1.06),(-3.28,4.80,1.30),.017)
box('exit_indicator','exit',(-3.35,5.58,2.64),(.38,.05,.16))
# The white wall functions as a writable surface. Subtle panel joints, tray,
# speaker and clock are visible in the archived room photograph.
for y in [-3.6,-1.1,1.4,3.9]:
    box('writing_wall_panel_joint','steel',(x0+.015,y,1.90),(.01,.008,3.15))
box('writing_wall_tray','steel',(x0+.10,-1.40,.81),(.18,5.0,.045))
box('wall_speaker','dark',(x0+.15,-3.66,2.95),(.20,.35,.44))
tube('wall_clock_body','white',(x0+.12,-.55,3.05),(x0+.21,-.55,3.05),.15,24)
tube('clock_hands','dark',(x0+.217,-.55,3.05),(x0+.217,-.55,3.16),.005)
tube('clock_hands','dark',(x0+.217,-.55,3.05),(x0+.217,-.63,3.02),.005)

seat_count=0;seat_centers=[]
def shell_chair(x,y,normal):
    global seat_count
    seat_count+=1;seat_centers.append((x,y))
    angle=math.atan2(normal.y,normal.x)-math.pi/2
    def p(a,b,c):return transform(x,y,angle,(a,b,c))
    # One bent polypropylene shell, with broad seat and gently curved back.
    profile=[(-.24,.46),(-.12,.447),(.10,.45),(.21,.49),(.265,.64),(.28,.79),(.285,.91)]
    vertices=[]
    for skin in [0,1]:
        for j,(py,pz) in enumerate(profile):
            width=.48 if j<4 else .46-.02*(j-4)/2
            for i in range(7):
                t=(i/6-.5)*2;px=t*width/2
                curve=.025*t*t if j<4 else -.04*t*t
                vertices.append(p(px,py+(skin*.023 if j>=3 else 0),pz+curve-(skin*.023 if j<3 else 0)))
    count=len(profile)*7;faces=[]
    for skin in range(2):
        offset=skin*count
        for j in range(len(profile)-1):
            for i in range(6):
                a=offset+j*7+i;face=(a,a+1,a+8,a+7)
                faces.append(face if skin==0 else tuple(reversed(face)))
    for j in range(len(profile)-1):
        for i in [0,6]:
            a=j*7+i;b=(j+1)*7+i;faces.append((a,b,b+count,a+count))
    for j in [0,len(profile)-1]:
        for i in range(6):
            a=j*7+i;faces.append((a,a+1,a+1+count,a+count))
    group('moulded_chair_shells','seat').add(vertices,faces)
    for side in [-1,1]:
        # Thin black sled bases match the photograph, avoiding generic office chairs.
        tube('chair_sled_base','dark',p(side*.205,-.30,.035),p(side*.205,.29,.035),.012)
        tube('chair_sled_base','dark',p(side*.205,-.30,.035),p(side*.19,-.12,.43),.012)
        tube('chair_sled_base','dark',p(side*.205,.29,.035),p(side*.19,.14,.445),.012)
    tube('chair_underseat_crossbar','dark',p(-.20,.10,.42),p(.20,.10,.42),.012)

def curved_table_outline(vertices):
    outline=[]
    for i,a in enumerate(vertices):
        b=vertices[(i+1)%3];c=vertices[(i+2)%3]
        start=.87*a+.13*b;end=.13*a+.87*b
        middle=(a+b)/2;normal=middle.normalized();control=middle+normal*.14
        for step in range(10):
            t=step/10;outline.append((1-t)**2*start+2*t*(1-t)*control+t*t*end)
        nxt=.87*b+.13*c
        for step in range(5):
            t=step/5;outline.append((1-t)**2*end+2*t*(1-t)*b+t*t*nxt)
    return outline

table_records=[]
def group_table(px,py,angle):
    x,y=plan_point(px,py)
    vertices=[Vector((1.02*math.cos(angle+i*math.tau/3),1.02*math.sin(angle+i*math.tau/3))) for i in range(3)]
    outline=[(x+p.x,y+p.y) for p in curved_table_outline(vertices)]
    prism('three_lobed_tabletops','white',outline,.747,.047)
    for v in vertices:
        tube('table_legs','steel',(x+v.x*.66,y+v.y*.66,.035),(x+v.x*.68,y+v.y*.68,.738),.035)
    for i,a in enumerate(vertices):
        b=vertices[(i+1)%3];mid=(a+b)/2;normal=mid.normalized()
        for t in [.30,.70]:
            q=a.lerp(b,t)+normal*.55
            shell_chair(x+q.x,y+q.y,normal)
    table_records.append({'planCenterPixels':[px,py],'estimatedCenter':[x,y],'seats':6})
for px,py,angle in [(340,355,-math.pi/2),(435,355,-math.pi/2),(340,437,math.pi/2),
                   (435,437,math.pi/2),(240,520,-math.pi/2),(340,520,-math.pi/2),(435,520,-math.pi/2)]:
    group_table(px,py,angle)
assert seat_count==42
minimum_seat_spacing=min(math.dist(a,b) for i,a in enumerate(seat_centers) for b in seat_centers[i+1:])
assert minimum_seat_spacing>.55, 'Seats overlap'
# Lectern follows the matching plan, with restrained visible AV equipment.
lx,ly=plan_point(242,350)
box('av_lectern','steel',(lx,ly,.56),(1.10,.67,1.12))
box('lectern_top','dark',(lx,ly,1.14),(1.16,.74,.065))
box('lectern_monitor','dark',(lx,ly+.08,1.50),(.56,.07,.35))
box('monitor_display','screen',(lx,ly+.039,1.50),(.50,.01,.29))
tube('monitor_stand','steel',(lx,ly+.1,1.18),(lx,ly+.1,1.37),.022)
box('lectern_keyboard','dark',(lx,ly-.16,1.185),(.44,.15,.025))
box('lectern_red_badge','red',(lx,ly-.342,.90),(.11,.015,.12))
tube('lectern_microphone','dark',(lx+.36,ly-.05,1.17),(lx+.36,ly+.01,1.48),.009)
# Partial exposed services and rounded acoustic rafts preserve the photographed
# ceiling character, while the open centre keeps all seven groups readable.
for x in [-4.55,-1.05,2.95]:
    tube('exposed_round_ducts','duct',(x,y0+.40,3.34),(x,2.0,3.34),.17,20)
    for y in [-4.1,-2.4,-.7,1.0]:
        tube('duct_joint_bands','steel',(x,y-.025,3.34),(x,y+.025,3.34),.178,20)
        tube('duct_hangers','steel',(x-.21,y,3.35),(x-.21,y,3.82),.009)
        tube('duct_hangers','steel',(x+.21,y,3.35),(x+.21,y,3.82),.009)
        box('duct_hanger_bracket','steel',(x,y,3.19),(.49,.04,.025))
# Service elbows are segmented curves, not disconnected vertical cylinders.
for x in [-4.55,-1.05,2.95]:
    for i in range(12):
        a=i*math.pi/24;b=(i+1)*math.pi/24
        tube('duct_elbows','duct',(x,2+.35*math.sin(a),3.34-.35*(1-math.cos(a))),
             (x,2+.35*math.sin(b),3.34-.35*(1-math.cos(b))),.17,16)
    tube('duct_drop','duct',(x,2.35,2.99),(x,2.35,2.82),.17,16)
    tube('duct_outlet_grille','dark',(x,2.35,2.813),(x,2.35,2.825),.143,20)
def raft(x,y,length,width):
    radius=width/2;half=(length-width)/2;outline=[]
    for side,base in [(1,half),(-1,-half)]:
        for i in range(17):
            a=(-math.pi/2 if side==1 else math.pi/2)+i*math.pi/16
            outline.append((x+base+radius*math.cos(a),y+radius*math.sin(a)))
    prism('blue_acoustic_rafts','baffle',outline,3.10,.075)
    for dx in [-length*.30,length*.30]:
        tube('raft_suspension','steel',(x+dx,y,3.18),(x+dx,y,3.82),.007)
for x,y in [(-3.15,-3.50),(.35,-3.50),(3.9,-3.50),(-3.15,-.60),(.35,-.60)]:raft(x,y,2.2,1.1)
for x in [-4.40,-.82,2.72]:
    for y in [-3.35,-.3]:
        box('linear_light_body','steel',(x,y,3.01),(.12,1.90,.08))
        box('linear_light_diffuser','light',(x,y,2.962),(.095,1.85,.023))
        for dy in [-.65,.65]:tube('light_suspension','steel',(x,y+dy,3.05),(x,y+dy,3.82),.007)
for x in [-4.85,-2.0,.85,3.75]:
    box('overhead_cable_tray','steel',(x,-4.63,3.63),(1.9,.22,.07))
# Explicit supporting header avoids floating ceiling services in the open study.
for y in [-4.40,-.4]:box('ceiling_cross_support','wall',(.1,y,3.84),(11.1,.14,.14))

for g in batches.values():
    obj=g.finish();obj['roomCode']='CBG.1.02';obj['scope']='Official historical room sample, estimated dimensions'
    for modifier in list(obj.modifiers):obj.modifiers.remove(modifier)
position=[14.0,16.0,12.5];target=[0,.2,1.2]
camera=bpy.data.objects.new('CBG_V23_TEACH_camera',bpy.data.cameras.new('CBG_V23_TEACH_camera'))
scene.collection.objects.link(camera);camera.location=position
camera.rotation_euler=(Vector(target)-camera.location).to_track_quat('-Z','Y').to_euler()
camera.data.type='ORTHO';camera.data.ortho_scale=17.2;scene.camera=camera
scene.world=bpy.data.worlds.new('CBG_V23_TEACH_world');scene.world.color=(.82,.84,.85)
scene.render.engine='BLENDER_WORKBENCH';scene.display.shading.light='STUDIO'
scene.display.shading.studiolight_rotate_z=.6;scene.display.shading.color_type='MATERIAL'
scene.display.shading.show_shadows=True;scene.display.shading.show_cavity=True;scene.display.shading.cavity_type='BOTH'
scene.display.shading.background_type='WORLD';scene.view_settings.view_transform='Standard'
scene.render.resolution_x=1500;scene.render.resolution_y=1250;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.render.filepath=str(OUT/'cbg-1-02.png')
assert fingerprint(originals)==protected
assert set(bpy.data.scenes['00_CAMPUS_COMPLETE'].objects.keys())==campus_names
scope='依据LSE官方CBG.1.02平面与同房间照片建立的42座分组教学室历史样本。七组六座沿用平面布局；房间尺度、设备间距及不可见构造为估算，局部墙和吊顶剖开，不代表2026年现状或与中庭的实测连接。'
sources=[{'path':'data/collections/interiors/images/9ca41c8b2a2c_CBG.1.02.gif','url':'https://www.lse.ac.uk/assets/roomInformation/images/CBG.1.02.gif','supports':'RoomCBG.1.02, first floor,42seat capacity; seven six-seat group positions and door/glazing edges'},
 {'path':'data/collections/interiors/images/02d586d5de16_CBG.1.02.jpg','url':'https://www.lse.ac.uk/assets/roomInformation/images/photos/CBG.1.02.jpg','supports':'Matching room photo: three-lobed white tables, bent-shell sled chairs, ducts, dark blue rafts, glazing, blinds, white writing wall and lectern'}]
record={'code':'CBG','roomCode':'CBG.1.02','roomLabel':collection['roomLabel'],'collection':collection.name,
 'scene':scene.name,'camera':position,'target':target,'cameraName':camera.name,'scope':scope,'sources':sources,
 'addedObjects':[{'name':g.name,'collection':collection.name} for g in batches.values()],
 'changes':['新增独立42座分组教学室，不改变原中庭','七组三瓣桌、42把曲面椅、讲台AV、玻璃墙、风管和局部吸声吊顶'],
 'limitations':['无尺寸平面，房间尺度和设备构造估算','公开历史资料没有明确拍摄年代，不证明2026布置','后侧/右侧墙及部分吊顶为观察剖开','不推测门外走廊或与中庭的连接'],
 'seatCount':seat_count,'tableGroups':table_records,
 'roomStudy':{'id':'cbg-102','label':'CBG.1.02分组教室','camera':position,'target':target,'scope':scope,'collection':collection.name}}
manifest={'stage':23,'baseline':'result/blender/LSE_campus_detailed_v22.blend','buildings':[record],
 'qa':{'originalFingerprintBefore':protected,'originalFingerprintAfter':fingerprint(originals),'campusObjectsUnchanged':True,
       'newMeshObjects':len(batches),'seatCount':seat_count,'tableCount':7,'minimumSeatCenterSpacing':minimum_seat_spacing,
       'render':'result/blender/stage23/cbg/cbg-1-02.png'}}
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'refined.blend'))
(OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
bpy.ops.render.render(write_still=True)
print('CBG_TEACHING_DONE',seat_count,len(batches),flush=True)
