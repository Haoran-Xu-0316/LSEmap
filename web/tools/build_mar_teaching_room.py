"""Build MAR.1.04 as an independent, archive-supported 90-seat room study.

Run in Blender's Text Editor. The official room plan fixes capacity and broad
furniture layout; room dimensions, tier heights and chair spacing are estimates.
The existing MAR hall and all edition-21 objects remain unchanged.
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
OUT=ROOT/'result/blender/stage22/mar'
OUT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(Path(__file__).resolve().parent))
from facade_geometry import Geometry, materials
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v21.blend'))
originals=list(bpy.data.objects)
campus_names=set(bpy.data.scenes['00_CAMPUS_COMPLETE'].objects.keys())

def fingerprint(objects):
    digest=hashlib.sha256()
    for obj in sorted(objects,key=lambda item:item.name):
        digest.update(obj.name.encode())
        digest.update(array.array('f',[v for row in obj.matrix_world for v in row]).tobytes())
        if obj.type=='MESH':
            vertices=array.array('f',[0])*(3*len(obj.data.vertices))
            obj.data.vertices.foreach_get('co',vertices);digest.update(vertices.tobytes())
            digest.update('|'.join(m.name if m else '' for m in obj.data.materials).encode())
    return digest.hexdigest()
original_hash=fingerprint(originals)
assert not bpy.data.collections.get('MAR_TEACHING_ROOM_study')
collection=bpy.data.collections.new('MAR_TEACHING_ROOM_study')
collection['roomSample']=True
collection['roomLabel']='MAR.1.04阶梯教学室，90座历史样本'
scene=bpy.data.scenes.new('ROOM22_MAR_TEACHING')
scene.collection.children.link(collection)
bpy.context.window.scene=scene
PALETTE={'plaster':(.66,.65,.59),'oak':(.53,.42,.27),'oak_edge':(.65,.55,.37),
         'desk':(.21,.24,.24),'carpet':(.23,.27,.25),'concrete':(.40,.40,.36),
         'chair_frame':(.11,.13,.13),'seat':(.26,.29,.25),'steel':(.28,.30,.29),
         'screen':(.10,.18,.22),'whiteboard':(.82,.85,.80),'dark':(.035,.04,.037),
         'light':(.90,.86,.70),'exit':(.04,.45,.18),'window':(.38,.52,.57)}
materials.clear()
for name,color in PALETTE.items():
    mat=bpy.data.materials.new('MAR_V22_TEACH_'+name);mat.diffuse_color=(*color,1);mat.use_nodes=True
    node=mat.node_tree.nodes['Principled BSDF'];node.inputs['Base Color'].default_value=(*color,1)
    node.inputs['Roughness'].default_value=.70
    if name=='steel':node.inputs['Metallic'].default_value=.55
    if name in ['light','exit']:
        node.inputs['Emission Color'].default_value=(*color,1);node.inputs['Emission Strength'].default_value=.5
    materials[name]=mat
batches={}
def group(family,material):
    key=(family,material)
    if key not in batches:
        geometry=Geometry('MAR',family,material);geometry.collection=collection
        geometry.name='MAR_V22_TEACH_'+family+'_'+material;batches[key]=geometry
    return batches[key]
def box(family,material,p,size,angle=0):group(family,material).box(p,size,angle)
def prism(family,material,polygon,z,depth):
    n=len(polygon);v=[(x,y,h) for h in [z,z+depth] for x,y in polygon]
    group(family,material).add(v,[tuple(reversed(range(n))),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)])
def tube(family,material,a,b,r=.018):
    a,b=Vector(a),Vector(b);direction=(b-a).normalized();u=direction.cross(Vector((0,0,1)))
    if u.length<.05:u=direction.cross(Vector((0,1,0)))
    u.normalize();v=direction.cross(u);n=8
    points=[p+r*(u*math.cos(i*math.tau/n)+v*math.sin(i*math.tau/n)) for p in [a,b] for i in range(n)]
    faces=[tuple(reversed(range(n))),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    group(family,material).add(points,faces)
def point(pixel):return Vector(((pixel[0]-325)*.04,(pixel[1]-510)*.04))
def path_points(pixels):return [point(p) for p in pixels]
def offset_path(points,distance):
    result=[]
    for i,p in enumerate(points):
        before=(p-points[i-1]).normalized() if i else (points[1]-p).normalized()
        after=(points[i+1]-p).normalized() if i+1<len(points) else before
        n1=Vector((-before.y,before.x));n2=Vector((-after.y,after.x));bisector=(n1+n2).normalized()
        scale=distance/max(.55,bisector.dot(n2));result.append(p+bisector*scale)
    return result
def ribbon(family,material,points,left,right,z,height):
    a=offset_path(points,left);b=offset_path(points,right)
    for i in range(len(points)-1):prism(family,material,[a[i],a[i+1],b[i+1],b[i]],z,height)
def sample_path(points,t):
    lengths=[(b-a).length for a,b in zip(points[:-1],points[1:])];distance=t*sum(lengths)
    for i,length in enumerate(lengths):
        if distance<=length or i==len(lengths)-1:
            tangent=(points[i+1]-points[i]).normalized();return points[i]+tangent*min(distance,length),tangent
        distance-=length
seat_count=0

def chair(x,y,z,normal):
    global seat_count
    seat_count+=1
    # Local +Y is the chair back, pointing away from the desk.
    angle=math.atan2(normal.y,normal.x)-math.pi/2;c,s=math.cos(angle),math.sin(angle)
    def p(dx,dy,dz):return(x+c*dx-s*dy,y+s*dx+c*dy,z+dz)
    box('chair_upholstery','seat',p(0,0,.48),(.48,.45,.075),angle)
    for dx in [-.23,.23]:
        tube('chair_back_frame','chair_frame',p(dx,.21,.48),p(dx,.24,.96),.019)
        box('chair_arms','chair_frame',p(dx*1.22,0,.70),(.055,.40,.045),angle)
        tube('chair_arm_support','steel',p(dx*1.15,.11,.48),p(dx*1.22,.11,.68),.012)
    for zbar in [.62,.67,.72,.77,.82,.87,.92]:
        box('chair_mesh_back','chair_frame',p(0,.24,zbar),(.43,.025,.027),angle)
    tube('chair_back_top','chair_frame',p(-.23,.24,.97),p(.23,.24,.97),.019)
    tube('chair_height_post','steel',p(0,0,.13),p(0,0,.43),.035)
    for i in range(5):
        a=i*math.tau/5;dx,dy=.32*math.cos(a),.32*math.sin(a)
        tube('chair_five_star_base','chair_frame',p(0,0,.16),p(dx,dy,.075),.024)
        tube('chair_casters','dark',p(dx-.03,dy,.048),p(dx+.03,dy,.048),.038)

furniture=[]
def desk_run(label,pixels,count,z,seat_ranges=None):
    points=path_points(pixels)
    # Floor follows the occupied bank, leaving the central and cross aisles open.
    if z>0:ribbon('stepped_seating_platforms','carpet',points,1.02,-.43,0,z)
    ribbon('continuous_table_tops','desk',points,.30,-.30,z+.74,.055)
    ribbon('pale_table_edge','oak_edge',points,.325,.30,z+.735,.065)
    ribbon('pale_front_edge','oak_edge',points,-.30,-.325,z+.735,.065)
    ribbon('timber_table_fronts','oak',points,-.28,-.325,z+.10,.60)
    seat_parameters=[]
    if seat_ranges:
        for a,b,n in seat_ranges:seat_parameters.extend([a+(b-a)*(i+.5)/n for i in range(n)])
    else:seat_parameters=[.06+.88*(i+.5)/count for i in range(count)]
    assert len(seat_parameters)==count
    for t in seat_parameters:
        p,tangent=sample_path(points,t);normal=Vector((-tangent.y,tangent.x));q=p+normal*.67
        chair(q.x,q.y,z,normal)
        tube('table_pedestals','steel',(p.x,p.y,z+.06),(p.x,p.y,z+.71),.025)
        socket=p+normal*.14
        box('desk_power_ports','dark',(socket.x,socket.y,z+.801),(.075,.045,.012),math.atan2(tangent.y,tangent.x))
    furniture.append({'label':label,'capacityInModel':count,'tierHeightEstimated':z,'planPolylinePixels':pixels})

# The front display-wall corners are simplified, while the seating-bank
# layout remains traced from the plan. Keep the floor under every wall.
outline=[(170,308),(500,308),(500,688),(179,688),(151,649),(156,575),(170,559)]
prism('room_floor','carpet',path_points(outline),-.18,.18)
# Two complete walls and two low edges make an explicit cutaway. The room is
# local to this scene; it is never inserted into the ground-floor hall.
box('front_wall','plaster',(0,-7.92,2.40),(10.65,.16,4.8))
box('left_wall','plaster',(-6.10,-2.1,2.4),(.16,11.70,4.8))
box('back_cutaway_edge','concrete',(0,7.11,.12),(13.60,.15,.24))
box('right_cutaway_edge','concrete',(7.01,-.65,.12),(.15,15.45,.24))
# Front wall acoustic timber, projection field and flanking confidence displays.
for i in range(95):
    x=-5.15+i*.11
    if -2.10<x<2.10:continue
    box('front_acoustic_slats','oak',(x,-7.79,2.35),(.045,.095,4.55))
box('projection_frame','dark',(0,-7.74,2.55),(3.8,.12,2.35))
box('projection_surface','whiteboard',(0,-7.664,2.55),(3.66,.025,2.20))
for x in [-3.0,3.0]:
    box('confidence_display_frame','dark',(x,-7.61,2.65),(1.26,.12,.82))
    box('confidence_display','screen',(x,-7.54,2.65),(1.14,.025,.69))
for x in [-4.50,4.50]:
    box('door_leaf','dark',(x,-7.66,1.08),(1.03,.10,2.14))
    for dx in [-.56,.56]:box('door_jamb','steel',(x+dx,-7.57,1.10),(.065,.08,2.22))
    box('door_header','steel',(x,-7.57,2.21),(1.16,.08,.065))
    tube('door_pull','steel',(x+.34,-7.48,.89),(x+.34,-7.48,1.23),.017)
    box('illuminated_exit','exit',(x,-7.52,2.47),(.34,.05,.15))
# Long vertical timber fins and writable boards observed in the photograph.
for i in range(99):
    y=-7.56+i*.112
    box('side_acoustic_slats','oak',(-5.995,y,2.4),(.07,.04,4.55))
for y in [-4.6,-.7]:
    box('wall_board_frame','steel',(-5.925,y,2.12),(.08,2.30,1.26))
    box('wall_whiteboard','whiteboard',(-5.871,y,2.12),(.025,2.19,1.16))
# Visible structural piers and cut-open glazing sills follow the room-plan edge.
for x,y in [(-5.46,-6.11),(6.1,-5.70),(-5.56,6.30),(6.10,6.27)]:
    box('concrete_piers','plaster',(x,y,2.3),(.60,.54,4.60))
for x in [-4.1,-1.3,1.5,4.3]:
    box('rear_window_sills','plaster',(x,6.86,.37),(2.45,.31,.18))
    box('rear_window_cut_frames','steel',(x-1.25,6.98,.62),(.06,.10,1.0))
# Ninety seats, matching the capacity printed in the official room record.
# Exact icon spacing is estimated; broad desk-bank shapes follow the plan.
desk_run('front left outside',[(209,414),(216,503)],6,.60)
desk_run('front left middle',[(242,414),(250,503)],6,.30)
desk_run('front left inner',[(272,405),(273,444),(286,483)],4,0)
desk_run('front right inner',[(355,483),(369,444),(368,405)],4,0)
desk_run('front right middle',[(386,503),(394,414)],6,.30)
desk_run('front right outside',[(420,503),(430,414)],6,.60)
desk_run('rear centre U',[(305,528),(309,558),(335,558),(340,528)],4,.20,[(0,.29,2),(.71,1,2)])
desk_run('rear inner U',[(252,534),(264,612),(289,622),(360,622),(390,608),(402,534)],17,.62,[(0,.29,5),(.32,.68,7),(.71,1,5)])
desk_run('rear outer U',[(218,534),(230,643),(276,654),(365,654),(421,639),(438,534)],25,1.04,[(0,.28,7),(.30,.70,11),(.72,1,7)])
desk_run('left perimeter',[(183,573),(191,640)],4,1.30)
desk_run('right perimeter',[(456,631),(472,489)],8,1.30)
assert seat_count==90
# Cross-aisle steps and nosings expose the relative tier structure.
for side in [-1,1]:
    for i in range(4):
        x=side*(2.2+i*.78);height=(i+1)*.26
        box('cross_aisle_steps','carpet',(x,.36,height/2),(.78,.88,height))
        box('cross_aisle_nosings','oak_edge',(x-side*.37,.36,height+.009),(.025,.85,.016))
# Instructor console with AV equipment, microphone and cable apertures.
box('lectern_body','oak',(1.8,-6.08,.56),(1.24,.70,1.12))
box('lectern_top','desk',(1.8,-6.08,1.15),(1.36,.78,.065))
box('lectern_monitor','dark',(1.8,-6.0,1.46),(.53,.045,.32))
box('lectern_monitor_stand','steel',(1.8,-6.0,1.26),(.07,.09,.19))
tube('lectern_microphone','dark',(2.15,-6.24,1.19),(2.19,-6.22,1.56),.009)
# A limited ceiling strip retains the defining oak-baffle and exposed-service
# language without hiding the whole teaching layout in the cutaway view.
for i in range(18):
    x=-5.6+i*.30
    box('ceiling_oak_baffles','oak_edge',(x,-4.65,4.66),(.06,6.05,.25))
for y in [-6.45,-3.20]:
    box('ceiling_service_carriers','dark',(-2.9,y,4.89),(5.55,.20,.16))
    for x in [-4.8,-2.7,-.6]:
        tube('round_ceiling_services','dark',(x,y,4.70),(x,y,4.47),.12)
for x in [-4.1,-1.2]:
    box('suspended_linear_lights','light',(x,-4.4,4.49),(.085,2.7,.055))
    tube('light_hanger','steel',(x,-5.3,4.51),(x,-5.3,4.93),.008)
box('projector_body','plaster',(0,-4.6,4.3),(.56,.47,.19))
box('projector_lens','dark',(0,-4.84,4.28),(.12,.035,.08))
tube('projector_mount','steel',(0,-4.6,4.40),(0,-4.6,4.93),.025)

for geometry in batches.values():
    obj=geometry.finish();obj['scope']='Historical MAR.1.04 sample; dimensions and tier heights estimated'
    obj['roomCode']='MAR.1.04'
    for modifier in list(obj.modifiers):obj.modifiers.remove(modifier)
position=[17.8,20.8,15.0];target=[0,-.2,1.5]
camera=bpy.data.objects.new('MAR_V22_TEACH_camera',bpy.data.cameras.new('MAR_V22_TEACH_camera'))
scene.collection.objects.link(camera);camera.location=position
camera.rotation_euler=(Vector(target)-camera.location).to_track_quat('-Z','Y').to_euler()
camera.data.type='ORTHO';camera.data.ortho_scale=22.5;scene.camera=camera
scene.world=bpy.data.worlds.new('MAR_V22_TEACH_world');scene.world.color=(.80,.82,.83)
scene.render.engine='BLENDER_WORKBENCH'
scene.display.shading.light='STUDIO';scene.display.shading.studiolight_rotate_z=.45
scene.display.shading.color_type='MATERIAL';scene.display.shading.show_shadows=True
scene.display.shading.show_cavity=True;scene.display.shading.cavity_type='BOTH'
scene.display.shading.background_type='WORLD'
scene.render.resolution_x=1600;scene.render.resolution_y=1300;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='Standard'
scene.render.filepath=str(OUT/'mar-1-04.png')
assert fingerprint(originals)==original_hash
assert set(bpy.data.scenes['00_CAMPUS_COMPLETE'].objects.keys())==campus_names
sources=[{'path':'data/collections/interiors/images/1eb304f61708_MAR.1.04.gif','url':'https://www.lse.ac.uk/assets/roomInformation/images/MAR.1.04.gif','supports':'Official90-seat room plan, room outline and desk-bank arrangement'},
 {'path':'data/collections/interiors/images/2f04d6322e38_MAR.1.04.jpg','url':'https://www.lse.ac.uk/assets/roomInformation/images/photos/MAR.1.04.jpg','supports':'Matching room photo: timber baffles/slats, tiered desks, mesh office chairs and AV'},
 {'path':'data/collections/interiors/pages/fd81b8cfce44_0.htm','url':'https://www.lse.ac.uk/admin/timetables/confirmed_old/ttrooms/marshall_building/0.htm','supports':'RoomMAR.1.04, floor1, capacity90; page refreshed2022-08-17, not photo date'}]
scope='依据LSE官方MAR.1.04平面与同房间照片建立的90座阶梯教学室历史样本。房间尺寸、阶梯标高和具体椅位为估算；独立展示，不代表2026年现状或与大厅的实测连接。'
record={'code':'MAR','roomCode':'MAR.1.04','roomLabel':collection['roomLabel'],'collection':collection.name,'scene':scene.name,
 'camera':position,'target':target,'cameraName':camera.name,'scope':scope,'sources':sources,
 'addedObjects':[{'name':g.name,'collection':collection.name} for g in batches.values()],
 'changes':['新增独立90座阶梯教学室，保留原大厅、楼梯和夹层','左右前部桌组、中后部U形桌、阶梯平台、办公椅、AV、木条墙与局部吊顶'],
 'limitations':['平面无尺寸标注，模型尺度和层高估算；前侧弧形墙角作直线简化','90座为官方容量，低清平面的逐椅位置不能精确测量','后侧与右侧墙、吊顶作剖开处理；不构造无依据的门外走廊或楼层连接','原图与照片年代未知，不能声称当前布置'],
 'seatCount':seat_count,'furnitureGroups':furniture,
 'roomStudy':{'id':'mar-104','label':'MAR.1.04阶梯教室','camera':position,'target':target,'scope':scope,'collection':collection.name}}
manifest={'stage':22,'baseline':'result/blender/LSE_campus_detailed_v21.blend','buildings':[record],
 'qa':{'originalFingerprintBefore':original_hash,'originalFingerprintAfter':fingerprint(originals),
       'campusObjectsUnchanged':True,'newMeshObjects':len(batches),'render':'result/blender/stage22/mar/mar-1-04.png'}}
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'refined.blend'))
(OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
bpy.ops.render.render(write_still=True)
print('MAR_TEACHING_DONE',seat_count,len(batches),flush=True)
