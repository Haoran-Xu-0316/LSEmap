"""Build the paired historical FAW.4.01 thirty-seat room as an isolated study.

Run in Blender's Text Editor. Four distinct group tables, the irregular outline,
window positions and thirty seats follow the archived plan. Yellow swivel
chairs and teaching equipment follow the same-room photograph. Dimensions,
height and unseen construction are estimates, not a current floor survey.
"""
from pathlib import Path
import hashlib,json,math,sys
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'web/tools'))
from build_room_samples167 import RoomGeometry
from integrate_exterior_round194 import object_fingerprint
BASE=ROOT/'result/blender/LSE_campus_detailed_v196.blend'
BASE_SHA='1c1185738e796221c6d30f06aec906b99829cad4867fbb2bced77d657afc298b'
OUT=ROOT/'result/blender/faw-room197'
COLLECTION='FAW401_ROOM197_study'
PREFIX='FAW401_R197_'
SCALE=.024
PLAN='data/collections/interiors/images/7554e7c536df_FAW.4.01.GIF'
PHOTO='data/collections/interiors/images/9e1ff978add7_FAW.4.01.jpg'
OUTLINE=[(150,33),(379,33),(379,291),(368,291),(368,316),(379,316),(379,472),(147,472),(64,389),(64,204),(15,154),(146,35)]
GROUPS=[
 {'center':(264,121),'radius':46,'direction':math.pi/2,'neckWidth':62,'length':86,'seats':[(222,56),(300,56),(211,111),(314,108),(225,151),(304,151),(265,169)]},
 {'center':(225,240),'radius':47,'direction':math.pi,'neckWidth':64,'length':156,'seats':[(89,199),(128,199),(164,200),(88,274),(128,274),(166,274),(211,187),(254,197),(276,237),(256,280),(215,292)]},
 {'center':(171,364),'radius':47,'direction':math.atan2(-58,-43),'neckWidth':47,'length':74,'seats':[(165,313),(125,335),(103,388),(148,434),(202,409),(221,373),(210,335)]},
 {'center':(300,362),'radius':46,'seats':[(299,313),(341,335),(334,405),(275,410),(253,355)]},
]


def point(px,py):return((px-200)*SCALE,(250-py)*SCALE)


def office_chair(g,x,y,angle):
    """Photo-supported padded yellow front, black rear shell and five-star base."""
    c,s=math.cos(angle),math.sin(angle)
    def at(a,b,z):return(x+c*a-s*b,y+s*a+c*b,z)
    g.box('yellow_padded_seats','yellow',at(0,0,.46),(.46,.44,.065),angle)
    g.box('black_back_shells','dark',at(0,.215,.74),(.46,.06,.51),angle)
    g.box('yellow_back_pads','yellow',at(0,.177,.75),(.425,.025,.48),angle)
    g.tube('swivel_stems','dark',at(0,0,.075),at(0,0,.43),.031)
    for i in range(5):
        a=angle+i*math.tau/5
        end=(x+.29*math.cos(a),y+.29*math.sin(a),.065)
        g.tube('five_star_bases','dark',(x,y,.10),end,.018)
        g.tube('casters','dark',(end[0]-.028*math.sin(a),end[1]+.028*math.cos(a),.04),(end[0]+.028*math.sin(a),end[1]-.028*math.cos(a),.04),.037)
    for side in [-1,1]:
        g.box('armrests','dark',at(side*.27,0,.66),(.045,.30,.04),angle)
        g.tube('arm_supports','dark',at(side*.25,.1,.48),at(side*.27,.1,.64),.015)


def table_outline(group):
    cx,cy=point(*group['center']);r=group['radius']*SCALE
    if 'direction' not in group:
        return[(cx+r*math.cos(i*math.tau/48),cy+r*math.sin(i*math.tau/48))for i in range(48)]
    angle=group['direction'];u=Vector((math.cos(angle),math.sin(angle)));v=Vector((-u.y,u.x));center=Vector((cx,cy));half=group['neckWidth']*SCALE/2;length=group['length']*SCALE
    alpha=math.asin(half/r);depth=math.sqrt(r*r-half*half)
    polygon=[center+u*length-v*half,center+u*length+v*half,center+u*depth+v*half]
    polygon.extend(center+Vector((math.cos(a),math.sin(a)))*r for a in [angle+alpha+(math.tau-2*alpha)*i/48 for i in range(1,49)])
    return[tuple(p)for p in polygon]


def window(g,a,b):
    a,b=Vector(point(*a)),Vector(point(*b));delta=b-a;length=delta.length;angle=math.atan2(delta.y,delta.x);center=(a+b)/2
    g.box('window_parapets','wall',(*center,.42),(length,.14,.84),angle)
    g.box('window_headers','wall',(*center,2.97),(length,.14,.42),angle)
    g.box('plan_window_panes','glass',(*center,1.8),(length-.055,.025,1.82),angle)
    g.box('window_sills','white',(*center,.86),(length+.04,.20,.05),angle)
    for p in [a,b]:g.box('window_jambs','steel',(*p,1.8),(.05,.07,1.92),angle)
    for z in [.87,2.73]:g.box('window_rails','steel',(*center,z),(length,.07,.045),angle)


def build():
    OUT.mkdir(parents=True,exist_ok=True)
    assert hashlib.sha256(BASE.read_bytes()).hexdigest()==BASE_SHA
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    for scene in bpy.data.scenes:
        for layer in scene.view_layers:layer.update()
    original={obj.name:object_fingerprint(obj)for obj in bpy.data.objects}
    visibility={obj.name:obj.hide_render for obj in bpy.data.objects}
    collection=bpy.data.collections.new(COLLECTION);collection['roomSample']=True;collection['roomCode']='FAW.4.01';collection['studentSeatCount']=30
    scene=bpy.data.scenes.new('ROOM197_FAW401');scene.collection.children.link(collection);bpy.context.window.scene=scene
    g=RoomGeometry(collection,PREFIX)
    for key,color in [('wall',(.78,.79,.76)),('white',(.82,.83,.80)),('carpet',(.22,.24,.235)),('dark',(.017,.021,.023)),('steel',(.12,.14,.14))]:
        mat=g.materials[key];mat.diffuse_color=(*color,1);shader=mat.node_tree.nodes['Principled BSDF'];shader.inputs['Base Color'].default_value=mat.diffuse_color;shader.inputs['Metallic'].default_value=0;shader.inputs['Roughness'].default_value=.8
    yellow=g.materials['red'].copy();yellow.name=PREFIX+'mustard_yellow_upholstery';yellow.diffuse_color=(.72,.43,.018,1);yellow.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=yellow.diffuse_color;g.materials['yellow']=yellow
    wood=g.materials['dark'].copy();wood.name=PREFIX+'door_timber';wood.diffuse_color=(.22,.12,.045,1);wood.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=wood.diffuse_color;g.materials['wood']=wood
    g.materials['glass']['webOpacity']=.30
    g.materials['light']['webEmission']=True
    g.prism('irregular_plan_floor','carpet',[point(*p)for p in OUTLINE],-.14,.14)
    # Keep unseen left/front walls cut down so the plan can be inspected.
    for a,b in zip(OUTLINE,OUTLINE[1:]+OUTLINE[:1]):
        if a==(379,472) or a==(150,33):continue
        p,q=Vector(point(*a)),Vector(point(*b));d=q-p
        g.box('cutaway_perimeter','wall',(*((p+q)/2),.16),(d.length,.12,.32),math.atan2(d.y,d.x))
    # Visible teaching-wall system; heights remain estimated from the photograph.
    x,y=point(379,162);g.box('teaching_wall','wall',(x+.06,y,1.6),(.12,258*SCALE,3.2))
    for start,end in [(103,174),(184,258)]:
        x,y=point(376,(start+end)/2);g.box('paired_whiteboards','white',(x,y,1.64),(.035,(end-start)*SCALE,1.30))
    # Five upper straight-window bays and two angled bays are explicit in plan.
    for start,end in [(150,187),(198,236),(246,283),(294,332),(343,379)]:window(g,(start,33),(end,33))
    for a,b in [((42,130),(79,96)),((91,84),(127,51))]:window(g,a,b)
    for a,b in [(187,198),(236,246),(283,294),(332,343)]:
        x,y=point((a+b)/2,33);g.box('window_wall_piers','wall',(x,y,1.6),((b-a)*SCALE,.14,3.2))
    students=[];registrations=[]
    for index,group in enumerate(GROUPS):
        outline=table_outline(group);g.prism('four_registered_white_tables','white',outline,.735,.055)
        cx,cy=point(*group['center'])
        g.tube('round_table_pedestals','steel',(cx,cy,.035),(cx,cy,.733),.095)
        g.box('round_table_bases','dark',(cx,cy,.025),(.60,.60,.05))
        if 'direction' in group:
            d=group['direction'];end=(cx+math.cos(d)*group['length']*SCALE*.76,cy+math.sin(d)*group['length']*SCALE*.76)
            g.tube('tongue_table_supports','steel',(*end,.03),(*end,.733),.035)
        for px,py in group['seats']:
            sx,sy=point(px,py);target=Vector((cx,cy))
            if index==0 and py==56:target=Vector(point(264,56))
            if index==1 and px<=166:target=Vector(point(px,240))
            angle=math.atan2(target.y-sy,target.x-sx)+math.pi/2
            office_chair(g,sx,sy,angle);students.append((sx,sy))
        registrations.append({'planCenter':group['center'],'studentSeats':len(group['seats']),'outline':outline})
    assert len(students)==30
    minimum_spacing=min(math.dist(a,b)for i,a in enumerate(students)for b in students[i+1:]);assert minimum_spacing>.65
    # Plan's lecturer desk is distinct from the thirty student seats.
    dx,dy=point(363,76);g.box('lecturer_white_desk','white',(dx,dy,.76),(.62,1.08,.05))
    for yy in [dy-.42,dy+.42]:g.box('lecturer_desk_supports','steel',(dx,yy,.37),(.49,.045,.74))
    g.box('desk_monitor','dark',(dx-.08,dy,1.05),(.04,.41,.28))
    g.tube('monitor_stand','steel',(dx,dy,.79),(dx,dy,1.01),.019)
    # Wood leaf on the plan's lower-right doorway; open position is an estimate.
    dx,dy=point(379,450);g.box('open_timber_door','wood',(dx-.015,dy,1.05),(.045,44*SCALE,2.10))
    g.box('door_vision_panel','glass',(dx-.04,dy,1.51),(.018,.14,.65))
    # A limited ceiling strip preserves room visibility without inventing a full roof.
    x,y=point(350,162);g.box('ceiling_cutaway_strip','wall',(x,y,3.16),(1.15,258*SCALE,.10))
    for py in [72,157,242]:
        x,y=point(350,py);g.box('square_recessed_diffusers','light',(x,y,3.101),(.55,.55,.018))
    x,y=point(219,208);g.box('ceiling_projector','white',(x,y,2.92),(.42,.31,.14));g.tube('projector_drop','dark',(x,y,3.0),(x,y,3.18),.018)
    g.box('projector_lens','dark',(x+.22,y,2.91),(.025,.09,.09))
    objects=g.finish();floor=next(obj for obj in objects if obj.name.endswith('irregular_plan_floor'))
    tree=BVHTree.FromPolygons([v.co for v in floor.data.vertices],[list(face.vertices)for face in floor.data.polygons])
    for sx,sy in students:assert tree.ray_cast(Vector((sx,sy,.1)),Vector((0,0,-1)),.3)[0] is not None
    # Door apron: all student bases remain clear of a photo/plan-sized entrance zone.
    apron=(335,436,379,472)
    for group in GROUPS:
        for px,py in group['seats']:
            assert not (apron[0]-12.5<px<apron[2]+12.5 and apron[1]-12.5<py<apron[3]+12.5)
    for obj in objects:obj['roomCode']='FAW.4.01';obj['dimensionBasis']='Historical plan registration, estimated .024m per pixel; no whole-floor registration'
    scope='同房号历史平面与实拍支持的30座协作教室。4组圆形及带延伸桌、黄色转椅、折角边界、7组平面窗位及教学墙按图近似；尺度、层高和不可见构造估计，未与整栋楼层配准，不代表2026年现状。'
    space=dict(id='faw-401',code='FAW',collection=COLLECTION,label='FAW.4.01协作教室',scope=scope,gallery='faw-401-interior',interiorStudy=dict(kind='room-sample',label='FAW.4.01协作教室',scope=scope),interiorView=dict(position=[-12,12,15],target=[0,1,0],fov=48))
    collection['authoringRecord']=json.dumps(space,ensure_ascii=False)
    assert all(object_fingerprint(bpy.data.objects[name])==value for name,value in original.items())
    assert all(bpy.data.objects[name].hide_render==value for name,value in visibility.items())
    assert not any(obj.name in bpy.data.scenes['00_CAMPUS_COMPLETE'].objects for obj in objects)
    component=OUT/'faw401-room197-component.blend';bpy.data.libraries.write(str(component),set(objects),fake_user=True,compress=True)
    fingerprints={obj.name:object_fingerprint(obj)for obj in objects}
    report=dict(version=197,baselineSha256=BASE_SHA,componentPath=str(component.relative_to(ROOT)),componentSha256=hashlib.sha256(component.read_bytes()).hexdigest(),targetCollection=COLLECTION,collectionSpec=dict(name=COLLECTION,scene='ROOM197_FAW401',kind='independent-room'),addedObjects=[obj.name for obj in objects],archivedObjects=[],space=space,studentSeatCount=30,tableSeatCounts=[len(group['seats'])for group in GROUPS],tables=registrations,minimumSeatSpacing=minimum_spacing,doorApronPlanPixels=apron,doorWidth=44*SCALE,floorCoverageSamples=len(students),solidProof=g.solid_proof,sourceFiles=[dict(path=p,sha256=hashlib.sha256((ROOT/p).read_bytes()).hexdigest())for p in [PLAN,PHOTO]],record='data/collections/interiors/pages/1e0f4804d461_10.htm',recordTypeDiscrepancy='Archive record labels this a Computer Teaching Room; paired plan/photo show collaboration tables. No computer bank inferred.',limitations=scope,fingerprints=fingerprints)
    (OUT/'audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    # Review scene is temporary and is not included in the component object set.
    camera=bpy.data.objects.new(PREFIX+'review_camera',bpy.data.cameras.new(PREFIX+'review_camera'));scene.collection.objects.link(camera);camera.data.type='ORTHO';camera.data.ortho_scale=16
    camera.location=(-11,-14,15);target=Vector((0,0,1.1));camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler();scene.camera=camera
    scene.render.engine='CYCLES';scene.cycles.samples=16;scene.cycles.use_denoising=True
    scene.render.resolution_x=1100;scene.render.resolution_y=1000;scene.render.resolution_percentage=100;scene.render.filepath=str(OUT/'room-preview.png')
    world=bpy.data.worlds.new(PREFIX+'world');world.use_nodes=True;world.node_tree.nodes['Background'].inputs[0].default_value=(.8,.83,.87,1);world.node_tree.nodes['Background'].inputs[1].default_value=.7;scene.world=world
    sun_data=bpy.data.lights.new(PREFIX+'review_sun','SUN');sun_data.energy=2;sun=bpy.data.objects.new(sun_data.name,sun_data);scene.collection.objects.link(sun);sun.rotation_euler=Vector((-.6,.5,-1)).to_track_quat('-Z','Y').to_euler()
    bpy.ops.render.render(write_still=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    with bpy.data.libraries.load(str(component),link=False)as(available,loaded):loaded.objects=list(report['addedObjects'])
    for obj in loaded.objects:bpy.context.scene.collection.objects.link(obj)
    bpy.context.view_layer.update()
    for obj in loaded.objects:assert object_fingerprint(obj)==fingerprints[obj.name]
    assert hashlib.sha256(BASE.read_bytes()).hexdigest()==BASE_SHA
    (OUT/'verification.json').write_text(json.dumps(dict(componentReopened=True,addedObjectsVerified=len(objects),studentSeats=30,tableGroups=4,planSeatCounts=[7,11,7,5],minimumSeatSpacing=minimum_spacing,doorApronClear=True,originalCampusUnchanged=True),indent=2)+'\n')
    print('FAW401_ROOM197_VERIFIED',len(objects),flush=True)


if __name__=='__main__':build()
