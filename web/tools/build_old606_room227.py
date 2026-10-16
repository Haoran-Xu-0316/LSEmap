"""Independent OLD.6.06 plan-layout teaching room from paired historical assets.

The20-seat plan controls positions; its furniture arrangement differs from the
photograph. The photograph controls finishes and visible equipment types only.
No Shaw identification, geographic registration or2026 capacity claim is made.
"""
from pathlib import Path
import hashlib,json,math,sys
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'result/blender/old606-room227'
DATA=ROOT/'data/collections/old606-room227'
BASE=ROOT/'result/blender/LSE_campus_detailed_v226.blend'
SHA='4e6c1482f97ac61b42e8a344bc503fd2fa86395006a6b43312bd6be21ac214a2'
COLLECTION='OLD606_ROOM227_study'
SCENE='ROOM227_OLD606'
PREFIX='OLD606_R227_'
PHOTO='data/collections/interiors/images/f5b99ac2ccc3_OLD.6.06.jpg'
PLAN='data/collections/interiors/images/c72b329bf46f_OLD.6.06.GIF'
HEIGHT=2.90

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def prepare():
 from shapely.geometry import Polygon,box
 DATA.mkdir(parents=True,exist_ok=True);OUT.mkdir(parents=True,exist_ok=True)
 scale=.03125
 def point(p):return[(p[0]-294.5)*scale,(245-p[1])*scale]
 outline=[[208,93],[381,93],[381,397],[208,397]];metric=Polygon([point(p)for p in outline])
 students=[]
 for side,x in [('left',251),('right',345)]:
  for i in range(10):
   y=142+i*24;students.append(dict(side=side,index=i,centre=[x,y],target=[298,y],color=('burgundy'if i%3!=1 else'green')if side=='left'else['green','yellow','burgundy','green','burgundy'][i%5]))
 tables=[]
 for side,x in [('left',267),('right',329)]:
  for i in range(5):tables.append(dict(id=f'{side}{i+1}',centre=[x,154+i*48],length=1.50,depth=.60,angle=math.pi/2))
 tables.append(dict(id='teaching',centre=[298,140],length=1.3125,depth=.60,angle=0))
 planks=[];x0,y0,x1,y1=metric.bounds
 for i in range(math.floor(x0/.16),math.ceil(x1/.16)):
  for j in range(math.floor(y0/1.2)-1,math.ceil(y1/1.2)+1):
   start=j*1.2+(i%3)*.4;part=metric.intersection(box(i*.16,start,(i+1)*.16,start+1.2))
   if not part.is_empty and part.area>1e-7:planks.append(dict(outline=list(part.exterior.coords)[:-1],material='wood'+['A','B','C'][(i+2*j)%3]))
 windows=[dict(id='right1',a=[381,209],b=[381,283]),dict(id='right2',a=[381,318],b=[381,380])]
 door=dict(a=[208,350],b=[208,382],hinge=[208,382],openTip=[240,382])
 lights=[[x,y]for x in [-1.55,1.55]for y in [-2.7,0,2.7]]
 layout=dict(room='OLD.6.06',sourcePlan=PLAN,sourcePhoto=PHOTO,coordinateConvention='Plan right maps to native+X; plan down maps to native-Y; native+Z up; web[X,Z,-Y]. This preserves right windows and left pinboard when viewed from rear.',outlinePixels=outline,outline=[point(p)for p in outline],scaleMetresPerPixel=scale,scaleBasis='Estimated0.03125m/pixel from32px doorway approximately1.00m; source is an undimensioned teaching-layout diagram, not a measured plan',roomAreaSquareMetres=metric.area,studentSeatCount=20,planTeacherSeatCount=1,students=students,tables=tables,windows=windows,door=door,floorPlanks=planks,ceilingHeight=HEIGHT,lights=lights,teacherSeat=[298,121],avCabinet=[361,115],projector=[294.5,205],principalRoutes=[[[208,366],[225,366]],[[225,366],[225,373]],[[225,373],[265,373]],[[265,373],[265,383]],[[265,383],[366,383]],[[366,383],[366,145]],[[225,366],[225,112]],[[298,383],[298,163]]],placementNotes=['Plan controls the20 side seats and left-rear door; photograph shows a different closed rectangular table arrangement. Only one plan-layout sample is authored.','Two-seat table modules and0.60m worktop depths are photo-informed estimates, not exact dimensions recoverable from the diagram.','Front teaching-desk bridge follows the labelled front teaching desk; rear photo table bridge is omitted because it is absent from the plan.','Photograph controls light timber tops, burgundy/green/yellow moulded chairs, chrome legs, brown left pinboard, right windows, teaching equipment and suspended projector.'])
 (DATA/'layout.json').write_text(json.dumps(layout,ensure_ascii=False,indent=2)+'\n')
 source=json.loads((ROOT/'data/collections/interiors/sources.json').read_text());refs=[r for r in source['sources']if r.get('local_path')in [PHOTO,PLAN]];assert len(refs)==2
 manifest=dict(room='OLD.6.06',building='Old Building',notShaw=True,sources=refs,photoSha256=sha(ROOT/PHOTO),planSha256=sha(ROOT/PLAN),sameRoomPairVerified=True,bothImagesActualNotPlaceholder=True,sourceArrangementDifference='Plan:two facing ten-seat rows and labelled front teaching desk. Photo:closed rectangular table arrangement. The model displays the plan scheme, with photographic furniture finishes/equipment only.',sourceDates='Both creation/capture dates unknown; retrieved2026-09-12 does not establish simultaneous sources or2026 use.',limitations=['Undimensioned historical teaching-layout diagram;0.03125m/pixel scale,51.36m² derived area,2.90m ceiling and furniture dimensions are estimates.','Plan and photo furniture arrangements differ and their dates are unknown; this is the plan scheme, not the photograph at the same time.','20 is the printed historical plan capacity, not certified current use or accessible/egress capacity.','Independent Old Building room sample; no geographic upper-floor registration and no complete Shaw claim.','No source photograph is used as a published texture.'])
 (DATA/'sources.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n');print('OLD606_PLAN_READY',metric.area,len(students),len(tables),flush=True)

try:import bpy
except ModuleNotFoundError:
 if __name__=='__main__':prepare()
else:
 from mathutils import Vector
 sys.path.insert(0,str(ROOT/'web/tools'))
 from build_room_samples167 import RoomGeometry
 from integrate_exterior_round194 import object_fingerprint,accepted_fingerprints,update_scene
 from refine_portsmouth_exterior207 import material_fingerprint
 from refine_sal_structure221 import stable_modifiers,rooms_state
 L=json.loads((DATA/'layout.json').read_text());S=L['scaleMetresPerPixel']
 def point(p):return Vector(((p[0]-294.5)*S,(245-p[1])*S))
 def material(g,key,color,rough=.7,metal=0):
  m=bpy.data.materials.new(PREFIX+key);m.use_nodes=True;m.diffuse_color=(*color,1);n=m.node_tree.nodes['Principled BSDF'];n.inputs['Base Color'].default_value=m.diffuse_color;n.inputs['Roughness'].default_value=rough;n.inputs['Metallic'].default_value=metal;g.materials[key]=m
 def span(g,family,key,a,b,lo,hi,depth=.14):
  a,b=Vector(a),Vector(b);d=b-a;c=(a+b)/2;g.box(family,key,(*c,(lo+hi)/2),(d.length,depth,hi-lo),math.atan2(d.y,d.x))
 def chair(g,p,target,color,teacher=False):
  p,t=Vector(p),Vector(target);angle=math.atan2(t.y-p.y,t.x-p.x)+math.pi/2;c,s=math.cos(angle),math.sin(angle)
  def at(x,y,z):return(p.x+c*x-s*y,p.y+s*x+c*y,z)
  g.box('coloured_moulded_seats',color,at(0,0,.45),(.43,.43,.045),angle)
  ring=[]
  for i in range(13):
   a=math.radians(-65+i*130/12);ring.append(at(.25*math.sin(a),.26*math.cos(a),0)[:2])
  for i in reversed(range(13)):
   a=math.radians(-65+i*130/12);ring.append(at(.228*math.sin(a),.238*math.cos(a),0)[:2])
  g.prism('coloured_curved_chair_backs',color,ring,.48,.38)
  feet=[]
  for x in [-.19,.19]:
   for y in [-.19,.19]:
    foot=at(x*1.14,y*1.14,.0125);g.box('chair_black_floor_pads','darkframe',foot,(.045,.045,.025),angle);g.tube('chrome_chair_legs','chrome',at(x*1.14,y*1.14,.022),at(x,y,.435),.014);feet.append(list(foot))
  for x in [-.19,.19]:g.tube('chrome_back_supports','chrome',at(x,.16,.43),at(x,.23,.64),.013)
  return dict(centre=list(p),target=list(t),teacher=teacher,feet=feet,color=color)
 def build():
  scene=bpy.data.scenes.new(SCENE);col=bpy.data.collections.new(COLLECTION);scene.collection.children.link(col);col['roomSample']=True;col['roomCode']='OLD.6.06';g=RoomGeometry(col,PREFIX)
  for k,c,r,m in [('plaster',(.76,.77,.72),.87,0),('woodA',(.48,.39,.25),.68,0),('woodB',(.55,.45,.30),.68,0),('woodC',(.60,.49,.34),.68,0),('tablewood',(.65,.58,.42),.57,0),('burgundy',(.17,.045,.065),.60,0),('green',(.29,.48,.30),.60,0),('yellow',(.55,.54,.22),.60,0),('chrome',(.48,.51,.50),.30,.72),('darkframe',(.022,.028,.027),.60,0),('pinboard',(.30,.23,.21),.94,0),('ceiling',(.78,.79,.74),.9,0),('whiteframe',(.80,.82,.78),.5,0),('glassroom',(.09,.16,.21),.17,0),('blindroom',(.76,.79,.76),.78,0),('doorwood',(.34,.25,.16),.70,0),('boardwhite',(.85,.86,.82),.4,0),('screenblack',(.008,.011,.012),.38,0),('cabinet',(.61,.64,.60),.64,0)]:material(g,k,c,r,m)
  g.prism('complete_plan_floor','woodA',L['outline'],-.13,.127)
  for plank in L['floorPlanks']:g.prism('timber_floor_planks',plank['material'],plank['outline'],-.003,.003)
  da,db=point(L['door']['a']),point(L['door']['b']);window_segments=[(point(w['a']),point(w['b']))for w in L['windows']]
  for a,b in zip(L['outline'],L['outline'][1:]+L['outline'][:1]):
   a,b=Vector(a),Vector(b);d=b-a;events=[(0.,1.,'wall')]
   for u,v,kind in [(da,db,'door')]+[(u,v,'window')for u,v in window_segments]:
    if abs(d.cross(u-a))>.0001 or abs(d.cross(v-a))>.0001:continue
    lo,hi=sorted(((u-a).dot(d)/d.length_squared,(v-a).dot(d)/d.length_squared))
    if lo<-.001 or hi>1.001:continue
    updated=[]
    for s,e,k in events:
     if k!='wall'or hi<=s or lo>=e:updated.append((s,e,k));continue
     if s<lo:updated.append((s,lo,'wall'))
     updated.append((max(lo,s),min(hi,e),kind))
     if hi<e:updated.append((hi,e,'wall'))
    events=updated
   for s,e,kind in events:
    p,q=a+d*s,a+d*e
    if kind!='door':span(g,'perimeter_skirting','whiteframe',p,q,0,.10,.045)
    if kind=='wall':span(g,'complete_perimeter_walls','plaster',p,q,.10,HEIGHT)
    elif kind=='door':span(g,'true_door_lintel','plaster',p,q,2.20,HEIGHT)
    else:span(g,'window_lower_wall','plaster',p,q,.10,.82);span(g,'window_upper_wall','plaster',p,q,2.72,HEIGHT)
  for w in L['windows']:
   a,b=point(w['a']),point(w['b']);d=b-a;u=d.normalized();inward=Vector((-1,0))
   for p in [a,b]:span(g,'window_jamb_frames','whiteframe',p-u*.030,p+u*.030,.80,2.74,.12)
   span(g,'timber_window_sills','tablewood',a,b,.79,.85,.27)
   for z in [.88,2.69]:span(g,'window_cross_frames','whiteframe',a,b,z-.028,z+.028,.09)
   for f in [1/3,2/3]:
    p=a+d*f;span(g,'dark_casement_mullions','darkframe',p-u*.024,p+u*.024,.88,2.69,.075)
   span(g,'restrained_window_glass','glassroom',a+inward*.01,b+inward*.01,.87,2.69,.014)
   span(g,'vertical_blind_headrail','whiteframe',a+inward*.10,b+inward*.10,2.69,2.75,.07)
   length=d.length;count=max(3,round(length/.15))
   for i in range(count):
    c=a+d*((i+.5)/count)+inward*.105;g.box('photo_vertical_blind_slats','blindroom',(*c,1.84),(.018,.095,1.66),math.radians(25))
   span(g,'window_heating_panels','whiteframe',a+u*.10+inward*.10,b-u*.10+inward*.10,.16,.64,.095)
   for f in [.22,.78]:
    p=a+d*f+inward*.03;g.box('radiator_wall_brackets','darkframe',(*p,.40),(.16,.04,.14))
  u=(db-da).normalized()
  for p in [da,db]:span(g,'door_jamb_frames','doorwood',p-u*.027,p+u*.027,0,2.24,.16)
  span(g,'door_header_frame','doorwood',da,db,2.18,2.24,.16)
  hinge,tip=point(L['door']['hinge']),point(L['door']['openTip']);span(g,'open_door_leaf','doorwood',hinge,tip,.035,2.18,.045)
  # The photograph's long brown teaching/pinboard wall is distinct from the
  # front whiteboard. Heights, joints and electrical trunking are estimates.
  a,b=point([208,112]),point([208,337]);span(g,'long_brown_pinboard_wall','pinboard',a+Vector((.085,0)),b+Vector((.085,0)),.69,2.66,.035)
  for py in [190,265]:
   p=point([208,py]);g.box('pinboard_fine_joints','darkframe',(p.x+.107,p.y,1.675),(.003,.006,1.97))
  for px in [208,381]:
   a,b=point([px,110]),point([px,337]);off=Vector((.04 if px==208 else-.04,0));span(g,'wall_electrical_trunking','whiteframe',a+off,b+off,.42,.49,.06)
  a,b=point([247,93]),point([341,93]);inside=Vector((0,-.10));span(g,'teaching_whiteboard_frame','chrome',a+inside,b+inside,.97,2.17,.055);span(g,'teaching_whiteboard_face','boardwhite',a+Vector((0,-.136)),b+Vector((0,-.136)),1.01,2.13,.018);span(g,'whiteboard_pen_tray','chrome',a+Vector((0,-.17)),b+Vector((0,-.17)),.98,1.01,.12)
  span(g,'rolled_projection_screen_case','whiteframe',a+inside,b+inside,2.38,2.52,.15);span(g,'rolled_screen_dark_bottom','darkframe',a+Vector((0,-.184)),b+Vector((0,-.184)),2.38,2.405,.018)
  for px in [236,352]:
   x,y=point([px,93]);g.box('wall_speaker_brackets','chrome',(x,y-.05,2.39),(.07,.10,.10));g.box('teaching_wall_speakers','darkframe',(x,y-.12,2.39),(.14,.12,.26))
  x,y=point(L['avCabinet']);g.box('AV_cabinet','cabinet',(x,y,.50),(.52,.56,1.0));g.box('AV_cabinet_worktop','tablewood',(x,y,1.03),(.60,.64,.06));g.box('AV_monitor_foot','darkframe',(x,y,1.075),(.22,.18,.03));g.tube('AV_monitor_stand','darkframe',(x,y,1.08),(x,y,1.23),.024);g.box('AV_monitor','screenblack',(x,y,1.38),(.44,.07,.30))
  seats=[];supports=[];table_contacts=[]
  for t in L['tables']:
   p=point(t['centre']);angle=t['angle'];c,s=math.cos(angle),math.sin(angle)
   def at(a,b,z):return(p.x+c*a-s*b,p.y+s*a+c*b,z)
   g.box('light_timber_tabletops','tablewood',(*p,.75),(t['length'],t['depth'],.04),angle)
   # Photo-supported steelT supports and small black wheels; wheel lowest
   # vertices are exactly0,not floating cylinder end caps above the floor.
   for longitudinal in [-t['length']*.32,t['length']*.32]:
    g.box('table_T_ground_crossfeet','chrome',at(longitudinal,0,.0675),(.055,.53,.075),angle)
    g.tube('table_vertical_supports','chrome',at(longitudinal,0,.085),at(longitudinal,0,.742),.025);table_contacts.append(at(longitudinal,0,.742))
    for lateral in [-.235,.235]:
     wheel=at(longitudinal,lateral,.03);g.tube('table_black_casters','darkframe',at(longitudinal-.013,lateral,.03),at(longitudinal+.013,lateral,.03),.03);supports.append(dict(kind='tablecaster',foot=list(wheel),top=list(at(longitudinal,0,.742))))
  for s in L['students']:seats.append(chair(g,point(s['centre']),point(s['target']),s['color']))
  seats.append(chair(g,point(L['teacherSeat']),point([298,145]),'burgundy',teacher=True))
  g.prism('continuous_painted_ceiling','ceiling',L['outline'],HEIGHT,.09)
  a,b=point([214,93]),point([214,397]);span(g,'photo_left_ceiling_downstand','ceiling',a,b,2.64,HEIGHT+.01,.36)
  for x,y in L['lights']:
   g.box('ceiling_strip_light_housings','whiteframe',(x,y,HEIGHT-.035),(.14,1.22,.09));g.box('ceiling_strip_light_diffusers','light',(x,y,HEIGHT-.085),(.10,1.16,.025))
  x,y=point(L['projector']);g.tube('projector_ceiling_hanger','whiteframe',(x,y,2.63),(x,y,HEIGHT+.015),.025);g.box('suspended_projector_body','whiteframe',(x,y,2.585),(.36,.29,.13));g.tube('projector_front_lens','darkframe',(x+.09,y+.14,2.585),(x+.09,y+.17,2.585),.039)
  objects=g.finish()
  for o in objects:o['roomCode']='OLD.6.06';o['destinationCollection']=COLLECTION;o['scope']='Independent Old Building historical plan scheme; photo arrangement differs; notShaw or2026survey'
  records=dict(seats=seats,supports=supports,tableContacts=table_contacts,projector=[x,y],door=dict(jambs=[list(da),list(db)],clearWidth=(db-da).length-.054,hinge=list(hinge),openTip=list(tip)))
  return scene,col,objects,records,g.solid_proof

 def tree(objects):
  from mathutils.bvhtree import BVHTree
  vs=[];fs=[];owners=[]
  for o in objects:
   if o.type!='MESH':continue
   offset=len(vs);vs.extend(o.matrix_world@v.co for v in o.data.vertices);fs.extend(tuple(offset+i for i in p.vertices)for p in o.data.polygons);owners.extend([o.name]*len(o.data.polygons))
  return BVHTree.FromPolygons(vs,fs),owners
 def checks(objects,R):
  floor,_=tree([o for o in objects if any(k in o.name for k in ['complete_plan_floor','timber_floor_planks'])]);solid,owners=tree([o for o in objects if not any(k in o.name for k in ['complete_plan_floor','timber_floor_planks','ceiling','light','projector'])]);ceiling,_=tree([o for o in objects if o.name==PREFIX+'continuous_painted_ceiling'])
  feet=[]
  for kind,points in [('studentchair',[p for s in R['seats']if not s['teacher']for p in s['feet']]),('teacherchair',[p for s in R['seats']if s['teacher']for p in s['feet']]),('tablecaster',[r['foot']for r in R['supports']])]:
   for p in points:
    hit=floor.ray_cast(Vector((p[0],p[1],.04)),Vector((0,0,-1)),.08);assert hit[0]is not None and abs(hit[0].z)<.001,('Unsupportedfoot',kind,p)
    for i in range(8):
     r=.032 if kind=='tablecaster'else.033;q=Vector((p[0]+r*math.cos(i*math.tau/8),p[1]+r*math.sin(i*math.tau/8),.04));assert floor.ray_cast(q,Vector((0,0,-1)),.08)[0]is not None,('Footedgeoutsidefloor',kind,p)
    feet.append(dict(kind=kind,point=p,actualFloorZ=hit[0].z))
  actual_contact=[]
  for name in ['chair_black_floor_pads','table_black_casters']:
   obj=next(o for o in objects if o.name==PREFIX+name);minimum=min((obj.matrix_world@v.co).z for v in obj.data.vertices);assert abs(minimum)<1e-6;actual_contact.append(dict(object=obj.name,actualMeshLowestZ=minimum,floorZ=0))
  a,b=map(Vector,R['door']['jambs']);mid=(a+b)/2;u=(b-a).normalized();inward=Vector((1,0));door=[]
  for side in [-.25,0,.25]:
   for z in [.04,.20,1.2,2.07]:
    p=mid+u*side-inward*.3;hit=solid.ray_cast(Vector((*p,z)),Vector((*inward,0)),.90);assert hit[0]is None,('Doorblocked',side,z,owners[hit[2]]if hit[2]is not None else None);door.append([side,z])
  paths=[];sections=[];body=.44
  for p,q in L['principalRoutes']:
   a,b=point(p),point(q);d=(b-a).normalized();n=Vector((-d.y,d.x));count=max(2,math.ceil((b-a).length/.14))
   for i in range(count+1):
    if i==0 and p==[208,366]:continue
    c=a.lerp(b,i/count);assert floor.ray_cast(Vector((*c,.04)),Vector((0,0,-1)),.08)[0]is not None
    for h in [.10,.45,.65,.95,1.0,1.2,1.6]:
     start=c-n*body/2;hit=solid.ray_cast(Vector((*start,h)),Vector((*n,0)),body);assert hit[0]is None,('Routeblocked',p,q,list(c),h,owners[hit[2]]if hit[2]is not None else None)
     distances=[]
     for sign in [-1,1]:
      hit=solid.ray_cast(Vector((*c,h)),Vector((*(n*sign),0)),2.5);distances.append(hit[3]if hit[0]is not None else 2.5)
     sections.append(dict(position=list(c),height=h,surfaceGap=sum(distances),centredWidth=2*min(distances)))
    paths.append(list(c))
  step=.20;coverage=[];xs=[p[0]for p in L['outline']];ys=[p[1]for p in L['outline']]
  for i in range(math.floor(min(xs)/step),math.ceil(max(xs)/step)):
   for j in range(math.floor(min(ys)/step),math.ceil(max(ys)/step)):
    x,y=(i+.5)*step,(j+.5)*step
    if not(min(xs)<x<max(xs)and min(ys)<y<max(ys)):continue
    hit=ceiling.ray_cast(Vector((x,y,1.5)),Vector((0,0,1)),1.5);assert hit[0]is not None and abs(hit[0].z-HEIGHT)<.001,('Ceilinghole',x,y);coverage.append([x,y,hit[0].z])
  lamps=[]
  for p in L['lights']:
   hit=ceiling.ray_cast(Vector((*p,HEIGHT-.04)),Vector((0,0,1)),.08);assert hit[0]is not None;lamps.append(dict(position=p,actualCeilingUnderside=hit[0].z,housingTop=HEIGHT+.01,diffuserToHousingOverlap=.0075))
  tops,_=tree([o for o in objects if o.name==PREFIX+'light_timber_tabletops']);contacts=[]
  for p in R['tableContacts']:
   hit=tops.ray_cast(Vector((p[0],p[1],.72)),Vector((0,0,1)),.06);assert hit[0]is not None;contacts.append([p[0],p[1],hit[0].z])
  projector=next(o for o in objects if o.name==PREFIX+'projector_ceiling_hanger');height=max(v.co.z for v in projector.data.vertices);assert height>HEIGHT and min(v.co.z for v in projector.data.vertices)<2.65
  hanger=dict(actualMeshTop=height,ceilingUnderside=HEIGHT,actualProjectorBodyTop=2.65,actualHangerBottom=min(v.co.z for v in projector.data.vertices),ceilingAndBodyOverlap=True)
  downstand=next(o for o in objects if o.name==PREFIX+'photo_left_ceiling_downstand');beam=dict(lowestActualZ=min(v.co.z for v in downstand.data.vertices),highestActualZ=max(v.co.z for v in downstand.data.vertices),continuousCeilingOverlap=True)
  assert len(coverage)>1200
  return dict(studentSeatCount=sum(not s['teacher']for s in R['seats']),planTeacherSeatCount=sum(s['teacher']for s in R['seats']),continuousCeilingCoverage=dict(method='Upward rays over the complete saved ceiling mesh',spacingMetres=step,probeCount=len(coverage),missCount=0,undersideHeightRange=[min(p[2]for p in coverage),max(p[2]for p in coverage)],pointDigest=hashlib.sha256(json.dumps(coverage).encode()).hexdigest(),noCeilingOpening=True),actualFloorContactMeshes=actual_contact,footSupportProbes=feet,doorClearWidth=R['door']['clearWidth'],doorwayClearRays=door,principalRouteBodyWidth=body,minimumSampledSurfaceGap=min(r['surfaceGap']for r in sections),minimumCentredSweptWidth=min(r['centredWidth']for r in sections),routeCrossSections=sections,clearRouteProbes=paths,routeLimitation='Body-width sweep checks actual saved surfaces,including chair backs and door leaf; this is not accessible route,egress or current capacity certification.',tableLegUndersideContacts=contacts,lightCeilingSupport=lamps,projectorHangerSupport=hanger,photoCeilingDownstand=beam,closedGeometry=True)
 def render(scene):
  bpy.context.window.scene=scene;world=bpy.data.worlds.new(PREFIX+'world');world.use_nodes=True;world.node_tree.nodes['Background'].inputs[0].default_value=(.77,.80,.84,1);world.node_tree.nodes['Background'].inputs[1].default_value=.5;scene.world=world
  ld=bpy.data.lights.new(PREFIX+'previewArea','AREA');ld.energy=950;ld.shape='DISK';ld.size=5;lamp=bpy.data.objects.new(ld.name,ld);scene.collection.objects.link(lamp);lamp.location=(0,0,HEIGHT-.18)
  cd=bpy.data.cameras.new(PREFIX+'previewCamera');camera=bpy.data.objects.new(cd.name,cd);scene.collection.objects.link(camera);scene.camera=camera;cd.lens=18;cd.clip_end=100
  scene.render.engine='BLENDER_EEVEE';scene.eevee.taa_render_samples=32;scene.render.resolution_x=1200;scene.render.resolution_y=900;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='AgX';views=[]
  for name,pp,tp,z,tz,label in [('default',[298,389],[294,144],1.70,1.30,'OLD.6.06两列20席与教学端'),('teaching-wall',[225,265],[310,108],1.72,1.55,'OLD.6.06教学墙与悬挂投影')]:
   p,t=point(pp),point(tp);camera.location=(*p,z);target=Vector((*t,tz));camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler();scene.render.filepath=str(OUT/('built-'+name+'.png'));bpy.ops.render.render(write_still=True);views.append(dict(name='old-606-'+name+'-interior',label=label,code='OLD',spaceId='old-606',view=dict(position=[p.x,z,-p.y],target=[t.x,tz,-t.y],fov=73.74)))
  for o in [camera,lamp]:bpy.data.objects.remove(o,do_unlink=True)
  bpy.data.cameras.remove(cd);bpy.data.lights.remove(ld);return views
 def run():
  assert sha(BASE)==SHA;bpy.ops.wm.open_mainfile(filepath=str(BASE));update_scene();expected=accepted_fingerprints(ROOT/'result/blender/stage226',SHA);original=expected;assert {o.name for o in bpy.data.objects}==set(expected) and len(original)==7858
  mats={m.name:material_fingerprint(m)for m in bpy.data.materials};mods={o.name:stable_modifiers(o)for o in bpy.data.objects};rooms=rooms_state();assert len(rooms)==23;assert len(set(n for r in rooms for n in r['objects']))==853;members={o.name:sorted(c.name for c in o.users_collection)for o in bpy.data.objects};visibility={o.name:o.hide_render for o in bpy.data.objects}
  scene,col,owned,records,solid=build();update_scene();proof=checks(owned,records);assert proof['studentSeatCount']==20;views=render(scene)
  scope='依据LSE标注Old Building、OLD.6.06、Capacity20的历史平面建立独立教学室样本。模型展示两列各10席及前方教学桌的plan方案，左后门和右侧两段窗按图定位；浅木桌、酒红/浅绿椅、左棕色大板、教学墙与悬挂投影按实照估算。照片为不同的矩形围桌布置，两图年代均未知，不主张照片同刻、2026现用容量或完整Shaw。比例、层高和隐藏构造未实测，不接全楼地理楼层。'
  space=dict(code='OLD',id='old-606',label='OLD.6.06教学室',collection=COLLECTION,gallery=views[0]['name'],scope=scope,interiorView=views[0]['view'],interiorStudy=dict(kind='room-sample',label='OLD.6.06教学室',scope=scope));col['authoringRecord']=json.dumps(space,ensure_ascii=False)
  fingerprints={o.name:object_fingerprint(o)for o in owned};bindings={o.name:[m.name for m in o.data.materials]for o in owned};component=OUT/'component.blend';bpy.data.libraries.write(str(component),{col},fake_user=True,compress=True)
  bpy.ops.wm.open_mainfile(filepath=str(BASE));update_scene();assert{o.name for o in bpy.data.objects}==set(expected)
  with bpy.data.libraries.load(str(component),link=False)as(src,dst):dst.collections=[COLLECTION]
  saved=dst.collections[0];scene=bpy.data.scenes.new(SCENE);scene.collection.children.link(saved);bpy.context.window.scene=scene;update_scene();assert checks(list(saved.all_objects),records)==proof
  assert all(object_fingerprint(bpy.data.objects[n])==v for n,v in fingerprints.items());assert all(object_fingerprint(bpy.data.objects[n])==v for n,v in original.items());assert all(material_fingerprint(bpy.data.materials[n])==v for n,v in mats.items());assert all(stable_modifiers(bpy.data.objects[n])==v for n,v in mods.items());assert rooms_state()==rooms;assert all(sorted(c.name for c in bpy.data.objects[n].users_collection)==v for n,v in members.items());assert all(bpy.data.objects[n].hide_render==v for n,v in visibility.items());assert not any(n in bpy.data.scenes['00_CAMPUS_COMPLETE'].objects for n in fingerprints);assert sha(BASE)==SHA;assert all(o.parent is None and len(o.constraints)==0 for o in saved.all_objects)
  verification=dict(savedComponentReopened=True,sourceFingerprintMethod='Accepted baseline fingerprints bound to the verified nativeSHA; all7858source objects checked after saved append',independentAcceptedObjectsVerified=len(original),allOriginalMaterialNodesVerified=len(mats),allOriginalModifierStacksVerified=len(mods),oldSpacesPreserved=len(rooms),oldSpaceUniqueObjectsPreserved=853,allOriginalMembershipsUnchanged=True,allSourceGeometryUVTransformsBindingsUnchanged=True,allOriginalVisibilityUnchanged=True,noNewRoomObjectInCampus=True,allOwnedObjectsParentlessNoConstraints=True,sourceNativeShaUnchanged=True,sourcePhotoNotUsedAsTexture=True,triangles=sum(len(f.vertices)-2 for o in saved.all_objects for f in o.data.polygons))
  audit=dict(version=227,building='OLD',baseline=str(BASE.relative_to(ROOT)),baselineSha256=SHA,componentPath=str(component.relative_to(ROOT)),componentSha256=sha(component),targetCollection=COLLECTION,destinationCollection=COLLECTION,collectionSpec=dict(kind='independent-room',name=COLLECTION,scene=SCENE),space=space,addedObjects=list(fingerprints),archivedObjects=[],changedObjects=[],addedFingerprints=fingerprints,replacementMaterialBindings=bindings,sourceManifest='data/collections/old606-room227/sources.json',planLayout='data/collections/old606-room227/layout.json',studentSeatCount=20,planTeacherSeatCount=1,scaleMetresPerPixel=S,roomAreaSquareMetres=L['roomAreaSquareMetres'],estimatedCeilingHeight=HEIGHT,gallerySuggestions=views,checks=proof,solidProof=solid,verification=verification,previews=['built-default.png','built-teaching-wall.png'],beforeEvidence=[PLAN,PHOTO],previewLighting='One temporaryArea at2.72m below the complete2.90m ceiling; no exported lights or screenshot-only geometry',sourceArrangementDifference=json.loads((DATA/'sources.json').read_text())['sourceArrangementDifference'],limitations=json.loads((DATA/'sources.json').read_text())['limitations'])
  (OUT/'audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n');print('OLD606_ROOM227_READY',len(fingerprints),verification,flush=True)
 if __name__=='__main__':run()
