"""Build a separate CKK.1.04 archive room study in Blender's Text Editor.

The official plan contains 80 chair symbols. Dimensions and furniture details
are estimated; the archive does not establish current occupancy or floor levels.
Existing campus objects and the CKK atrium are preserved byte-for-byte by a
geometry/transform/material-name fingerprint.
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
OUT = ROOT / 'result/blender/stage23/ckk'
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(Path(__file__).resolve().parent))
from facade_geometry import Geometry, materials
bpy.ops.wm.open_mainfile(filepath=str(ROOT / 'result/blender/LSE_campus_detailed_v22.blend'))
originals = list(bpy.data.objects)
campus_names = set(bpy.data.scenes['00_CAMPUS_COMPLETE'].objects.keys())

def fingerprint(objects):
    digest = hashlib.sha256()
    for obj in sorted(objects, key=lambda item: item.name):
        digest.update(obj.name.encode())
        digest.update(array.array('f', [v for row in obj.matrix_world for v in row]).tobytes())
        if obj.type == 'MESH':
            vertices = array.array('f', [0]) * (3 * len(obj.data.vertices))
            obj.data.vertices.foreach_get('co', vertices)
            digest.update(vertices.tobytes())
            digest.update('|'.join(m.name if m else '' for m in obj.data.materials).encode())
    return digest.hexdigest()

original_hash = fingerprint(originals)
assert not bpy.data.collections.get('CKK_TEACHING_ROOM_study')
collection = bpy.data.collections.new('CKK_TEACHING_ROOM_study')
collection['roomSample'] = True
collection['roomLabel'] = 'CKK.1.04排式教室，80座平面历史样本'
scene = bpy.data.scenes.new('ROOM23_CKK_TEACHING')
scene.collection.children.link(collection)
bpy.context.window.scene = scene
PREFIX = 'CKK_V23_TEACH_'
PALETTE = {'plaster': (.79,.78,.73), 'white': (.90,.90,.86),
           'carpet': (.31,.32,.29), 'red': (.64,.025,.035),
           'black': (.045,.048,.048), 'steel': (.42,.44,.43),
           'board': (.86,.88,.84), 'projection': (.60,.67,.81),
           'window': (.60,.74,.79), 'blind': (.43,.49,.54),
           'light': (.94,.94,.84), 'edge': (.52,.52,.48)}
materials.clear()
for name, color in PALETTE.items():
    mat = bpy.data.materials.new(PREFIX + name)
    mat.diffuse_color = (*color, 1)
    mat.use_nodes = True
    node = mat.node_tree.nodes['Principled BSDF']
    node.inputs['Base Color'].default_value = (*color, 1)
    node.inputs['Roughness'].default_value = .65
    if name == 'steel': node.inputs['Metallic'].default_value = .65
    materials[name] = mat
batches = {}
def group(family, material):
    key = (family, material)
    if key not in batches:
        geo = Geometry('CKK', family, material)
        geo.collection = collection
        geo.name = PREFIX + family + '_' + material
        batches[key] = geo
    return batches[key]
def box(family, material, position, size):
    group(family, material).box(position, size)
def tube(family, material, a, b, radius=.018):
    a,b = Vector(a), Vector(b)
    direction = (b-a).normalized()
    u = direction.cross(Vector((0,0,1)))
    if u.length < .05: u = direction.cross(Vector((0,1,0)))
    u.normalize(); v = direction.cross(u); n = 8
    vertices = [p+radius*(u*math.cos(i*math.tau/n)+v*math.sin(i*math.tau/n)) for p in [a,b] for i in range(n)]
    group(family,material).add(vertices,[tuple(reversed(range(n))),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)])

def plan_point(px,py):
    # Plan front is left. Its top edge is the photographed right-hand window wall.
    return ((225-py)*.024, (px-290)*.024)

# Full front and window-side walls, low left/rear edges, open roof.
box('floor','carpet',(0,0,-.09),(8.4,13.25,.18))
box('front_wall','plaster',(0,-6.57,1.95),(8.4,.18,3.9))
box('left_cutaway_edge','edge',(-4.15,0,.10),(.12,13.1,.20))
box('rear_cutaway_edge','edge',(0,6.56,.10),(8.4,.12,.20))
# Preserve plan window bays; only the near-front opening's arch is visible in the photo.
window_bays = [(49,115,'arched'),(170,288,'rectangular'),(343,403,'rectangular')]
wall_segments = [(-6.5,(49-290)*.024),((115-290)*.024,(170-290)*.024),((288-290)*.024,(343-290)*.024),((403-290)*.024,6.5)]
for start,end in wall_segments:
    box('window_wall_piers','plaster',(4.15,(start+end)/2,1.95),(.20,end-start,3.9))
for left,right,shape in window_bays:
    start,end = (left-290)*.024,(right-290)*.024
    centre,half = (start+end)/2,(end-start)/2
    sill,top = .88,3.35
    box('window_low_wall','plaster',(4.15,centre,sill/2),(.20,end-start,sill))
    box('window_sill','white',(3.99,centre,sill),(.40,end-start+.08,.10))
    if shape == 'arched':
        spring = top-half
        # Glazed arch polygon, actual opening between modeled spandrels.
        polygon = [(start,sill),(end,sill),(end,spring)] + [(centre+half*math.cos(i*math.pi/24),spring+half*math.sin(i*math.pi/24)) for i in range(1,25)]
        group('arched_window_glass','window').add([(4.15,y,z) for y,z in polygon],[tuple(range(len(polygon)))])
        for i in range(24):
            a,b = i*math.pi/24,(i+1)*math.pi/24
            y1,y2 = centre+half*math.cos(a),centre+half*math.cos(b)
            z1,z2 = spring+half*math.sin(a),spring+half*math.sin(b)
            group('arch_spandrel','plaster').add([(4.04,y1,z1),(4.04,y2,z2),(4.04,y2,3.9),(4.04,y1,3.9)],[(0,1,2,3)])
            tube('arch_frame','steel',(4.005,y1,z1),(4.005,y2,z2),.035)
        for y in [start,end]: tube('arch_jamb','steel',(4.005,y,sill),(4.005,y,spring),.035)
        tube('arch_transom','steel',(4.005,start,spring),(4.005,end,spring),.025)
    else:
        box('other_plan_window_glass','window',(4.15,centre,2.08),(.04,end-start,2.4))
        box('other_window_head','plaster',(4.15,centre,3.58),(.20,end-start,.64))
        for y in [start,end]:box('other_window_jamb','steel',(4.02,y,2.08),(.07,.055,2.40))
    tube('window_mullion','steel',(4.005,centre,sill),(4.005,centre,top-.08),.024)
# Projection screen and flanking boards as photographed, no invented projected content.
box('projection_frame','black',(0,-6.43,2.52),(2.52,.09,1.88))
box('projection_surface','projection',(0,-6.373,2.52),(2.36,.025,1.72))
for x,width in [(-2.05,1.42),(2.64,2.13)]:
    box('whiteboard_frame','steel',(x,-6.42,2.13),(width,.055,1.62))
    box('whiteboard_surface','board',(x,-6.382,2.13),(width-.09,.025,1.53))
    box('whiteboard_tray','steel',(x,-6.32,1.34),(width-.04,.10,.04))
# Front entrance is shown in the plan bottom-left; shallow dark leaf on front wall.
box('entrance_leaf','edge',(-3.5,-6.435,1.03),(1.0,.045,2.06))
for x in [-4.04,-2.96]:box('entrance_jamb','white',(x,-6.40,1.06),(.065,.08,2.12))
tube('entrance_pull','steel',(-3.10,-6.34,.86),(-3.10,-6.34,1.18),.017)

seat_count = 0
black_count = 0
def chair(x,y,black=False):
    global seat_count,black_count
    seat_count += 1
    black_count += int(black)
    material = 'black' if black else 'red'
    box('chair_seats',material,(x,y,.46),(.47,.45,.065))
    # Back curvature is approximated by three shallow planar strips.
    for dx,width,back in [(-.155,.15,.22),(0,.17,.24),(.155,.15,.22)]:
        box('chair_backs',material,(x+dx,y+back,.76),(width,.052,.48))
    for dx in [-.21,.21]:
        for dy in [-.18,.18]:tube('chair_legs','steel',(x+dx,y+dy,.03),(x+dx,y+dy,.43),.016)
        tube('chair_back_uprights','steel',(x+dx,y+.18,.40),(x+dx,y+.23,.94),.015)

def desk(x,y,width):
    box('long_table_tops','white',(x,y,.755),(width,.50,.055))
    box('table_underframe','steel',(x,y,.69),(width-.08,.08,.07))
    for dx in [-width/2+.12,width/2-.12]:
        for dy in [-.18,.18]:tube('table_legs','steel',(x+dx,y+dy,.035),(x+dx,y+dy,.725),.020)

# Each list is counted from the official chair symbols, not inferred capacity.
rows = [(135,8),(187,10),(237,10),(287,10),(338,10),(386,10),(437,6),(487,8),(536,8)]
furniture=[]
for row,(px,count) in enumerate(rows):
    y=(px-290)*.024
    seat_pixels=[77+29.4*i for i in range(count)]
    xs=[plan_point(px,py)[0] for py in seat_pixels]
    # Plan desks are continuous banks with a two-seat module rhythm.
    for first in range(0,count,2):
        positions=xs[first:first+2]
        desk(sum(positions)/len(positions),y-.29,.706*len(positions))
    for col,x in enumerate(xs):chair(x,y+.21,black=(row,col) in {(0,2),(0,6),(1,4),(2,1),(3,5),(4,3),(5,0),(6,4),(7,2),(8,6)})
    furniture.append({'rowFromFront':row+1,'planRowPixelX':px,'capacityInModel':count,'planChairPixelY':seat_pixels})
assert seat_count == 80
# AV console near the window at the front, visible in the room photograph.
box('instructor_desk','white',(2.55,-5.65,.77),(1.70,.72,.065))
for x in [1.83,3.27]:box('instructor_desk_sides','edge',(x,-5.65,.37),(.08,.65,.74))
box('av_monitor','black',(2.75,-5.67,1.09),(.52,.065,.33))
box('av_monitor_base','steel',(2.75,-5.67,.84),(.24,.20,.025))
box('av_rack','edge',(1.78,-5.66,.43),(.35,.56,.70))
for z in [.22,.34,.46,.58]:box('av_rack_panels','black',(1.78,-5.365,z),(.28,.022,.085))
# Keep the ceiling open: partial front beam, projector and representative luminaires.
box('front_ceiling_beam','plaster',(0,-5.95,3.69),(8.1,.35,.35))
box('ceiling_projector','edge',(0,-4.80,3.38),(.52,.43,.19))
box('projector_lens','black',(0,-5.025,3.38),(.12,.035,.095))
tube('projector_hanger','black',(0,-4.80,3.48),(0,-4.80,3.94),.025)
for x in [-2.7,2.7]:
    box('suspended_light_housing','white',(x,-4.15,3.52),(.15,2.6,.10))
    box('suspended_light_diffuser','light',(x,-4.15,3.46),(.13,2.56,.023))
    for y in [-5.1,-3.2]:tube('light_hangers','steel',(x,y,3.57),(x,y,3.88),.008)

for geometry in batches.values():
    obj=geometry.finish()
    obj['roomCode']='CKK.1.04'
    obj['scope']='Historical room sample; 80 counted plan chair symbols; dimensions estimated'
    for modifier in list(obj.modifiers):obj.modifiers.remove(modifier)
position=[-14.5,18.5,14.2];target=[0,0,.8]
camera=bpy.data.objects.new(PREFIX+'camera',bpy.data.cameras.new(PREFIX+'camera'))
scene.collection.objects.link(camera);camera.location=position
camera.rotation_euler=(Vector(target)-camera.location).to_track_quat('-Z','Y').to_euler()
camera.data.type='ORTHO';camera.data.ortho_scale=19.8;scene.camera=camera
scene.world=bpy.data.worlds.new(PREFIX+'world');scene.world.color=(.83,.84,.85)
scene.render.engine='BLENDER_WORKBENCH'
scene.display.shading.light='STUDIO';scene.display.shading.studiolight_rotate_z=.6
scene.display.shading.color_type='MATERIAL';scene.display.shading.show_shadows=True
scene.display.shading.show_cavity=True;scene.display.shading.cavity_type='BOTH'
scene.display.shading.background_type='WORLD'
scene.render.resolution_x=1500;scene.render.resolution_y=1250;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='Standard'
scene.render.filepath=str(OUT/'ckk-1-04.png')
assert fingerprint(originals)==original_hash
assert set(bpy.data.scenes['00_CAMPUS_COMPLETE'].objects.keys())==campus_names
sources=[{'path':'data/collections/interiors/images/526ca76baee9_CKK.1.04.GIF','url':'https://www.lse.ac.uk/assets/roomInformation/images/CKK.1.04.GIF','supports':'CKK.1.04 plan, nine rows with 8+10+10+10+10+10+6+8+8 chair symbols, room/window/entrance layout'},
{'path':'data/collections/interiors/images/cdcfdd8f28bc_CKK.1.04.jpg','url':'https://www.lse.ac.uk/assets/roomInformation/images/photos/CKK.1.04.jpg','supports':'Matching room photo, white desks, red/black chairs, front projection/boards/AV, right front arched window'}]
scope='依据LSE官方CKK.1.04平面与照片制作的独立排式教室历史样本；逐排共80个座椅符号。尺寸、窗高和红黑椅位置估算，未确认高差按平层表达，不代表2026年现状或与中庭的实测连接。'
record={'code':'CKK','roomCode':'CKK.1.04','roomLabel':collection['roomLabel'],'collection':collection.name,'scene':scene.name,'camera':position,'target':target,'cameraName':camera.name,'scope':scope,'sources':sources,
'addedObjects':[{'name':g.name,'collection':collection.name} for g in batches.values()],
'changes':['新增独立80座排式教室样本，原中庭未改动','按平面保留9排不同长度桌椅，按照片补前投影、白板、AV和近前弧窗'],
'limitations':['尺寸与层高无标注，采用估算比例；模型不是实测复原','80为平面逐椅计数，不另行声称现行官方容量；黑椅10个仅是照片混色的示意分布','未见可确认的重复阶梯或标高，地面按平层示意','仅近前弧顶窗形状可由照片确认；其他平面窗位以简化矩形窗表达，窗高估算','门开启方向、墙厚、家具细部与AV尺寸简化；屋顶及两侧剖开，不补无依据走廊','图片制作日期不明，不表示2026年教室布置'],
'seatCount':seat_count,'seatCountBasis':'Counted 80 chair symbols in official plan: 8+10+10+10+10+10+6+8+8','blackChairCountEstimated':black_count,'furnitureGroups':furniture,
'roomStudy':{'id':'ckk-104','label':'CKK.1.04排式教室','collection':collection.name,'camera':position,'target':target,'scope':scope}}
manifest={'stage':23,'baseline':'result/blender/LSE_campus_detailed_v22.blend','buildings':[record],'qa':{'originalFingerprintBefore':original_hash,'originalFingerprintAfter':fingerprint(originals),'campusObjectsUnchanged':True,'newMeshObjects':len(batches),'render':'result/blender/stage23/ckk/ckk-1-04.png'}}
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'refined.blend'))
(OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
bpy.ops.render.render(write_still=True)
print('CKK_TEACHING_DONE',seat_count,len(batches),flush=True)
