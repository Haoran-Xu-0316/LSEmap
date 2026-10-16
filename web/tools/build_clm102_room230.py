"""CLM.1.02 independent historical classroom component.

Fixed configuration for Blender's Text Editor and the MachineLearning Python.
Five counted six-chair pods follow the actual plan. No campus attachment,
photographic textures, measured-dimension claim or current-capacity claim.
"""
from pathlib import Path
import hashlib,json,math,sys
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'result/blender/clm102-room230'
DATA=ROOT/'data/collections/clm102-room230'
BASE=ROOT/'result/blender/LSE_campus_detailed_v229.blend'
SHA='2ec7b3a42776f870e99b2a63f83f0736b70a0f2400a145b477f3d80bf54baa18'
COLLECTION='CLM102_ROOM230_study'
SCENE='ROOM230_CLM102'
PREFIX='CLM102_R230_'
PLAN='data/collections/interiors/images/d8b44f24810a_CLM.1.02.GIF'
PHOTO='data/collections/interiors/images/8058fb5223e9_CLM.1.02.jpg'
SCALE=.023
HEIGHT=3.38

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def xy(q):return[(q[0]-320)*SCALE,(155-q[1])*SCALE]
def prepare():
 from shapely.geometry import Polygon,box,Point
 from PIL import Image,ImageDraw
 DATA.mkdir(parents=True,exist_ok=True);OUT.mkdir(parents=True,exist_ok=True)
 outline=[[42,16],[202,16],[202,41],[237,41],[237,16],[404,16],[404,41],[438,41],[438,16],[600,16],[600,95],[585,95],[585,291],[438,291],[438,266],[399,266],[399,291],[237,291],[237,266],[200,266],[200,291],[56,291],[56,95],[42,95]]
 poly=Polygon([xy(p)for p in outline]);assert poly.is_valid
 pods=[
  dict(id='upperLeft',outline=[[133,103],[135,78],[146,58],[158,49],[174,57],[190,74],[194,91],[184,104],[160,113],[141,117],[134,114]],chairs=[[133,56],[171,45],[200,80],[187,113],[151,126],[122,94]]),
  dict(id='upperRight',outline=[[471,74],[487,64],[520,61],[536,65],[538,80],[530,102],[515,121],[501,126],[488,116],[476,96],[470,82]],chairs=[[486,56],[526,56],[548,89],[523,124],[487,124],[463,89]]),
  dict(id='central',outline=[[294,129],[311,121],[339,121],[356,128],[357,141],[346,163],[330,183],[319,184],[304,171],[292,151],[291,137]],chairs=[[305,110],[345,110],[364,146],[346,180],[305,180],[285,146]]),
  dict(id='lowerLeft',outline=[[186,174],[202,165],[233,161],[249,166],[253,178],[245,199],[230,220],[219,227],[207,220],[191,198],[184,184]],chairs=[[201,154],[242,155],[263,187],[240,224],[202,224],[179,187]]),
  dict(id='lowerRight',outline=[[412,177],[429,158],[442,154],[456,160],[474,180],[478,199],[473,211],[452,218],[428,219],[413,213],[407,202],[409,188]],chairs=[[423,154],[462,155],[482,188],[462,224],[420,224],[402,188]])]
 seats=[]
 for pod in pods:
  shape=Polygon([xy(p)for p in pod['outline']]);assert shape.is_valid
  pod['centre']=list(shape.centroid.coords)[0];pod['metreOutline']=[xy(p)for p in pod['outline']]
  centre=shape.centroid;pod['supports']=[list(centre.coords)[0]]
  for v in [pod['metreOutline'][i]for i in [0,len(pod['metreOutline'])//3,2*len(pod['metreOutline'])//3]]:pod['supports'].append([centre.x+(v[0]-centre.x)*.60,centre.y+(v[1]-centre.y)*.60])
  for i,p in enumerate(pod['chairs']):seats.append(dict(id=pod['id']+str(i+1),pixel=p,centre=xy(p),target=pod['centre']))
 assert len(seats)==30
 doors=[dict(id='main',a=[295,16],b=[346,16],hinge=[346,16],openTip=[346,65]),dict(id='left',a=[42,42],b=[42,88],hinge=[42,88],openTip=[87,88]),dict(id='right',a=[600,42],b=[600,88],hinge=[600,88],openTip=[648,88])]
 windows=[dict(id='leftBay',a=[56,291],b=[200,291]),dict(id='middleBay',a=[237,291],b=[399,291]),dict(id='rightBay',a=[438,291],b=[585,291])]
 tiles=[];grid=[];x0,y0,x1,y1=poly.bounds
 def parts(v):return[v]if v.geom_type=='Polygon'else[g for g in v.geoms if g.geom_type=='Polygon']
 for i in range(math.floor(x0/.50),math.ceil(x1/.50)):
  for j in range(math.floor(y0/.50),math.ceil(y1/.50)):
   q=poly.intersection(box(i*.5,j*.5,(i+1)*.5,(j+1)*.5))
   if not q.is_empty:tiles.extend(dict(outline=list(t.exterior.coords)[:-1],material='carpet'+['A','B','C'][(i+2*j)%3])for t in parts(q)if t.area>1e-7)
 for axis,lo,hi in [(0,x0,x1),(1,y0,y1)]:
  for i in range(math.ceil(lo/.6),math.floor(hi/.6)+1):
   v=i*.6;q=poly.intersection(box(v-.004,y0-1,v+.004,y1+1)if axis==0 else box(x0-1,v-.004,x1+1,v+.004))
   if not q.is_empty:grid.extend(list(t.exterior.coords)[:-1]for t in parts(q)if t.area>1e-7)
 layout=dict(room='CLM.1.02',outlinePixels=outline,outline=[xy(p)for p in outline],scaleMetresPerPixel=SCALE,scaleBasis='Estimated0.023m/pixel from51px central door approximately1.17m;cropped plan has no printed measured dimension',roomAreaSquareMetres=poly.area,studentSeatCount=30,printedCapacity=None,teacherSeatCount=0,pods=pods,seats=seats,doors=doors,windows=windows,teacherDesk=dict(a=[126,217],b=[150,244]),ceilingGridParts=grid,carpetTiles=tiles,lights=[[230,80],[420,80],[140,230],[330,230],[530,230]],principalRoutes=[[[320.5,17],[320.5,70]]])
 if (DATA/'navigation-routes.json').exists():
  navigation=json.loads((DATA/'navigation-routes.json').read_text())
  if navigation.get('allFiveGroupsReachable'):layout['principalRoutes']=navigation['principalRoutes']
 (DATA/'layout.json').write_text(json.dumps(layout,ensure_ascii=False,indent=2)+'\n')
 source=json.loads((ROOT/'data/collections/interiors/sources.json').read_text());refs=[r for r in source['sources']if r.get('local_path')in[PLAN,PHOTO]];assert len(refs)==2
 limitations=['历史平面创建与照片拍摄日期未知；网页2022年刷新时间与2026年检索时间均不是拍摄或测绘日期。','平面片段无可见房号、容量或尺寸文字；同房号配对依据官方归档路径与同型五组桌、教室长向布局，不能由该片段单独验证房号或现用容量。','比例0.023m/像素、层高3.38m、门高2.43m、窗台0.91m、窗顶2.94m、隐藏构造和家具竖向尺寸均为估算。','实际平面可数5张六人小组桌及30把学生椅，另有左下AV讲台；没有教师椅符号，不增补座位，不代表核定容量。','平面控制五组桌椅、三处门洞、两处上墙凹口及下侧窗湾与结构柱；照片控制木饰面、黑壳橙褐座面、白色圆角桌、地毯和灯具类型。','下侧多线墙带结合照片右侧深木窗台，解释为三段窗湾；具体窗格、竖向尺寸与未见外景估算。','左侧板墙符号结合照片显示屏与两侧白板，解释为教学端；照片与平面年代及设备位置未核实同期。','照片中可移动白板的精确足架位置未由平面固定；本模型将双板沿教学端布置，保留五组来源椅位。','木墙分格、古典门套和墙顶线脚依据照片概括；隐藏立面分格与三处门扇同型处理均为估算。','连续完整吊顶与悬挂线灯按照片类型建立；具体网格、灯位、吊杆和通风设备位置估算。','独立Clement House教室研究，不作校园地理或楼层配准、2026年现况、全楼覆盖、无障碍或疏散认证。','源照片仅供私下核对，不作为发布纹理；全宽全高通道为估计几何探针，不作规范净宽声明。']
 manifest=dict(room='CLM.1.02',sources=refs,planSha256=sha(ROOT/PLAN),photoSha256=sha(ROOT/PHOTO),sameRoomPairVerified=True,bothImagesActualNotPlaceholder=True,sourceInterpretation=['Plan is an actual architectural room diagram,withfive rounded triangular tables andsix chairs per table,three door swings,left AV station,upper structural notches andlower window bays. No printed capacity is visible in the cropped image.','Official photo is a real timber-panelled classroom withwhite curved table tops,black chairs withorange-brown seats,black legs,grey carpet squares,a wall teaching display andtwo whiteboards,ornate doorcase andwhite suspended linear lights.','Exact chronology and lower-wall glazing heights are unknown;photo provides finishes andequipment types,plan controls layout.'],limitations=limitations)
 (DATA/'sources.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
 im=Image.open(ROOT/PLAN).convert('RGB');d=ImageDraw.Draw(im);d.line(outline+[outline[0]],fill=(190,30,30),width=2)
 for seat in seats:
  x,y=seat['pixel'];d.ellipse((x-2,y-2,x+2,y+2),fill=(30,50,200))
 im.save(DATA/'registered-plan.png');print('CLM102_LAYOUT_READY',poly.area,len(seats),flush=True)

def solve_navigation():
 """Prepare body-clear paths against actual saved geometry,without moving furniture."""
 import heapq
 from shapely.geometry import Polygon,LineString,Point
 from shapely.ops import unary_union,nearest_points
 from shapely.prepared import prep
 layout=json.loads((DATA/'layout.json').read_text());source=json.loads((DATA/'navigation-surfaces.json').read_text())
 assert source['componentSha256']==sha(OUT/'component.blend')
 shapes=[];owners=[]
 for item in source['surfaces']:
  q=item['polygon'];shape=Polygon(q)if len(q)>=3 else LineString(q)
  # Vertical saved faces project to lines: retain them before polygon repair.
  if shape.area<1e-12:shape=LineString(q).convex_hull
  elif not shape.is_valid:shape=shape.buffer(0)
  if shape.is_empty:continue
  shapes.append(shape);owners.append(item['owner'])
 obstacles=unary_union(shapes);room=Polygon(layout['outline']);radius=.23
 free=room.buffer(-radius).difference(obstacles.buffer(radius));prepared=prep(free)
 step=.05;x0,y0,x1,y1=room.bounds
 def coord(n):return(x0+n[0]*step,y0+n[1]*step)
 nodes={(i,j)for i in range(math.ceil((x1-x0)/step)+1)for j in range(math.ceil((y1-y0)/step)+1)if prepared.contains(Point(coord((i,j))))}
 def connected(a,b):return prepared.covers(LineString([a,b]))
 def anchor(p):
  options=sorted(nodes,key=lambda n:(coord(n)[0]-p[0])**2+(coord(n)[1]-p[1])**2)
  return next((n for n in options[:40]if connected(p,coord(n))),None)
 def path(a,b):
  if not prepared.contains(Point(a))or not prepared.contains(Point(b)):return None
  start,end=anchor(a),anchor(b)
  if start is None or end is None:return None
  queue=[(0,start)];cost={start:0};previous={}
  while queue:
   _,node=heapq.heappop(queue)
   if node==end:break
   for dx,dy in[(1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)]:
    nxt=(node[0]+dx,node[1]+dy)
    if nxt not in nodes or not connected(coord(node),coord(nxt)):continue
    candidate=cost[node]+math.hypot(dx,dy)
    if candidate>=cost.get(nxt,1e99):continue
    cost[nxt]=candidate;previous[nxt]=node;heapq.heappush(queue,(candidate+math.dist(nxt,end),nxt))
  if end not in cost:return None
  order=[end]
  while order[-1]!=start:order.append(previous[order[-1]])
  points=[a]+[coord(n)for n in reversed(order)]+[b];result=[points[0]];index=0
  while index<len(points)-1:
   farthest=next(j for j in range(len(points)-1,index,-1)if connected(points[index],points[j]));result.append(points[farthest]);index=farthest
  return result
 def pixel(p):return[p[0]/SCALE+320,155-p[1]/SCALE]
 start=xy([320.5,32]);teaching=xy([105,160]);entrance=path(start,teaching);assert entrance
 routes=[[[320.5,17],[320.5,32]]]+[[pixel(a),pixel(b)]for a,b in zip(entrance,entrance[1:])];groups=[];candidateOutcomes=[]
 for pod in layout['pods']:
  candidates=[]
  for seat in [v for v in layout['seats']if v['id'].startswith(pod['id'])]:
   c,t=seat['centre'],seat['target'];d=[c[0]-t[0],c[1]-t[1]];length=math.hypot(*d);approach=[c[0]+d[0]/length*.55,c[1]+d[1]/length*.55];points=path(teaching,approach)
   candidateOutcomes.append(dict(group=pod['id'],seatId=seat['id'],approachPoint=pixel(approach),reachable=points is not None,reason='Connected body-clear path found'if points else'Approach or connecting route blocked by saved furniture at0.23m planning radius'))
   if points:candidates.append((sum(math.dist(a,b)for a,b in zip(points,points[1:])),seat,points,approach))
  assert candidates,('GroupNotReachable',pod['id'])
  length,seat,points,approach=min(candidates,key=lambda v:v[0]);segments=[[pixel(a),pixel(b)]for a,b in zip(points,points[1:])];routes.extend(segments);groups.append(dict(group=pod['id'],reachable=True,seatId=seat['id'],seatPixel=seat['pixel'],approachPoint=pixel(approach),distanceBehindChairCentre=.55,lengthFromTeachingPoint=length,continuousPathFromTeachingPoint=[pixel(p)for p in points],continuousPathFromEntry=[[320.5,17]]+[pixel(p)for p in entrance]+[pixel(p)for p in points[1:]]))
 failed=LineString([xy([220,140]),xy([275,165])]);nearest=min(zip(shapes,owners),key=lambda item:failed.distance(item[0]));distance=failed.distance(nearest[0]);near=nearest_points(failed,nearest[0]);assert failed.buffer(.22,cap_style=2).intersects(obstacles),'ShortcutDiagnosticUnexpectedlyClear'
 diagnosis=dict(candidate=[[220,140],[275,165]],passed=False,bodyWidth=.44,verticalRange=[.04,2.10],nearestSavedMesh=nearest[1],minimumCentrelineToObstruction=distance,maximumSymmetricBodyWidthAtThisCandidate=distance*2,closestSourcePixels=[pixel(list(p.coords)[0])for p in near],intersectedFamilies=sorted(set(owner for shape,owner in zip(shapes,owners)if failed.buffer(.22,cap_style=2).intersects(shape))),reason='Actual saved furniture surfaces intersect the complete body corridor. Candidate retained as a failed shortcut; source furniture remains unchanged.')
 proof=dict(componentSha256=source['componentSha256'],geometryFingerprints=json.loads((OUT/'audit.json').read_text())['addedFingerprints'],principalRoutes=routes,method='Actual saved world triangles clipped to0.04–2.10m,projected to floor. Planar obstacles inflated0.23m;0.05m grid Astar with every edge and simplified segment covered by free space. Final complete0.44m rectangular sweeps and0.22m radius turn volumes are verified against actual saved triangles in Blender twice.',startPixel=[320.5,17],teachingPoint=[105,160],bodyProbeWidth=.44,planningRadius=.23,groups=groups,allSeatApproachCandidates=candidateOutcomes,failedCandidates=[diagnosis],allFiveGroupsReachable=True,routeScope='Entrance to teaching point then continuous approaches behind one chair in every pod;geometric probe only,not code or accessibility approval')
 attempts=json.loads((DATA/'navigation-attempts.json').read_text())if(DATA/'navigation-attempts.json').exists()else{};proof['planningAttemptDiagnostics']=attempts;proof['failedCandidates'].extend(attempts.get('failedSavedMeshCandidates',[]))
 layout['principalRoutes']=routes;layout['navigationProof']='data/collections/clm102-room230/navigation-routes.json';(DATA/'layout.json').write_text(json.dumps(layout,ensure_ascii=False,indent=2)+'\n');(DATA/'navigation-routes.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n');print('FIVE_GROUP_PATHS_PREPARED',len(routes),[(v['group'],round(v['lengthFromTeachingPoint'],2))for v in groups],diagnosis)

try:import bpy
except ModuleNotFoundError:
 if __name__=='__main__':prepare()
else:
 from mathutils import Vector
 sys.path.insert(0,str(ROOT/'web/tools'))
 from build_room_samples167 import RoomGeometry
 from integrate_exterior_round194 import object_fingerprint,accepted_fingerprints
 from refine_portsmouth_exterior207 import material_fingerprint
 from refine_sal_structure221 import stable_modifiers,rooms_state
 L=json.loads((DATA/'layout.json').read_text())
 def point(p):return Vector(xy(p))
 def update():
  for scene in bpy.data.scenes:
   for layer in scene.view_layers:layer.update()
 def material(g,key,color,rough=.7,metal=0):
  m=bpy.data.materials.new(PREFIX+key);m.use_nodes=True;m.diffuse_color=(*color,1);n=m.node_tree.nodes['Principled BSDF'];n.inputs['Base Color'].default_value=m.diffuse_color;n.inputs['Roughness'].default_value=rough;n.inputs['Metallic'].default_value=metal;g.materials[key]=m
 def span(g,family,key,a,b,lo,hi,depth=.14):
  a,b=Vector(a),Vector(b);d=b-a;c=(a+b)/2;g.box(family,key,(*c,(lo+hi)/2),(d.length,depth,hi-lo),math.atan2(d.y,d.x))
 def chair(g,seat):
  p,t=Vector(seat['centre']),Vector(seat['target']);angle=math.atan2(t.y-p.y,t.x-p.x)+math.pi/2;c,s=math.cos(angle),math.sin(angle)
  def at(x,y,z):return(p.x+c*x-s*y,p.y+s*x+c*y,z)
  g.box('black_chair_seat_shells','black',at(0,0,.448),(.46,.44,.046),angle);g.box('orange_brown_seat_cushions','seatOrange',at(0,-.005,.481),(.425,.40,.025),angle)
  profile=[[-.20,.51],[.20,.51],[.235,.60],[.225,.93],[.18,.98],[-.18,.98],[-.225,.93],[-.235,.60]]
  vertices=[at(x,.22+(z-.51)*.09+depth,z)for depth in [0,.027]for x,z in profile];n=len(profile);faces=[tuple(reversed(range(n))),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n)for i in range(n)];g.add('rounded_black_chair_backs','black',vertices,[tuple(reversed(f))for f in faces])
  feet=[]
  for x in [-.19,.19]:
   for y in [-.17,.18]:
    foot=at(x*1.1,y*1.2,0);g.tube('chair_floor_contact_pads','black',foot,at(x*1.1,y*1.2,.025),.019);g.tube('black_chair_legs','metal',at(x*1.1,y*1.2,.025),at(x,y,.445),.015);feet.append(list(foot))
   g.tube('chair_back_shell_supports','metal',at(x,.18,.44),at(x,.235,.63),.014)
  return dict(feet=feet)
 def build():
  scene=bpy.data.scenes.new(SCENE);col=bpy.data.collections.new(COLLECTION);scene.collection.children.link(col);col['roomSample']=True;col['roomCode']='CLM.1.02';g=RoomGeometry(col,PREFIX)
  for k,c,r,m in [('plaster',(.79,.78,.73),.86,0),('black',(.019,.025,.025),.75,0),('metal',(.045,.050,.047),.45,.2),('seatOrange',(.46,.155,.045),.84,0),('tabletop',(.84,.84,.78),.58,0),('carpetA',(.27,.29,.27),.98,0),('carpetB',(.36,.37,.33),.98,0),('carpetC',(.21,.24,.24),.98,0),('ceiling',(.79,.80,.75),.88,0),('joint',(.63,.65,.60),.9,0),('whiteframe',(.80,.81,.76),.5,0),('glassroom',(.29,.35,.36),.22,0),('wood',(.34,.18,.075),.72,0),('woodlight',(.43,.25,.115),.72,0),('woodDark',(.24,.12,.045),.75,0),('boardwhite',(.87,.88,.82),.64,0),('screen',(.008,.011,.012),.24,0),('cabinet',(.17,.19,.18),.7,0)]:material(g,k,c,r,m)
  g.prism('complete_plan_floor','carpetA',L['outline'],-.14,.137)
  for tile in L['carpetTiles']:g.prism('patterned_carpet_tiles',tile['material'],tile['outline'],-.003,.003)
  def roomward(a,b):
   u=(b-a).normalized();normal=Vector((-u.y,u.x))
   if normal.dot(-(a+b)/2)<0:normal=-normal
   return normal
  def panelled_wall(a,b):
   span(g,'complete_perimeter_walls','wood',a,b,0,HEIGHT,.18);normal=roomward(a,b);u=(b-a).normalized();length=(b-a).length
   for z in [.12,.96,2.78,3.10]:span(g,'wood_wall_horizontal_mouldings','woodDark',a+normal*.105,b+normal*.105,z,z+.045,.055)
   count=max(1,round(length/.85))
   for i in range(count):
    p,q=a.lerp(b,i/count),a.lerp(b,(i+1)/count)
    if (q-p).length<.16:continue
    for z0,z1 in [(.19,.91),(1.05,2.71)]:span(g,'wood_wall_inset_panel_faces','woodlight',p+u*.055+normal*.102,q-u*.055+normal*.102,z0,z1,.025)
    for r in [p,q]:span(g,'wood_wall_vertical_panel_stiles','woodDark',r-u*.020+normal*.110,r+u*.020+normal*.110,.17,2.78,.055)
   for z0,z1,depth in [(HEIGHT-.21,HEIGHT-.14,.18),(HEIGHT-.14,HEIGHT-.08,.23),(HEIGHT-.08,HEIGHT,.28)]:span(g,'continuous_timber_ceiling_cornice','woodDark',a+normal*.04,b+normal*.04,z0,z1,depth)
  for aa,bb in zip(L['outlinePixels'],L['outlinePixels'][1:]+L['outlinePixels'][:1]):
   a,b=point(aa),point(bb);d=b-a;events=[(0.,1.,'wall')]
   for u,v,kind in [(point(v['a']),point(v['b']),'door')for v in L['doors']]+[(point(v['a']),point(v['b']),'window')for v in L['windows']]:
    if abs(d.cross(u-a))>1e-5 or abs(d.cross(v-a))>1e-5:continue
    lo,hi=sorted(((u-a).dot(d)/d.length_squared,(v-a).dot(d)/d.length_squared))
    if lo<-.001 or hi>1.001:continue
    new=[]
    for st,en,k in events:
     if k!='wall'or hi<=st or lo>=en:new.append((st,en,k));continue
     if st<lo:new.append((st,lo,'wall'))
     new.append((max(st,lo),min(en,hi),kind))
     if hi<en:new.append((hi,en,'wall'))
    events=new
   for st,en,kind in events:
    if en-st<1e-7:continue
    p,q=a+d*st,a+d*en
    if kind=='wall':panelled_wall(p,q)
    elif kind=='door':span(g,'real_door_lintel_wall','wood',p,q,2.43,HEIGHT,.18)
    else:span(g,'window_sill_wall','wood',p,q,0,.91,.18);span(g,'window_upper_wall','wood',p,q,2.94,HEIGHT,.18)
    if kind!='door':span(g,'timber_perimeter_skirting','woodDark',p,q,0,.12,.06)
  for w in L['windows']:
   a,b=point(w['a']),point(w['b']);u=(b-a).normalized();normal=roomward(a,b)
   for p in [a,b]:span(g,'wood_window_jamb_frames','woodDark',p-u*.029,p+u*.029,.87,2.97,.20)
   for z in [.91,2.91]:span(g,'wood_window_horizontal_rails','woodDark',a,b,z,z+.045,.18)
   for t in [1/3,2/3]:
    p=a.lerp(b,t);span(g,'wood_window_mullions','woodDark',p-u*.023,p+u*.023,.94,2.94,.12)
   span(g,'window_glass','glassroom',a,b,.955,2.91,.016);span(g,'deep_wood_window_sills','woodlight',a+normal*.20,b+normal*.20,.85,.91,.55)
   span(g,'window_radiator_wood_cabinet','wood',a+normal*.22,b+normal*.22,0,.80,.38)
   count=max(3,int((b-a).length/.07))
   for i in range(1,count):
    p=a.lerp(b,i/count)+normal*.24;span(g,'radiator_top_dark_vent_slots','black',p-u*.012,p+u*.012,.802,.811,.22)
  doorRecords=[]
  for door in L['doors']:
   da,db=point(door['a']),point(door['b']);u=(db-da).normalized();normal=roomward(da,db)
   for p in [da,db]:span(g,'ornate_doorcase_vertical_posts','woodDark',p-u*.042+normal*.095,p+u*.042+normal*.095,0,2.57,.21)
   span(g,'ornate_doorcase_lintel','woodDark',da+normal*.09,db+normal*.09,2.43,2.63,.22);span(g,'doorcase_cornice','woodlight',da-u*.08+normal*.105,db+u*.08+normal*.105,2.61,2.68,.27)
   c=(da+db)/2
   for p in [da-u*.09,db+u*.09]:g.tube('classical_pediment_slopes','woodDark',(* (p+normal*.12),2.69),(*(c+normal*.12),2.99),.05)
   hinge,tip=point(door['hinge']),point(door['openTip']);span(g,'open_wooden_door_leaves','woodlight',hinge,tip,.02,2.42,.055);h=hinge.lerp(tip,.85);g.tube('door_metal_handles','black',(*h,1.02),(*h,1.15),.014)
   doorRecords.append(dict(id=door['id'],a=list(da),b=list(db),normal=list(normal),clearWidth=(db-da).length-.084))
  # Screen and two mobile whiteboards occupy the plan's left teaching wall.
  a,b=point([62,132]),point([62,182]);span(g,'teaching_display_black_frame','black',a,b,1.20,2.12,.085);span(g,'blank_teaching_display','screen',a+Vector((.052,0)),b+Vector((.052,0)),1.24,2.08,.016)
  boardFeet=[]
  for y0,y1 in [(97,128),(186,224)]:
   a,b=point([74,y0]),point([74,y1]);u=(b-a).normalized();c=(a+b)/2;span(g,'mobile_whiteboard_frames','whiteframe',a,b,.36,2.30,.055);span(g,'mobile_whiteboard_faces','boardwhite',a+Vector((.034,0)),b+Vector((.034,0)),.40,2.26,.018)
   for shift in [-.28,.28]:
    p=c+u*shift;g.tube('whiteboard_floor_legs','whiteframe',(*p,.08),(*p,.40),.021);g.tube('whiteboard_low_crossfeet','whiteframe',(p.x-.24,p.y,.08),(p.x+.24,p.y,.08),.022)
    for dx in [-.24,.24]:g.tube('whiteboard_castors','black',(p.x+dx,p.y-.018,.03),(p.x+dx,p.y+.018,.03),.03);boardFeet.append([p.x+dx,p.y,0])
  ta,tb=point(L['teacherDesk']['a']),point(L['teacherDesk']['b']);tc=(ta+tb)/2;tw,td=abs(tb.x-ta.x),abs(tb.y-ta.y)
  g.box('AV_lectern_floor_plinth','cabinet',(*tc,.04),(tw-.04,td-.04,.08));g.box('AV_equipment_cabinet','cabinet',(*tc,.48),(tw-.065,td-.065,.88));g.box('AV_lectern_worktop','whiteframe',(*tc,.95),(tw,td,.06))
  g.box('AV_monitor_base','black',(*tc,.995),(.26,.20,.03));g.tube('AV_monitor_stand','metal',(*tc,1.01),(*tc,1.22),.022);g.box('AV_monitor','screen',(tc.x,tc.y,1.38),(.47,.065,.33));g.box('AV_keyboard','black',(tc.x+.08,tc.y-.21,.995),(.35,.12,.03));g.box('AV_control_panel','black',(tc.x-.12,tc.y+.16,1.015),(.22,.15,.07))
  supports=[]
  for pod in L['pods']:
   g.prism('five_rounded_white_group_tabletops','tabletop',pod['metreOutline'],.735,.045)
   for p in pod['supports']:
    g.tube('table_floor_contact_pads','black',(*p,0),(*p,.022),.032);g.tube('black_table_legs','metal',(*p,.022),(*p,.742),.026);supports.append(dict(foot=[*p,0],top=[*p,.742]))
  seats=[chair(g,v)for v in L['seats']]
  g.prism('continuous_complete_ceiling','ceiling',L['outline'],HEIGHT,.10)
  for ring in L['ceilingGridParts']:g.prism('continuous_ceiling_panel_grid','joint',ring,HEIGHT-.004,.004)
  lightSupports=[]
  for px in L['lights']:
   p=point(px)
   for dx in [-.43,.43]:g.tube('pendant_lamp_ceiling_rods','whiteframe',(p.x+dx,p.y,HEIGHT+.01),(p.x+dx,p.y,HEIGHT-.33),.007);lightSupports.append([p.x+dx,p.y,HEIGHT])
   g.box('pendant_light_housings','whiteframe',(*p,HEIGHT-.36),(1.10,.30,.08));g.box('pendant_light_diffusers','light',(*p,HEIGHT-.408),(1.04,.25,.016))
  objects=g.finish()
  for o in objects:o['roomCode']='CLM.1.02';o['destinationCollection']=COLLECTION;o['scope']='Independent historical plan-layout classroom;estimated dimensions;no geographic registration or2026capacityclaim'
  return scene,col,objects,dict(seats=seats,tableSupports=supports,boardFeet=boardFeet,lecternCentre=list(tc),lightSupports=lightSupports,doors=doorRecords),g.solid_proof
 def tree(objects):
  from mathutils.bvhtree import BVHTree
  vs=[];fs=[];owners=[]
  for o in objects:
   if o.type!='MESH':continue
   off=len(vs);vs.extend(o.matrix_world@v.co for v in o.data.vertices);fs.extend(tuple(off+i for i in f.vertices)for f in o.data.polygons);owners.extend([o.name]*len(o.data.polygons))
  return BVHTree.FromPolygons(vs,fs),owners
 def inside(x,y):
  answer=False
  for a,b in zip(L['outline'],L['outline'][1:]+L['outline'][:1]):
   if(a[1]>y)!=(b[1]>y)and x<(b[0]-a[0])*(y-a[1])/(b[1]-a[1])+a[0]:answer=not answer
  return answer
 def swept_route_surfaces(objects):
  """Clip every actual saved mesh triangle against each complete body corridor.

  Vertical clipping includes all furniture surfaces between0.04and2.10m.
  Unlike three horizontal rays,this also tests thin tabletops and whole routes.
  """
  def clip(poly,value,keep):
   result=[]
   if not poly:return result
   previous=poly[-1];pv=value(previous);pin=keep(pv)
   for current in poly:
    cv=value(current);cin=keep(cv)
    if cin!=pin:
     t=pv/(pv-cv);result.append(previous+(current-previous)*t)
    if cin:result.append(current)
    previous,pv,pin=current,cv,cin
   return result
  surfaces=[]
  for obj in objects:
   if obj.type!='MESH'or any(k in obj.name for k in ['complete_plan_floor','quiet_carpet_tiles']):continue
   obj.data.calc_loop_triangles()
   for tri in obj.data.loop_triangles:
    poly=[obj.matrix_world@obj.data.vertices[i].co for i in tri.vertices]
    if max(p.z for p in poly)<.04 or min(p.z for p in poly)>2.1:continue
    poly=clip(poly,lambda p:p.z-.04,lambda v:v>=0)
    poly=clip(poly,lambda p:2.1-p.z,lambda v:v>=0)
    if poly:surfaces.append((obj.name,poly))
  routes=[]
  for pa,pb in L['principalRoutes']:
   a,b=point(pa),point(pb);d=(b-a).normalized();n=Vector((-d.y,d.x));length=(b-a).length;tested=0
   for owner,poly in surfaces:
    q=[Vector(((p.xy-a).dot(d),(p.xy-a).dot(n)))for p in poly]
    if max(p.x for p in q)<=1e-6 or min(p.x for p in q)>=length-1e-6 or max(p.y for p in q)<=-.22+1e-6 or min(p.y for p in q)>=.22-1e-6:continue
    tested+=1
    for f in [lambda p:p.x-1e-6,lambda p:length-1e-6-p.x,lambda p:p.y+.22-1e-6,lambda p:.22-1e-6-p.y]:q=clip(q,f,lambda v:v>=0)
    assert not q,('ActualSavedMeshInBodyCorridor',pa,pb,owner,[list(p)for p in q])
   routes.append(dict(sourceEndpoints=[pa,pb],length=length,width=.44,verticalRange=[.04,2.1],candidateTriangles=tested,intersections=0))
  # A swept circular body needs an end/turn disk at every segment junction.
  # Thirty-two supporting planes form a conservative circumscribed cylinder.
  endpoints={tuple(round(float(v),8)for v in p):p for route in L['principalRoutes']for p in route};turns=[]
  for sourcePixel in endpoints.values():
   centre=point(sourcePixel);tested=0
   for owner,poly in surfaces:
    q=[p.xy-centre for p in poly]
    if max(p.x for p in q)<=-.222 or min(p.x for p in q)>=.222 or max(p.y for p in q)<=-.222 or min(p.y for p in q)>=.222:continue
    tested+=1
    for i in range(32):
     normal=Vector((math.cos(i*math.tau/32),math.sin(i*math.tau/32)));q=clip(q,lambda p:.22-1e-6-p.dot(normal),lambda v:v>=0)
     if not q:break
    assert not q,('ActualSavedMeshInTurnVolume',sourcePixel,owner,[list(p)for p in q])
   turns.append(dict(sourceCentre=sourcePixel,bodyRadius=.22,conservativeOuterRadius=.22/math.cos(math.pi/32),verticalRange=[.04,2.1],candidateTriangles=tested,intersections=0))
  failedProofs=[]
  if (DATA/'navigation-routes.json').exists():
   nav=json.loads((DATA/'navigation-routes.json').read_text())
   def node(p):return tuple(round(float(v),7)for v in p)
   adjacency={}
   for a,b in L['principalRoutes']:adjacency.setdefault(node(a),set()).add(node(b));adjacency.setdefault(node(b),set()).add(node(a))
   visited=set();todo=[node(nav['startPixel'])]
   while todo:
    v=todo.pop()
    if v in visited:continue
    visited.add(v);todo.extend(adjacency.get(v,set())-visited)
   assert node(nav['teachingPoint'])in visited
   assert all(node(group['approachPoint'])in visited for group in nav['groups'])
   for candidate in nav['failedCandidates']:
    pa,pb=candidate['candidate'];a,b=point(pa),point(pb);d=(b-a).normalized();n=Vector((-d.y,d.x));length=(b-a).length;hits=[]
    for owner,poly in surfaces:
     q=[Vector(((p.xy-a).dot(d),(p.xy-a).dot(n)))for p in poly]
     if max(p.x for p in q)<=0 or min(p.x for p in q)>=length or max(p.y for p in q)<=-.22 or min(p.y for p in q)>=.22:continue
     for f in [lambda p:p.x,lambda p:length-p.x,lambda p:p.y+.22,lambda p:.22-p.y]:q=clip(q,f,lambda v:v>=0)
     if q:hits.append(dict(owner=owner,clippedTriangle=[[float(v)for v in p]for p in q]))
    assert hits,('FailedShortcutNotReproduced',candidate)
    failedProofs.append(dict(sourceEndpoints=[pa,pb],width=.44,verticalRange=[.04,2.1],passed=False,intersections=len(hits),owners=sorted(set(v['owner']for v in hits)),clippedTriangleEvidence=hits))
  return dict(method='Every saved world triangle clipped to0.04–2.10m body height,complete0.44m wide rectangular sweeps,and conservative32plane0.22m radius cylinders at all endpoints andturns;thin horizontal andslanted surfaces included',eligibleTriangles=len(surfaces),routes=routes,turnVolumes=turns,totalIntersections=0,entryTeachingFiveGroupsGraphConnected=True if(DATA/'navigation-routes.json').exists()else None,failedShortcutSavedTriangleProofs=failedProofs)
 def checks(objects,R):
  floor,_=tree([o for o in objects if any(k in o.name for k in ['complete_plan_floor','patterned_carpet_tiles'])]);ceiling,_=tree([o for o in objects if o.name==PREFIX+'continuous_complete_ceiling']);tops,_=tree([o for o in objects if o.name==PREFIX+'five_rounded_white_group_tabletops']);solid,names=tree([o for o in objects if not any(k in o.name for k in ['complete_plan_floor','patterned_carpet_tiles','ceiling'])])
  feet=[]
  for seat in R['seats']:
   for p in seat['feet']:
    h=floor.ray_cast(Vector((p[0],p[1],.04)),Vector((0,0,-1)),.08);assert h[0]is not None and abs(h[0].z)<.001,('UnsupportedChairFoot',p);feet.append(dict(point=p,floorZ=h[0].z))
  contacts=[]
  for s in R['tableSupports']:
   p=s['foot'];f=floor.ray_cast(Vector((p[0],p[1],.04)),Vector((0,0,-1)),.08);assert f[0]is not None and abs(f[0].z)<.001
   t=tops.ray_cast(Vector((p[0],p[1],.70)),Vector((0,0,1)),.08);assert t[0]is not None and abs(t[0].z-.735)<.001
   contacts.append(dict(foot=p,floorZ=f[0].z,tabletopUnderside=t[0].z,supportTop=s['top']))
  p=R['lecternCentre'];h=floor.ray_cast(Vector((*p,.04)),Vector((0,0,-1)),.08);assert h[0]is not None and abs(h[0].z)<.001;lecternContact=list(h[0])
  coverage=[];step=.20;xs=[p[0]for p in L['outline']];ys=[p[1]for p in L['outline']]
  for i in range(math.floor(min(xs)/step),math.ceil(max(xs)/step)):
   for j in range(math.floor(min(ys)/step),math.ceil(max(ys)/step)):
    x,y=(i+.5)*step,(j+.5)*step
    if not inside(x,y):continue
    h=ceiling.ray_cast(Vector((x,y,1.5)),Vector((0,0,1)),2);assert h[0]is not None and abs(h[0].z-HEIGHT)<.001,('CeilingHole',x,y);coverage.append([x,y,h[0].z])
  assert len(coverage)>1000
  lampSupport=[]
  for p in R['lightSupports']:
   h=ceiling.ray_cast(Vector((p[0],p[1],HEIGHT-.10)),Vector((0,0,1)),.15);assert h[0]is not None and abs(h[0].z-p[2])<.001;lampSupport.append([*p,h[0].z])
  boardContacts=[]
  for p in R['boardFeet']:
   h=floor.ray_cast(Vector((p[0],p[1],.04)),Vector((0,0,-1)),.08);assert h[0]is not None and abs(h[0].z)<.001;boardContacts.append(dict(point=p,floorZ=h[0].z))
  doorway=[]
  for door in R['doors']:
   a,b=Vector(door['a']),Vector(door['b']);c=(a+b)/2;u=(b-a).normalized();normal=Vector(door['normal'])
   for d in [-.22,0,.22]:
    for z in [.04,.65,1.20,2.1]:
     p=c+u*d-normal*.25;h=solid.ray_cast(Vector((*p,z)),Vector((*normal,0)),.5);assert h[0]is None,('DoorBlocked',door['id'],d,z,names[h[2]]if h[2]is not None else'');doorway.append([door['id'],d,z])
  walltree,_=tree([o for o in objects if any(k in o.name for k in ['perimeter_walls','sill_wall','upper_wall','door_lintel'])]);window=[]
  for w in L['windows']:
   a,b=point(w['a']),point(w['b']);u=(b-a).normalized();normal=Vector((-u.y,u.x))
   for t in [.2,.5,.8]:
    c=a.lerp(b,t)
    for z in [1.2,1.7,2.5]:
     h=walltree.ray_cast(Vector((c.x-normal.x*.25,c.y-normal.y*.25,z)),Vector((*normal,0)),.5);assert h[0]is None,('UncutWindow',w['id'],t,z);window.append([w['id'],t,z])
  result=dict(studentSeatCount=30,groupTableCount=5,teacherSeatCount=0,AVLecternCount=1,studentFootCount=120,footSupportProbes=feet,tableFloorAndWorktopContacts=contacts,lecternFloorContact=lecternContact,ceilingLightSupportContacts=lampSupport,continuousCeilingCoverage=dict(spacingMetres=step,probeCount=len(coverage),missCount=0,undersideHeight=HEIGHT,pointDigest=hashlib.sha256(json.dumps(coverage).encode()).hexdigest()),realDoorOpeningClearRays=doorway,doorClearWidths={v['id']:v['clearWidth']for v in R['doors']},whiteboardWheelFloorContacts=boardContacts,realWindowWallApertureRays=window,wholeRouteSavedMeshSweep=swept_route_surfaces(objects),routeScope='入口主门初始体积探针，完整五组可达性在保存后实际网格导航复核中生成，不作规范认证',allAuthoredComponentsClosed=True)
  if (DATA/'navigation-routes.json').exists():
   navigation=json.loads((DATA/'navigation-routes.json').read_text());assert{o.name:object_fingerprint(o)for o in objects}==navigation['geometryFingerprints'];result['continuousSeatGroupReachability']=navigation;result['routeScope']='入口经教学端、周边通道及后侧绕行，到达五组各一处座席后侧接近点；保留失败候选捷径诊断，几何探针非规范认证'
  return result
 def gallery_views():
  views=[]
  for name,pp,tp,z,tz,label in [('teaching',[555,238],[68,155],1.65,1.46,'CLM.1.02五组座位与木饰面教学端'),('seating',[85,60],[478,208],1.65,1.28,'CLM.1.02五组六人桌与古典木墙')]:
   p,t=point(pp),point(tp);views.append(dict(name='clm-102-'+name+'-interior',code='CLM',spaceId='clm-102',label=label,view=dict(position=[p.x,z,-p.y],target=[t.x,tz,-t.y],fov=83.97)))
  return views
 def render(scene):
  bpy.context.window.scene=scene;world=bpy.data.worlds.new(PREFIX+'previewWorld');world.use_nodes=True;world.node_tree.nodes['Background'].inputs[0].default_value=(.76,.80,.84,1);world.node_tree.nodes['Background'].inputs[1].default_value=.22;scene.world=world
  ld=bpy.data.lights.new(PREFIX+'previewArea','AREA');ld.energy=800;ld.shape='DISK';ld.size=6;lamp=bpy.data.objects.new(ld.name,ld);scene.collection.objects.link(lamp);lamp.location=(0,0,HEIGHT-.30)
  cd=bpy.data.cameras.new(PREFIX+'previewCamera');camera=bpy.data.objects.new(cd.name,cd);scene.collection.objects.link(camera);scene.camera=camera;cd.lens=20;cd.clip_end=100
  scene.render.engine='BLENDER_EEVEE';scene.eevee.taa_render_samples=24;scene.render.resolution_x=1100;scene.render.resolution_y=850;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='AgX';views=[]
  for view in gallery_views():
   v=view['view'];p,t=v['position'],v['target'];camera.location=(p[0],-p[2],p[1]);camera.rotation_euler=(Vector((t[0],-t[2],t[1]))-camera.location).to_track_quat('-Z','Y').to_euler();scene.render.filepath=str(OUT/('built-'+view['name'].split('-')[-2]+'.png'));bpy.ops.render.render(write_still=True);views.append(view)
  for obj in [camera,lamp]:bpy.data.objects.remove(obj,do_unlink=True)
  bpy.data.cameras.remove(cd);bpy.data.lights.remove(ld);bpy.data.worlds.remove(world);scene.world=None;return views
 def export_navigation():
  """Export actual height-clipped saved triangles for planar route preparation."""
  bpy.ops.wm.open_mainfile(filepath=str(OUT/'component.blend'));update();surfaces=[]
  def clip(poly,value):
   result=[]
   if not poly:return result
   previous=poly[-1];pv=value(previous);pin=pv>=0
   for current in poly:
    cv=value(current);cin=cv>=0
    if cin!=pin:result.append(previous+(current-previous)*(pv/(pv-cv)))
    if cin:result.append(current)
    previous,pv,pin=current,cv,cin
   return result
  for obj in bpy.data.objects:
   if obj.type!='MESH'or any(k in obj.name for k in ['complete_plan_floor','patterned_carpet_tiles','ceiling']):continue
   obj.data.calc_loop_triangles()
   for tri in obj.data.loop_triangles:
    poly=[obj.matrix_world@obj.data.vertices[i].co for i in tri.vertices]
    poly=clip(poly,lambda p:p.z-.04);poly=clip(poly,lambda p:2.10-p.z)
    if poly:surfaces.append(dict(owner=obj.name,polygon=[[p.x,p.y]for p in poly]))
  (DATA/'navigation-surfaces.json').write_text(json.dumps(dict(componentSha256=sha(OUT/'component.blend'),height=[.04,2.10],surfaces=surfaces)))
  print('CLM_NAVIGATION_SURFACES',len(surfaces),flush=True);bpy.ops.wm.quit_blender()
 def verify_navigation():
  report=json.loads((OUT/'audit.json').read_text());proofs=[]
  for repeat in range(2):
   bpy.ops.wm.open_mainfile(filepath=str(OUT/'component.blend'));update();assert{o.name:object_fingerprint(o)for o in bpy.data.objects}==report['addedFingerprints'];proofs.append(swept_route_surfaces(list(bpy.data.objects)))
  assert proofs[0]==proofs[1]and sha(BASE)==SHA
  report['checks']['wholeRouteSavedMeshSweep']=proofs[0];report['checks']['routeScope']='入口经教学端、周边通道绕行，到达五组桌各至少一处座席后侧接近点；0.44m几何探针，非规范认证'
  report['checks']['continuousSeatGroupReachability']=json.loads((DATA/'navigation-routes.json').read_text());report['verification']['completeRouteThinSurfaceSweepReopened']=True;report['verification']['routeProofIndependentReopens']=2;report['verification']['completeRouteTurnVolumesReopened']=True;report['verification']['failedShortcutsReproducedOnSavedTriangles']=True
  (OUT/'audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print('CLM_FIVE_GROUP_ROUTE_VERIFIED',len(proofs[0]['routes']),flush=True);bpy.ops.wm.quit_blender()
 def review_existing():
  bpy.ops.wm.open_mainfile(filepath=str(OUT/'component.blend'));scene=bpy.data.scenes.new(SCENE);scene.collection.children.link(bpy.data.collections[COLLECTION]);update();views=render(scene)
  report=json.loads((OUT/'audit.json').read_text());report['gallerySuggestions']=views;(OUT/'audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');bpy.ops.wm.quit_blender()
 def run():
  assert sha(BASE)==SHA;bpy.ops.wm.open_mainfile(filepath=str(BASE));update();expected=accepted_fingerprints(ROOT/'result/blender/stage229',SHA);original={o.name:object_fingerprint(o)for o in bpy.data.objects};assert original==expected and len(original)==8179
  mats={m.name:material_fingerprint(m)for m in bpy.data.materials};mods={o.name:stable_modifiers(o)for o in bpy.data.objects};rooms=rooms_state();assert len(rooms)==29 and len(set(n for r in rooms for n in r['objects']))==1170;members={o.name:sorted(c.name for c in o.users_collection)for o in bpy.data.objects};vis={o.name:o.hide_render for o in bpy.data.objects};props={o.name:dict(o.items())for o in bpy.data.objects}
  scene,col,owned,records,solid=build();update();proof=checks(owned,records);views=gallery_views()
  scope='依据LSE官方历史同房号归档平面与照片建立CLM.1.02独立教室。按图保留5张六人小组桌、30把学生椅、3处门洞、上墙凹口、下侧窗湾和AV讲台；照片控制木饰面、黑壳橙褐座椅、白色桌面、灰色地毯、教学显示屏、双白板及悬挂灯。尺度、层高、窗带解释与隐藏构造估算，连续完整天花，不作地理配准、现用容量或2026现况认证。'
  space=dict(code='CLM',id='clm-102',label='CLM.1.02小组教室',collection=COLLECTION,gallery=views[0]['name'],scope=scope,interiorView=views[0]['view'],interiorStudy=dict(kind='room-sample',label='CLM.1.02小组教室',scope=scope));col['authoringRecord']=json.dumps(space,ensure_ascii=False)
  fingerprints={o.name:object_fingerprint(o)for o in owned};bindings={o.name:[m.name for m in o.data.materials]for o in owned};component=OUT/'component.blend';bpy.data.libraries.write(str(component),{col},fake_user=True,compress=True)
  # Fresh native reopen proves source preservation independently of build state.
  bpy.ops.wm.open_mainfile(filepath=str(BASE));update();assert{o.name:object_fingerprint(o)for o in bpy.data.objects}==expected
  with bpy.data.libraries.load(str(component),link=False)as(src,dst):dst.collections=[COLLECTION]
  saved=dst.collections[0];scene=bpy.data.scenes.new(SCENE);scene.collection.children.link(saved);bpy.context.window.scene=scene;update();assert checks(list(saved.all_objects),records)==proof
  assert all(object_fingerprint(bpy.data.objects[n])==v for n,v in fingerprints.items());assert all(object_fingerprint(bpy.data.objects[n])==v for n,v in original.items());assert all(material_fingerprint(bpy.data.materials[n])==v for n,v in mats.items());assert all(stable_modifiers(bpy.data.objects[n])==v for n,v in mods.items());assert rooms_state()==rooms;assert all(sorted(c.name for c in bpy.data.objects[n].users_collection)==v for n,v in members.items());assert all(bpy.data.objects[n].hide_render==v for n,v in vis.items());assert all(dict(bpy.data.objects[n].items())==v for n,v in props.items());assert not any(n in bpy.data.scenes['00_CAMPUS_COMPLETE'].objects for n in fingerprints);assert sha(BASE)==SHA
  # Second component save/reopen has identical protected geometry and checks.
  checkpath=OUT/'reopen-check.blend';bpy.data.libraries.write(str(checkpath),{saved},fake_user=True,compress=True);bpy.ops.wm.open_mainfile(filepath=str(checkpath));update();assert{o.name:object_fingerprint(o)for o in bpy.data.objects}==fingerprints;assert checks(list(bpy.data.objects),records)==proof;assert not any(o.type in {'LIGHT','CAMERA'}for o in bpy.data.objects);checkpath.unlink();assert sha(BASE)==SHA
  verification=dict(savedComponentReopened=True,secondSavedComponentReopened=True,independentAcceptedObjectsVerified=len(original),allOriginalMaterialNodesVerified=len(mats),allOriginalModifierStacksVerified=len(mods),oldSpacesPreserved=len(rooms),oldSpaceUniqueObjectsPreserved=1170,allOriginalMembershipsAndPropertiesUnchanged=True,allSourceGeometryUVTransformsBindingsUnchanged=True,allOriginalVisibilityUnchanged=True,noNewRoomObjectInCampus=True,sourceNativeShaUnchanged=True,sourcePhotoNotUsedAsTexture=True,previewLightsAndCamerasExcluded=True,completeRouteThinSurfaceSweepReopened=True,triangles=sum(len(f.vertices)-2 for o in bpy.data.objects for f in o.data.polygons))
  audit=dict(version=230,building='CLM',baselinePath=str(BASE.relative_to(ROOT)),baselineSha256=SHA,componentPath=str(component.relative_to(ROOT)),componentSha256=sha(component),targetCollection=COLLECTION,destinationCollection=COLLECTION,collectionSpec=dict(kind='independent-room',name=COLLECTION,scene=SCENE),space=space,report=dict(space=space),addedObjects=list(fingerprints),archivedObjects=[],changedObjects=[],addedFingerprints=fingerprints,replacementMaterialBindings=bindings,sourceManifest='data/collections/clm102-room230/sources.json',planLayout='data/collections/clm102-room230/layout.json',studentSeatCount=30,teacherSeatCount=0,groupTableCount=5,scaleMetresPerPixel=SCALE,roomAreaSquareMetres=L['roomAreaSquareMetres'],estimatedCeilingHeight=HEIGHT,gallerySuggestions=views,checks=proof,solidProof=solid,verification=verification,previews=['built-teaching.png','built-seating.png'],beforeEvidence=[PLAN,PHOTO],previewLighting='Temporary area lamp below full ceiling,excluded from component;no photographic texture',limitations=json.loads((DATA/'sources.json').read_text())['limitations'])
  (OUT/'audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n');print('CLM102_ROOM230_READY',len(fingerprints),verification,flush=True);bpy.ops.wm.quit_blender()
 if __name__=='__main__':run()
