"""FAW.1.02 independent historical classroom component.

Fixed configuration for Blender's Text Editor and the MachineLearning Python.
Four counted six-chair pods follow the actual plan. No campus attachment,
photographic textures, measured-dimension claim or current-capacity claim.
"""
from pathlib import Path
import hashlib,json,math,sys
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'result/blender/faw102-room229'
DATA=ROOT/'data/collections/faw102-room229'
BASE=ROOT/'result/blender/LSE_campus_detailed_v228.blend'
SHA='0ddf5bb3791d146690d2af1f44b4cb6b113930cf687bc30d1cb916d84f4f066b'
COLLECTION='FAW102_ROOM229_study'
SCENE='ROOM229_FAW102'
PREFIX='FAW102_R229_'
PLAN='data/collections/interiors/images/190e7b49e645_FAW.1.02.GIF'
PHOTO='data/collections/interiors/images/89dfa5af7004_FAW.1.02.jpg'
SCALE=.0225
HEIGHT=3.02

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def xy(q):return[(q[0]-320)*SCALE,(480-q[1])*SCALE]
def prepare():
 from shapely.geometry import Polygon,box,Point
 from PIL import Image,ImageDraw
 DATA.mkdir(parents=True,exist_ok=True);OUT.mkdir(parents=True,exist_ok=True)
 outline=[[94,315],[533,315],[533,645],[321,645],[94,414]]
 poly=Polygon([xy(p)for p in outline]);assert poly.is_valid
 pods=[
  dict(id='upperLeft',outline=[[207,438],[217,426],[245,412],[261,411],[270,421],[273,449],[267,472],[255,476],[227,462],[211,449]],chairs=[[248,401],[217,411],[204,449],[238,477],[277,465],[282,429]]),
  dict(id='upperRight',outline=[[360,448],[367,428],[382,415],[399,405],[410,406],[423,424],[429,450],[429,467],[419,475],[395,475],[372,467],[361,458]],chairs=[[385,403],[368,428],[379,467],[407,481],[440,450],[425,415]]),
  dict(id='lowerLeft',outline=[[278,525],[288,509],[309,494],[324,490],[336,497],[345,518],[348,543],[343,554],[326,559],[300,552],[282,538]],chairs=[[311,485],[285,506],[286,544],[320,560],[355,534],[349,499]]),
  dict(id='lowerRight',outline=[[411,557],[420,537],[437,523],[451,514],[462,518],[476,536],[482,558],[480,575],[469,583],[444,584],[422,576],[413,568]],chairs=[[440,517],[414,546],[425,577],[460,584],[491,550],[478,526]])]
 seats=[]
 for pod in pods:
  shape=Polygon([xy(p)for p in pod['outline']]);assert shape.is_valid
  pod['centre']=list(shape.centroid.coords)[0];pod['metreOutline']=[xy(p)for p in pod['outline']]
  # Four steel supports are inset beneath each rounded triangular top.
  centre=shape.centroid
  pod['supports']=[list(centre.coords)[0]]
  for v in [pod['metreOutline'][i]for i in [0,len(pod['metreOutline'])//3,2*len(pod['metreOutline'])//3]]:
   p=Point(v);pod['supports'].append([centre.x+(p.x-centre.x)*.60,centre.y+(p.y-centre.y)*.60])
  for i,p in enumerate(pod['chairs']):seats.append(dict(id=pod['id']+str(i+1),pixel=p,centre=xy(p),target=pod['centre']))
 assert len(seats)==24
 def diag(t):return[94+227*t,414+231*t]
 windows=[dict(id='diagonalA',a=diag(.04),b=diag(.42)),dict(id='diagonalB',a=diag(.57),b=diag(.94)),dict(id='bottomA',a=[322,645],b=[416,645]),dict(id='bottomB',a=[430,645],b=[526,645])]
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
 layout=dict(room='FAW.1.02',outlinePixels=outline,outline=[xy(p)for p in outline],scaleMetresPerPixel=SCALE,scaleBasis='Estimated0.0225m/pixel from49px door approximately1.10m;no measured dimension printed',roomAreaSquareMetres=poly.area,studentSeatCount=24,printedCapacity=24,teacherSeatCount=0,pods=pods,seats=seats,door=dict(a=[234,315],b=[283,315],hinge=[234,315],openTip=[234,363]),windows=windows,teacherDesk=dict(a=[462,389],b=[529,429]),ceilingGridParts=grid,carpetTiles=tiles,lights=[[175,350],[355,350],[470,350],[220,470],[375,505],[455,610]],principalRoutes=[[[258.5,316],[258.5,365]],[[258.5,365],[474,365]],[[320,365],[320,455]]])
 if (DATA/'navigation-routes.json').exists():
  navigation=json.loads((DATA/'navigation-routes.json').read_text())
  if navigation.get('allFourGroupsReachable'):layout['principalRoutes']=navigation['principalRoutes']
 (DATA/'layout.json').write_text(json.dumps(layout,ensure_ascii=False,indent=2)+'\n')
 source=json.loads((ROOT/'data/collections/interiors/sources.json').read_text());refs=[r for r in source['sources']if r.get('local_path')in[PLAN,PHOTO]];assert len(refs)==2
 limitations=['历史平面创建与照片拍摄日期未知；网页2022年刷新时间与2026年检索时间均不是拍摄或测绘日期。','比例0.0225m/像素、层高3.02m、门高2.22m、窗台0.80m、窗顶2.64m、家具与隐藏构造均为估算。','平面可数4张六人小组桌及24把学生椅，恰与标注24一致；不代表当前核定容量或疏散认证。','平面控制五边形周界、四组桌椅、入口及AV讲台。照片仅拍摄部分室内，未证明全部座位、精确桌面曲率与所有家具脚型。','右侧锯齿符号结合照片木饰面，解释为关闭的木饰面可折叠隔断，不作为室外玻璃窗。','下边与斜边多线墙带解释为窗带；照片未显示这些立面。开口分段、竖向尺寸、框与灰色卷帘均属估计，来源仍可进一步测绘核实。','投影幕位于上侧教学墙，AV讲台仍按平面放在右上角；照片中的幕与木隔断支持该方位关系，但不证明同期配置。','吊顶、灯具、通风口与投影设备取照片支持的类型；连续吊顶完整，具体网格与位置估算。','独立Fawcett House教室研究，不作校园地理或楼层配准、2026年现况、全楼覆盖、无障碍或疏散认证。','严格0.44m全体积检查显示两排之间的斜捷径被图示椅位占用；保留失败候选及净距诊断，另经左侧与后侧绕行到达四组各一处座席后侧接近点。几何探针不是规范或疏散认证。','源照片仅供私下核对，不作为发布纹理。']
 manifest=dict(room='FAW.1.02',sources=refs,planSha256=sha(ROOT/PLAN),photoSha256=sha(ROOT/PHOTO),sameRoomPairVerified=True,bothImagesActualNotPlaceholder=True,sourceInterpretation=['Plan explicitly labelsFawcettHouse,floor1,room1.02,capacity24. Four pods each have six actual chair symbols,plus separate AV lectern;no teacher chair symbol is invented.','Photo shows rounded white table tops,black mesh-back chairs with arms,grey carpet squares,white suspended ceiling with square light panels,projection screen,AV lectern and floor-to-ceiling timber folding partition.','Plan lower-left diagonal is retained;entrance is on upper wall,AV station upper-right,closed movable partition is the right boundary.'],limitations=limitations)
 (DATA/'sources.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
 im=Image.open(ROOT/PLAN).convert('RGB');d=ImageDraw.Draw(im);d.line(outline+[outline[0]],fill=(190,30,30),width=2)
 for s in seats:
  x,y=s['pixel'];d.ellipse((x-2,y-2,x+2,y+2),fill=(30,50,200))
 im.save(DATA/'registered-plan.png');print('FAW102_LAYOUT_READY',poly.area,len(seats),flush=True)

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
  if not shape.is_valid:shape=shape.buffer(0)
  if shape.is_empty:continue
  if shape.area<1e-12:shape=LineString(q)
  shapes.append(shape);owners.append(item['owner'])
 obstacles=unary_union(shapes);room=Polygon(layout['outline']);radius=.23
 free=room.buffer(-radius).difference(obstacles.buffer(radius));prepared=prep(free)
 step=.10;x0,y0,x1,y1=room.bounds
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
 def pixel(p):return[p[0]/SCALE+320,480-p[1]/SCALE]
 start=xy([258.5,330]);teaching=xy([320,365]);entrance=path(start,teaching);assert entrance
 routes=[[[258.5,316],[258.5,330]]]+[[pixel(a),pixel(b)]for a,b in zip(entrance,entrance[1:])];groups=[]
 for pod in layout['pods']:
  candidates=[]
  for seat in [v for v in layout['seats']if v['id'].startswith(pod['id'])]:
   c,t=seat['centre'],seat['target'];d=[c[0]-t[0],c[1]-t[1]];length=math.hypot(*d);approach=[c[0]+d[0]/length*.55,c[1]+d[1]/length*.55];points=path(teaching,approach)
   if points:candidates.append((sum(math.dist(a,b)for a,b in zip(points,points[1:])),seat,points,approach))
  assert candidates,('GroupNotReachable',pod['id'])
  length,seat,points,approach=min(candidates,key=lambda v:v[0]);segments=[[pixel(a),pixel(b)]for a,b in zip(points,points[1:])];routes.extend(segments);groups.append(dict(group=pod['id'],reachable=True,seatId=seat['id'],seatPixel=seat['pixel'],approachPoint=pixel(approach),distanceBehindChairCentre=.55,lengthFromTeachingPoint=length,continuousPathFromTeachingPoint=[pixel(p)for p in points]))
 failed=LineString([xy([320,455]),xy([375,495])]);nearest=min(zip(shapes,owners),key=lambda item:failed.distance(item[0]));distance=failed.distance(nearest[0]);near=nearest_points(failed,nearest[0])
 diagnosis=dict(candidate=[[320,455],[375,495]],passed=False,bodyWidth=.44,verticalRange=[.04,2.10],nearestSavedMesh=nearest[1],minimumCentrelineToObstruction=distance,maximumSymmetricBodyWidthAtThisCandidate=distance*2,closestSourcePixels=[pixel(list(p.coords)[0])for p in near],intersectedFamilies=sorted(set(owner for shape,owner in zip(shapes,owners)if failed.buffer(.22,cap_style=2).intersects(shape))),reason='Actual saved furniture surfaces intersect the complete body corridor. Candidate retained as a failed shortcut; source furniture remains unchanged.')
 proof=dict(componentSha256=source['componentSha256'],geometryFingerprints=json.loads((OUT/'audit.json').read_text())['addedFingerprints'],principalRoutes=routes,method='Actual saved world triangles clipped to0.04–2.10m,projected to floor. Planar obstacles inflated0.23m;0.10m grid Astar with every edge and simplified segment covered by free space. Final complete0.44m rectangular sweeps are verified in Blender twice.',startPixel=[258.5,316],teachingPoint=[320,365],bodyProbeWidth=.44,planningRadius=.23,groups=groups,failedCandidates=[diagnosis],allFourGroupsReachable=True,routeScope='Entrance to teaching point then continuous approaches behind one chair in every pod;geometric probe only,not code or accessibility approval')
 layout['principalRoutes']=routes;layout['navigationProof']='data/collections/faw102-room229/navigation-routes.json';(DATA/'layout.json').write_text(json.dumps(layout,ensure_ascii=False,indent=2)+'\n');(DATA/'navigation-routes.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n');print('FOUR_GROUP_PATHS_PREPARED',len(routes),[(v['group'],round(v['lengthFromTeachingPoint'],2))for v in groups],diagnosis)

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
  g.box('black_student_seats','black',at(0,0,.46),(.45,.43,.065),angle)
  for x in [-.222,.222]:g.tube('black_chair_back_frames','black',at(x,.21,.47),at(x,.26,.94),.018)
  for h in [.51,.93]:g.tube('black_chair_back_frames','black',at(-.222,.21+(h-.47)*.106,h),at(.222,.21+(h-.47)*.106,h),.018)
  for i in range(16):
   z=.525+i*.025;g.box('chair_mesh_back_weave','mesh',at(0,.216+(z-.525)*.106,z),(.425,.014,.012),angle)
  feet=[]
  for x in [-.19,.19]:
   for y in [-.17,.18]:
    foot=at(x*1.10,y*1.20,0);g.tube('chair_floor_contact_pads','black',foot,at(x*1.1,y*1.2,.025),.019);g.tube('chair_steel_legs','metal',at(x*1.1,y*1.2,.025),at(x,y,.43),.016);feet.append(list(foot))
   g.tube('chair_arm_supports','black',at(x,.05,.44),at(x*1.28,.05,.65),.016);g.box('chair_armrests','black',at(x*1.28,0,.66),(.045,.30,.035),angle)
  return dict(feet=feet)
 def build():
  scene=bpy.data.scenes.new(SCENE);col=bpy.data.collections.new(COLLECTION);scene.collection.children.link(col);col['roomSample']=True;col['roomCode']='FAW.1.02';g=RoomGeometry(col,PREFIX)
  for k,c,r,m in [('plaster',(.80,.79,.73),.86,0),('black',(.015,.019,.019),.68,0),('mesh',(.055,.064,.062),.9,0),('metal',(.43,.46,.44),.37,.58),('tabletop',(.83,.83,.74),.58,0),('carpetA',(.28,.30,.28),.98,0),('carpetB',(.36,.37,.33),.98,0),('carpetC',(.22,.25,.25),.98,0),('ceiling',(.78,.79,.74),.88,0),('joint',(.51,.53,.50),.9,0),('whiteframe',(.78,.80,.75),.5,0),('glassroom',(.26,.32,.34),.22,0),('blindroom',(.40,.41,.38),.87,0),('wood',(.44,.31,.18),.72,0),('woodlight',(.51,.38,.23),.72,0),('projection',(.85,.86,.81),.72,0),('screen',(.008,.011,.012),.24,0),('cabinet',(.53,.56,.53),.67,0)]:material(g,k,c,r,m)
  g.prism('complete_plan_floor','carpetA',L['outline'],-.14,.137)
  for tile in L['carpetTiles']:g.prism('patterned_carpet_tiles',tile['material'],tile['outline'],-.003,.003)
  door=L['door'];da,db=point(door['a']),point(door['b'])
  for aa,bb in zip(L['outlinePixels'],L['outlinePixels'][1:]+L['outlinePixels'][:1]):
   a,b=point(aa),point(bb);d=b-a;events=[(0.,1.,'wall')]
   for u,v,kind in [(da,db,'door')]+[(point(w['a']),point(w['b']),'window')for w in L['windows']]:
    if abs(d.cross(u-a))>1e-5 or abs(d.cross(v-a))>1e-5:continue
    lo,hi=sorted(((u-a).dot(d)/d.length_squared,(v-a).dot(d)/d.length_squared))
    if lo<-.001 or hi>1.001:continue
    new=[]
    for s,e,k in events:
     if k!='wall'or hi<=s or lo>=e:new.append((s,e,k));continue
     if s<lo:new.append((s,lo,'wall'))
     new.append((max(s,lo),min(e,hi),kind))
     if hi<e:new.append((hi,e,'wall'))
    events=new
   for s,e,kind in events:
    if e-s<1e-7:continue
    p,q=a+d*s,a+d*e
    if kind=='wall':span(g,'complete_perimeter_walls','plaster',p,q,0,HEIGHT,.16)
    elif kind=='door':span(g,'real_door_lintel_wall','plaster',p,q,2.22,HEIGHT,.16)
    else:span(g,'window_sill_wall','plaster',p,q,0,.80,.16);span(g,'window_upper_wall','plaster',p,q,2.64,HEIGHT,.16)
    if kind!='door':span(g,'perimeter_skirting','whiteframe',p,q,0,.10,.045)
  # Closed timber operable partition: complete solid backing with actual panels.
  # This wall is not interpreted as an exterior window from the zigzag symbol.
  a,b=point([533,315]),point([533,645]);u=(b-a).normalized()
  for i in range(11):
   p,q=a.lerp(b,i/11)+Vector((-.09,0)),a.lerp(b,(i+1)/11)+Vector((-.09,0));span(g,'timber_operable_partition_panels','woodlight'if i%3==0 else'wood',p+u*.005,q-u*.005,.11,HEIGHT-.055,.045)
  span(g,'partition_upper_track','metal',a+Vector((-.09,0)),b+Vector((-.09,0)),HEIGHT-.055,HEIGHT,.065)
  for w in L['windows']:
   a,b=point(w['a']),point(w['b']);u=(b-a).normalized();inward=Vector((-u.y,u.x))
   # Outline has clockwise winding in worldXY: choose roomwardnormal by centre.
   if inward.dot(Vector((0,0))-(a+b)/2)<0:inward=-inward
   for p in [a,b]:span(g,'window_jamb_frames','whiteframe',p-u*.023,p+u*.023,.79,2.65,.18)
   for z in [.80,2.62]:span(g,'window_horizontal_frames','whiteframe',a,b,z,z+.035,.14)
   p=a.lerp(b,.5);span(g,'window_mullions','whiteframe',p-u*.020,p+u*.020,.82,2.64,.11)
   span(g,'window_glass','glassroom',a,b,.835,2.62,.016);span(g,'window_inner_sills','whiteframe',a+inward*.08,b+inward*.08,.78,.82,.25)
   span(g,'estimated_grey_roller_blinds','blindroom',a+inward*.075,b+inward*.075,1.91,2.62,.018)
  du=(db-da).normalized()
  for p in [da,db]:span(g,'door_jamb_frames','whiteframe',p-du*.025,p+du*.025,0,2.25,.18)
  span(g,'door_header_frame','whiteframe',da,db,2.22,2.27,.18)
  hinge,tip=point(door['hinge']),point(door['openTip']);span(g,'open_inward_door_leaf','wood',hinge,tip,.025,2.21,.045);h=hinge.lerp(tip,.88);g.tube('door_metal_handle','metal',(*h,.96),(*h,1.09),.013)
  # Plan shows a structural pier between the entrance and projection screen.
  p=point([315,323]);g.box('plan_structural_pier','plaster',(*p,HEIGHT/2),(.72,.37,HEIGHT))
  a,b=point([337,319]),point([462,319]);span(g,'projection_screen_black_border','black',a,b,.86,2.59,.07);span(g,'white_projection_screen','projection',a+Vector((0,-.045)),b+Vector((0,-.045)),.92,2.54,.018);span(g,'projection_screen_roll_housing','whiteframe',a,b,2.58,2.68,.12)
  ta,tb=point(L['teacherDesk']['a']),point(L['teacherDesk']['b']);tc=(ta+tb)/2;tw,td=abs(tb.x-ta.x),abs(tb.y-ta.y)
  g.box('AV_lectern_floor_plinth','cabinet',(*tc,.045),(tw-.08,td-.08,.09));g.box('AV_equipment_cabinet','cabinet',(*tc,.52),(tw-.13,td-.13,.95));g.box('AV_lectern_worktop','tabletop',(*tc,1.025),(tw,td,.06))
  g.box('AV_monitor_base','black',(tc.x+.30,tc.y,1.07),(.29,.23,.03));g.tube('AV_monitor_stand','metal',(tc.x+.30,tc.y,1.085),(tc.x+.30,tc.y,1.31),.022);g.box('AV_monitor','screen',(tc.x+.30,tc.y,1.45),(.48,.065,.29));g.box('AV_keyboard','black',(tc.x+.28,tc.y-.24,1.07),(.43,.15,.03));g.box('AV_control_panel','black',(tc.x-.36,tc.y-.11,1.09),(.29,.23,.07))
  g.tube('document_camera_support','black',(tc.x-.43,tc.y+.12,1.055),(tc.x-.43,tc.y+.12,1.51),.018);g.tube('document_camera_arm','black',(tc.x-.43,tc.y+.12,1.51),(tc.x-.63,tc.y-.06,1.50),.018);g.box('document_camera_head','black',(tc.x-.63,tc.y-.06,1.48),(.12,.10,.055))
  supports=[]
  for pod in L['pods']:
   g.prism('four_rounded_white_group_tabletops','tabletop',pod['metreOutline'],.735,.045)
   for p in pod['supports']:
    g.tube('table_floor_contact_pads','black',(*p,0),(*p,.022),.032);g.tube('table_steel_legs','metal',(*p,.022),(*p,.742),.026);supports.append(dict(foot=[*p,0],top=[*p,.742]))
  seats=[chair(g,s)for s in L['seats']]
  g.prism('continuous_complete_ceiling','ceiling',L['outline'],HEIGHT,.10)
  for ring in L['ceilingGridParts']:g.prism('continuous_ceiling_panel_grid','joint',ring,HEIGHT-.004,.004)
  lightSupports=[]
  for px in L['lights']:
   p=point(px);g.box('ceiling_light_housings','whiteframe',(*p,HEIGHT-.027),(.57,.57,.054));g.box('ceiling_light_diffusers','light',(*p,HEIGHT-.059),(.53,.53,.010));lightSupports.append([*p,HEIGHT])
  for px in [[320,395],[455,465]]:
   p=point(px);g.box('ceiling_vent_frame','whiteframe',(*p,HEIGHT-.016),(.54,.54,.032))
   for d in range(12):g.box('ceiling_vent_dark_louvres','mesh',(p.x-.24+d*.044,p.y,HEIGHT-.036),(.012,.46,.014))
  p=point([397,465]);g.tube('projector_ceiling_hanger','whiteframe',(*p,HEIGHT+.01),(*p,2.72),.024);g.box('ceiling_projector','whiteframe',(*p,2.67),(.42,.32,.12));g.tube('projector_lens','black',(p.x,p.y+.15,2.67),(p.x,p.y+.20,2.67),.038)
  objects=g.finish()
  for o in objects:o['roomCode']='FAW.1.02';o['destinationCollection']=COLLECTION;o['scope']='Independent historical plan-layout classroom;estimated dimensions;no geographic registration or2026capacityclaim'
  return scene,col,objects,dict(seats=seats,tableSupports=supports,lecternCentre=list(tc),lightSupports=lightSupports,door=dict(a=list(da),b=list(db),clearWidth=(db-da).length-.05)),g.solid_proof

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
  return dict(method='Allsavedworldtrianglesclippedto0.04–2.10mbodyheightandthecomplete0.44mwiderectangularcorridor;thinhorizontalandslantedfurnituresurfacesincluded',eligibleTriangles=len(surfaces),routes=routes,totalIntersections=0)
 def checks(objects,R):
  floor,_=tree([o for o in objects if any(k in o.name for k in ['complete_plan_floor','patterned_carpet_tiles'])]);ceiling,_=tree([o for o in objects if o.name==PREFIX+'continuous_complete_ceiling']);tops,_=tree([o for o in objects if o.name==PREFIX+'four_rounded_white_group_tabletops']);solid,names=tree([o for o in objects if not any(k in o.name for k in ['complete_plan_floor','patterned_carpet_tiles','ceiling'])])
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
  doorway=[];a,b=Vector(R['door']['a']),Vector(R['door']['b']);c=(a+b)/2;u=(b-a).normalized()
  for d in [-.22,0,.22]:
   for z in [.04,.65,1.20,2.1]:
    p=c+u*d+Vector((0,-.25));h=solid.ray_cast(Vector((*p,z)),Vector((0,1,0)),.5);assert h[0]is None,('DoorBlocked',d,z,names[h[2]]if h[2]is not None else'');doorway.append([d,z])
  walltree,_=tree([o for o in objects if any(k in o.name for k in ['perimeter_walls','sill_wall','upper_wall','door_lintel'])]);window=[]
  for w in L['windows']:
   a,b=point(w['a']),point(w['b']);u=(b-a).normalized();normal=Vector((-u.y,u.x))
   for t in [.2,.5,.8]:
    c=a.lerp(b,t)
    for z in [1.2,1.7,2.5]:
     h=walltree.ray_cast(Vector((c.x-normal.x*.25,c.y-normal.y*.25,z)),Vector((*normal,0)),.5);assert h[0]is None,('UncutWindow',w['id'],t,z);window.append([w['id'],t,z])
  result=dict(studentSeatCount=24,groupTableCount=4,teacherSeatCount=0,AVLecternCount=1,studentFootCount=96,footSupportProbes=feet,tableFloorAndWorktopContacts=contacts,lecternFloorContact=lecternContact,ceilingLightSupportContacts=lampSupport,continuousCeilingCoverage=dict(spacingMetres=step,probeCount=len(coverage),missCount=0,undersideHeight=HEIGHT,pointDigest=hashlib.sha256(json.dumps(coverage).encode()).hexdigest()),realDoorOpeningClearRays=doorway,doorClearWidth=R['door']['clearWidth'],realWindowWallApertureRays=window,wholeRouteSavedMeshSweep=swept_route_surfaces(objects),routeScope='入口经教学端及左侧与后侧绕行，连接四组各一处座席接近点；0.44m宽、0.04至2.10m高完整体积，失败斜捷径另存，不作规范认证',allAuthoredComponentsClosed=True)
  if (DATA/'navigation-routes.json').exists():
   navigation=json.loads((DATA/'navigation-routes.json').read_text());assert{o.name:object_fingerprint(o)for o in objects}==navigation['geometryFingerprints'];result['continuousSeatGroupReachability']=navigation;result['routeScope']='入口经教学端、左侧斜墙及后侧绕行，到达四组各一处座席后侧接近点；保留失败斜捷径诊断，几何探针非规范认证'
  return result
 def render(scene):
  bpy.context.window.scene=scene;world=bpy.data.worlds.new(PREFIX+'previewWorld');world.use_nodes=True;world.node_tree.nodes['Background'].inputs[0].default_value=(.76,.80,.84,1);world.node_tree.nodes['Background'].inputs[1].default_value=.22;scene.world=world
  ld=bpy.data.lights.new(PREFIX+'previewArea','AREA');ld.energy=650;ld.shape='DISK';ld.size=6;lamp=bpy.data.objects.new(ld.name,ld);scene.collection.objects.link(lamp);lamp.location=(0,0,HEIGHT-.30)
  cd=bpy.data.cameras.new(PREFIX+'previewCamera');camera=bpy.data.objects.new(cd.name,cd);scene.collection.objects.link(camera);scene.camera=camera;cd.lens=18;cd.clip_end=100
  scene.render.engine='BLENDER_EEVEE';scene.eevee.taa_render_samples=24;scene.render.resolution_x=1100;scene.render.resolution_y=850;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='AgX';views=[]
  for name,pp,tp,z,tz,label in [('teaching',[374,606],[376,325],1.66,1.48,'FAW.1.02小组桌与投影教学端'),('seating',[184,375],[420,550],1.65,1.23,'FAW.1.02四组六人桌与木饰面隔断')]:
   p,t=point(pp),point(tp);camera.location=(*p,z);camera.rotation_euler=(Vector((*t,tz))-camera.location).to_track_quat('-Z','Y').to_euler();scene.render.filepath=str(OUT/('built-'+name+'.png'));bpy.ops.render.render(write_still=True);views.append(dict(name='faw-102-'+name+'-interior',code='FAW',spaceId='faw-102',label=label,view=dict(position=[p.x,z,-p.y],target=[t.x,tz,-t.y],fov=90)))
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
  print('FAW_NAVIGATION_SURFACES',len(surfaces),flush=True);bpy.ops.wm.quit_blender()
 def verify_navigation():
  report=json.loads((OUT/'audit.json').read_text());proofs=[]
  for repeat in range(2):
   bpy.ops.wm.open_mainfile(filepath=str(OUT/'component.blend'));update();assert{o.name:object_fingerprint(o)for o in bpy.data.objects}==report['addedFingerprints'];proofs.append(swept_route_surfaces(list(bpy.data.objects)))
  assert proofs[0]==proofs[1]and sha(BASE)==SHA
  report['checks']['wholeRouteSavedMeshSweep']=proofs[0];report['checks']['routeScope']='入口经教学端、左侧斜墙绕行，到达四组桌各至少一处座席后侧接近点；0.44m几何探针，非规范认证'
  report['checks']['continuousSeatGroupReachability']=json.loads((DATA/'navigation-routes.json').read_text());report['verification']['completeRouteThinSurfaceSweepReopened']=True;report['verification']['routeProofIndependentReopens']=2
  (OUT/'audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print('FAW_FOUR_GROUP_ROUTE_VERIFIED',len(proofs[0]['routes']),flush=True);bpy.ops.wm.quit_blender()
 def review_existing():
  bpy.ops.wm.open_mainfile(filepath=str(OUT/'component.blend'));scene=bpy.data.scenes.new(SCENE);scene.collection.children.link(bpy.data.collections[COLLECTION]);update();views=render(scene)
  report=json.loads((OUT/'audit.json').read_text());report['gallerySuggestions']=views;(OUT/'audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');bpy.ops.wm.quit_blender()
 def run():
  assert sha(BASE)==SHA;bpy.ops.wm.open_mainfile(filepath=str(BASE));update();expected=accepted_fingerprints(ROOT/'result/blender/stage228',SHA);original={o.name:object_fingerprint(o)for o in bpy.data.objects};assert original==expected and len(original)==8074
  mats={m.name:material_fingerprint(m)for m in bpy.data.materials};mods={o.name:stable_modifiers(o)for o in bpy.data.objects};rooms=rooms_state();assert len(rooms)==27 and len(set(n for r in rooms for n in r['objects']))==1068;members={o.name:sorted(c.name for c in o.users_collection)for o in bpy.data.objects};vis={o.name:o.hide_render for o in bpy.data.objects};props={o.name:dict(o.items())for o in bpy.data.objects}
  scene,col,owned,records,solid=build();update();proof=checks(owned,records);views=render(scene)
  scope='依据LSE历史同房号平面与照片建立FAW.1.02独立教室。按图保留五边形周界、4张六人小组桌、24把黑色网背椅、AV讲台、上侧入口、下边及斜边窗带和右侧木饰面隔断；照片控制白色桌面、灰色地毯、投影幕及吊顶设备。尺度、层高、窗带解释与隐藏构造估算，连续完整天花，不作地理配准或2026现况认证。'
  space=dict(code='FAW',id='faw-102',label='FAW.1.02小组教室',collection=COLLECTION,gallery=views[0]['name'],scope=scope,interiorView=views[0]['view'],interiorStudy=dict(kind='room-sample',label='FAW.1.02小组教室',scope=scope));col['authoringRecord']=json.dumps(space,ensure_ascii=False)
  fingerprints={o.name:object_fingerprint(o)for o in owned};bindings={o.name:[m.name for m in o.data.materials]for o in owned};component=OUT/'component.blend';bpy.data.libraries.write(str(component),{col},fake_user=True,compress=True)
  # Fresh native reopen proves source preservation independently of build state.
  bpy.ops.wm.open_mainfile(filepath=str(BASE));update();assert{o.name:object_fingerprint(o)for o in bpy.data.objects}==expected
  with bpy.data.libraries.load(str(component),link=False)as(src,dst):dst.collections=[COLLECTION]
  saved=dst.collections[0];scene=bpy.data.scenes.new(SCENE);scene.collection.children.link(saved);bpy.context.window.scene=scene;update();assert checks(list(saved.all_objects),records)==proof
  assert all(object_fingerprint(bpy.data.objects[n])==v for n,v in fingerprints.items());assert all(object_fingerprint(bpy.data.objects[n])==v for n,v in original.items());assert all(material_fingerprint(bpy.data.materials[n])==v for n,v in mats.items());assert all(stable_modifiers(bpy.data.objects[n])==v for n,v in mods.items());assert rooms_state()==rooms;assert all(sorted(c.name for c in bpy.data.objects[n].users_collection)==v for n,v in members.items());assert all(bpy.data.objects[n].hide_render==v for n,v in vis.items());assert all(dict(bpy.data.objects[n].items())==v for n,v in props.items());assert not any(n in bpy.data.scenes['00_CAMPUS_COMPLETE'].objects for n in fingerprints);assert sha(BASE)==SHA
  # Second component save/reopen has identical protected geometry and checks.
  checkpath=OUT/'reopen-check.blend';bpy.data.libraries.write(str(checkpath),{saved},fake_user=True,compress=True);bpy.ops.wm.open_mainfile(filepath=str(checkpath));update();assert{o.name:object_fingerprint(o)for o in bpy.data.objects}==fingerprints;assert checks(list(bpy.data.objects),records)==proof;assert not any(o.type in {'LIGHT','CAMERA'}for o in bpy.data.objects);checkpath.unlink();assert sha(BASE)==SHA
  verification=dict(savedComponentReopened=True,secondSavedComponentReopened=True,independentAcceptedObjectsVerified=len(original),allOriginalMaterialNodesVerified=len(mats),allOriginalModifierStacksVerified=len(mods),oldSpacesPreserved=len(rooms),oldSpaceUniqueObjectsPreserved=1068,allOriginalMembershipsAndPropertiesUnchanged=True,allSourceGeometryUVTransformsBindingsUnchanged=True,allOriginalVisibilityUnchanged=True,noNewRoomObjectInCampus=True,sourceNativeShaUnchanged=True,sourcePhotoNotUsedAsTexture=True,previewLightsAndCamerasExcluded=True,completeRouteThinSurfaceSweepReopened=True,triangles=sum(len(f.vertices)-2 for o in bpy.data.objects for f in o.data.polygons))
  audit=dict(version=229,building='FAW',baselinePath=str(BASE.relative_to(ROOT)),baselineSha256=SHA,componentPath=str(component.relative_to(ROOT)),componentSha256=sha(component),targetCollection=COLLECTION,destinationCollection=COLLECTION,collectionSpec=dict(kind='independent-room',name=COLLECTION,scene=SCENE),space=space,report=dict(space=space),addedObjects=list(fingerprints),archivedObjects=[],changedObjects=[],addedFingerprints=fingerprints,replacementMaterialBindings=bindings,sourceManifest='data/collections/faw102-room229/sources.json',planLayout='data/collections/faw102-room229/layout.json',studentSeatCount=24,teacherSeatCount=0,groupTableCount=4,scaleMetresPerPixel=SCALE,roomAreaSquareMetres=L['roomAreaSquareMetres'],estimatedCeilingHeight=HEIGHT,gallerySuggestions=views,checks=proof,solidProof=solid,verification=verification,previews=['built-teaching.png','built-seating.png'],beforeEvidence=[PLAN,PHOTO],previewLighting='Temporary area lamp below full ceiling,excluded from component;no photographic texture',limitations=json.loads((DATA/'sources.json').read_text())['limitations'])
  (OUT/'audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n');print('FAW102_ROOM229_READY',len(fingerprints),verification,flush=True);bpy.ops.wm.quit_blender()
 if __name__=='__main__':run()
