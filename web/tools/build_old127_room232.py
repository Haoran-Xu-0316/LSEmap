"""OLD.1.27 independent historical classroom component.

Fixed configuration for Blender's Text Editor and the MachineLearning Python.
Three counted six-chair pods follow the actual plan. No campus attachment,
photographic textures, measured-dimension claim or current-capacity claim.
"""
from pathlib import Path
import hashlib,json,math,sys
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'result/blender/old127-room232'
DATA=ROOT/'data/collections/old127-room232'
BASE=ROOT/'result/blender/LSE_campus_detailed_v231.blend'
SHA='667c0d1a8763d1e0ad0d026316ce38186c29678fffecc6b880e29ba3663c88b7'
COLLECTION='OLD127_ROOM232_study'
SCENE='ROOM232_OLD127'
PREFIX='OLD127_R232_'
PLAN='data/collections/interiors/images/90de02ad1c36_OLD.1.27.GIF'
PHOTO='data/collections/interiors/images/df8419ee55c9_OLD.1.27.jpg'
SCALE=.020
HEIGHT=2.95

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def write(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
def xy(q):return[(q[0]-305)*SCALE,(470-q[1])*SCALE]
def prepare():
 from shapely.geometry import Polygon,box
 from PIL import Image,ImageDraw
 metadata=json.loads((ROOT/'web/tools/building-metadata.json').read_text());assert not any(v.get('id')=='old-127' or '1.27' in v.get('label','')for v in metadata['spaces'])
 assert not any('1.27' in b.get('interiorStudy',{}).get('label','')for b in metadata['buildings'])
 DATA.mkdir(parents=True,exist_ok=True);OUT.mkdir(parents=True,exist_ok=True)
 write(DATA/'deduplication.json',dict(metadataSha256=sha(ROOT/'web/tools/building-metadata.json'),spaceRecordsChecked=len(metadata['spaces']),buildingDefaultsChecked=len(metadata['buildings']),existingOLDSpaces=[v for v in metadata['spaces']if v.get('code')=='OLD'],allBuildingInteriorStudyDefaults=[dict(code=b.get('code'),interiorStudy=b.get('interiorStudy'),interiorView=b.get('interiorView'))for b in metadata['buildings']],duplicateRoomFound=False))
 outline=[[124,299],[392,299],[392,277],[444,277],[444,299],[486,299],[486,633],[459,633],[437,653],[365,653],[345,633],[270,633],[250,653],[175,653],[156,633],[124,633]]
 poly=Polygon([xy(p)for p in outline]);assert poly.is_valid
 pods=[
  dict(id='upper',outline=[[190,400],[202,382],[225,362],[248,350],[259,348],[269,356],[276,379],[278,410],[275,432],[269,439],[247,440],[221,433],[199,422],[190,411]],chairs=[[230,348],[195,377],[205,431],[251,448],[291,413],[280,366]]),
  dict(id='right',outline=[[351,442],[366,424],[391,412],[416,404],[429,404],[440,411],[445,433],[444,467],[438,487],[428,494],[403,491],[380,480],[359,461]],chairs=[[374,416],[415,397],[456,431],[451,478],[403,501],[360,473]]),
  dict(id='lower',outline=[[253,547],[270,531],[295,519],[322,512],[335,512],[343,522],[344,543],[340,568],[331,590],[320,601],[309,600],[288,588],[268,571],[256,557]],chairs=[[274,516],[318,502],[352,540],[337,584],[294,604],[257,572]])]
 seats=[]
 for pod in pods:
  shape=Polygon([xy(p)for p in pod['outline']]);assert shape.is_valid
  pod['centre']=list(shape.centroid.coords)[0];pod['metreOutline']=[xy(p)for p in pod['outline']]
  centre=shape.centroid;pod['supports']=[]
  for v in [pod['metreOutline'][i]for i in [1,len(pod['metreOutline'])//3,2*len(pod['metreOutline'])//3]]:pod['supports'].append([centre.x+(v[0]-centre.x)*.67,centre.y+(v[1]-centre.y)*.67])
  for i,p in enumerate(pod['chairs']):seats.append(dict(id=pod['id']+str(i+1),pixel=p,centre=xy(p),target=pod['centre']))
 assert len(seats)==18
 doors=[dict(id='main',a=[392,277],b=[444,277],hinge=[444,277],openTip=[444,329])]
 windows=[dict(id='lowerLeftBay',a=[175,653],b=[250,653]),dict(id='lowerRightBay',a=[365,653],b=[437,653])]
 tiles=[];grid=[];x0,y0,x1,y1=poly.bounds
 def parts(v):return[v]if v.geom_type=='Polygon'else[g for g in getattr(v,'geoms',[])if g.geom_type=='Polygon']
 for i in range(math.floor(x0/.50),math.ceil(x1/.50)):
  for j in range(math.floor(y0/.50),math.ceil(y1/.50)):
   q=poly.intersection(box(i*.5,j*.5,(i+1)*.5,(j+1)*.5))
   if not q.is_empty:tiles.extend(dict(outline=list(t.exterior.coords)[:-1],material='carpet'+['A','B','C'][(i+2*j)%3])for t in parts(q)if t.area>1e-7)
 for axis,lo,hi in [(0,x0,x1),(1,y0,y1)]:
  for i in range(math.ceil(lo/.6),math.floor(hi/.6)+1):
   v=i*.6;q=poly.intersection(box(v-.004,y0-1,v+.004,y1+1)if axis==0 else box(x0-1,v-.004,x1+1,v+.004))
   if not q.is_empty:grid.extend(list(t.exterior.coords)[:-1]for t in parts(q)if t.area>1e-7)
 layout=dict(room='OLD.1.27',outlinePixels=outline,outline=[xy(p)for p in outline],scaleMetresPerPixel=SCALE,scaleBasis='Estimated0.020m/pixel from52px entry about1.04m;no printed measured dimensions',roomAreaSquareMetres=poly.area,studentSeatCount=18,printedHistoricalCapacity=18,teacherSeatCount=0,pods=pods,seats=seats,doors=doors,windows=windows,teacherDesk=dict(a=[172,566],b=[208,629]),ceilingGridParts=grid,carpetTiles=tiles,lights=[[196,338],[333,338],[187,476],[420,552],[200,610],[411,610]],principalRoutes=[[[418,277],[418,325]]])
 if(DATA/'navigation-routes.json').exists():
  navigation=json.loads((DATA/'navigation-routes.json').read_text())
  if navigation.get('allThreeGroupsReachable'):layout['principalRoutes']=navigation['principalRoutes']
 write(DATA/'layout.json',layout)
 archive=json.loads((ROOT/'data/collections/interiors/sources.json').read_text());refs=[r for r in archive['sources']if r.get('local_path')in[PLAN,PHOTO]];assert len(refs)==2
 assert next(v for v in refs if v['local_path']==PLAN)['source_type']=='historical_room_plan'
 assert all(sha(ROOT/v['local_path'])==v['sha256']for v in refs)
 limitations=['历史平面明确标注Old Building、Floor1、Room1.27、Capacity18，实际逐组可数三张曲边桌各六椅。18为历史来源印刷数字，不能证明当前核定容量。','照片与平面均实际目检；照片为同房号官方归档，照片拍摄和平面制作日期未知，网页刷新和2026检索日期不等于来源创建日期或2026现况。','平面控制三组18个椅位、曲边桌、上右入口、下侧两处窗湾、左侧教学面和左下AV讲台。照片只用于家具、材料、教学设备及天花类型，不能证明两来源同期。','比例0.020m/像素、层高2.95m、门高2.30m、窗台0.91m、窗顶2.68m、灯位、设备数量、隐蔽构造和未见面均为估算。','照片支持黑色塑壳椅与浅金属四腿、白色曲边桌、灰色拼块地毯、木质护墙、浅色墙面、木门和投影屏及AV台；投影面朝向结合平面左墙长线符号解释，不能证明精确设备布置同期。','下侧两处多线退进边界按窗湾解释；照片左侧可见窗及木质暖气罩，但具体窗格与全部竖向尺寸没有测绘依据。','来源照片仅供私下核对，未复制为交付图、不作纹理、未确认公开复用授权。','独立OLD.1.27室内样本，不作校园地理、整楼或楼层配准，不声称无障碍、疏散或现用容量认证。','完整0.44m宽、0.04至2.10m高连通路线在保存网格上验证，含转折末端体积与失败捷径；保留18个平面椅位，不移动家具强行通过。']
 write(DATA/'sources.json',dict(room='OLD.1.27',sources=refs,planSha256=sha(ROOT/PLAN),photoSha256=sha(ROOT/PHOTO),sameRoomPairVerified=True,pairBasis='Official archive room identifier,printed plan room1.27 andmatching three curved six-seat tables;chronology unverified',bothImagesActualNotPlaceholder=True,sourceSeatCount=dict(upper=6,right=6,lower=6,total=18),limitations=limitations))
 im=Image.open(ROOT/PLAN).convert('RGB');d=ImageDraw.Draw(im);d.line(outline+[outline[0]],fill=(190,30,30),width=2)
 for seat in seats:
  x,y=seat['pixel'];d.ellipse((x-3,y-3,x+3,y+3),fill=(30,50,200))
 im.save(DATA/'registered-plan.png');print('OLD127_LAYOUT_READY',poly.area,len(seats),flush=True)

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
 def pixel(p):return[p[0]/SCALE+305,470-p[1]/SCALE]
 start=xy([418,325]);teaching=xy([153,512]);entrance=path(start,teaching);assert entrance
 routes=[[[418,277],[418,325]]]+[[pixel(a),pixel(b)]for a,b in zip(entrance,entrance[1:])];groups=[];candidateOutcomes=[]
 for pod in layout['pods']:
  candidates=[]
  for seat in [v for v in layout['seats']if v['id'].startswith(pod['id'])]:
   c,t=seat['centre'],seat['target'];d=[c[0]-t[0],c[1]-t[1]];length=math.hypot(*d);approach=[c[0]+d[0]/length*.55,c[1]+d[1]/length*.55];points=path(teaching,approach)
   candidateOutcomes.append(dict(group=pod['id'],seatId=seat['id'],approachPoint=pixel(approach),reachable=points is not None,reason='Connected body-clear path found'if points else'Approach or connecting route blocked by saved furniture at0.23m planning radius'))
   if points:candidates.append((sum(math.dist(a,b)for a,b in zip(points,points[1:])),seat,points,approach))
  assert candidates,('GroupNotReachable',pod['id'])
  length,seat,points,approach=min(candidates,key=lambda v:v[0]);segments=[[pixel(a),pixel(b)]for a,b in zip(points,points[1:])];routes.extend(segments);groups.append(dict(group=pod['id'],reachable=True,seatId=seat['id'],seatPixel=seat['pixel'],approachPoint=pixel(approach),distanceBehindChairCentre=.55,lengthFromTeachingPoint=length,continuousPathFromTeachingPoint=[pixel(p)for p in points],continuousPathFromEntry=[[418,277]]+[pixel(p)for p in entrance]+[pixel(p)for p in points[1:]]))
 failed=LineString([xy([230,400]),xy([420,450])]);nearest=min(zip(shapes,owners),key=lambda item:failed.distance(item[0]));distance=failed.distance(nearest[0]);near=nearest_points(failed,nearest[0]);assert failed.buffer(.22,cap_style=2).intersects(obstacles),'ShortcutDiagnosticUnexpectedlyClear'
 diagnosis=dict(candidate=[[230,400],[420,450]],passed=False,bodyWidth=.44,verticalRange=[.04,2.10],nearestSavedMesh=nearest[1],minimumCentrelineToObstruction=distance,maximumSymmetricBodyWidthAtThisCandidate=distance*2,closestSourcePixels=[pixel(list(p.coords)[0])for p in near],intersectedFamilies=sorted(set(owner for shape,owner in zip(shapes,owners)if failed.buffer(.22,cap_style=2).intersects(shape))),reason='Actual saved furniture surfaces intersect the complete body corridor. Candidate retained as a failed shortcut; source furniture remains unchanged.')
 proof=dict(componentSha256=source['componentSha256'],geometryFingerprints=json.loads((OUT/'audit.json').read_text())['addedFingerprints'],principalRoutes=routes,method='Actual saved world triangles clipped to0.04–2.10m,projected to floor. Planar obstacles inflated0.23m;0.05m grid Astar with every edge and simplified segment covered by free space. Final complete0.44m rectangular sweeps and0.22m radius turn volumes are verified against actual saved triangles in Blender twice.',startPixel=[418,325],teachingPoint=[153,512],bodyProbeWidth=.44,planningRadius=.23,groups=groups,allSeatApproachCandidates=candidateOutcomes,failedCandidates=[diagnosis],allThreeGroupsReachable=True,routeScope='Entrance to teaching point then continuous approaches behind one chair in every pod;geometric probe only,not code or accessibility approval')
 attempts=json.loads((DATA/'navigation-attempts.json').read_text())if(DATA/'navigation-attempts.json').exists()else{};proof['planningAttemptDiagnostics']=attempts;proof['failedCandidates'].extend(attempts.get('failedSavedMeshCandidates',[]))
 layout['principalRoutes']=routes;layout['navigationProof']='data/collections/old127-room232/navigation-routes.json';(DATA/'layout.json').write_text(json.dumps(layout,ensure_ascii=False,indent=2)+'\n');(DATA/'navigation-routes.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n');print('THREE_GROUP_PATHS_PREPARED',len(routes),[(v['group'],round(v['lengthFromTeachingPoint'],2))for v in groups],diagnosis)

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
  g.box('black_chair_seat_shells','black',at(0,0,.448),(.46,.44,.046),angle);g.box('black_seat_cushions','seatOrange',at(0,-.005,.481),(.425,.40,.025),angle)
  profile=[[-.20,.51],[.20,.51],[.235,.60],[.225,.93],[.18,.98],[-.18,.98],[-.225,.93],[-.235,.60]]
  vertices=[at(x,.22+(z-.51)*.09+depth,z)for depth in [0,.027]for x,z in profile];n=len(profile);faces=[tuple(reversed(range(n))),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n)for i in range(n)];g.add('rounded_black_chair_backs','black',vertices,[tuple(reversed(f))for f in faces])
  feet=[]
  for x in [-.19,.19]:
   for y in [-.17,.18]:
    foot=at(x*1.1,y*1.2,0);g.tube('chair_floor_contact_pads','black',foot,at(x*1.1,y*1.2,.025),.019);g.tube('black_chair_legs','metal',at(x*1.1,y*1.2,.025),at(x,y,.445),.015);feet.append(list(foot))
   g.tube('chair_back_shell_supports','metal',at(x,.18,.44),at(x,.235,.63),.014)
  return dict(feet=feet)
 def build():
  scene=bpy.data.scenes.new(SCENE);col=bpy.data.collections.new(COLLECTION);scene.collection.children.link(col);col['roomSample']=True;col['roomCode']='OLD.1.27';g=RoomGeometry(col,PREFIX)
  for k,c,r,m in [('plaster',(.79,.78,.73),.86,0),('black',(.019,.025,.025),.75,0),('metal',(.43,.45,.44),.45,.6),('seatOrange',(.025,.030,.029),.84,0),('tabletop',(.84,.84,.78),.58,0),('carpetA',(.15,.17,.16),.98,0),('carpetB',(.21,.23,.22),.98,0),('carpetC',(.18,.20,.19),.98,0),('ceiling',(.79,.80,.75),.88,0),('joint',(.63,.65,.60),.9,0),('whiteframe',(.80,.81,.76),.5,0),('glassroom',(.29,.35,.36),.22,0),('wood',(.12,.055,.019),.72,0),('woodlight',(.18,.09,.033),.72,0),('woodDark',(.075,.03,.009),.75,0),('boardwhite',(.87,.88,.82),.64,0),('screen',(.008,.011,.012),.24,0),('cabinet',(.17,.19,.18),.7,0)]:material(g,k,c,r,m)
  g.prism('complete_plan_floor','carpetA',L['outline'],-.14,.137)
  for tile in L['carpetTiles']:g.prism('patterned_carpet_tiles',tile['material'],tile['outline'],-.003,.003)
  def roomward(a,b):
   u=(b-a).normalized();normal=Vector((-u.y,u.x))
   if normal.dot(-(a+b)/2)<0:normal=-normal
   return normal
  def panelled_wall(a,b):
   normal=roomward(a,b);u=(b-a).normalized();length=(b-a).length
   timber=a.y<xy([305,630])[1]and b.y<xy([305,630])[1]
   span(g,'complete_perimeter_walls','plaster',a,b,0,HEIGHT,.16)
   if timber:
    span(g,'deep_timber_wall_panels','wood',a+normal*.091,b+normal*.091,.12,2.30,.025)
    for z in [.12,.45,2.23,2.30]:span(g,'timber_panel_horizontal_rails','woodDark',a+normal*.111,b+normal*.111,z,z+.035,.04)
    for i in range(max(1,round(length/.9))+1):
     p=a.lerp(b,i/max(1,round(length/.9)));span(g,'timber_panel_stiles','woodlight',p-u*.016+normal*.113,p+u*.016+normal*.113,.13,2.30,.045)
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
    elif kind=='door':span(g,'real_door_lintel_wall','wood',p,q,2.30,HEIGHT,.18)
    else:span(g,'window_sill_wall','wood',p,q,0,.91,.18);span(g,'window_upper_wall','wood',p,q,2.68,HEIGHT,.18)
    if kind!='door':span(g,'timber_perimeter_skirting','woodDark',p,q,0,.12,.06)
  for a,b in [([202,299],[211,323]),([362,299],[370,323])]:
   pa,pb=point(a),point(b);c=(pa+pb)/2;g.box('source_top_wall_pilasters','plaster',(*c,HEIGHT/2),(abs(pb.x-pa.x),abs(pb.y-pa.y),HEIGHT))
  for w in L['windows']:
   a,b=point(w['a']),point(w['b']);u=(b-a).normalized();normal=roomward(a,b)
   for p in [a,b]:span(g,'wood_window_jamb_frames','whiteframe',p-u*.029,p+u*.029,.87,2.71,.20)
   for z in [.91,2.65]:span(g,'wood_window_horizontal_rails','whiteframe',a,b,z,z+.045,.18)
   for t in [1/3,2/3]:
    p=a.lerp(b,t);span(g,'wood_window_mullions','whiteframe',p-u*.023,p+u*.023,.94,2.68,.12)
   span(g,'window_glass','glassroom',a,b,.955,2.65,.016);span(g,'deep_wood_window_sills','woodlight',a+normal*.20,b+normal*.20,.85,.91,.55)
   span(g,'window_radiator_wood_cabinet','wood',a+normal*.22,b+normal*.22,0,.80,.38)
   count=max(3,int((b-a).length/.07))
   for i in range(1,count):
    p=a.lerp(b,i/count)+normal*.24;span(g,'radiator_top_dark_vent_slots','black',p-u*.012,p+u*.012,.802,.811,.22)
  doorRecords=[]
  for door in L['doors']:
   da,db=point(door['a']),point(door['b']);u=(db-da).normalized();normal=roomward(da,db)
   for p in [da,db]:span(g,'simple_timber_doorcase_posts','woodlight',p-u*.035+normal*.055,p+u*.035+normal*.055,0,2.35,.18)
   span(g,'simple_timber_doorcase_header','woodlight',da+normal*.055,db+normal*.055,2.30,2.37,.18)
   hinge,tip=point(door['hinge']),point(door['openTip'])
   for low,high in [(.02,.80),(2.12,2.29)]:span(g,'open_wooden_door_leaf_rails','woodlight',hinge,tip,low,high,.055)
   for low,high in [(0,.24),(.76,1)]:span(g,'open_wooden_door_leaf_stiles','woodlight',hinge.lerp(tip,low),hinge.lerp(tip,high),.80,2.12,.055)
   span(g,'door_leaf_glazed_vision_panel','glassroom',hinge.lerp(tip,.24),hinge.lerp(tip,.76),.80,2.12,.016)
   h=hinge.lerp(tip,.85);g.tube('door_metal_handles','metal',(*h,1.02),(*h,1.15),.014)
   doorRecords.append(dict(id=door['id'],a=list(da),b=list(db),normal=list(normal),clearWidth=(db-da).length-.084))
  # Historical plan left-wall symbol interpreted with the photo screen.
  a,b=point([130,386]),point([130,545]);span(g,'projection_screen_white_surface','boardwhite',a,b,.85,2.55,.025);span(g,'projection_screen_black_case','black',a,b,2.55,2.64,.11)
  span(g,'teaching_wall_whiteboard','boardwhite',point([474,539]),point([474,609]),.88,2.15,.023)
  p=point([333,307]);g.tube('teaching_wall_clock_frame','black',(p.x,p.y+.01,2.52),(p.x,p.y-.025,2.52),.15);g.tube('teaching_wall_clock_face','boardwhite',(p.x,p.y-.026,2.52),(p.x,p.y-.030,2.52),.13)
  g.tube('wall_clock_hour_hand','black',(p.x,p.y-.034,2.52),(p.x-.055,p.y-.034,2.55),.007);g.tube('wall_clock_minute_hand','black',(p.x,p.y-.034,2.52),(p.x+.012,p.y-.034,2.62),.005)
  for px in [[132,367],[132,555]]:
   p=point(px);g.box('screen_wall_speakers','cabinet',(*p,2.61),(.12,.19,.24))
  boardFeet=[]
  ta,tb=point(L['teacherDesk']['a']),point(L['teacherDesk']['b']);tc=(ta+tb)/2;tw,td=abs(tb.x-ta.x),abs(tb.y-ta.y)
  g.box('AV_lectern_floor_plinth','cabinet',(*tc,.04),(tw-.04,td-.04,.08));g.box('AV_equipment_cabinet','cabinet',(*tc,.48),(tw-.065,td-.065,.88));g.box('AV_lectern_worktop','whiteframe',(*tc,.95),(tw,td,.06))
  g.box('AV_monitor_base','black',(*tc,.995),(.26,.20,.03));g.tube('AV_monitor_stand','metal',(*tc,1.01),(*tc,1.22),.022);g.box('AV_monitor','screen',(tc.x,tc.y,1.38),(.47,.065,.33));g.box('AV_keyboard','black',(tc.x+.08,tc.y-.21,.995),(.35,.12,.03));g.box('AV_control_panel','black',(tc.x-.12,tc.y+.16,1.015),(.22,.15,.07))
  supports=[]
  for pod in L['pods']:
   g.prism('three_rounded_white_group_tabletops','tabletop',pod['metreOutline'],.735,.045)
   for p in pod['supports']:
    g.tube('table_floor_contact_pads','black',(*p,0),(*p,.022),.032);g.tube('black_table_legs','metal',(*p,.022),(*p,.742),.026);supports.append(dict(foot=[*p,0],top=[*p,.742]))
  seats=[chair(g,v)for v in L['seats']]
  g.prism('continuous_complete_ceiling','ceiling',L['outline'],HEIGHT,.10)
  for ring in L['ceilingGridParts']:g.prism('continuous_ceiling_panel_grid','joint',ring,HEIGHT-.004,.004)
  lightSupports=[]
  for px in L['lights']:
   p=point(px);g.box('recessed_ceiling_light_housings','whiteframe',(*p,HEIGHT-.027),(.57,.57,.054));g.box('recessed_ceiling_light_diffusers','light',(*p,HEIGHT-.059),(.53,.53,.010));lightSupports.append([*p,HEIGHT])
  for px in [[318,337],[330,616]]:
   p=point(px);g.box('ceiling_vent_grilles','whiteframe',(*p,HEIGHT-.019),(.55,.32,.038))
   for i in range(7):g.box('ceiling_vent_slots','black',(p.x+(i-3)*.065,p.y,HEIGHT-.04),(.025,.27,.007))
  p=point([328,461]);g.tube('projector_ceiling_support','metal',(*p,HEIGHT+.01),(*p,2.69),.022);g.box('ceiling_projector_housing','whiteframe',(*p,2.61),(.36,.28,.16));g.tube('projector_lens','black',(p.x-.18,p.y,2.61),(p.x-.24,p.y,2.61),.044)
  objects=g.finish()
  for o in objects:o['roomCode']='OLD.1.27';o['destinationCollection']=COLLECTION;o['scope']='Independent historical plan-layout classroom;estimated dimensions;no geographic registration or2026capacityclaim'
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
  return dict(method='Every saved world triangle clipped to0.04–2.10m body height,complete0.44m wide rectangular sweeps,and conservative32plane0.22m radius cylinders at all endpoints andturns;thin horizontal andslanted surfaces included',eligibleTriangles=len(surfaces),routes=routes,turnVolumes=turns,totalIntersections=0,entryTeachingThreeGroupsGraphConnected=True if(DATA/'navigation-routes.json').exists()else None,failedShortcutSavedTriangleProofs=failedProofs)
 def checks(objects,R):
  floor,_=tree([o for o in objects if any(k in o.name for k in ['complete_plan_floor','patterned_carpet_tiles'])]);ceiling,_=tree([o for o in objects if o.name==PREFIX+'continuous_complete_ceiling']);tops,_=tree([o for o in objects if o.name==PREFIX+'three_rounded_white_group_tabletops']);solid,names=tree([o for o in objects if not any(k in o.name for k in ['complete_plan_floor','patterned_carpet_tiles','ceiling'])])
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
  eyeProof=[]
  for view in gallery_views():
   v=view['view'];p=v['position'];t=v['target'];eye=Vector((p[0],-p[2],p[1]));target=Vector((t[0],-t[2],t[1]));assert inside(eye.x,eye.y)
   nearest=solid.find_nearest(eye);assert nearest[0] is None or nearest[3]>.12,('EyeNearSurface',view['name'],nearest[3])
   hit=solid.ray_cast(eye,(target-eye).normalized(),.14);assert hit[0] is None,('EyeNearPlaneObstruction',view['name'])
   eyeProof.append(dict(name=view['name'],inside=True,eye=list(eye),nearestSurfaceDistance=nearest[3],nearPlane=.14,nearPlaneClear=True))
  result=dict(insideEyeChecks=eyeProof,studentSeatCount=18,groupTableCount=3,teacherSeatCount=0,AVLecternCount=1,studentFootCount=72,footSupportProbes=feet,tableFloorAndWorktopContacts=contacts,lecternFloorContact=lecternContact,ceilingLightSupportContacts=lampSupport,continuousCeilingCoverage=dict(spacingMetres=step,probeCount=len(coverage),missCount=0,undersideHeight=HEIGHT,pointDigest=hashlib.sha256(json.dumps(coverage).encode()).hexdigest()),realDoorOpeningClearRays=doorway,doorClearWidths={v['id']:v['clearWidth']for v in R['doors']},whiteboardWheelFloorContacts=boardContacts,realWindowWallApertureRays=window,wholeRouteSavedMeshSweep=swept_route_surfaces(objects),routeScope='入口主门初始体积探针，完整三组可达性在保存后实际网格导航复核中生成，不作规范认证',allAuthoredComponentsClosed=True)
  if (DATA/'navigation-routes.json').exists():
   navigation=json.loads((DATA/'navigation-routes.json').read_text());assert{o.name:object_fingerprint(o)for o in objects}==navigation['geometryFingerprints'];result['continuousSeatGroupReachability']=navigation;result['routeScope']='入口经教学端、周边通道及后侧绕行，到达三组各一处座席后侧接近点；保留失败候选捷径诊断，几何探针非规范认证'
  return result
 def gallery_views():
  views=[]
  for name,pp,tp,z,tz,label in [('teaching',[457,590],[136,420],1.65,1.40,'OLD.1.27三组六人桌与教学端'),('seating',[461,348],[210,613],1.65,1.27,'OLD.1.27来源椅位与木饰面窗湾')]:
   p,t=point(pp),point(tp);views.append(dict(name='old-127-'+name+'-interior',code='OLD',spaceId='old-127',label=label,view=dict(position=[p.x,z,-p.y],target=[t.x,tz,-t.y],fov=86.9)))
  return views
 def render(scene):
  bpy.context.window.scene=scene;world=bpy.data.worlds.new(PREFIX+'previewWorld');world.use_nodes=True;world.node_tree.nodes['Background'].inputs[0].default_value=(.76,.80,.84,1);world.node_tree.nodes['Background'].inputs[1].default_value=.22;scene.world=world
  ld=bpy.data.lights.new(PREFIX+'previewArea','AREA');ld.energy=800;ld.shape='DISK';ld.size=6;lamp=bpy.data.objects.new(ld.name,ld);scene.collection.objects.link(lamp);lamp.location=(0,0,HEIGHT-.30)
  cd=bpy.data.cameras.new(PREFIX+'previewCamera');camera=bpy.data.objects.new(cd.name,cd);scene.collection.objects.link(camera);scene.camera=camera;cd.lens=19;cd.clip_end=100
  scene.render.engine='BLENDER_EEVEE';scene.eevee.taa_render_samples=48;scene.render.resolution_x=1100;scene.render.resolution_y=850;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='AgX';views=[]
  for view in gallery_views():
   v=view['view'];p,t=v['position'],v['target'];camera.location=(p[0],-p[2],p[1]);camera.rotation_euler=(Vector((t[0],-t[2],t[1]))-camera.location).to_track_quat('-Z','Y').to_euler();scene.render.filepath=str(OUT/('built-'+view['name'].split('-')[-2]+'.png'));bpy.ops.render.render(write_still=True);views.append(view)
  for obj in [camera,lamp]:bpy.data.objects.remove(obj,do_unlink=True)
  bpy.data.cameras.remove(cd);bpy.data.lights.remove(ld);bpy.data.worlds.remove(world);scene.world=None;return views
 def export_navigation():
  """Export actual height-clipped saved triangles for planar route preparation."""
  bpy.ops.wm.open_mainfile(filepath=str(OUT/'component.blend'));update();surfaces=[]
  collection=bpy.data.collections[COLLECTION];scene=bpy.data.scenes.get(SCENE)or bpy.data.scenes.new(SCENE)
  if COLLECTION not in scene.collection.children:scene.collection.children.link(collection)
  bpy.context.window.scene=scene;update()
  bpy.data.libraries.write(str(OUT/'component.blend'),{collection,scene},fake_user=True,compress=True)
  report=json.loads((OUT/'audit.json').read_text());report['componentSha256']=sha(OUT/'component.blend');report['verification']['savedIndependentScene']=SCENE;write(OUT/'audit.json',report)
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
  print('OLD_NAVIGATION_SURFACES',len(surfaces),flush=True);bpy.ops.wm.quit_blender()
 def verify_navigation():
  report=json.loads((OUT/'audit.json').read_text());proofs=[]
  for repeat in range(2):
   bpy.ops.wm.open_mainfile(filepath=str(OUT/'component.blend'));update();assert{o.name:object_fingerprint(o)for o in bpy.data.objects}==report['addedFingerprints']
   scene=bpy.data.scenes.get(SCENE);assert scene is not None and COLLECTION in scene.collection.children
   assert set(scene.objects.keys())==set(report['addedObjects']);proofs.append(swept_route_surfaces(list(bpy.data.objects)))
  assert proofs[0]==proofs[1]and sha(BASE)==SHA
  report['checks']['wholeRouteSavedMeshSweep']=proofs[0];report['checks']['routeScope']='入口经教学端、周边通道绕行，到达三组桌各至少一处座席后侧接近点；0.44m几何探针，非规范认证'
  report['checks']['continuousSeatGroupReachability']=json.loads((DATA/'navigation-routes.json').read_text());report['verification']['savedComponentContainsIndependentScene']=True;report['verification']['completeRouteThinSurfaceSweepReopened']=True;report['verification']['routeProofIndependentReopens']=2;report['verification']['completeRouteTurnVolumesReopened']=True;report['verification']['failedShortcutsReproducedOnSavedTriangles']=True
  (OUT/'audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print('OLD_THREE_GROUP_ROUTE_VERIFIED',len(proofs[0]['routes']),flush=True);bpy.ops.wm.quit_blender()
 def review_existing():
  bpy.ops.wm.open_mainfile(filepath=str(OUT/'component.blend'));scene=bpy.data.scenes.get(SCENE)or bpy.data.scenes.new(SCENE)
  if COLLECTION not in scene.collection.children:scene.collection.children.link(bpy.data.collections[COLLECTION])
  update();views=render(scene)
  report=json.loads((OUT/'audit.json').read_text());report['gallerySuggestions']=views;(OUT/'audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');bpy.ops.wm.quit_blender()
 def run():
  assert sha(BASE)==SHA;bpy.ops.wm.open_mainfile(filepath=str(BASE));update();expected=accepted_fingerprints(ROOT/'result/blender/stage231',SHA);original={o.name:object_fingerprint(o)for o in bpy.data.objects};assert original==expected and len(original)==8383
  mats={m.name:material_fingerprint(m)for m in bpy.data.materials};mods={o.name:stable_modifiers(o)for o in bpy.data.objects};rooms=rooms_state();assert len(rooms)==32 and len(set(n for r in rooms for n in r['objects']))==1325;members={o.name:sorted(c.name for c in o.users_collection)for o in bpy.data.objects};vis={o.name:o.hide_render for o in bpy.data.objects};props={o.name:dict(o.items())for o in bpy.data.objects}
  scene,col,owned,records,solid=build();update();proof=checks(owned,records);views=gallery_views()
  scope='依据LSE官方历史同房号归档平面与照片建立OLD.1.27独立教室。按图保留3张六人小组桌、18把学生椅、上右入口、下侧两窗湾、左侧教学端和左下AV讲台；照片控制黑椅白桌、灰色拼块地毯、木门和窗侧木饰面、投影设备及连续方格吊顶。尺度、层高、隐蔽构造与两来源同期性未经测绘确认，独立局部样本，不作现用容量或整楼完成声明。'
  space=dict(code='OLD',id='old-127',label='OLD.1.27小组教室',collection=COLLECTION,gallery=views[0]['name'],scope=scope,interiorView=views[0]['view'],interiorStudy=dict(kind='room-sample',label='OLD.1.27小组教室',scope=scope));col['authoringRecord']=json.dumps(space,ensure_ascii=False)
  fingerprints={o.name:object_fingerprint(o)for o in owned};bindings={o.name:[m.name for m in o.data.materials]for o in owned};component=OUT/'component.blend';bpy.data.libraries.write(str(component),{col,scene},fake_user=True,compress=True)
  # Fresh native reopen proves source preservation independently of build state.
  bpy.ops.wm.open_mainfile(filepath=str(BASE));update();assert{o.name:object_fingerprint(o)for o in bpy.data.objects}==expected
  with bpy.data.libraries.load(str(component),link=False)as(src,dst):dst.collections=[COLLECTION]
  saved=dst.collections[0];scene=bpy.data.scenes.new(SCENE);scene.collection.children.link(saved);bpy.context.window.scene=scene;update();assert checks(list(saved.all_objects),records)==proof
  assert all(object_fingerprint(bpy.data.objects[n])==v for n,v in fingerprints.items());assert all(object_fingerprint(bpy.data.objects[n])==v for n,v in original.items());assert all(material_fingerprint(bpy.data.materials[n])==v for n,v in mats.items());assert all(stable_modifiers(bpy.data.objects[n])==v for n,v in mods.items());assert rooms_state()==rooms;assert all(sorted(c.name for c in bpy.data.objects[n].users_collection)==v for n,v in members.items());assert all(bpy.data.objects[n].hide_render==v for n,v in vis.items());assert all(dict(bpy.data.objects[n].items())==v for n,v in props.items());assert not any(n in bpy.data.scenes['00_CAMPUS_COMPLETE'].objects for n in fingerprints);assert sha(BASE)==SHA
  # Second component save/reopen has identical protected geometry and checks.
  checkpath=OUT/'reopen-check.blend';bpy.data.libraries.write(str(checkpath),{saved},fake_user=True,compress=True);bpy.ops.wm.open_mainfile(filepath=str(checkpath));update();assert{o.name:object_fingerprint(o)for o in bpy.data.objects}==fingerprints;assert checks(list(bpy.data.objects),records)==proof;assert not any(o.type in {'LIGHT','CAMERA'}for o in bpy.data.objects);checkpath.unlink();assert sha(BASE)==SHA
  verification=dict(savedComponentReopened=True,secondSavedComponentReopened=True,independentAcceptedObjectsVerified=len(original),allOriginalMaterialNodesVerified=len(mats),allOriginalModifierStacksVerified=len(mods),oldSpacesPreserved=len(rooms),oldSpaceUniqueObjectsPreserved=1325,allOriginalMembershipsAndPropertiesUnchanged=True,allSourceGeometryUVTransformsBindingsUnchanged=True,allOriginalVisibilityUnchanged=True,noNewRoomObjectInCampus=True,sourceNativeShaUnchanged=True,sourcePhotoNotUsedAsTexture=True,previewLightsAndCamerasExcluded=True,completeRouteThinSurfaceSweepReopened=False,triangles=sum(len(f.vertices)-2 for o in bpy.data.objects for f in o.data.polygons))
  audit=dict(version=232,building='OLD',baselinePath=str(BASE.relative_to(ROOT)),baselineSha256=SHA,componentPath=str(component.relative_to(ROOT)),componentSha256=sha(component),targetCollection=COLLECTION,destinationCollection=COLLECTION,collectionSpec=dict(kind='independent-room',name=COLLECTION,scene=SCENE),space=space,report=dict(space=space),addedObjects=list(fingerprints),archivedObjects=[],changedObjects=[],addedFingerprints=fingerprints,replacementMaterialBindings=bindings,sourceManifest='data/collections/old127-room232/sources.json',planLayout='data/collections/old127-room232/layout.json',studentSeatCount=18,teacherSeatCount=0,groupTableCount=3,scaleMetresPerPixel=SCALE,roomAreaSquareMetres=L['roomAreaSquareMetres'],estimatedCeilingHeight=HEIGHT,gallerySuggestions=views,checks=proof,solidProof=solid,verification=verification,previews=['built-teaching.png','built-seating.png'],beforeEvidence=[PLAN,PHOTO],previewLighting='Temporary area lamp below full ceiling,excluded from component;no photographic texture',limitations=json.loads((DATA/'sources.json').read_text())['limitations'])
  (OUT/'audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n');print('OLD127_ROOM232_READY',len(fingerprints),verification,flush=True);bpy.ops.wm.quit_blender()
 if __name__=='__main__':run()
