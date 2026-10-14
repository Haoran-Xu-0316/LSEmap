"""Build a photo-informed CON.7.05 committee-room study from paired LSE sources.

Fixed Blender Text Editor configuration. The source plan controls the18 seat
centres, door positions and room outline; the photograph controls visible finish
and a solid table rather than interpreting the plan's centre label as a hole.
Metric scale, wall registration, heights and hidden construction are estimates.
The study has its own scene and never invents a connection to the campus shell.
"""
from pathlib import Path
import hashlib
import json
import math
import sys
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'web/tools'))
from build_room_samples167 import RoomGeometry
from build_mar107_room200 import reopened_mesh_checks
BASE = ROOT/'result/blender/LSE_campus_detailed_v209.blend'
BASE_SHA = '6398f422e2fefde66c33e0d87a36092bfad46b7fee69494d5c955caae443e455'
OUT = ROOT/'result/blender/con-room210'
COLLECTION = 'CON705_ROOM210_study'
SCENE = 'ROOM210_CON705'
PREFIX = 'CON705_R210_'
SCALE = .02
FILES = [
 ('1325534b6e71_CON.7.05.GIF', 'c8b681cc966089c977652f6e25d35986230554545838ac2ade79d640e4b0341b',
  'https://www.lse.ac.uk/assets/roomInformation/images/CON.7.05.GIF'),
 ('12d7ce0af100_CON.7.05.jpg', 'b566128212cd2210d470ffd6ffbfa10d5311d9b8b8097157828a079c11e67fd0',
  'https://www.lse.ac.uk/assets/roomInformation/images/photos/CON.7.05.jpg'),
]
OUTLINE = [(86,104),(375,104),(375,79),(445,79),(529,169),(534,239),
           (495,239),(495,252),(488,252),(488,374),(86,374)]
HEIGHT = 3.05


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def point(px, py):
    return ((px-280)*SCALE, (260-py)*SCALE)


def finish(g, key, color, roughness=.65, metallic=0):
    material = g.materials.get(key) or bpy.data.materials.new(PREFIX+key)
    material.use_nodes = True
    material.diffuse_color = (*color, 1)
    shader = material.node_tree.nodes['Principled BSDF']
    shader.inputs['Base Color'].default_value = material.diffuse_color
    shader.inputs['Roughness'].default_value = roughness
    shader.inputs['Metallic'].default_value = metallic
    g.materials[key] = material
    return material


def chair(g, px, py, angle):
    x, y = point(px, py)
    cosine, sine = math.cos(angle), math.sin(angle)
    def at(a,b,z):
        return (x+cosine*a-sine*b, y+sine*a+cosine*b, z)
    g.box('eighteen_black_seat_cushions', 'dark', at(0,0,.47), (.45,.43,.065), angle)
    g.box('black_padded_backrests', 'dark', at(0,.228,.75), (.435,.055,.48), angle)
    for side in [-1,1]:
        g.tube('chrome_back_supports', 'chrome', at(side*.23,.24,.42), at(side*.23,.24,.94), .014)
        # The photograph shows chrome loop arms and black pads, not white shells.
        g.tube('chrome_loop_arms', 'chrome', at(side*.26,.16,.43), at(side*.26,.16,.69), .015)
        g.tube('chrome_loop_arms', 'chrome', at(side*.26,.16,.69), at(side*.26,-.20,.66), .015)
        g.tube('chrome_loop_arms', 'chrome', at(side*.26,-.20,.66), at(side*.26,-.20,.43), .015)
        g.box('black_arm_pads', 'dark', at(side*.26,-.025,.69), (.045,.27,.035), angle)
    g.tube('chair_swivel_columns', 'chrome', at(0,0,.12), at(0,0,.44), .037)
    for spoke in range(5):
        theta = math.tau*spoke/5
        a,b = .30*math.cos(theta), .30*math.sin(theta)
        g.tube('five_spoke_chrome_bases', 'chrome', at(0,0,.14), at(a,b,.075), .022)
        g.box('black_castors', 'dark', at(a,b,.044), (.065,.075,.065), angle+theta)
    return dict(planPixel=[px,py], center=[x,y], angleRadians=angle)


def bottom_wall(g):
    # Two doors on the long paneled wall are independently marked in the plan.
    y = point(0,374)[1]
    lo,hi = point(86,0)[0], point(488,0)[0]
    openings = [(point(a,0)[0],point(b,0)[0]) for a,b in [(177,220),(274,313)]]
    cursor = lo
    solids = []
    for a,b in openings+[(hi,hi)]:
        if a>cursor:
            g.box('full_long_oak_wall', 'oak', ((cursor+a)/2,y-.07,HEIGHT/2), (a-cursor,.14,HEIGHT))
            solids.append((cursor,a))
        if b>a:
            g.box('long_wall_door_lintels','oak',((a+b)/2,y-.07,(2.22+HEIGHT)/2),(b-a,.14,HEIGHT-2.22))
            g.box('two_oak_door_leaves','oak_dark',((a+b)/2,y-.015,1.10),(b-a-.035,.065,2.20))
            for z,h in [(.47,.55),(1.48,1.16)]:
                g.box('door_recessed_panels','oak',((a+b)/2,y+.024,z),(b-a-.17,.024,h))
            g.tube('door_metal_levers','chrome',(b-.10,y+.08,1.02),(b-.24,y+.08,1.02),.013)
        cursor = b
    for a,b in solids:
        count = max(1,round((b-a)/.54))
        for i in range(count+1):
            x = a+(b-a)*i/count
            g.box('vertical_oak_panel_stiles','oak_light',(x,y+.026,1.53),(.045,.045,2.75))
        for z in [.13,.74,.84,2.77,2.94]:
            g.box('long_wall_panel_rails','oak_light',((a+b)/2,y+.025,z),(b-a,.045,.045))
    return openings


def left_wall(g):
    x = point(86,0)[0]
    y0,y1 = point(0,374)[1],point(0,104)[1]
    a,b = sorted([point(0,359)[1],point(0,318)[1]])
    for lo,hi in [(y0,a),(b,y1)]:
        if hi>lo:
            g.box('short_oak_presentation_wall','oak',(x-.07,(lo+hi)/2,HEIGHT/2),(.14,hi-lo,HEIGHT))
            count = max(1,round((hi-lo)/.55))
            for i in range(count+1):
                g.box('short_wall_panel_stiles','oak_light',(x+.025,lo+(hi-lo)*i/count,1.53),(.045,.045,2.75))
            for z in [.13,.74,.84,2.77,2.94]:
                g.box('short_wall_panel_rails','oak_light',(x+.025,(lo+hi)/2,z),(.045,hi-lo,.045))
    g.box('entrance_door_lintel','oak',(x-.07,(a+b)/2,(2.22+HEIGHT)/2),(.14,b-a,HEIGHT-2.22))
    g.box('entrance_door_leaf','oak_dark',(x-.015,(a+b)/2,1.10),(.065,b-a-.035,2.20))
    # The large wall-mounted screen is visible in the photo; the historic page's
    # projector list is not used to invent a second current device.
    g.box('large_black_display_frame','dark',(x+.065,.90,2.01),(.09,2.14,1.23))
    g.box('display_black_glass','screen_black',(x+.116,.90,2.01),(.017,2.02,1.11))
    g.box('display_camera','dark',(x+.19,.90,1.30),(.08,.18,.085))
    g.box('small_av_shelf','oak_light',(x+.14,.90,1.03),(.26,1.10,.055))
    return [a,b]


def build():
    assert BASE.exists() and digest(BASE)==BASE_SHA
    sources = []
    for name,expected,url in FILES:
        path = ROOT/'data/collections/interiors/images'/name
        assert digest(path)==expected
        sources.append(dict(path=str(path.relative_to(ROOT)),sha256=expected,url=url,creationDate='unknown'))
    OUT.mkdir(parents=True,exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.name = SCENE
    collection = bpy.data.collections.new(COLLECTION)
    scene.collection.children.link(collection)
    geometry = RoomGeometry(collection,PREFIX)
    for key,color,rough,metal in [
        ('oak',(.32,.19,.085),.47,0),('oak_dark',(.25,.14,.061),.5,0),
        ('oak_light',(.39,.24,.11),.43,0),('table_oak',(.58,.36,.14),.43,0),
        ('dark',(.014,.019,.022),.52,0),('chrome',(.48,.50,.50),.26,.72),
        ('carpet',(.045,.085,.125),.96,0),('wall',(.78,.78,.72),.9,0),
        ('screen_black',(.008,.015,.022),.2,0),('glass',(.16,.21,.23),.18,0),
    ]:
        finish(geometry,key,color,rough,metal)
    # Unseen exterior context is absent. Window fragments stay opaque proxies.
    glass = geometry.materials['glass']
    glass.node_tree.nodes['Principled BSDF'].inputs['Transmission Weight'].default_value=0
    glass['webOpacity']=1.0
    geometry.prism('registered_bay_floor','carpet',[point(*p) for p in OUTLINE],-.12,.12)
    doors = bottom_wall(geometry)
    main_door = left_wall(geometry)
    # Retain low sill walls on the cutaway sides. Floor geometry carries the
    # complete source outline; no claim is made about unpictured window height.
    for a,b in zip(OUTLINE,OUTLINE[1:]+OUTLINE[:1]):
        if a[1]==374 and b[1]==374 or a[0]==86 and b[0]==86:
            continue
        if a == (86,104) and b == (375,104):
            for lo,hi in [(86,190),(226,375)]:
                p,q = point(lo,104),point(hi,104)
                geometry.box('cutaway_window_side_walls','wall',((p[0]+q[0])/2,p[1],.43),(q[0]-p[0],.12,.86))
            continue
        p,q = point(*a),point(*b)
        dx,dy = q[0]-p[0],q[1]-p[1]
        length = math.hypot(dx,dy)
        geometry.box('cutaway_window_side_walls','wall',((p[0]+q[0])/2,(p[1]+q[1])/2,.43),(length,.12,.86),math.atan2(dy,dx))
    # Plan-supported top wall windows and fourth door remain visible as low
    # sectional fragments rather than guessing their complete elevations.
    y = point(0,104)[1]
    for lo,hi in [(124,190),(278,360)]:
        x0,x1 = point(lo,0)[0],point(hi,0)[0]
        geometry.box('sectioned_window_sills','oak_light',((x0+x1)/2,y,.89),(x1-x0,.19,.055))
        geometry.box('sectioned_opaque_glazing','glass',((x0+x1)/2,y,.995),(x1-x0-.05,.032,.15))
    a,b = point(190,0)[0],point(226,0)[0]
    geometry.box('sectioned_fourth_door','oak_dark',((a+b)/2,y,.43),(b-a-.035,.065,.86))
    # The photograph shows one continuous top. The red plan centre rectangle is
    # a layout label, and is not modeled as an unsupported open table hole.
    x0,y0 = point(168,191)
    x1,y1 = point(363,303)
    geometry.box('solid_photo_oak_conference_table','table_oak',((x0+x1)/2,(y0+y1)/2,.755),(x1-x0,abs(y1-y0),.055))
    for fraction in [.20,.50,.80]:
        x = x0+(x1-x0)*fraction
        for y in [y0-.22,y1+.22]:
            geometry.box('table_dark_supports','dark',(x,y,.355),(.085,.085,.71))
    seats = []
    for px in [187,219,249,280,312,343]:
        seats.append(chair(geometry,px,175,0))
        seats.append(chair(geometry,px,319,math.pi))
    for py in [198,247,297]:
        seats.append(chair(geometry,157,py,math.pi/2))
        seats.append(chair(geometry,374,py,-math.pi/2))
    # Retained ceiling edge and a photographed metallic service tube define the
    # room height while the central ceiling is cut away for inspection.
    wall_y = point(0,374)[1]
    geometry.box('cutaway_ceiling_edge','wall',(.14,wall_y+.35,HEIGHT+.06),(8.04,.85,.12))
    geometry.tube('ceiling_metallic_service_tube','chrome',(-3.7,wall_y+.43,2.83),(3.9,wall_y+.43,2.83),.065)
    geometry.box('ceiling_linear_light','light',(.12,wall_y+.67,2.99),(7.2,.08,.045))
    objects = geometry.finish()
    assert len(seats)==18
    minimum_spacing = min(math.dist(a['center'],b['center']) for i,a in enumerate(seats) for b in seats[i+1:])
    assert minimum_spacing >= .60-1e-6
    for obj in objects:
        obj['roomCode']='CON.7.05'
        obj['scope']='Independent historical paired-source room study; unmeasured dimensions and photo-to-plan wall registration'
    next(obj for obj in objects if 'eighteen_black_seat_cushions' in obj.name)['studentSeatCount']=18
    scope='依据LSE官方CON.7.05同房号历史平面与实拍建立18座会议室样本。座位和折角房间边界按图近似；整板木桌、木饰墙、黑色旋转椅及大屏按照片表达。尺度、墙面对应、窗高与不可见构造为估计；侧墙和吊顶剖开，不推断整层连通，不代表2026年现状。'
    space = dict(id='con-705',code='CON',collection=COLLECTION,label='CON.7.05会议室',gallery='con-705-interior',scope=scope,
                 interiorStudy=dict(kind='room-sample',label='CON.7.05会议室',scope=scope),
                 interiorView=dict(position=[10.8,8.6,-9.8],target=[.25,1.0,-.55],fov=48))
    collection['roomSample']=True
    collection['studentSeatCount']=18
    collection['authoringRecord']=json.dumps(space,ensure_ascii=False)
    component = OUT/'component.blend'
    names = sorted(obj.name for obj in objects)
    expected = {obj.name:(len(obj.data.vertices),len(obj.data.polygons)) for obj in objects}
    bpy.data.libraries.write(str(component),set(objects),fake_user=True,compress=True)
    report = dict(version=210,baselineSha256=BASE_SHA,componentPath=str(component.relative_to(ROOT)),componentSha256=digest(component),
                  targetCollection=COLLECTION,collectionSpec=dict(name=COLLECTION,scene=SCENE,kind='independent-room'),
                  space=space,addedObjects=names,archivedObjects=[],studentSeatCount=18,seatPositions=seats,
                  planMapping=dict(originPixel=[280,260],metresPerPixel=SCALE,outlinePixels=OUTLINE,estimatedRoomHeight=HEIGHT),
                  minimumSeatCenterSpacingMetres=minimum_spacing,doorIntervals=doors,mainDoorInterval=main_door,
                  triangleCount=sum(sum(len(f.vertices)-2 for f in obj.data.polygons) for obj in objects),
                  scope=scope,sources=sources,closedSolidProof=geometry.solid_proof,
                  limitations=['No image creation dates known. Historical page refresh2022 is not a photograph date.',
                               'The current legacy page links broken CONN aliases; archived CON asset aliases are paired by room number.',
                               'Plan furniture count controls18 seats; the photo supports a solid table and modern screen. Sources may not be contemporaneous.',
                               'Scale, wall-to-photo registration, height, hidden construction and window elevations estimated; no full-floor or current-fitout claim.',
                               'Only derived native geometry is published; reference photographs and plan pixels stay local.'])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    with bpy.data.libraries.load(str(component),link=False) as(source,target):
        target.objects = list(names)
    for obj in target.objects:
        bpy.context.scene.collection.objects.link(obj)
        assert (len(obj.data.vertices),len(obj.data.polygons))==expected[obj.name]
    solid = reopened_mesh_checks(target.objects)
    assert digest(BASE)==BASE_SHA
    verification = dict(componentReopened=True,ownedObjectsVerified=len(names),closedSolidObjectsVerified=len(solid),
                        eighteenSeats=True,minimumSeatCenterSpacingMetres=minimum_spacing,sourceUnchanged=True,
                        distinctRoomIdentity=True,noCampusOrDefaultInteriorMutation=True)
    (OUT/'audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    (OUT/'verification.json').write_text(json.dumps(verification,indent=2)+'\n')
    print('CON705_ROOM210_COMPONENT',len(names),report['triangleCount'],flush=True)


if __name__=='__main__':
    build()
