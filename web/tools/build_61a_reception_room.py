"""Build the photographed 2021 main reception as a separate historical sample.

Open this script in Blender's Text Editor. It preserves edition23 meshes and
never connects the estimated local room to the uncalibrated campus envelope.
No tenant office space-plan options or future LSE designs are used.
"""
from pathlib import Path
import array
import hashlib
import json
import math
import sys
import bpy
from mathutils import Vector
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'result/blender/stage24/61a'
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
            vertices=array.array('f',[0])*(3*len(obj.data.vertices))
            obj.data.vertices.foreach_get('co',vertices);digest.update(vertices.tobytes())
            digest.update('|'.join(m.name if m else '' for m in obj.data.materials).encode())
    return digest.hexdigest()
original_hash=fingerprint(originals)
name='61A_PUBLIC_INTERIOR_study'
collection=bpy.data.collections.get(name)
if collection:
    assert not collection.all_objects, 'Existing interior is nonempty; do not replace it'
    bpy.data.collections.remove(collection)
collection=bpy.data.collections.new(name)
collection['roomSample']=True
collection['roomLabel']='61A 2021历史接待厅'
scene=bpy.data.scenes.new('ROOM24_61A_RECEPTION')
scene.collection.children.link(collection);bpy.context.window.scene=scene
PREFIX='61A_V24_RECEPTION_'
PALETTE={'marble':(.84,.83,.77),'vein':(.62,.61,.55),'floor':(.58,.58,.54),
 'grout':(.45,.45,.42),'wood':(.31,.17,.078),'wood_dark':(.18,.095,.04),
 'white':(.92,.91,.85),'black':(.035,.04,.035),'leather':(.075,.077,.061),
 'oak':(.47,.32,.16),'steel':(.49,.51,.49),'glass':(.50,.67,.66),
 'rug':(.49,.47,.41),'green':(.15,.28,.08),'soil':(.085,.065,.04),'light':(.98,.96,.88)}
materials.clear()
for key,color in PALETTE.items():
    mat=bpy.data.materials.new(PREFIX+key);mat.diffuse_color=(*color,1);mat.use_nodes=True
    node=mat.node_tree.nodes['Principled BSDF'];node.inputs['Base Color'].default_value=(*color,1)
    node.inputs['Roughness'].default_value=.60
    if key=='steel':node.inputs['Metallic'].default_value=.7
    if key=='light':
        node.inputs['Emission Color'].default_value=(*color,1);node.inputs['Emission Strength'].default_value=.4
    materials[key]=mat
batches={}
def group(family,material):
    key=(family,material)
    if key not in batches:
        geo=Geometry('61A',family,material);geo.collection=collection
        geo.name=PREFIX+family+'_'+material;batches[key]=geo
    return batches[key]
def box(family,material,p,size,angle=0):group(family,material).box(p,size,angle)
def tube(family,material,a,b,r=.025):
    a,b=Vector(a),Vector(b);axis=(b-a).normalized();u=axis.cross(Vector((0,0,1)))
    if u.length<.05:u=axis.cross(Vector((0,1,0)))
    u.normalize();v=axis.cross(u);n=10
    vertices=[p+r*(u*math.cos(i*math.tau/n)+v*math.sin(i*math.tau/n)) for p in [a,b] for i in range(n)]
    group(family,material).add(vertices,[tuple(reversed(range(n))),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)])
def cylinder(family,material,x,y,z,r,height):tube(family,material,(x,y,z),(x,y,z+height),r)

# A cropped photographed room volume, not a complete ground-floor plan.
box('floor','floor',(0,0,-.10),(12.4,9.6,.20))
for x in range(-6,7):box('floor_joint','grout',(x,0,.003),(.012,9.55,.006))
for y in range(-4,5):box('floor_joint','grout',(0,y,.003),(12.35,.012,.006))
box('waiting_wall','wood',(-2.85,-4.72,1.58),(6.25,.16,3.16))
for x in [-5.85,-4.85,-3.85,-2.85,-1.85,-.85,.15]:
    box('wood_panel_joint','wood_dark',(x,-4.627,1.58),(.012,.012,3.10))
box('upper_waiting_wall','marble',(-2.85,-4.72,4.36),(6.25,.20,2.4))
box('right_clad_wall','marble',(6.10,-.2,2.80),(.18,9.05,5.6))
box('rear_access_wall','marble',(3.35,-4.72,2.8),(5.55,.16,5.6))
box('cutaway_floor_edge','grout',(-6.12,0,.08),(.12,9.6,.16))
box('cutaway_front_edge','grout',(0,4.72,.08),(12.35,.12,.16))
# Main square stone-clad pillar and low horizontal seat/plinth from all three views.
box('central_pillar','marble',(-2.80,-2.20,1.70),(.64,.72,3.4))
box('pillar_low_seat','marble',(-2.80,-1.99,.31),(1.20,1.27,.18))
box('waiting_ceiling_soffit','marble',(-2.80,-3.43,3.31),(6.35,2.65,.20))
# Sparse vein strips suggest photographed veined stone; no source image textures.
for z in [.8,1.75,2.65]:
    tube('pillar_stone_veins','vein',(-3.115,-1.832,z),(-2.485,-1.832,z+.43),.009)
for x in [-5.3,-4.0,-1.4,-.2]:
    tube('upper_stone_veins','vein',(x,-4.608,3.40),(x+.65,-4.608,4.08),.012)
    tube('upper_stone_veins','vein',(x+.65,-4.608,4.08),(x+.94,-4.608,5.38),.009)
for y in [-3.7,-2.2,-.7,.8,2.3]:
    tube('side_stone_veins','vein',(5.995,y,.5),(5.995,y+.66,2.15),.013)
    tube('side_stone_veins','vein',(5.995,y+.66,2.15),(5.995,y+.92,4.9),.010)
# Photographed luminous box over access gates, with timber slats below.
box('suspended_luminous_front','light',(2.68,-1.95,4.26),(4.12,.11,2.02))
box('suspended_box_side','white',(.57,-3.05,4.26),(.11,2.24,2.02))
box('suspended_box_underlay','wood_dark',(2.68,-3.02,3.24),(4.20,2.30,.10))
for x in [.57,1.95,3.33,4.79]:box('luminous_panel_mullions','wood_dark',(x,-1.875,4.26),(.045,.045,2.12))
for i in range(22):box('timber_box_underside','wood',(.68+i*.184,-3.02,3.18),(.11,2.24,.10))
# Gates are a cropped simplified bank; exact mechanism and count are not a survey.
for i,x in enumerate([.92,2.00,3.08,4.16]):
    box('access_gate_pedestal','steel',(x,-1.53,.52),(.26,.84,1.04))
    box('access_reader','black',(x,-1.84,1.055),(.17,.22,.028))
    box('gate_vertical_seam','black',(x-.137,-1.43,.56),(.012,.25,.36))
    if i<3:box('gate_glass_leaf','glass',(x+.54,-1.50,.66),(.72,.034,.68))
# Glass doors at the visible end of the access opening, no invented corridor.
for x in [2.16,3.02]:
    box('inner_glazed_door','glass',(x,-4.59,1.25),(.82,.045,2.50))
    for dx in [-.43,.43]:box('door_upright','steel',(x+dx,-4.55,1.26),(.04,.07,2.54))
    tube('door_pull','steel',(x+.26,-4.49,.89),(x+.26,-4.49,1.36),.018)
box('door_top','steel',(2.59,-4.55,2.52),(1.76,.07,.05))
# Reception desk visible in the oblique photograph, with restrained equipment.
box('reception_counter','white',(5.16,-3.46,.53),(1.44,.76,1.06))
box('reception_counter_top','black',(5.16,-3.46,1.09),(1.55,.86,.09))
box('reception_counter_plinth','black',(5.16,-3.46,.10),(1.38,.70,.20))
box('reception_monitor','black',(5.40,-3.54,1.32),(.43,.045,.30))
# Waiting-zone rug, dark sofa, black-shell timber chairs and occasional tables.
box('waiting_rug','rug',(-3.30,-3.10,.018),(5.35,2.87,.032))
box('sofa_base','leather',(-1.28,-4.12,.35),(2.16,.72,.30))
box('sofa_back','leather',(-1.28,-4.42,.76),(2.16,.16,.64))
for x in [-2.25,-.31]:box('sofa_arm','leather',(x,-4.10,.59),(.20,.77,.48))
for x in [-1.83,-1.28,-.73]:box('sofa_seat_cushion','leather',(x,-4.05,.55),(.52,.58,.12))
for x in [-2.1,-.48]:tube('sofa_feet','steel',(x,-4.15,.035),(x,-4.15,.21),.025)
def chair(x,y,angle):
    c,s=math.cos(angle),math.sin(angle)
    def p(dx,dy,z):return(x+c*dx-s*dy,y+s*dx+c*dy,z)
    box('lounge_chair_seat','leather',p(0,0,.48),(.65,.59,.09),angle)
    box('lounge_chair_back','leather',p(0,.26,.78),(.63,.085,.50),angle)
    for dx in [-.30,.30]:
        tube('chair_wood_front_legs','oak',p(dx,-.31,.04),p(dx,-.19,.47),.031)
        tube('chair_wood_rear_legs','oak',p(dx,.35,.04),p(dx,.18,.51),.031)
        tube('chair_wood_arm','oak',p(dx,-.22,.62),p(dx,.30,.63),.028)
for x,y,a in [(-5.14,-3.84,.15),(-3.98,-3.83,-.18),(-1.96,-2.35,math.pi+.3),(-.55,-2.27,math.pi-.35)]:chair(x,y,a)
for x,y,r in [(-4.53,-3.12,.48),(-1.30,-3.19,.58)]:
    cylinder('occasional_table_top','white',x,y,.43,r,.045)
    for dx,dy in [(-.28,-.23),(.28,-.23),(.28,.23),(-.28,.23)]:tube('table_legs','black',(x+dx,y+dy,.04),(x+dx,y+dy,.42),.018)
# Potted plants in observed waiting and gate zones; stylised leaf clusters.
def plant(x,y,height,r):
    cylinder('plant_pot','black',x,y,.025,r,.48)
    cylinder('plant_soil','soil',x,y,.50,r*.91,.025)
    for i in range(9):
        a=i*math.tau/9;z=.62+height*(.58+.28*math.sin(i*2.2)**2)
        tip=(x+math.cos(a)*r*1.45,y+math.sin(a)*r*1.45,z)
        tube('plant_stems','green',(x,y,.5),tip,.018)
        for dz in [-.10,.06]:
            p=Vector((tip[0],tip[1],tip[2]+dz));d=Vector((math.cos(a)*.22,math.sin(a)*.22,.10));u=Vector((-math.sin(a)*.075,math.cos(a)*.075,0))
            group('plant_leaves','green').add([p-d,p+u,p+d,p-u],[(0,1,2,3)])
plant(.05,-2.88,1.90,.32)
plant(-5.37,-1.52,1.18,.30)
# Building identity uses modeled typography, not copyrighted source-photo textures.
text_objects=[]
def text_label(body,p,size):
    curve=bpy.data.curves.new(PREFIX+'identity','FONT');curve.body=body;curve.align_x='CENTER';curve.size=size;curve.extrude=.001
    obj=bpy.data.objects.new(PREFIX+'identity',curve);collection.objects.link(obj);obj.location=p
    obj.rotation_euler=(math.pi/2,0,math.pi);curve.materials.append(materials['black'])
    bpy.context.view_layer.objects.active=obj;obj.select_set(True)
    bpy.ops.object.convert(target='MESH');obj.select_set(False);text_objects.append(obj)
for x in [-4.40,-1.31]:
    box('lit_wall_display_frame','steel',(x,-4.585,2.22),(.72,.065,1.13))
    box('lit_wall_display','light',(x,-4.54,2.22),(.65,.025,1.06))
    text_label('61\nALDWYCH',(x,-4.514,2.18),.115)
text_label('61\nALDWYCH',(4.90,-4.616,2.44),.23)
for x in [-5.0,-3.5,-1.2]:cylinder('soffit_downlights','light',x,-3.40,3.198,.07,.02)
for geometry in batches.values():
    obj=geometry.finish();obj['scope']='2021 historical reception photo study; estimated local geometry';obj['roomCode']='61A_RECEPTION_2021'
    for modifier in list(obj.modifiers):obj.modifiers.remove(modifier)
position=[-14.8,18.5,12.1];target=[0,-.5,1.80]
camera=bpy.data.objects.new(PREFIX+'camera',bpy.data.cameras.new(PREFIX+'camera'))
scene.collection.objects.link(camera);camera.location=position
camera.rotation_euler=(Vector(target)-camera.location).to_track_quat('-Z','Y').to_euler()
camera.data.type='ORTHO';camera.data.ortho_scale=19.6;scene.camera=camera
scene.world=bpy.data.worlds.new(PREFIX+'world');scene.world.color=(.84,.85,.86)
scene.render.engine='BLENDER_WORKBENCH';scene.display.shading.light='STUDIO'
scene.display.shading.studiolight_rotate_z=.4;scene.display.shading.color_type='MATERIAL'
scene.display.shading.show_shadows=True;scene.display.shading.show_cavity=True
scene.display.shading.cavity_type='BOTH';scene.display.shading.background_type='WORLD'
scene.render.resolution_x=1500;scene.render.resolution_y=1250;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='Standard'
scene.render.filepath=str(OUT/'61a-reception-2021.png')
assert fingerprint(originals)==original_hash
assert set(bpy.data.scenes['00_CAMPUS_COMPLETE'].objects.keys())==campus_names
scope='依据2021年5月61 Aldwych租赁册页的主接待厅实景照片制作的独立历史样本。仅表达照片可见接待、候客和闸机局部；尺寸估算，不代表当前LSE内部，不与尚未校准的校园外壳连接。'
source={'path':'data/documents/61aldwych_brochure_2021.pdf','pdfPages':[2,8,11],'printedPages':[4,16],'date':'May 2021 brochure; photo creation dates unreported','supports':'Three overlapping built-reception photographs;61 ALDWYCH signage and main entrance description','url':None}
record={'code':'61A','roomCode':'61A_RECEPTION_2021','roomLabel':collection['roomLabel'],'collection':collection.name,'scene':scene.name,'camera':position,'target':target,'cameraName':camera.name,'scope':scope,'sources':[source],
'addedObjects':[{'name':o.name,'collection':collection.name} for o in collection.objects],
'changes':['新增独立2021历史主接待厅照片样本','石材柱与低座台、木候客墙和61标牌、座椅/矮桌、悬挂灯箱/木底、闸机与可见接待台'],
'limitations':['无接待厅平面或尺寸；几何、家具尺度与相互距离为照片比例估算','闸机仅作可见样式的简化示意，不宣称精确数量或机构','石纹和植物为程序化示意，不复制照片纹理','只保留照片可见局部，不延伸完整底层、办公布置或通往电梯的未知路线','2021册页日期不等于照片拍摄日期；不用于当前LSE内部或未来改造设计'],
'roomStudy':{'id':'61a-reception','label':'2021历史接待厅','collection':collection.name,'camera':position,'target':target,'scope':scope}}
manifest={'stage':24,'baseline':'result/blender/LSE_campus_detailed_v23.blend','buildings':[record],
'qa':{'originalFingerprintBefore':original_hash,'originalFingerprintAfter':fingerprint(originals),'campusObjectsUnchanged':True,'newMeshObjects':len(collection.objects),'render':'result/blender/stage24/61a/61a-reception-2021.png'}}
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'refined.blend'))
(OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
bpy.ops.render.render(write_still=True)
print('61A_RECEPTION_DONE',len(collection.objects),flush=True)
