"""PAN.2.01 independent historical sample from its paired LSE plan/photo.

One uniform estimated scale follows the doorway. No campus native is saved.
The complete ceiling, apertures, caster feet and principal routes are checked
again against the meshes loaded from the saved component library.
"""
from pathlib import Path
import hashlib,json,math,sys
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'result/blender/pan201-room226'
DATA=ROOT/'data/collections/pan201-room226'
BASE=ROOT/'result/blender/LSE_campus_detailed_v225.blend'
SHA='81cc0cd66d4472b7b575654330802d33b09c693829aaaeb276b12c7c17c88d04'
COLLECTION='PAN201_ROOM226_study'
SCENE='ROOM226_PAN201'
PREFIX='PAN201_R226_'
PHOTO='data/collections/interiors/images/4aef374d42c6_PAN.2.01.jpg'
PLAN='data/collections/interiors/images/9515bc0dc3c2_PAN.2.01.GIF'
HEIGHT=2.85

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def prepare():
 from shapely.geometry import Polygon,box
 DATA.mkdir(parents=True,exist_ok=True);OUT.mkdir(parents=True,exist_ok=True)
 # Trace of the inner face of the actual same-room drawing,including the
 # diagonal window wall and the right-hand folded partition boundary.
 outline=[[55,98],[114,41],[294,41],[307,61],[295,85],[307,109],[295,133],[307,158],[295,182],[295,210],[244,210],[244,216],[55,216]]
 scale=.032
 def point(p):return[(p[0]-180)*scale,(p[1]-130)*scale]
 metric=Polygon([point(p)for p in outline]);assert metric.is_valid
 tables=[dict(id='A',centre=[143,73],outline=[[126,57],[142,55],[158,59],[164,65],[160,77],[150,88],[143,92],[137,91],[128,82],[122,69],[122,62]],seats=[[133,52],[154,53],[121,70],[167,73],[132,90],[156,93]]),dict(id='B',centre=[222,74],outline=[[205,57],[222,55],[238,58],[244,65],[239,79],[229,90],[221,93],[215,89],[206,78],[202,65]],seats=[[214,53],[235,54],[198,71],[246,78],[214,91],[235,95]]),dict(id='C',centre=[96,140],outline=[[80,131],[90,123],[103,121],[111,126],[112,139],[108,153],[101,159],[95,158],[82,149],[75,139],[75,134]],seats=[[101,117],[82,126],[122,136],[121,152],[98,163],[80,151]]),dict(id='D',centre=[178,143],outline=[[164,129],[180,125],[193,129],[197,134],[195,146],[187,158],[180,164],[173,162],[162,151],[157,138],[157,132]],seats=[[170,121],[189,122],[156,142],[204,140],[168,163],[191,163]]),dict(id='E',centre=[255,143],outline=[[249,126],[261,128],[274,137],[277,142],[271,151],[258,158],[247,161],[242,156],[241,144],[243,132]],seats=[[260,117],[277,128],[277,147],[257,161],[235,151],[237,131]])]
 for t in tables:t['worldOutline']=[point(p)for p in t['outline']];t['worldCentre']=point(t['centre']);t['worldSeats']=[point(p)for p in t['seats']]
 windows=[dict(id='far1',a=[116,41],b=[167,41]),dict(id='far2',a=[176,41],b=[230,41]),dict(id='far3',a=[238,41],b=[291,41])]
 a,b=outline[0],outline[1]
 windows.append(dict(id='diagonal',a=[a[k]+.08*(b[k]-a[k])for k in range(2)],b=[a[k]+.90*(b[k]-a[k])for k in range(2)]))
 door=dict(a=[264,210],b=[295,210],hinge=[295,210],openTip=[295,182])
 grid=[];tiles=[];lights=[];x0,y0,x1,y1=metric.bounds
 def polygons(part):return [part]if part.geom_type=='Polygon'else[p for p in part.geoms if p.geom_type=='Polygon']
 for axis,lo,hi in [(0,x0,x1),(1,y0,y1)]:
  for index in range(math.ceil(lo/.6),math.floor(hi/.6)+1):
   c=index*.6;stripe=box(c-.004,y0-1,c+.004,y1+1)if axis==0 else box(x0-1,c-.004,x1+1,c+.004);part=metric.intersection(stripe)
   if not part.is_empty:
    grid.extend(list(p.exterior.coords)[:-1]for p in polygons(part)if p.area>1e-6)
 for i in range(math.floor(x0/.5),math.ceil(x1/.5)):
  for j in range(math.floor(y0/.5),math.ceil(y1/.5)):
   part=metric.intersection(box(i*.5,j*.5,(i+1)*.5,(j+1)*.5))
   if not part.is_empty:tiles.extend(dict(outline=list(p.exterior.coords)[:-1],material='carpet'+['A','B','C'][(i+2*j)%3])for p in polygons(part)if p.area>1e-6)
 for x in [-2.4,0,2.4]:
  for y in [-1.2,1.2]:
   if metric.buffer(-.1).covers(box(x-.31,y-.31,x+.31,y+.31)):lights.append([x,y])
 layout=dict(room='PAN.2.01',sourcePlan=PLAN,sourcePhoto=PHOTO,outlinePixels=outline,outline=[point(p)for p in outline],tables=tables,windows=windows,door=door,scaleMetresPerPixel=scale,scaleBasis='Estimateduniform0.032m/pixel:31pxdoorleafapproximately0.99m;drawinghasnoprinteddimensions',roomAreaSquareMetres=metric.area,studentSeatCount=30,photoTeacherSeatCount=1,carpetTiles=tiles,ceilingGridParts=grid,lights=lights,ceilingHeight=HEIGHT,placementNotes=['Top-rowchairscentresadjusted2pxinsideapproximateplan-symbolcentresforfullcasterclearance;0.064mwithintraceuncertainty.','Mobileboardpositionsarethetwonarrowright-sideplanstrokes;workstationandteacherchairarephoto-supportedestimates.'],teacherDesk=[78,184],teacherSeat=[78,200],mobileBoards=[dict(a=[276,54],b=[271,82]),dict(a=[283,88],b=[291,115])],principalRoutes=[[[279,210],[279,199]],[[279,199],[140,199]],[[140,199],[140,111]],[[220,199],[220,110]]])
 (DATA/'layout.json').write_text(json.dumps(layout,indent=2)+'\n')
 source=json.loads((ROOT/'data/collections/interiors/sources.json').read_text())
 selected=[r for r in source['sources']if r.get('local_path')in [PHOTO,PLAN]or r.get('localPath')in [PHOTO,PLAN]]
 if not selected:selected=[r for r in source['sources']if 'PAN.2.01' in json.dumps(r)]
 manifest=dict(room='PAN.2.01',sources=selected,photoSha256=sha(ROOT/PHOTO),planSha256=sha(ROOT/PLAN),officialRoomRecord='data/collections/interiors/pages/261f5b07f73e_4.htm',recordRefresh='17Aug2022 02:30',officialSeats=30,sourceInterpretation=['Bothlocalassetsvisuallyverifiedasactualsame-roomphotoandplan,notplaceholders.','Fivegroupswithsixchairsymbolseach;whitecollaborationtables,whitebacksblackcushionsandcastersmatchphoto.','Onebottom-rightentrance,diagonalandlongfarwindowwall,foldedrightpartitionfollowplan.','Phototwomobilewhiteboardsandteacherworkstationareincluded;exactequipmentpositionandfurniturechronologyunmeasured.','Continuousmineral-tileceilingand6fixtureplacementsareestimates;reflectedtilegridandlampsarevisibleinthephoto.'],limitations=['Assetcapture/creationdatesunknown;2022pagerefreshisnotasurveydateor2026currentlayout.','Drawinghasnoprintedarea/dimension;uniformdoor-basedscale,2.85mheight,verticalopeningsandfurnitureconstructionestimated.','Independentroom,noPANupper-floorgeographicregistration;nosourcephotographpublishedastexture.','Historicalplanhasdensefurniture;0.44msweptbodyverificationisnotaccessibility,egressorcurrentcapacitycertification.'])
 (DATA/'sources.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n');print('PAN201_PLAN_READY',metric.area,len(tables),len(lights),flush=True)

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
 def point(p):return Vector(((p[0]-180)*S,(p[1]-130)*S))
 def material(g,key,color,rough=.7,metal=0):
  m=bpy.data.materials.new(PREFIX+key);m.use_nodes=True;m.diffuse_color=(*color,1);n=m.node_tree.nodes['Principled BSDF'];n.inputs['Base Color'].default_value=m.diffuse_color;n.inputs['Roughness'].default_value=rough;n.inputs['Metallic'].default_value=metal;g.materials[key]=m
 def span(g,family,key,a,b,lo,hi,depth=.14):
  a,b=Vector(a),Vector(b);d=b-a;c=(a+b)/2;g.box(family,key,(*c,(lo+hi)/2),(d.length,depth,hi-lo),math.atan2(d.y,d.x))
 def chair(g,p,target,teacher=False):
  p,t=Vector(p),Vector(target);angle=math.atan2(t.y-p.y,t.x-p.x)+math.pi/2;c,s=math.cos(angle),math.sin(angle)
  def at(x,y,z):return(p.x+c*x-s*y,p.y+s*x+c*y,z)
  g.box('black_seat_cushions','cushion',at(0,0,.45),(.43,.42,.055),angle)
  if teacher:g.box('teacher_task_chair_back','cushion',at(0,.24,.72),(.43,.065,.50),angle)
  else:
   # Closed annular strip gives the photograph's curved white shell.
   ring=[]
   for i in range(13):
    a=math.radians(-70+i*140/12);ring.append(at(.245*math.sin(a),.265*math.cos(a),0)[:2])
   for i in reversed(range(13)):
    a=math.radians(-70+i*140/12);ring.append(at(.219*math.sin(a),.239*math.cos(a),0)[:2])
   g.prism('curved_white_chair_backs','shell',ring,.48,.38)
  feet=[]
  for x in [-.205,.205]:
   for y in [-.205,.205]:
    foot=at(x*1.10,y*1.10,.032);g.tube('black_caster_wheels','darkframe',at(x*1.10-.014,y*1.10,.032),at(x*1.10+.014,y*1.10,.032),.032);g.tube('chair_support_legs','darkframe'if teacher else'shell',at(x*1.10,y*1.10,.061),at(x,y,.423),.016);feet.append(list(foot))
  for x in [-.20,.20]:g.tube('chair_back_supports','shell'if not teacher else'darkframe',at(x,.18,.42),at(x,.23,.64),.013)
  return dict(centre=list(p),target=list(t),teacher=teacher,feet=feet,seatHeight=.45)
 def build():
  scene=bpy.data.scenes.new(SCENE);col=bpy.data.collections.new(COLLECTION);scene.collection.children.link(col);col['roomSample']=True;col['roomCode']='PAN.2.01';g=RoomGeometry(col,PREFIX)
  for k,c,r,m in [('plaster',(.76,.77,.73),.86,0),('shell',(.82,.84,.81),.48,0),('cushion',(.018,.022,.021),.85,0),('tablewhite',(.83,.84,.81),.53,0),('carpetA',(.14,.16,.15),.94,0),('carpetB',(.19,.21,.20),.94,0),('carpetC',(.24,.26,.24),.94,0),('ceiling',(.76,.77,.73),.9,0),('grid',(.53,.55,.52),.76,0),('darkframe',(.026,.032,.031),.6,0),('windowwhite',(.77,.80,.78),.43,0),('glassroom',(.38,.47,.49),.18,0),('blindroom',(.38,.42,.41),.68,0),('doorwood',(.39,.31,.22),.7,0),('boardwhite',(.86,.87,.84),.4,0),('metal',(.44,.47,.46),.35,.45),('screenblack',(.006,.009,.010),.38,0),('cabinet',(.39,.43,.43),.64,0)]:material(g,k,c,r,m)
  g.prism('complete_plan_floor','carpetA',L['outline'],-.13,.127)
  for tile in L['carpetTiles']:g.prism('checker_carpet_tiles',tile['material'],tile['outline'],-.003,.003)
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
    if kind!='door':span(g,'perimeter_skirting','darkframe',p,q,0,.09,.035)
    if kind=='wall':span(g,'complete_perimeter_walls','plaster',p,q,.09,HEIGHT)
    elif kind=='door':span(g,'real_door_lintel','plaster',p,q,2.20,HEIGHT)
    else:span(g,'window_solid_sill_wall','plaster',p,q,.09,.80);span(g,'window_upper_wall','plaster',p,q,2.65,HEIGHT)
  for w in L['windows']:
   a,b=point(w['a']),point(w['b']);d=b-a;u=d.normalized();n=Vector((-u.y,u.x));mid=(a+b)/2;inward=n if n.dot(-mid)>0 else-n
   for p in [a,b]:span(g,'window_jamb_frames','windowwhite',p-u*.025,p+u*.025,.79,2.67,.11)
   span(g,'window_sill_frames','windowwhite',a,b,.78,.84,.23)
   for z in [.86,1.72,2.63]:span(g,'window_cross_frames','windowwhite',a,b,z-.025,z+.025,.085)
   for f in [1/2]:
    p=a+d*f;span(g,'window_mullions','windowwhite',p-u*.022,p+u*.022,.84,2.65,.08)
   span(g,'restrained_reflective_window_glass','glassroom',a+inward*.015,b+inward*.015,.85,2.62,.014)
   span(g,'venetian_blind_headrail','windowwhite',a+inward*.09,b+inward*.09,2.60,2.66,.065)
   for z in [1.15+i*.042 for i in range(35)]:span(g,'venetian_blind_slats','blindroom',a+u*.035+inward*.105,b-u*.035+inward*.105,z,z+.013,.035)
   for f in [.25,.75]:
    p=a+d*f+inward*.105;g.tube('blind_control_tapes','windowwhite',(*p,1.15),(*p,2.61),.004)
  u=(db-da).normalized()
  for p in [da,db]:span(g,'door_jamb_frames','doorwood',p-u*.027,p+u*.027,0,2.24,.16)
  span(g,'door_header_frame','doorwood',da,db,2.18,2.24,.16)
  hinge,tip=point(L['door']['hinge']),point(L['door']['openTip']);span(g,'open_door_leaf','doorwood',hinge,tip,.035,2.18,.045)
  # Fixed teaching board on the solid left wall,as seen in the photograph.
  a,b=point([55,122]),point([55,176]);normal=Vector((.09,0));span(g,'fixed_whiteboard_frame','metal',a+normal,b+normal,.90,2.21,.055);span(g,'fixed_whiteboard_writing_face','boardwhite',a+Vector((.126,0)),b+Vector((.126,0)),.94,2.17,.018);span(g,'fixed_whiteboard_pen_tray','metal',a+Vector((.16,0)),b+Vector((.16,0)),.91,.94,.11)
  x,y=point(L['teacherDesk']);g.box('teacher_AV_cabinet','cabinet',(x,y,.40),(.78,.45,.80));g.box('teacher_AV_worktop','tablewhite',(x,y,.83),(.96,.51,.06));g.box('teacher_monitor_foot','darkframe',(x,y-.10,.875),(.20,.17,.03));g.tube('teacher_monitor_stand','darkframe',(x,y-.10,.89),(x,y-.10,1.04),.025);g.box('teacher_monitor','screenblack',(x,y-.10,1.18),(.40,.06,.29));g.box('visualiser_base','darkframe',(x,y+.24,.88),(.19,.20,.04));g.tube('visualiser_arm','darkframe',(x,y+.24,.90),(x+.03,y+.27,1.18),.012);g.tube('visualiser_arm','darkframe',(x+.03,y+.27,1.18),(x+.15,y+.24,1.25),.012)
  seats=[];supports=[]
  for t in L['tables']:
   g.prism('five_white_collaborative_tabletops','tablewhite',t['worldOutline'],.72,.045);center=Vector(t['worldCentre'])
   # Three supports are deliberately inside each actual table footprint.
   for fraction in [0,.34,.67]:
    v=Vector(t['worldOutline'][int(fraction*len(t['worldOutline']))]);p=center.lerp(v,.58);foot=center.lerp(v,.67);g.tube('table_white_support_legs','shell',(*foot,.025),(*p,.725),.025);supports.append(dict(kind='table',foot=[*foot,.025],top=[*p,.725]))
   for p in t['worldSeats']:seats.append(chair(g,p,center))
  seats.append(chair(g,point(L['teacherSeat']),point(L['teacherDesk']),teacher=True))
  boardfeet=[]
  for board in L['mobileBoards']:
   a,b=point(board['a']),point(board['b']);d=b-a;u=d.normalized();n=Vector((-u.y,u.x));angle=math.atan2(d.y,d.x);c=(a+b)/2
   span(g,'two_mobile_whiteboard_frames','metal',a,b,.91,2.15,.055);span(g,'mobile_whiteboard_writing_faces','boardwhite',a+u*.035+n*.034,b-u*.035+n*.034,.95,2.11,.019)
   for p in [a+u*.07,b-u*.07]:
    g.tube('mobile_board_uprights','metal',(*p,.08),(*p,.95),.022)
    span(g,'mobile_board_ground_bases','metal',p-n*.16,p+n*.16,.045,.075,.045)
    for sign in [-1,1]:
     foot=p+n*sign*.16;g.tube('mobile_board_casters','darkframe',(*(foot-u*.013),.03),(*(foot+u*.013),.03),.03);boardfeet.append([*foot,.03])
  # Entire room projection remains a closed,continuous mineral-tile ceiling.
  g.prism('continuous_mineral_tile_ceiling','ceiling',L['outline'],HEIGHT,.075)
  for ring in L['ceilingGridParts']:g.prism('fine_ceiling_grid_seams','grid',ring,HEIGHT-.006,.007)
  for x,y in L['lights']:
   g.box('ceiling_lamp_housings','grid',(x,y,HEIGHT-.015),(.62,.62,.055));g.box('ceiling_light_diffusers','light',(x,y,HEIGHT-.048),(.55,.55,.022))
  objects=g.finish()
  for o in objects:o['roomCode']='PAN.2.01';o['destinationCollection']=COLLECTION;o['scope']='Independentpairedhistoricalroom;notgeographicPANregistrationor2026survey'
  records=dict(seats=seats,supports=supports,boardFeet=boardfeet,door=dict(jambs=[list(da),list(db)],clearWidth=(db-da).length-.054,hinge=list(hinge),openTip=list(tip)))
  return scene,col,objects,records,g.solid_proof

 def tree(objects):
  from mathutils.bvhtree import BVHTree
  vs=[];fs=[];owners=[]
  for o in objects:
   if o.type!='MESH':continue
   off=len(vs);vs.extend(o.matrix_world@v.co for v in o.data.vertices);fs.extend(tuple(off+i for i in f.vertices)for f in o.data.polygons);owners.extend([o.name]*len(o.data.polygons))
  return BVHTree.FromPolygons(vs,fs),owners
 def inside(x,y):
  result=False
  for a,b in zip(L['outline'],L['outline'][1:]+L['outline'][:1]):
   if(a[1]>y)!=(b[1]>y)and x<(b[0]-a[0])*(y-a[1])/(b[1]-a[1])+a[0]:result=not result
  return result
 def checks(objects,R):
  floor,_=tree([o for o in objects if any(k in o.name for k in ['complete_plan_floor','checker_carpet_tiles'])]);solid,owners=tree([o for o in objects if not any(k in o.name for k in ['complete_plan_floor','checker_carpet_tiles','ceiling','lamp'])]);ceil,_=tree([o for o in objects if o.name==PREFIX+'continuous_mineral_tile_ceiling'])
  feet=[]
  for kind,ps in [('studentchair',[p for s in R['seats']if not s['teacher']for p in s['feet']]),('teacherchair',[p for s in R['seats']if s['teacher']for p in s['feet']]),('table',[r['foot']for r in R['supports']]),('mobileboard',R['boardFeet'])]:
   for p in ps:
    hit=floor.ray_cast(Vector((p[0],p[1],.04)),Vector((0,0,-1)),.08);assert hit[0]is not None and abs(hit[0].z)<.001,('Unsupportedfoot',kind,p,hit)
    if 'chair'in kind or kind=='mobileboard':
     for a in range(8):
      q=Vector((p[0]+.034*math.cos(a*math.tau/8),p[1]+.034*math.sin(a*math.tau/8),.04));edge=floor.ray_cast(q,Vector((0,0,-1)),.08);assert edge[0]is not None,('Casteredgeoutsideroom',kind,p,list(q))
    feet.append(dict(kind=kind,point=p,floorZ=hit[0].z))
  door=[];a,b=map(Vector,R['door']['jambs']);mid=(a+b)/2;u=(b-a).normalized();inward=Vector((0,-1))
  for side in [-.22,0,.22]:
   for z in [.04,.20,1.2,2.07]:
    p=mid+u*side-inward*.3;hit=solid.ray_cast(Vector((*p,z)),Vector((*inward,0)),.9);assert hit[0]is None,('Doorblocked',side,z,owners[hit[2]]if hit[2]is not None else None);door.append([side,z])
  paths=[];cross_sections=[]
  for p,q in L['principalRoutes']:
   a,b=point(p),point(q);d=(b-a).normalized();perp=Vector((-d.y,d.x));count=max(2,math.ceil((b-a).length/.14))
   for i in range(count+1):
    c=a.lerp(b,i/count)
    # Skip the boundary itself for the floor sample,while checking the true door separately.
    if i==0 and p==[279,210]:continue
    hit=floor.ray_cast(Vector((*c,.04)),Vector((0,0,-1)),.08);assert hit[0]is not None,('Routeofffloor',p,q,list(c))
    for h in [.20,.65,1.2]:
     start=c-perp*.22;hit=solid.ray_cast(Vector((*start,h)),Vector((*perp,0)),.44);assert hit[0]is None,('Routeblocked',p,q,list(c),h,owners[hit[2]]if hit[2]is not None else None)
    for h in [.20,.65,1.2]:
     distances=[]
     for sign in [-1,1]:
      hit=solid.ray_cast(Vector((*c,h)),Vector((*(perp*sign),0)),2.0);distances.append(hit[3]if hit[0]is not None else 2.0)
     cross_sections.append(dict(position=list(c),height=h,surfaceGap=sum(distances),centeredWidth=2*min(distances)))
    paths.append(list(c))
  coverage=[];step=.20;xs=[p[0]for p in L['outline']];ys=[p[1]for p in L['outline']]
  for i in range(math.floor(min(xs)/step),math.ceil(max(xs)/step)):
   for j in range(math.floor(min(ys)/step),math.ceil(max(ys)/step)):
    x,y=(i+.5)*step,(j+.5)*step
    if not inside(x,y):continue
    hit=ceil.ray_cast(Vector((x,y,1.5)),Vector((0,0,1)),1.5);assert hit[0]is not None and abs(hit[0].z-HEIGHT)<.001,('Ceilinghole',x,y,hit);coverage.append([x,y,hit[0].z])
  lamps=[]
  for p in L['lights']:
   hit=ceil.ray_cast(Vector((*p,HEIGHT-.04)),Vector((0,0,1)),.08);assert hit[0]is not None;lamps.append(dict(position=p,actualCeilingUnderside=hit[0].z))
  # Upward rays from every leg top intersect an actual table underside.
  tabletops,_=tree([o for o in objects if o.name==PREFIX+'five_white_collaborative_tabletops']);tablehits=[]
  for leg in R['supports']:
   p=leg['top'];hit=tabletops.ray_cast(Vector((p[0],p[1],.70)),Vector((0,0,1)),.06);assert hit[0]is not None;tablehits.append([p[0],p[1],hit[0].z])
  assert len(coverage)>900
  return dict(studentSeatCount=sum(not s['teacher']for s in R['seats']),photoTeacherSeatCount=sum(s['teacher']for s in R['seats']),continuousCeilingCoverage=dict(method='Savedmeshupwardraysacrosstheactualcompleteinteriorpolygon',spacingMetres=step,probeCount=len(coverage),missCount=0,undersideHeightRange=[min(p[2]for p in coverage),max(p[2]for p in coverage)],pointDigest=hashlib.sha256(json.dumps(coverage).encode()).hexdigest(),noCeilingOpening=True),footSupportProbes=feet,doorClearWidth=R['door']['clearWidth'],doorwayClearRays=door,principalRouteBodyWidth=.44,routeWidthInterpretation='0.44misasweptbodycheck,notaroute-widthstandardoraccessibilitycertification;surfacegapsuseactualsavedchairback/leg/table/wallmeshesatthreeheights',minimumSampledSurfaceGap=min(r['surfaceGap']for r in cross_sections),minimumCenteredSweptWidth=min(r['centeredWidth']for r in cross_sections),routeCrossSections=cross_sections,clearRouteProbes=paths,tableLegUndersideContacts=tablehits,lightCeilingSupport=lamps,closedGeometry=True)
 def render(scene):
  bpy.context.window.scene=scene;world=bpy.data.worlds.new(PREFIX+'world');world.use_nodes=True;world.node_tree.nodes['Background'].inputs[0].default_value=(.76,.80,.84,1);world.node_tree.nodes['Background'].inputs[1].default_value=.5;scene.world=world
  ld=bpy.data.lights.new(PREFIX+'previewArea','AREA');ld.energy=850;ld.shape='DISK';ld.size=5;lamp=bpy.data.objects.new(ld.name,ld);scene.collection.objects.link(lamp);lamp.location=(0,0,HEIGHT-.16)
  cd=bpy.data.cameras.new(PREFIX+'previewCamera');camera=bpy.data.objects.new(cd.name,cd);scene.collection.objects.link(camera);scene.camera=camera;cd.lens=18;cd.clip_end=100
  scene.render.engine='BLENDER_EEVEE';scene.eevee.taa_render_samples=32;scene.render.resolution_x=1200;scene.render.resolution_y=900;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='AgX'
  views=[]
  for name,pp,tp,z,tz,label in [('default',[65,206],[191,100],1.70,1.25,'PAN.2.01三角协作桌与窗边'),('teaching-wall',[259,66],[65,174],1.68,1.35,'PAN.2.01教学墙与协作座位')]:
   p,t=point(pp),point(tp);camera.location=(*p,z);target=Vector((*t,tz));camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler();scene.render.filepath=str(OUT/('built-'+name+'.png'));bpy.ops.render.render(write_still=True);views.append(dict(name='pan-201-'+name+'-interior',label=label,spaceId='pan-201',view=dict(position=[p.x,z,-p.y],target=[t.x,tz,-t.y],fov=73.74)))
  for o in [camera,lamp]:bpy.data.objects.remove(o,do_unlink=True)
  bpy.data.cameras.remove(cd);bpy.data.lights.remove(ld);return views
 def run():
  assert sha(BASE)==SHA;bpy.ops.wm.open_mainfile(filepath=str(BASE));update_scene();expected=accepted_fingerprints(ROOT/'result/blender/stage225',SHA);original={o.name:object_fingerprint(o)for o in bpy.data.objects};assert original==expected and len(original)==7809
  mats={m.name:material_fingerprint(m)for m in bpy.data.materials};mods={o.name:stable_modifiers(o)for o in bpy.data.objects};rooms=rooms_state();assert len(rooms)==22;assert len(set(n for r in rooms for n in r['objects']))==804;members={o.name:sorted(c.name for c in o.users_collection)for o in bpy.data.objects};vis={o.name:o.hide_render for o in bpy.data.objects}
  scene,col,owned,records,solid=build();update_scene();proof=checks(owned,records);assert proof['studentSeatCount']==30;views=render(scene)
  scope='依据LSE同房号历史平面与实照建立PAN.2.01独立协作教室样本。完整描摹斜角窗边、折线隔断及右下实际门洞，5组三角桌共30个计划学生座位；白壳黑座脚轮椅、固定教学白板、两块移动白板、教师AV工作台和窗百叶按照片估算。连续矿棉板吊顶覆盖完整周界；门宽比例、层高及家具细节未实测，不接地理楼层，不表示2026当前全楼。'
  space=dict(code='PAN',id='pan-201',label='PAN.2.01协作教室',collection=COLLECTION,gallery=views[0]['name'],scope=scope,interiorView=views[0]['view'],interiorStudy=dict(kind='room-sample',label='PAN.2.01协作教室',scope=scope));col['authoringRecord']=json.dumps(space,ensure_ascii=False)
  fingerprints={o.name:object_fingerprint(o)for o in owned};bindings={o.name:[m.name for m in o.data.materials]for o in owned};component=OUT/'component.blend';bpy.data.libraries.write(str(component),{col},fake_user=True,compress=True)
  bpy.ops.wm.open_mainfile(filepath=str(BASE));update_scene();assert{o.name:object_fingerprint(o)for o in bpy.data.objects}==expected
  with bpy.data.libraries.load(str(component),link=False)as(src,dst):dst.collections=[COLLECTION]
  saved=dst.collections[0];scene=bpy.data.scenes.new(SCENE);scene.collection.children.link(saved);bpy.context.window.scene=scene;update_scene();assert checks(list(saved.all_objects),records)==proof
  assert all(object_fingerprint(bpy.data.objects[n])==v for n,v in fingerprints.items());assert all(object_fingerprint(bpy.data.objects[n])==v for n,v in original.items());assert all(material_fingerprint(bpy.data.materials[n])==v for n,v in mats.items());assert all(stable_modifiers(bpy.data.objects[n])==v for n,v in mods.items());assert rooms_state()==rooms;assert all(sorted(c.name for c in bpy.data.objects[n].users_collection)==v for n,v in members.items());assert all(bpy.data.objects[n].hide_render==v for n,v in vis.items());assert not any(n in bpy.data.scenes['00_CAMPUS_COMPLETE'].objects for n in fingerprints);assert sha(BASE)==SHA
  verification=dict(savedComponentReopened=True,independentAcceptedObjectsVerified=len(original),allOriginalMaterialNodesVerified=len(mats),allOriginalModifierStacksVerified=len(mods),oldSpacesPreserved=len(rooms),oldSpaceUniqueObjectsPreserved=804,allOriginalMembershipsUnchanged=True,allSourceGeometryUVTransformsBindingsUnchanged=True,allOriginalVisibilityUnchanged=True,noNewRoomObjectInCampus=True,sourceNativeShaUnchanged=True,sourcePhotoNotUsedAsTexture=True,triangles=sum(len(f.vertices)-2 for o in saved.all_objects for f in o.data.polygons))
  audit=dict(version=226,building='PAN',baseline=str(BASE.relative_to(ROOT)),baselineSha256=SHA,componentPath=str(component.relative_to(ROOT)),componentSha256=sha(component),targetCollection=COLLECTION,destinationCollection=COLLECTION,collectionSpec=dict(kind='independent-room',name=COLLECTION,scene=SCENE),space=space,addedObjects=list(fingerprints),archivedObjects=[],changedObjects=[],addedFingerprints=fingerprints,replacementMaterialBindings=bindings,sourceManifest='data/collections/pan201-room226/sources.json',planLayout='data/collections/pan201-room226/layout.json',studentSeatCount=30,photoTeacherSeatCount=1,scaleMetresPerPixel=S,roomAreaSquareMetres=L['roomAreaSquareMetres'],estimatedCeilingHeight=HEIGHT,gallerySuggestions=views,checks=proof,solidProof=solid,verification=verification,previews=['built-default.png','built-teaching-wall.png'],beforeEvidence=[PLAN,PHOTO],previewLighting='One temporaryreviewArea at2.69m belowthecomplete2.85mceiling;noexportedlightsorpreview-onlygeometry',limitations=json.loads((DATA/'sources.json').read_text())['limitations'])
  (OUT/'audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n');print('PAN201_ROOM226_READY',len(fingerprints),verification,flush=True)
 if __name__=='__main__':run()
