"""Independent CBG.2.05 study from its paired official historical plan/photo.

Coordinates and heights are estimated. This room is not registered into the
current whole-building floor layout. Call apply_cbg205_room171() in Blender.
"""
from pathlib import Path
import hashlib,json,math
import bpy
from build_room_samples167 import RoomGeometry,curved_table
ROOT=Path(__file__).resolve().parents[2]
COLLECTION='CBG205_ROOM171_study'
PLAN='data/collections/interiors/images/c9d5445ddd37_CBG.2.05.gif'
PHOTO='data/collections/interiors/images/a31c569b821b_CBG.2.05.jpg'


def apply_cbg205_room171():
    if bpy.data.collections.get(COLLECTION):
        return dict(alreadyApplied=True,addedObjects=[],changedObjects=[],archivedObjects=[],spaces=[json.loads(bpy.data.collections[COLLECTION]['authoringRecord'])])
    collection=bpy.data.collections.new(COLLECTION)
    scene=bpy.data.scenes.new('ROOM171_CBG205');scene.collection.children.link(collection)
    geometry=RoomGeometry(collection,'CBG205_R171_')
    scale=.034
    def point(x,y):return ((x-338)*scale,(y-486)*scale)
    x0,y0=point(161,303);x1,y1=point(515,669)
    geometry.box('dark_carpet','carpet',((x0+x1)/2,(y0+y1)/2,-.08),(x1-x0,y1-y0,.16))
    # Only the photographed teaching wall is full height; unseen walls remain cut away.
    geometry.box('projection_wall','wall',(x1+.06,(y0+y1)/2,1.65),(.12,y1-y0,3.3))
    geometry.box('left_cutaway_wall','wall',(x0-.05,(y0+y1)/2,.16),(.1,y1-y0,.32))
    door=point(350,669)[0]
    for a,b in [(x0,door-.6),(door+.6,x1)]:geometry.box('rear_cutaway_wall','wall',((a+b)/2,y1+.05,.16),(b-a,.1,.32))
    geometry.box('rear_door_marker','steel',(door,y1,.012),(1.2,.1,.024))
    # Adjoining visible glazing and the perforated lower privacy panel in the photo.
    for a,b in [(x1-3.1,x1-1.55),(x1-1.55,x1)]:
        geometry.box('visible_window','glass',((a+b)/2,y0,1.8),(b-a-.055,.026,2.75))
        for x in [a,b]:geometry.box('window_mullions','steel',(x,y0,1.8),(.05,.07,2.85))
        geometry.box('lower_privacy_panel','screen',((a+b)/2,y0+.04,.75),(b-a-.055,.028,.72))
    sy=point(506,495)[1]
    geometry.box('whiteboard','white',(x1-.075,sy,1.55),(.04,4.55,1.25))
    # The source has projected light on a painted wall, rather than a black framed screen.
    geometry.box('projection_footprint','screen',(x1-.045,sy-1.05,2.1),(.02,2.65,1.15))
    lx,ly=point(461,376)
    geometry.box('av_lectern','steel',(lx,ly,.56),(.68,1.05,1.12))
    geometry.box('lectern_top','dark',(lx,ly,1.15),(.78,1.15,.06))
    geometry.box('lectern_monitor','dark',(lx,ly,1.43),(.06,.47,.31))
    geometry.tube('monitor_arm','steel',(lx,ly,1.18),(lx,ly,1.4),.023)
    geometry.box('front_speaker','steel',(x1-.16,sy-2.7,2.95),(.16,.36,.37))
    centers=[(235,396,math.pi/2),(340,394,math.pi/2),(397,453,math.pi/2),(216,483,math.pi/2),(235,582,math.pi/2),(340,570,-math.pi/2),(440,583,math.pi/2)]
    seats=[];tables=[]
    for px,py,angle in centers:
        x,y=point(px,py);seats+=curved_table(geometry,x,y,angle);tables.append(dict(planPixel=[px,py],center=[x,y],seats=6))
    assert len(seats)==42
    spacing=min(math.dist(a,b) for i,a in enumerate(seats) for b in seats[i+1:]);assert spacing>.5
    # Photo-visible exposed services and circular blue acoustic rafts.
    for y in [y0+.8,y0+3.5,y0+6.2,y0+8.9]:
        outline=[(1.05*math.cos(i*math.tau/40),y+1.05*math.sin(i*math.tau/40)) for i in range(40)]
        geometry.prism('circular_blue_acoustic_rafts','baffle',outline,3.08,.065)
        for x in [-2.3,2.3]:
            geometry.box('linear_light_housings','white',(x,y,3.14),(.15,2.5,.1))
            geometry.box('linear_light_diffusers','light',(x,y,3.08),(.10,2.42,.018))
    for x in [-3.6,3.2]:geometry.tube('exposed_ducts','duct',(x,y0+.1,3.48),(x,y1-.2,3.48),.18)
    geometry.box('projector','white',(x1-2.1,sy-.6,3.32),(.5,.44,.22))
    objects=geometry.finish()
    for obj in objects:obj['roomCode']='CBG.2.05';obj['scope']='Historical room-only study; estimated dimensions and hidden construction'
    scope='依据同房号LSE官方历史平面与照片建立42座Wolfson Seminar Room样本。7组六座曲线桌按平面注册，可见白色椅、蓝色圆形吸声板、明装风管与投影墙按照片近似。尺度、层高、不可见构造与顶面完整布置均为估算，未与整栋楼层测绘配准，不代表2026年布置。'
    record=dict(id='cbg-205',label='CBG.2.05 Wolfson Seminar Room',code='CBG',collection=COLLECTION,scope=scope,gallery='cbg-205-interior',interiorView=dict(position=[-13,11,-14],target=[0,1,0],fov=50),interiorStudy=dict(kind='room-sample',label='CBG.2.05 Wolfson Seminar Room',scope=scope))
    collection['authoringRecord']=json.dumps(record,ensure_ascii=False);collection['studentSeatCount']=42
    references=[dict(path=p,sha256=hashlib.sha256((ROOT/p).read_bytes()).hexdigest(),captureDate='unknown') for p in [PLAN,PHOTO]]
    return dict(alreadyApplied=False,addedObjects=[o.name for o in objects],changedObjects=[],archivedObjects=[],spaces=[record],roomAudits=[dict(studentSeatCount=42,tables=tables,minimumSeatSpacing=spacing,closedSolidProof=geometry.solid_proof,references=references,estimatedMetersPerPlanPixel=scale,roomBounds=[x0,y0,x1,y1])])
