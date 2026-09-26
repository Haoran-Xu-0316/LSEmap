"""Build the photographed 2014 Denning Learning Cafe architectural corner.

Run inside Blender. Source: official SAW occupants guide, pages4and11.
This independent cutaway does not claim a complete cafe, measured dimensions,
current furniture layout, or an exact connection to the existing SAW stair.
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
OUT=ROOT/'result/blender/stage24/saw'
OUT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(Path(__file__).resolve().parent))
from facade_geometry import Geometry, materials
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v23.blend'))
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
assert not bpy.data.collections.get('SAW_DENNING_ROOM_study')
collection=bpy.data.collections.new('SAW_DENNING_ROOM_study')
collection['roomSample']=True;collection['roomLabel']='Denning Learning Café，2014历史局部样本'
scene=bpy.data.scenes.new('ROOM24_SAW_DENNING');scene.collection.children.link(collection)
bpy.context.window.scene=scene
palette={'concrete':(.55,.53,.46),'stone':(.66,.64,.55),'stone_joint':(.47,.46,.40),
 'wood':(.50,.38,.23),'wood_light':(.55,.42,.26),'wood_dark':(.44,.32,.19),
 'red':(.34,.034,.028),'yellow':(.79,.47,.045),'cloud':(.84,.84,.77),
 'cloud_edge':(.71,.71,.66),'steel':(.48,.50,.46),'dark':(.055,.066,.061),
 'glass':(.36,.49,.47),'brick':(.38,.18,.095),'brick_light':(.46,.23,.12),
 'brick_dark':(.29,.12,.063),'mortar':(.34,.30,.24),'shutter':(.69,.70,.63),
 'shutter_shadow':(.48,.50,.45),'light':(.98,.95,.82),'blue':(.04,.31,.45)}
materials.clear()
for name,color in palette.items():
    mat=bpy.data.materials.new('SAW_V24_DENNING_'+name);mat.diffuse_color=(*color,1);mat.use_nodes=True
    shader=mat.node_tree.nodes['Principled BSDF'];shader.inputs['Base Color'].default_value=(*color,1)
    shader.inputs['Roughness'].default_value=.70 if name not in ['steel','glass'] else .32
    if name=='steel':shader.inputs['Metallic'].default_value=.65
    if name=='light':
        shader.inputs['Emission Color'].default_value=(*color,1);shader.inputs['Emission Strength'].default_value=.8
    if name=='glass':
        shader.inputs['Transmission Weight'].default_value=.35;shader.inputs['Alpha'].default_value=.20
        mat.diffuse_color=(*color,.20);mat.surface_render_method='DITHERED'
    materials[name]=mat
batches={}
def group(family,mat):
    key=(family,mat)
    if key not in batches:
        g=Geometry('SAW',family,mat);g.collection=collection
        g.name='SAW_V24_DENNING_'+family+'_'+mat;batches[key]=g
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

def upright_panel(family,material,xz,y,depth):
    n=len(xz);vertices=[(x,yy,z) for yy in [y,y+depth] for x,z in xz]
    group(family,material).add(vertices,[tuple(reversed(range(n))),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)])
def ellipse(family,material,x,y,rx,ry,z,depth,angle=0):
    c,s=math.cos(angle),math.sin(angle)
    outline=[]
    for i in range(96):
        a=i*math.tau/96;dx,dy=rx*math.cos(a),ry*math.sin(a)
        outline.append((x+c*dx-s*dy,y+s*dx+c*dy))
    prism(family,material,outline,z,depth)
def inside(point,polygon):
    x,y=point;result=False
    for i,(ax,ay) in enumerate(polygon):
        bx,by=polygon[i-1]
        if (ay>y)!=(by>y) and x<(bx-ax)*(y-ay)/(by-ay)+ax:result=not result
    return result

# A bounded photographed corner, not an inferred complete floor plate.
box('floor_substructure','concrete',(0,.25,-.10),(12.4,8.5,.20))
for i in range(62):
    x=-6.2+(i+.5)*.20
    cuts=[-4,-1.2+(i%4)*.26,1.7+(i%3)*.24,4.5]
    for j,(a,b) in enumerate(zip(cuts[:-1],cuts[1:])):
        box('oak_floorboards',['wood','wood_light','wood_dark'][(i+j)%3],(x,(a+b)/2,.009),(.193,b-a-.011,.018))
stone=[(-6.2,-2.6),(1.45,-2.6),(.15,2.9),(-2.95,4.45),(-6.2,4.45)]
prism('pale_stone_floor_zone','stone',stone,.025,.025)
# Tile joints stay wholly inside the photographed pale floor region.
for axis in [0,1]:
    for fixed in [-5.4,-4.2,-3,-1.8,-.6,.6,1.8,3.0,4.2]:
        for i in range(100):
            t=-6.2+i*.124;a=(fixed,t) if axis==0 else (t,fixed)
            b=(fixed,t+.124) if axis==0 else (t+.124,fixed)
            if inside(a,stone) and inside(b,stone):tube('stone_tile_joints','stone_joint',(*a,.051),(*b,.051),.003,4)
# Lift portal: yellow folded cladding with the red diagonal upper wall visible
# in the source. It is one photographed portal, without a conjectured lift shaft.
box('lift_backing','dark',(-4.66,3.39,1.52),(3.02,.16,3.04))
for x in [-5.21,-4.24]:
    box('stainless_lift_leaves','steel',(x,3.275,1.20),(.95,.07,2.38))
box('lift_leaf_joint','dark',(-4.725,3.229,1.20),(.016,.012,2.34))
box('lift_threshold','steel',(-4.73,3.15,.043),(2.04,.28,.04))
box('yellow_lift_jamb','yellow',(-3.36,3.22,1.38),(.58,.24,2.76))
box('yellow_lift_jamb','yellow',(-5.96,3.22,1.58),(.44,.24,3.16))
upright_panel('yellow_sloping_portal_head','yellow',[(-6.18,3.28),(-3.06,2.59),(-3.06,2.39),(-6.18,2.39)],3.10,.22)
upright_panel('red_diagonal_overpanel','red',[(-6.18,4.01),(-3.06,4.01),(-3.06,2.64),(-6.18,3.35)],3.24,.14)
box('lift_call_plate','steel',(-3.14,3.076,1.23),(.10,.025,.29))
box('lift_call_button','blue',(-3.14,3.055,1.29),(.035,.015,.055))
# Tall rear glazing, red-brown mullions and brick return are clear in the photo.
box('window_concrete_base','concrete',(-1.20,4.35,.22),(3.65,.18,.44))
for i in range(5):
    x=-2.79+i*.71
    box('rear_window_glass','glass',(x,4.36,1.96),(.665,.025,2.90))
for x in [-3.15,-2.44,-1.73,-1.02,-.31,.40]:
    box('window_vertical_mullions','red',(x,4.30,1.96),(.055,.075,3.02))
for z in [.48,1.58,2.46,3.47]:
    box('window_horizontal_rails','red',(-1.375,4.30,z),(3.60,.075,.055))
box('low_wall_grille','dark',(-1.1,4.232,.28),(1.13,.035,.18))
for i in range(14):box('low_grille_slats','steel',(-1.62+i*.08,4.208,.28),(.023,.025,.16))
box('brick_return_mortar','mortar',(.93,4.34,1.80),(1.03,.18,3.60))
for row in range(45):
    z=.04+row*.078
    for col in range(5):
        x=.465+col*.22+(row%2)*.11
        if x+.104>1.445:continue
        box('brick_return_units',['brick','brick_light','brick_dark'][(row+col)%3],(x,4.231,z),(.211,.055,.069))
# Service hatch is closed above and has a photographed metal grille below.
box('cafe_side_pier','concrete',(1.68,4.16,1.82),(.46,.62,3.64))
box('cafe_counter_base','concrete',(4.11,4.10,.53),(4.42,.72,1.06))
box('cafe_counter_sill','steel',(4.11,3.709,1.08),(4.47,.24,.075))
box('cafe_recess_back','dark',(4.11,4.43,1.54),(4.36,.10,1.06))
box('shutter_housing','concrete',(4.11,4.12,3.47),(4.42,.53,.31))
box('shutter_vent_strip','dark',(4.11,3.831,3.32),(4.31,.035,.27))
for x in [2.1,2.8,3.5,4.2,4.9,5.6]:
    box('upper_vent_stiles','steel',(x,3.803,3.32),(.036,.022,.235))
box('closed_shutter_backing','shutter',(4.11,3.89,2.58),(4.35,.12,1.21))
for i in range(24):
    z=2.0+i*.049
    box('roller_shutter_slats','shutter',(4.11,3.813,z),(4.29,.045,.039))
    box('shutter_recess_lines','shutter_shadow',(4.11,3.802,z-.022),(4.29,.007,.008))
for x in [1.955,6.265]:box('shutter_side_guide','steel',(x,3.79,2.13),(.052,.09,2.08))
for i in range(9):
    box('service_security_grille','steel',(4.11,3.797,1.13+i*.092),(4.24,.033,.017))
for x in [2.03,2.66,3.30,3.94,4.58,5.22,5.86,6.23]:
    box('service_grille_uprights','steel',(x,3.786,1.50),(.022,.040,.81))
for z in [1.2,1.52,1.85]:box('visible_service_shelves','steel',(4.11,4.11,z),(4.17,.40,.025))
# A narrow dark doorway between the brick and cafe pier is only a visible recess.
box('side_service_door','dark',(1.36,3.96,1.15),(.25,.045,2.3))
box('side_service_door_vision','glass',(1.36,3.93,1.39),(.10,.014,1.33))
# Red circular supports and small diagonal light brackets are characteristic.
for x,y,r in [(-1.15,-.45,.16),(4.42,-1.25,.19),(1.15,3.44,.105)]:
    tube('red_circular_columns','red',(x,y,.04),(x,y,3.62),r,40)
    tube('column_top_collars','red',(x,y,3.60),(x,y,3.65),r+.012,40)
for x,y,dx,dy in [(-1.15,-.45,.65,.38),(4.42,-1.25,.48,-.30)]:
    end=(x+dx,y+dy,3.31)
    tube('red_diagonal_light_brackets','red',(x,y,2.55),end,.037,12)
    box('bracket_light_housing','red',end,(.28,.18,.105),math.atan2(dy,dx))
    box('bracket_light_lens','light',(end[0],end[1],end[2]-.056),(.22,.13,.022),math.atan2(dy,dx))
# Two large elliptical acoustic clouds. No desks or PCs are inferred from the
# page11 capacity statement; this model records the empty corner photographed.
ellipse('left_acoustic_cloud_body','cloud_edge',-2.57,-.28,3.64,1.51,3.62,.18,math.radians(-8))
ellipse('left_cloud_underside','cloud',-2.57,-.28,3.60,1.48,3.608,.016,math.radians(-8))
ellipse('right_acoustic_cloud_body','cloud_edge',3.72,.55,2.41,1.88,3.62,.18,math.radians(12))
ellipse('right_cloud_underside','cloud',3.72,.55,2.38,1.85,3.608,.016,math.radians(12))
# Retain a cut-open rear strip of bare concrete ceiling, leaving cloud forms
# visible in the overview and below when the visitor rotates into the room.
box('rear_concrete_soffit_cutaway','concrete',(0,3.71,4.02),(12.4,1.58,.20))
for x in [-4.5,-1.3,1.7,4.5]:
    box('soffit_panel_seams','stone_joint',(x,3.69,3.913),(.013,1.48,.008))
for x,y in [(-4.8,-.55),(-.15,-.22),(3.1,.55),(4.55,.10)]:
    tube('cloud_recessed_downlight','light',(x,y,3.595),(x,y,3.614),.045,16)

for geometry in batches.values():
    obj=geometry.finish();obj['roomCode']='SAW_DENNING_2014'
    obj['scope']='2014 Denning Learning Cafe photographed corner; estimated dimensions'
    for modifier in list(obj.modifiers):obj.modifiers.remove(modifier)
position=[12.2,-16.0,10.0];target=[0,.7,1.85]
camera=bpy.data.objects.new('SAW_V24_DENNING_camera',bpy.data.cameras.new('SAW_V24_DENNING_camera'))
scene.collection.objects.link(camera);camera.location=position
camera.rotation_euler=(Vector(target)-camera.location).to_track_quat('-Z','Y').to_euler()
camera.data.type='ORTHO';camera.data.ortho_scale=16.9;scene.camera=camera
scene.world=bpy.data.worlds.new('SAW_V24_DENNING_world');scene.world.color=(.82,.84,.85)
scene.render.engine='BLENDER_WORKBENCH';scene.display.shading.light='STUDIO'
scene.display.shading.studiolight_rotate_z=.5;scene.display.shading.color_type='MATERIAL'
scene.display.shading.show_shadows=True;scene.display.shading.show_cavity=True;scene.display.shading.cavity_type='BOTH'
scene.display.shading.background_type='WORLD';scene.view_settings.view_transform='Standard'
scene.render.resolution_x=1600;scene.render.resolution_y=1250;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.render.filepath=str(OUT/'saw-denning.png')
assert fingerprint(originals)==protected
assert set(bpy.data.scenes['00_CAMPUS_COMPLETE'].objects.keys())==campus_names
scope='依据2014年LSE使用指南中明确标注的Denning Learning Café照片建立的第一层咖啡厅建筑角落。仅复原照片可见的红柱、吸声云、黄色电梯门框、玻璃墙、砖墙及售卖卷帘；尺度、相对位置和不可见构造估算，非全厅或2026年现状。'
record={'code':'SAW','roomCode':'SAW_DENNING_2014','roomLabel':collection['roomLabel'],'collection':collection.name,
 'scene':scene.name,'camera':position,'target':target,'cameraName':camera.name,'scope':scope,
 'sources':[{'path':'data/documents/saw_occupants_guide_2014.pdf','url':'https://info.lse.ac.uk/staff/divisions/estates-division/Assets/Documents/SAW/Final-Web-version-of-Occupants-Guide.pdf','pages':[4,11],'supports':'Page4 caption identifies Denning Learning Cafe acoustic clouds; page11 confirms cafe on first floor; capacity text does not locate furniture'},
 {'path':'result/blender/stage24/saw-cafe-reference.png','supports':'Rendered original page4 photograph, inspected before modelling'}],
 'addedObjects':[{'name':g.name,'collection':collection.name} for g in batches.values()],
 'changes':['新增独立2014咖啡厅建筑角落，原SAW楼梯与所有既有对象保留','照片可见的红色钢柱、两片椭圆吸声云、黄色电梯门框、砖墙玻璃、售卖卷帘和混合地面'],
 'limitations':['仅单张历史照片，没有尺寸平面；尺度、墙体夹角和位置估算','不按文字所载150座或24台PC推造家具','现有空间不在校园坐标中，不建立与楼梯的猜测连接','顶板只保留后侧剖开片段；不构造背后厨房或电梯井'],
 'roomStudy':{'id':'saw-denning','label':'Denning咖啡厅，2014局部','camera':position,'target':target,'scope':scope,'collection':collection.name}}
manifest={'stage':24,'baseline':'result/blender/LSE_campus_detailed_v23.blend','buildings':[record],
 'qa':{'originalFingerprintBefore':protected,'originalFingerprintAfter':fingerprint(originals),'campusObjectsUnchanged':True,
       'newMeshObjects':len(batches),'furnitureInferredFromCapacity':False,'render':'result/blender/stage24/saw/saw-denning.png'}}
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'refined.blend'))
(OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
bpy.ops.render.render(write_still=True)
print('SAW_DENNING_DONE',len(batches),flush=True)
