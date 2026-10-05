"""Independent CBG.1.03 historical room study, for Blender Text Editor.

Seven six-seat groups are traced from the official room-only floor plan.
Dimensions and hidden ceiling/door construction are visual estimates.
No connection to the campus, atrium or CBG.1.02 is invented.
"""
from pathlib import Path
import hashlib
import json
import math
import sys
import bpy
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'result/blender/stage158'
OUT.mkdir(parents=True,exist_ok=True)
baseline=ROOT/'result/blender/LSE_campus_detailed_v158.blend'
if not baseline.exists():
    baseline=ROOT/'result/blender/LSE_campus_detailed_v157.blend'
baseline_hash=hashlib.sha256(baseline.read_bytes()).hexdigest()
bpy.ops.wm.read_factory_settings(use_empty=True)
sys.path.insert(0,str(Path(__file__).resolve().parent))
from facade_geometry import Geometry, materials
placeholder=bpy.data.collections.new('CBG_EXTERIOR')
collection=bpy.data.collections.new('CBG103_TEACHING_ROOM_study')
collection['roomSample']=True
collection['roomLabel']='CBG.1.03分组教学室，42座历史样本'
scene=bpy.context.scene
scene.name='ROOM158_CBG103_TEACHING'
scene.collection.children.link(collection)
palette={'white':(.79,.80,.75),'seat':(.75,.80,.79),'wall':(.76,.77,.72),
         'carpet':(.12,.14,.14),'carpet_alt':(.135,.15,.15),'steel':(.45,.48,.46),
         'dark':(.035,.047,.049),'duct':(.66,.69,.66),'baffle':(.027,.071,.11),
         'glass':(.38,.54,.57),'screen':(.10,.16,.18),'light':(.96,.93,.81),
         'curtain':(.063,.069,.065),'exit':(.015,.42,.12),'red':(.67,.025,.045)}
materials.clear()
for name,color in palette.items():
    mat=bpy.data.materials.new('CBG103_V158_'+name);mat.diffuse_color=(*color,1);mat.use_nodes=True
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
        g.name='CBG103_V158_'+family+'_'+mat;batches[key]=g
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
def plan_point(x,y):return((x-332)*.034,(y-493)*.034)
def transform(x,y,angle,p):
    c,s=math.cos(angle),math.sin(angle);return(x+c*p[0]-s*p[1],y+s*p[0]+c*p[1],p[2])

# Room outline has no published metric dimensions. The 0.034 m/pixel
# factor is retained only as a visual estimate compatible with the 1.02 study.
x0,x1=plan_point(159,493)[0],plan_point(504,493)[0]
y0,y1=plan_point(332,328)[1],plan_point(332,657)[1]
box('floor_base','carpet',((x0+x1)/2,(y0+y1)/2,-.09),(x1-x0,y1-y0,.18))
for ix in range(12):
    for iy in range(12):
        w=(x1-x0)/12;d=(y1-y0)/12
        box('carpet_tiles','carpet' if (ix+iy)%3 else 'carpet_alt',
            (x0+(ix+.5)*w,y0+(iy+.5)*d,.005),(w-.008,d-.008,.009))
# Side and rear walls are cut away to expose the archived seating layout.
box('left_cutaway_wall','wall',(x0-.05,(y0+y1)/2,.18),(.10,y1-y0,.36))
box('right_cutaway_wall','wall',(x1+.05,(y0+y1)/2,.18),(.10,y1-y0,.36))
door_x=plan_point(345,493)[0]
for a,b in [(x0,door_x-.68),(door_x+.68,x1)]:
    box('rear_cutaway_wall','wall',((a+b)/2,y1+.05,.18),(b-a,.10,.36))
# Photo: central window and screen, large dark blinds either side.
box('front_head_beam','wall',((x0+x1)/2,y0,3.58),(x1-x0,.30,.38))
for x in [x0+.12,x1-.12]:
    box('front_structural_piers','wall',(x,y0,1.8),(.26,.32,3.6))
for a,b in [(x0+.26,-1.65),(-1.60,1.60),(1.65,x1-.26)]:
    box('front_glazing','glass',((a+b)/2,y0,1.77),(b-a,.035,3.30))
    for x in [a,b]:box('glazing_mullions','steel',(x,y0+.025,1.78),(.065,.10,3.4))
    box('roller_blind_cassette','steel',((a+b)/2,y0+.08,3.36),(b-a,.14,.14))
for a,b in [(x0+.28,-1.65),(1.65,x1-.28)]:
    box('dark_roller_blinds','curtain',((a+b)/2,y0+.10,1.76),(b-a,.03,3.14))
box('central_projection_screen_frame','dark',(0,y0+.22,2.27),(3.18,.09,2.41))
box('central_projection_screen','white',(0,y0+.275,2.27),(3.00,.025,2.21))
box('screen_bottom_weight','dark',(0,y0+.295,1.13),(3.21,.065,.055))
for x in [-2.33,2.33]:
    box('front_wall_speakers','wall',(x,y0+.24,2.99),(.49,.22,.46))
    tube('speaker_hangers','steel',(x,y0+.15,3.22),(x,y0+.15,3.53),.012)
# Door position follows the plan; construction is unphotographed and estimated.
box('door_leaf','wall',(door_x-.34,y1-.42,1.15),(1.24,.065,2.3),math.radians(-55))
# Lectern placement is traced, its visible shape matches the archived photo.
lx,ly=plan_point(244,379)
box('av_lectern','steel',(lx,ly,.56),(1.10,.67,1.12))
box('lectern_top','dark',(lx,ly,1.14),(1.18,.77,.065))
box('lectern_monitor','dark',(lx+.18,ly-.06,1.43),(.49,.07,.32))
tube('monitor_stand','steel',(lx+.18,ly,1.18),(lx+.18,ly,1.37),.025)
box('lectern_keyboard','dark',(lx+.12,ly+.18,1.185),(.44,.15,.025))
box('lectern_red_badge','red',(lx,ly+.342,.89),(.18,.015,.17))
tube('lectern_microphone','dark',(lx-.35,ly+.03,1.18),(lx-.35,ly-.02,1.48),.009)
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
    table_records.append({'planCenterPixels':[px,py],'estimatedCenter':[x,y],'orientationRadians':angle,'seats':6})
for px,py,angle in [(449,379,math.pi/2),(219,449,math.pi/2),(333,430,-math.pi/2),
                   (449,464,math.pi/2),(228,579,-math.pi/2),(333,569,math.pi/2),(449,579,-math.pi/2)]:
    group_table(px,py,angle)
assert seat_count==42
minimum_seat_spacing=min(math.dist(a,b) for i,a in enumerate(seat_centers) for b in seat_centers[i+1:])
assert minimum_seat_spacing>.55, 'Seats overlap'
# Photographed exposed services and hanging blue acoustic rafts.
# Only the front strip is retained overhead to keep all groups browsable.
for x in [-4.45,-1.48,1.48,4.45]:
    tube('exposed_round_ducts','duct',(x,y0+.16,3.65),(x,y0+2.20,3.65),.17,16)
    for y in [y0+.43,y0+1.55]:
        tube('duct_joint_bands','steel',(x,y-.025,3.65),(x,y+.025,3.65),.178,16)
for x in [-4.42,-1.46,1.47,4.40]:
    outline=[(x+1.08*math.cos(i*math.tau/40),y0+.95+.58*math.sin(i*math.tau/40)) for i in range(40)]
    prism('blue_acoustic_rafts','baffle',outline,3.14,.065)
    for dx in [-.65,.65]:tube('raft_suspension','steel',(x+dx,y0+.95,3.20),(x+dx,y0+.95,3.88),.007)
for y in [y0+.25,y0+1.75]:
    box('linear_light_body','steel',(.0,y,3.31),(x1-x0-.48,.12,.075))
    box('linear_light_diffuser','light',(.0,y,3.265),(x1-x0-.52,.085,.025))
box('projector_body','white',(0,y0+1.02,3.72),(.66,.55,.28))
box('projector_lens','dark',(0,y0+.735,3.68),(.12,.024,.12))
tube('projector_mount','steel',(0,y0+1.02,3.86),(0,y0+1.02,4.02),.035)
for y in [y0+.18,y0+2.16]:box('ceiling_cross_support','steel',(0,y,3.94),(x1-x0,.10,.09))
mesh_objects=[]
for g in batches.values():
    obj=g.finish();mesh_objects.append(obj)
    obj['roomCode']='CBG.1.03';obj['scope']='Official historical room sample, estimated metric dimensions'
    for modifier in list(obj.modifiers):obj.modifiers.remove(modifier)
bpy.data.collections.remove(placeholder)
position=[14.0,16.0,12.5];target=[0,.2,1.2]
camera=bpy.data.objects.new('CBG103_V158_camera',bpy.data.cameras.new('CBG103_V158_camera'))
scene.collection.objects.link(camera);camera.location=position
camera.rotation_euler=(Vector(target)-camera.location).to_track_quat('-Z','Y').to_euler()
camera.data.type='ORTHO';camera.data.ortho_scale=18.3;scene.camera=camera
scene.world=bpy.data.worlds.new('CBG103_V158_world');scene.world.color=(.82,.84,.85)
scene.render.engine='BLENDER_WORKBENCH';scene.display.shading.light='STUDIO'
scene.display.shading.color_type='MATERIAL';scene.display.shading.show_shadows=True
scene.display.shading.show_cavity=True;scene.display.shading.cavity_type='BOTH'
scene.display.shading.background_type='WORLD';scene.view_settings.view_transform='Standard'
scene.render.resolution_x=1200;scene.render.resolution_y=1050;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'
scope='依据LSE官方CBG.1.03平面与同房间照片建立42座历史教学室样本。七组六座按平面中心和方向描摹；米制尺度、不可见门构造和服务高度为估算。后侧与侧墙及部分吊顶为观察剖开，不推测与中庭或其他房间连接，不代表2026年布置。'
collection['roomCode']='CBG.1.03';collection['scope']=scope
assert seat_count==42 and len(table_records)==7
assert hashlib.sha256(baseline.read_bytes()).hexdigest()==baseline_hash
record={'stage':158,'code':'CBG','roomCode':'CBG.1.03','collection':collection.name,'scene':scene.name,
 'camera':position,'target':target,'scope':scope,'seatCount':seat_count,'tableCount':len(table_records),
 'minimumSeatCenterSpacing':minimum_seat_spacing,'tableGroups':table_records,
 'metricScale':{'metersPerPlanPixel':.034,'status':'visual estimate, no metric dimensions in plan'},
 'sources':[{'path':'data/collections/interiors/images/092448593146_CBG.1.03.gif','url':'https://www.lse.ac.uk/assets/roomInformation/images/CBG.1.03.gif','sha256':hashlib.sha256((ROOT/'data/collections/interiors/images/092448593146_CBG.1.03.gif').read_bytes()).hexdigest()},
 {'path':'data/collections/interiors/images/a8b911649cc7_CBG.1.03.jpg','url':'https://www.lse.ac.uk/assets/roomInformation/images/photos/CBG.1.03.jpg','sha256':hashlib.sha256((ROOT/'data/collections/interiors/images/a8b911649cc7_CBG.1.03.jpg').read_bytes()).hexdigest()}],
 'baselineSha256':baseline_hash,'baselineUnchanged':True,
 'meshCount':len(mesh_objects),'triangles':sum(sum(len(p.vertices)-2 for p in obj.data.polygons) for obj in mesh_objects),
 'roomStudy':{'id':'cbg-103','label':'CBG.1.03分组教室','camera':position,'target':target,'scope':scope,'collection':collection.name}}
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'cbg103-component.blend'))
scene.render.filepath=str(OUT/'cbg103-perspective.png');bpy.ops.render.render(write_still=True)
camera.location=(0,0,20);camera.rotation_euler=(0,0,0);camera.data.ortho_scale=13.2
scene.display.shading.show_shadows=False
for obj in mesh_objects:
    if any(word in obj.name for word in ['duct','raft','light','projector','ceiling_']):obj.hide_render=True
scene.render.filepath=str(OUT/'cbg103-plan.png');bpy.ops.render.render(write_still=True)
(OUT/'cbg103-audit.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
print('CBG103_VERIFIED',seat_count,len(table_records),len(mesh_objects),flush=True)
