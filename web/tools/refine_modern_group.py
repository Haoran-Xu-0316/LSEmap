"""Review ten modern-group studies and add three source-supported details.

Open in Blender's Text Editor and run. Existing objects and materials are kept.
All new mesh families are batched; source photographs are never embedded.
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
OUT = ROOT / 'result/blender/stage19/modern'
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(Path(__file__).resolve().parent))
from facade_geometry import Geometry, Facade, materials

BASE = ROOT / 'result/blender/LSE_campus_detailed_v18.blend'
bpy.ops.wm.open_mainfile(filepath=str(BASE))
bpy.context.window.scene = bpy.data.scenes['00_CAMPUS_COMPLETE']
bpy.context.view_layer.update()
originals = list(bpy.data.objects)

def fingerprint(objects):
    digest = hashlib.sha256()
    for obj in sorted(objects, key=lambda obj: obj.name):
        digest.update(obj.name.encode())
        digest.update(array.array('f', [v for row in obj.matrix_world for v in row]).tobytes())
        if obj.type == 'MESH':
            coords = array.array('f', [0]) * (len(obj.data.vertices) * 3)
            obj.data.vertices.foreach_get('co', coords)
            digest.update(coords.tobytes())
            digest.update(array.array('I', [v for p in obj.data.polygons for v in p.vertices]).tobytes())
    return digest.hexdigest()

before = fingerprint(originals)
materials.clear()
for name, color, metallic, emission in [
    ('dark', (.027,.030,.026), .5, 0),
    ('brass', (.48,.29,.07), .7, 0),
    ('bulb', (1,.55,.12), .0, 3),
    ('display', (.69,.71,.65), .0, .25),
    ('red', (.55,.017,.025), .0, 0),
    ('silver', (.48,.50,.47), .7, 0),
]:
    mat = bpy.data.materials.new('V19_MOD_'+name)
    mat.use_nodes = True
    mat.diffuse_color = (*color, 1)
    shader = mat.node_tree.nodes['Principled BSDF']
    shader.inputs['Base Color'].default_value = mat.diffuse_color
    shader.inputs['Metallic'].default_value = metallic
    shader.inputs['Roughness'].default_value = .38
    if emission:
        shader.inputs['Emission Color'].default_value = (*color, 1)
        shader.inputs['Emission Strength'].default_value = emission
    materials[name] = mat

class Detail(Geometry):
    def __init__(self, code, name, material, inside=False):
        super().__init__(code, name, material)
        self.name = code+'_V19_MOD_'+name
        if inside:
            self.collection = bpy.data.collections[code+'_PUBLIC_INTERIOR_study']
    def tube(self, a, b, radius, sides=10):
        a, b = Vector(a), Vector(b)
        axis = (b-a).normalized()
        ref = Vector((0,0,1)) if abs(axis.z)<.95 else Vector((1,0,0))
        u = axis.cross(ref).normalized()
        v = axis.cross(u).normalized()
        vertices = [p+radius*(u*math.cos(i*2*math.pi/sides)+v*math.sin(i*2*math.pi/sides)) for p in [a,b] for i in range(sides)]
        faces = [tuple(range(sides-1,-1,-1)),tuple(range(sides,2*sides))]
        faces += [(i,(i+1)%sides,(i+1)%sides+sides,i+sides) for i in range(sides)]
        self.add(vertices, faces)

added = {}
def finish(code, group, source):
    obj = group.finish()
    obj.modifiers.clear()
    obj['source_reference'] = source
    obj['scope'] = 'Visible component type follows archive photo; dimensions and exact count estimated.'
    added.setdefault(code, []).append(obj)
    return obj

profiles = json.loads((ROOT/'result/blender/stage05/infill-geometry.json').read_text())
facades = {}
for code in ['PEA','PEL']:
    profile = next(p for p in profiles if p['code']==code)
    facades[code] = Facade(profile, next(w for w in profile['walls'] if w['front']), {})

# PEA: the reference explicitly shows hanging warm bulbs beneath the canopy,
# with a dense central cluster and a long single perimeter row.
f = facades['PEA']
source_pea = 'data/collections/campus_photos_round3/images/PEA/PEA_sadlers_exterior_01.jpg'
bases = Detail('PEA','canopy_lamp_sockets','brass')
bulbs = Detail('PEA','canopy_warm_lamps','bulb')
for row in range(3):
    start, end = (.22, f.length-.22) if row==0 else (f.length*.30, f.length*.70)
    count = max(2, round((end-start)/.30))
    for j in range(count):
        x = start+(end-start)*j/(count-1)
        depth = 1.61-row*.43
        bases.tube(f.point(x,3.31,depth),f.point(x,3.22,depth),.047)
        bulbs.tube(f.point(x,3.22,depth),f.point(x,3.12,depth),.040)
for group in [bases, bulbs]: finish('PEA',group,source_pea)
# The two existing poster cases get recessed, unbranded diffuser faces and frames.
# No copyrighted posters or invented current shows are inserted.
frames = Detail('PEA','poster_case_rebates','silver')
diffusers = Detail('PEA','poster_case_blank_diffusers','display')
for side in [-1,1]:
    x = f.length/2+side*(min(2.1,f.length*.45)/2+1.0)
    diffusers.box(f.point(x,1.75,.305),(.79,.025,1.52),f.angle)
    for dx in [-.425,.425]: frames.box(f.point(x+dx,1.75,.322),(.03,.025,1.59),f.angle)
    for z in [.96,2.54]: frames.box(f.point(x,z,.322),(.88,.025,.03),f.angle)
for group in [frames,diffusers]: finish('PEA',group,source_pea)

# PEL: a distinct red vertical sign stands immediately beside its yellow portal.
f = facades['PEL']
source_pel = 'data/collections/tower_photos_round4/images/PEL/realm_p67_5.jpg'
marker = Detail('PEL','entrance_red_wayfinding_panel','red')
marker.box(f.point(f.length/2+1.91,1.58,.32),(.43,.16,2.96),f.angle)
finish('PEL',marker,source_pel)
# Its small dark mounting back plate is separate from the red face.
mount = Detail('PEL','wayfinding_mounting_plate','dark')
mount.box(f.point(f.length/2+1.91,1.58,.21),(.47,.065,3.0),f.angle)
finish('PEL',mount,source_pel)

# SAW: archive photo shows round dark wall-mounted rails on both sides of the
# concrete stair. Use the existing stair axis and rise; no floor plan changes.
source_saw = 'data/建筑图片/SAW_Saw Swee Hock Student Centre/01_建筑实拍/architecture_round5_SAW_saw_909_07.jpg'
center = json.loads((ROOT/'result/blender/stage02/detail_geometry.json').read_text())['saw_center']
angle = math.radians(68)
def stair_point(radius, t, z):
    x,y = 1+radius*math.cos(t),-4+radius*math.sin(t)
    return (center[0]+math.cos(angle)*x-math.sin(angle)*y,center[1]+math.sin(angle)*x+math.cos(angle)*y,z)
rails = Detail('SAW','spiral_wall_handrails','dark',True)
brackets = Detail('SAW','spiral_handrail_brackets','dark',True)
for radius, wall in [(1.37,1.27),(2.93,3.03)]:
    for i in range(256):
        t, tn = i*4*math.pi/256,(i+1)*4*math.pi/256
        rails.tube(stair_point(radius,t,1.06+i*14.1/256),stair_point(radius,tn,1.06+(i+1)*14.1/256),.025)
    for i in range(33):
        t,z = i*4*math.pi/32,1.06+i*14.1/32
        brackets.tube(stair_point(wall,t,z-.07),stair_point(radius,t,z-.07),.012)
        brackets.tube(stair_point(radius,t,z-.07),stair_point(radius,t,z),.012)
for group in [rails,brackets]: finish('SAW',group,source_saw)

reviews = {
 'CBG': ('reviewed-no-change', ['已有完整遮阳叶片和连接件、入口门把手、蓝钢结构及学术楼梯，未重复加构件。'], ['result/blender/agents/cbg/evidence.md','data/collections/exteriors/images/cbg_rshp_023.jpg'], ['公共中庭局部研究；教室、办公室及完整逐层布局未建立。']),
 'CKK': ('reviewed-no-change', ['已包含两层回廊、错列木阶、双侧楼梯、玻璃栏板和屋顶钢梁节点。'], ['result/blender/agents/atria/evidence.md'], ['中庭尺寸为估计；2008照片艺术装置不代表当前状态；其余房间未知。']),
 'LRB': ('reviewed-no-change', ['已有螺旋坡道、连续栏杆、双升降机及三角形采光顶。'], ['result/blender/agents/atria/evidence.md'], ['公共中庭局部研究；藏书及学习区非当前逐件清点。']),
 'MAR': ('reviewed-no-change', ['入口、门禁、树形柱、公共大厅和楼梯已有专项深化。'], ['data/collections/architecture_round5/contact_1.jpg','web/tools/build_mar_entry_details.py'], ['公共大厅之外的教室、体育空间及全部楼层未完成。']),
 'SAW': ('refined', ['补内外连续圆管扶手及短托架，沿原螺旋楼梯布置。'], [source_saw], ['只完善现有楼梯局部；原楼梯位置及连续高度仍为研究估算，非完整可通行室内。']),
 'PAN': ('reviewed-no-change', ['已有旋转门、黄色入口、标识、花池、长凳及自行车架。'], ['data/collections/tower_photos_round4/images/PAN/tour_p16_0.png','code/blender/phase03/build_tower_facades.py'], ['未建内部；高层幕墙和不可见背面仍为照片推估。']),
 'FAW': ('reviewed-no-change', ['共有入口归PAN模型；本栋保留已有独立窗带、骨料板缝及内侧遮帘。'], ['code/blender/phase03/build_tower_facades.py','data/collections/tower_photos_round4/contact_sheet.jpg'], ['未建内部；暂无足够独立入口证据，不虚构第二入口。']),
 'PEA': ('refined', ['补剧院雨棚暖色灯矩阵和灯座；灯箱新增独立边框及留白透光板。'], [source_pea], ['仅入口构件深化，灯数尺寸为照片比例估计；灯箱留白，未复制节目海报；剧场内部未建。']),
 'PEL': ('refined', ['补黄色门廊侧的红色竖向导向标识及独立安装背板。'], [source_pel], ['照片分辨率不足以读取完整文字，面板不伪造字样；未建内部，主体仍需准确曲率和竣工图。']),
 'OCS': ('reviewed-no-change', ['已有逐片瓦、脊瓦、异形屋顶、窗棂、双门、排水管及2023立面题字。'], ['data/collections/exterior_photos_round4/contact.jpg','code/blender/agents/phase03_ocs/build_ocs.py'], ['依据2023修复照片；无完整内部资料，未构造隐藏木结构和未知房间。']),
}
bpy.context.view_layer.update()
assert fingerprint(originals)==before, 'Existing geometry changed'
records=[]
for code,(status,changes,sources,limits) in reviews.items():
    objs=added.get(code,[])
    for obj in objs:
        assert all(math.isfinite(v) for vertex in obj.data.vertices for v in vertex.co)
    records.append({'code':code,'status':status,'changes':changes,'sources':sources,'limitations':limits,
                    'addedObjects':[{'name':o.name,'collection':o.users_collection[0].name} for o in objs],
                    'componentCount':sum(o.get('component_count',0) for o in objs)})
manifest={'baseline':str(BASE.relative_to(ROOT)),'buildings':records,'originalGeometrySha256':before,
          'originalGeometryUnchanged':True,'newObjectCount':sum(map(len,added.values())),
          'visibilityReview':{'PEA':{'image':'PEA-canopy.png','check':'Warm lamp rows and independent lightbox rims visible below canopy'},'PEL':{'image':'PEL-portal.png','check':'Red panel corrected to photographed left side of portal'},'SAW':{'image':'SAW-handrails.png','check':'Both rails and wall brackets visible on stair; floor slabs excluded only in QA view'}},
          'scope':'Local additive research model; no release or complete-building claim.'}
(OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'refined.blend'))
print('MODERN_SAVED',manifest['newObjectCount'],flush=True)

# Isolated review scenes are built after saving and are not part of the transfer.
for code in ['PEA','PEL','SAW']:
    scene=bpy.data.scenes.new('MOD19_REVIEW_'+code)
    scene.render.engine='CYCLES';scene.cycles.samples=12;scene.cycles.use_denoising=True
    scene.render.resolution_x=1000;scene.render.resolution_y=800;scene.render.resolution_percentage=100
    scene.world=bpy.data.worlds.new('MOD19_REVIEW_WORLD_'+code);scene.world.use_nodes=True
    scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.65,.69,.72,1)
    scene.world.node_tree.nodes['Background'].inputs[1].default_value=.8
    if code=='SAW':
        for name in ['SAW_spiral_stair_treads','SAW_spiral_anti_slip_nosings','SAW_spiral_concrete_guards']:
            scene.collection.objects.link(bpy.data.objects[name])
        for obj in added[code]:scene.collection.objects.link(obj)
        target=Vector(stair_point(0,0,7))
        pos=target+Vector((7,-8,9))
        filename='SAW-handrails.png'
    else:
        scene.collection.children.link(bpy.data.collections[code+'_EXTERIOR'])
        f=facades[code]
        target=Vector(f.point(f.length/2,2.65,.5))
        pos=Vector(f.point(f.length/2+2.5,2.7,14 if code=='PEA' else 11))
        filename=code+('-canopy.png' if code=='PEA' else '-portal.png')
    data=bpy.data.cameras.new('MOD19_CAMERA_'+code);cam=bpy.data.objects.new(data.name,data)
    scene.collection.objects.link(cam);cam.location=pos
    cam.rotation_euler=(target-pos).to_track_quat('-Z','Y').to_euler();data.lens=45
    scene.camera=cam
    ld=bpy.data.lights.new('MOD19_KEY_'+code,'AREA');ld.energy=2200;ld.size=9
    lo=bpy.data.objects.new(ld.name,ld);scene.collection.objects.link(lo);lo.location=pos+Vector((0,0,5))
    lo.rotation_euler=(target-lo.location).to_track_quat('-Z','Y').to_euler()
    scene.render.filepath=str(OUT/filename)
    bpy.ops.render.render(write_still=True,scene=scene.name)
    print('MODERN_RENDERED',filename,flush=True)
print('MODERN_COMPLETE',flush=True)
