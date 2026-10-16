"""CON.7.04 independent historical conference-room study, fixed configuration.

Run prepare() in MachineLearning, run() in Blender, solve_navigation() in
MachineLearning, then finalize() in Blender. No command-line argument interface,
source-photo textures, campus registration or edits to accepted original data.
"""
from pathlib import Path
import hashlib,json,math,sys
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'result/blender/con704-room231';DATA=ROOT/'data/collections/con704-room231'
BASE=ROOT/'result/blender/LSE_campus_detailed_v230.blend'
SHA='232793610db8d3ff488e7f10df9a4f96a239f7b870747777042b2332f242a0bf'
COLLECTION='CON704_ROOM231_study';SCENE='ROOM231_CON704';PREFIX='CON704_R231_'
PLAN='data/collections/interiors/images/11f7e4c56390_CON.7.04.GIF'
PHOTO='data/collections/interiors/images/73b7be2bc2de_CON.7.04.jpg'
SCALE=.020;HEIGHT=2.95

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def write(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
def xy(q):return[(q[0]-300)*SCALE,(220-q[1])*SCALE]
def pixel(q):return[q[0]/SCALE+300,220-q[1]/SCALE]
def prepare():
 from shapely.geometry import Polygon,box
 from PIL import Image,ImageDraw
 DATA.mkdir(parents=True,exist_ok=True);OUT.mkdir(parents=True,exist_ok=True)
 outline=[[130,112],[454,112],[458,148],[468,288],[470,329],[130,329],[130,249],[122,249],[122,194],[130,194]]
 # Three actual plan swings: upper/lower leaves open out of this room;
 # the named7.04side entrance leaf opens inward towards the upper side.
 doors=[dict(id='main',a=[122,194],b=[122,249],hinge=[122,194],openTip=[185,194]),dict(id='upper',a=[178,112],b=[236,112],hinge=[236,112],openTip=[236,44]),dict(id='lower',a=[179,329],b=[236,329],hinge=[236,329],openTip=[236,398])]
 windows=[dict(id='endWindow',a=[458,148],b=[468,288])]
 table=[[218,199],[249,192],[287,190],[332,190],[370,193],[409,199],[419,208],[422,220],[419,232],[409,241],[371,247],[332,250],[287,250],[250,247],[219,241],[209,233],[206,220],[209,208]]
 seats=[]
 for group,coords in [('north',[[260,188],[318,183],[374,188]]),('south',[[260,250],[318,254],[374,250]]),('west',[[212,220]]),('east',[[420,220]])]:
  for i,p in enumerate(coords):
   target=[p[0]+(4 if p[0]<318 else -4 if p[0]>318 else 0),220]if group in['north','south']else[318,220]
   seats.append(dict(id=group+str(i+1),group=group,pixel=p,centre=xy(p),target=xy(target)))
 poly=Polygon([xy(p)for p in outline]);assert poly.is_valid
 tiles=[]
 for i in range(math.floor(poly.bounds[0]/.5),math.ceil(poly.bounds[2]/.5)):
  for j in range(math.floor(poly.bounds[1]/.5),math.ceil(poly.bounds[3]/.5)):
   part=poly.intersection(box(i*.5,j*.5,(i+1)*.5,(j+1)*.5))
   pieces=[part]if part.geom_type=='Polygon'else[g for g in getattr(part,'geoms',[])if g.geom_type=='Polygon']
   tiles.extend(dict(outline=list(v.exterior.coords)[:-1],material='carpet'+str((i+2*j)%3))for v in pieces if v.area>1e-8)
 layout=dict(room='CON.7.04',outlinePixels=outline,outline=[xy(p)for p in outline],scaleMetresPerPixel=SCALE,scaleBasis='Estimated0.020m/pixel from55px side entrance approximately1.10m; no printed measured dimension',roomAreaSquareMetres=poly.area,seats=seats,seatCount=8,printedCapacity=8,teacherSeatCount=0,tableOutlinePixels=table,tableOutline=[xy(p)for p in table],doors=doors,windows=windows,carpetTiles=tiles,principalRoutes=[],ceilingHeight=HEIGHT,teachingPoint=[410,145])
 write(DATA/'layout.json',layout)
 refs=[r for r in json.loads((ROOT/'data/collections/interiors/sources.json').read_text())['sources']if r.get('local_path')in[PLAN,PHOTO]];assert len(refs)==2
 limits=['平面和照片创建日期未知，网页刷新及归档检索日期均非拍摄或测绘日期，不能证明同期或2026现况。','平面可直接识别CON7.04、印刷容量8及长边各3椅两端各1椅；模型严格保留8个来源椅位，不代表当前核定容量。','比例0.020m/像素、层高2.95m、门高2.24m、窗台0.94m、窗顶2.65m、桌椅高度及隐蔽构造均为估计。','平面控制不规则周界、左侧中部入口、上下两处向外开启的门、右端斜窗带、长弧边会议桌及8椅；照片未覆盖三处门，门套及叶片构造同型概括；平面开启弧线仅控制开启方向，门扇长度按对应门洞宽减0.03m估计，避免示意弧线产生比门洞更宽的门扇。','照片支持深色木饰面板墙、暖木色弧边会议桌及线槽盖、黑色扶手会议椅与金属支架、灰色地毯、端窗、浅色卷帘、邻窗左侧显示屏及其下方白色壁挂设备。','显示屏及白色壁挂设备在窗前上侧墙区布置；图上没有设备定位，精确位置、白色设备用途、木板分格与桌脚构造为估计。','照片未显示完整天花与照明，建立连续浅色完整天花及照片可见的周边木线脚，不臆测格栅或悬灯。','窗格依据照片概括为四竖格，窗斜角及立面高度估算；窗外不放源照片或虚构外景。','源照片仅供私下核对，不作为纹理，不拷入发布资源；未确认开放再利用许可。','独立历史会议室研究，不作校园地理或楼层配准、2026现况、疏散或无障碍认证。','通路验证使用实际保存网格0.04至2.10m全高三角面与0.44m完整扫掠，含转折和末端体积；椅位固定并保留失败捷径。']
 write(DATA/'sources.json',dict(room='CON.7.04',sources=refs,planSha256=sha(ROOT/PLAN),photoSha256=sha(ROOT/PHOTO),planResolution=[587,440],photoResolution=[450,600],sameRoomPairVerified=True,pairBasis='Official source filenames bothCON.7.04; plan visibly labelsCON7.04,capacity8; source chronology unverified',bothImagesActualNotPlaceholder=True,sourceSeatCount=dict(north=3,south=3,west=1,east=1,total=8),limitations=limits))
 im=Image.open(ROOT/PLAN).convert('RGB');d=ImageDraw.Draw(im);d.line(outline+[outline[0]],fill=(180,30,30),width=2);d.line(table+[table[0]],fill=(20,120,40),width=2)
 for seat in seats:
  x,y=seat['pixel'];d.ellipse((x-3,y-3,x+3,y+3),fill=(25,55,190))
 im.save(DATA/'registered-plan.png');print('CON704_LAYOUT_READY',poly.area,len(seats),flush=True)

def solve_navigation():
 """Find routes using saved triangles, retaining zero-area vertical projections."""
 import heapq
 from shapely.geometry import Polygon,LineString,Point
 from shapely.ops import unary_union,nearest_points
 from shapely.prepared import prep
 layout=json.loads((DATA/'layout.json').read_text());source=json.loads((DATA/'navigation-surfaces.json').read_text());assert source['componentSha256']==sha(OUT/'component.blend')
 shapes=[];owners=[];vertical=0
 for row in source['surfaces']:
  q=row['polygon'];shape=Polygon(q)if len(q)>=3 else LineString(q)
  if shape.area<1e-12:shape=LineString(q).convex_hull;vertical+=1
  elif not shape.is_valid:shape=shape.buffer(0)
  if shape.is_empty:continue
  shapes.append(shape);owners.append(row['owner'])
 obstacles=unary_union(shapes);room=Polygon(layout['outline']);radius=.23
 # The full open threshold is real floor geometry; only this doorway projects
 # outside the plan outline, by its estimated wall-thickness apron.
 threshold=Polygon([xy(p)for p in [[109,194],[134,194],[134,249],[109,249]]]);room=room.union(threshold)
 free=room.buffer(-radius).difference(obstacles.buffer(radius));prepared=prep(free);step=.05;x0,y0,x1,y1=room.bounds
 def coord(n):return(x0+n[0]*step,y0+n[1]*step)
 nodes={(i,j)for i in range(math.ceil((x1-x0)/step)+1)for j in range(math.ceil((y1-y0)/step)+1)if prepared.contains(Point(coord((i,j))))}
 def connected(a,b):return prepared.covers(LineString([a,b]))
 def anchor(p):
  return next((n for n in sorted(nodes,key=lambda n:math.dist(coord(n),p))[:50]if connected(p,coord(n))),None)
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
   j=next(j for j in range(len(points)-1,index,-1)if connected(points[index],points[j]));result.append(points[j]);index=j
  return result
 start=xy([123,221]);teaching=xy(layout['teachingPoint']);entrance=path(start,teaching);assert entrance,('DisplayPointUnreachable',layout['teachingPoint'])
 routes=[[pixel(a),pixel(b)]for a,b in zip(entrance,entrance[1:])];seats=[];outcomes=[]
 for seat in layout['seats']:
  c,t=seat['centre'],seat['target'];d=[c[0]-t[0],c[1]-t[1]];length=math.hypot(*d);d=[d[0]/length,d[1]/length];side=[-d[1],d[0]];candidates=[]
  for kind,offset in [('behind',[d[0]*.57,d[1]*.57]),('sideA',[d[0]*.16+side[0]*.64,d[1]*.16+side[1]*.64]),('sideB',[d[0]*.16-side[0]*.64,d[1]*.16-side[1]*.64])]:
   approach=[c[0]+offset[0],c[1]+offset[1]];points=path(teaching,approach);outcomes.append(dict(seatId=seat['id'],kind=kind,approachPixel=pixel(approach),reachable=points is not None))
   if points:candidates.append((0 if kind=='behind'else 1,sum(math.dist(a,b)for a,b in zip(points,points[1:])),kind,approach,points))
  assert candidates,('FixedSeatUnreachable',seat['id'])
  _,length,kind,approach,points=min(candidates,key=lambda v:(v[0],v[1]));routes.extend([[pixel(a),pixel(b)]for a,b in zip(points,points[1:])]);seats.append(dict(seatId=seat['id'],group=seat['group'],seatPixel=seat['pixel'],approachKind=kind,approachPixel=pixel(approach),pathFromDisplay=[pixel(p)for p in points],pathFromEntry=[pixel(p)for p in entrance]+[pixel(p)for p in points[1:]],reachable=True))
 failed=LineString([xy([165,220]),xy([442,220])]);nearest=min(zip(shapes,owners),key=lambda v:failed.distance(v[0]));distance=failed.distance(nearest[0]);near=nearest_points(failed,nearest[0]);assert failed.buffer(.22,cap_style=2).intersects(obstacles)
 failure=dict(candidate=[[165,220],[442,220]],passed=False,width=.44,verticalRange=[.04,2.10],nearestSavedMesh=nearest[1],minimumCentrelineToObstruction=distance,closestSourcePixels=[pixel(list(p.coords)[0])for p in near],intersectedFamilies=sorted(set(owner for shape,owner in zip(shapes,owners)if failed.buffer(.22,cap_style=2).intersects(shape))),reason='The complete saved tabletop and/or chairs occupy this shortcut body volume; furniture remains at source plan centres.')
 proof=dict(componentSha256=source['componentSha256'],principalRoutes=routes,method='All saved world triangles clipped to0.04–2.10m; zero-area projected vertical faces retained as lines before polygon repair.0.23m inflated obstacles and0.05m Astar grid, every edge and simplified segment covered by free space. Complete0.44m sweeps and turn/end volumes verified independently in Blender.',startPixel=[123,221],teachingPoint=layout['teachingPoint'],bodyProbeWidth=.44,planningRadius=.23,seatApproaches=seats,allSeatApproachCandidates=outcomes,failedCandidates=[failure],allEightSourceSeatsReachable=True,verticalTriangleProjectionsRetained=vertical,routeScope='Open side entrance to display operating point and a valid rear/side approach for every fixed chair; geometric study,not accessibility or egress certification')
 layout['principalRoutes']=routes;write(DATA/'layout.json',layout);write(DATA/'navigation-routes.json',proof);print('CON704_PATHS_PREPARED',len(routes),[(s['seatId'],s['approachKind'])for s in seats],flush=True)

try:import bpy
except ModuleNotFoundError:
 if __name__=='__main__':prepare()
else:
 from mathutils import Vector
 sys.path.insert(0,str(ROOT/'web/tools'))
 from build_room_samples167 import RoomGeometry
 from integrate_exterior_round194 import object_fingerprint
 from refine_portsmouth_exterior207 import material_fingerprint
 from refine_ksw_exterior219 import modifier_state
 L=json.loads((DATA/'layout.json').read_text())
 def point(q):return Vector(xy(q))
 def update():
  for scene in bpy.data.scenes:
   for layer in scene.view_layers:layer.update()
 def state():
  bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE'];update();meta=json.loads((ROOT/'web/tools/building-metadata.json').read_text())
  rooms={r['collection']:sorted(o.name for o in bpy.data.collections[r['collection']].all_objects)for r in meta['spaces']}
  return dict(objects={o.name:object_fingerprint(o)for o in bpy.data.objects},materials={m.name:material_fingerprint(m)for m in bpy.data.materials},modifiers={o.name:modifier_state(o)for o in bpy.data.objects},props={o.name:repr(sorted(o.items()))for o in bpy.data.objects},owners={o.name:sorted(c.name for c in o.users_collection)for o in bpy.data.objects},visibility={o.name:[o.hide_render,o.hide_viewport,o.hide_get()]for o in bpy.data.objects},rooms=rooms,scenes={s.name:sorted(s.objects.keys())for s in bpy.data.scenes})
 def verify_original(before):
  bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE'];update()
  assert all(object_fingerprint(bpy.data.objects[n])==v for n,v in before['objects'].items())
  assert all(material_fingerprint(bpy.data.materials[n])==v for n,v in before['materials'].items())
  assert all(modifier_state(bpy.data.objects[n])==v for n,v in before['modifiers'].items())
  assert all(repr(sorted(bpy.data.objects[n].items()))==v for n,v in before['props'].items())
  assert all(sorted(c.name for c in bpy.data.objects[n].users_collection)==v for n,v in before['owners'].items())
  assert all([bpy.data.objects[n].hide_render,bpy.data.objects[n].hide_viewport,bpy.data.objects[n].hide_get()]==v for n,v in before['visibility'].items())
  assert all(sorted(o.name for o in bpy.data.collections[n].all_objects)==v for n,v in before['rooms'].items())
  assert all(sorted(bpy.data.scenes[n].objects.keys())==v for n,v in before['scenes'].items())
  assert sha(BASE)==SHA
 def material(g,key,color,rough=.7,metal=0,wood=False):
  m=bpy.data.materials.new(PREFIX+key);m.use_nodes=True;m.diffuse_color=(*color,1);nodes=m.node_tree.nodes;links=m.node_tree.links;n=nodes['Principled BSDF'];n.inputs['Base Color'].default_value=m.diffuse_color;n.inputs['Roughness'].default_value=rough;n.inputs['Metallic'].default_value=metal
  if wood:
   uv=nodes.new('ShaderNodeTexCoord');mapping=nodes.new('ShaderNodeVectorMath');mapping.operation='MULTIPLY';mapping.inputs[1].default_value=(1.4,38,1);noise=nodes.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=2.8;noise.inputs['Detail'].default_value=2;ramp=nodes.new('ShaderNodeValToRGB');ramp.color_ramp.elements[0].color=(*[v*.67 for v in color],1);ramp.color_ramp.elements[1].color=(*[min(1,v*1.15)for v in color],1);links.new(uv.outputs['UV'],mapping.inputs[0]);links.new(mapping.outputs['Vector'],noise.inputs['Vector']);links.new(noise.outputs['Fac'],ramp.inputs[0]);links.new(ramp.outputs['Color'],n.inputs['Base Color'])
  g.materials[key]=m
 def span(g,family,key,a,b,lo,hi,depth=.14):
  a,b=Vector(a),Vector(b);d=b-a;c=(a+b)/2;g.box(family,key,(*c,(lo+hi)/2),(d.length,depth,hi-lo),math.atan2(d.y,d.x))
 def chair(g,seat):
  p,t=Vector(seat['centre']),Vector(seat['target']);angle=math.atan2(t.y-p.y,t.x-p.x)+math.pi/2;c,s=math.cos(angle),math.sin(angle)
  def at(x,y,z):return(p.x+c*x-s*y,p.y+s*x+c*y,z)
  g.box('eight_black_upholstered_seats','black',at(0,0,.46),(.48,.44,.055),angle)
  g.box('eight_black_upholstered_backs','black',at(0,.235,.76),(.46,.050,.40),angle)
  for z in [.64,.70,.76,.82,.88]:g.box('chair_back_horizontal_ribs','ribblack',at(0,.203,z),(.425,.014,.007),angle)
  feet=[]
  for x in [-.255,.255]:
   for y in [-.235,.245]:
    foot=at(x,y,0);g.tube('chair_floor_contact_pads','black',foot,at(x,y,.020),.020);feet.append(list(foot))
   # Photo-supported chrome sled/cantilever frame with black arm pads.
   g.tube('chrome_chair_sled_bases','metal',at(x,-.235,.028),at(x,.245,.028),.017)
   g.tube('chrome_chair_front_uprights','metal',at(x,-.235,.028),at(x,-.175,.65),.016)
   g.tube('chrome_chair_armrests','metal',at(x,-.175,.65),at(x,.24,.65),.016)
   g.tube('chrome_chair_back_supports','metal',at(x,.24,.65),at(x,.27,.91),.014)
   g.box('black_chair_armrest_pads','black',at(x,.045,.671),(.055,.33,.032),angle)
   g.tube('chair_underseat_supports','metal',at(x,-.17,.44),at(x,.22,.44),.016)
  return dict(id=seat['id'],sourcePixel=seat['pixel'],centre=list(p),feet=feet)
 def build():
  scene=bpy.data.scenes.new(SCENE);col=bpy.data.collections.new(COLLECTION);scene.collection.children.link(col);col['roomSample']=True;col['roomCode']='CON.7.04';g=RoomGeometry(col,PREFIX)
  for k,c,r,m,w in [('plaster',(.78,.76,.67),.84,0,False),('wood',(.27,.115,.035),.48,0,True),('woodlight',(.36,.18,.055),.46,0,True),('wooddark',(.12,.052,.015),.52,0,False),('tablewood',(.52,.245,.057),.28,0,True),('black',(.018,.021,.020),.77,0,False),('ribblack',(.035,.040,.038),.72,0,False),('metal',(.42,.45,.43),.28,.75,False),('whiteframe',(.71,.73,.68),.52,0,False),('carpet0',(.17,.19,.17),.98,0,False),('carpet1',(.19,.21,.19),.98,0,False),('carpet2',(.21,.22,.20),.98,0,False),('glassroom',(.31,.39,.41),.20,0,False),('screen',(.006,.008,.009),.25,0,False),('blind',(.52,.53,.48),.9,0,False)]:material(g,k,c,r,m,w)
  g.prism('complete_plan_floor','carpet0',L['outline'],-.14,.137)
  for tile in L['carpetTiles']:g.prism('patterned_carpet_tiles',tile['material'],tile['outline'],-.003,.003)
  g.prism('main_door_threshold_floor','carpet0',[xy(p)for p in [[109,194],[134,194],[134,249],[109,249]]],-.14,.14)
  def roomward(a,b):
   u=(b-a).normalized();normal=Vector((-u.y,u.x))
   if normal.dot(-(a+b)/2)<0:normal=-normal
   return normal
  def panelled_wall(a,b):
   normal=roomward(a,b);u=(b-a).normalized();length=(b-a).length;span(g,'complete_perimeter_walls','wood',a,b,0,HEIGHT,.16)
   for z in [.12,.88,2.56,2.72]:span(g,'wood_wall_horizontal_mouldings','wooddark',a+normal*.09,b+normal*.09,z,z+.04,.04)
   count=max(1,round(length/.78))
   for i in range(count):
    p,q=a.lerp(b,i/count),a.lerp(b,(i+1)/count)
    if(q-p).length<.15:continue
    for z0,z1 in[(.19,.82),(.96,2.50)]:span(g,'recessed_timber_wall_panels','woodlight',p+u*.055+normal*.086,q-u*.055+normal*.086,z0,z1,.018)
    for r in[p,q]:span(g,'timber_wall_panel_stiles','wooddark',r-u*.017+normal*.097,r+u*.017+normal*.097,.15,2.58,.035)
   for z0,z1,depth in[(HEIGHT-.23,HEIGHT-.17,.14),(HEIGHT-.17,HEIGHT-.09,.19),(HEIGHT-.09,HEIGHT,.23)]:span(g,'continuous_timber_ceiling_cornice','wooddark',a+normal*.04,b+normal*.04,z0,z1,depth)
  for aa,bb in zip(L['outlinePixels'],L['outlinePixels'][1:]+L['outlinePixels'][:1]):
   a,b=point(aa),point(bb);d=b-a;events=[(0.,1.,'wall')]
   for u,v,kind in[(point(q['a']),point(q['b']),'door')for q in L['doors']]+[(point(w['a']),point(w['b']),'window')for w in L['windows']]:
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
    elif kind=='door':span(g,'real_door_lintel_walls','wood',p,q,2.24,HEIGHT,.16)
    else:span(g,'window_sill_wall','wood',p,q,0,.94,.16);span(g,'window_upper_wall','wood',p,q,2.65,HEIGHT,.16)
    if kind!='door':span(g,'timber_perimeter_skirting','wooddark',p,q,0,.10,.045)
  for window in L['windows']:
   a,b=point(window['a']),point(window['b']);u=(b-a).normalized();normal=roomward(a,b)
   for p in[a,b]:span(g,'window_white_jamb_frames','whiteframe',p-u*.025,p+u*.025,.94,2.68,.15)
   for z in[.94,2.62]:span(g,'window_white_horizontal_rails','whiteframe',a,b,z,z+.045,.14)
   for t in[.25,.50,.75]:
    p=a.lerp(b,t);span(g,'window_white_mullions','whiteframe',p-u*.018,p+u*.018,.985,2.65,.11)
   span(g,'window_closed_glass','glassroom',a,b,.985,2.62,.015);span(g,'deep_timber_window_sill','woodlight',a+normal*.07,b+normal*.07,.90,.945,.29)
   span(g,'window_roller_blind_cassette','whiteframe',a+normal*.04,b+normal*.04,2.66,2.73,.11);span(g,'partial_pale_roller_blind','blind',a+normal*.045,b+normal*.045,2.40,2.64,.014)
  doorRecords=[]
  for door in L['doors']:
   a,b=point(door['a']),point(door['b']);u=(b-a).normalized();normal=roomward(a,b)
   for p in[a,b]:span(g,'timber_doorcase_jambs','wooddark',p-u*.025+normal*.055,p+u*.025+normal*.055,0,2.30,.15)
   span(g,'timber_doorcase_headers','wooddark',a+normal*.055,b+normal*.055,2.24,2.33,.18)
   hinge,tip=point(door['hinge']),point(door['openTip']);tip=hinge+(tip-hinge).normalized()*((b-a).length-.03);span(g,'source_swing_open_door_leaves','woodlight',hinge,tip,.02,2.235,.045);h=hinge.lerp(tip,.84);g.tube('door_metal_handles','metal',(*h,1.02),(*h,1.15),.013);doorRecords.append(dict(id=door['id'],a=list(a),b=list(b),normal=list(normal),clearWidth=(b-a).length-.05))
  # Photo establishes the display and white wall unit to the left of the end
  # window. Their exact plan position is not given and remains an estimate.
  a,b=point([397,117]),point([449,117]);span(g,'display_black_frame','black',a,b,1.47,2.48,.095);span(g,'blank_teaching_display','screen',a+Vector((0,-.055)),b+Vector((0,-.055)),1.51,2.44,.018)
  a,b=point([409,119]),point([446,119]);span(g,'white_wall_mounted_equipment','whiteframe',a,b,.98,1.42,.17)
  g.prism('single_curved_warm_wood_conference_tabletop','tablewood',L['tableOutline'],.74,.045)
  supports=[]
  for px in[[265,220],[370,220]]:
   p=point(px);g.box('table_pedestal_floor_bases','wooddark',(*p,.035),(.55,.66,.07));g.box('estimated_table_pedestal_supports','wooddark',(*p,.3975),(.32,.42,.665));g.box('table_underframe_bearers','wooddark',(*p,.735),(.60,.76,.03));supports.append(dict(foot=[*p,0],top=[*p,.75]))
  # Two narrow cable-access caps are visible on the wooden top; precise spacing
  # and mechanism remain estimated, without adding a third source seat or desk.
  for px in[[282,220],[350,220]]:
   p=point(px);g.box('two_table_cable_access_covers','woodlight',(*p,.788),(.30,.21,.006));g.box('two_table_cable_pull_slots','black',(p.x+.125,p.y,.793),(.009,.075,.003))
  seats=[chair(g,s)for s in L['seats']]
  g.prism('continuous_complete_ceiling','plaster',L['outline'],HEIGHT,.10)
  objects=g.finish()
  for o in objects:o['roomCode']='CON.7.04';o['spaceId']='con-704';o['destinationCollection']=COLLECTION;o['scope']='Independent historical8seat conference room;source plan centres fixed;estimated dimensions;no2026survey'
  return scene,col,objects,dict(seats=seats,tableSupports=supports,doors=doorRecords),g.solid_proof
 def tree(objects):
  from mathutils.bvhtree import BVHTree
  vs=[];fs=[];owners=[]
  for obj in objects:
   if obj.type!='MESH':continue
   obj.data.calc_loop_triangles();offset=len(vs);vs.extend(obj.matrix_world@v.co for v in obj.data.vertices);fs.extend(tuple(offset+i for i in f.vertices)for f in obj.data.loop_triangles);owners.extend([obj.name]*len(obj.data.loop_triangles))
  return BVHTree.FromPolygons(vs,fs),owners
 def inside(x,y):
  result=False
  for a,b in zip(L['outline'],L['outline'][1:]+L['outline'][:1]):
   dx,dy=b[0]-a[0],b[1]-a[1];t=max(0,min(1,((x-a[0])*dx+(y-a[1])*dy)/(dx*dx+dy*dy)))
   if math.hypot(x-a[0]-t*dx,y-a[1]-t*dy)<1e-5:return False
   if(a[1]>y)!=(b[1]>y)and x<(b[0]-a[0])*(y-a[1])/(b[1]-a[1])+a[0]:result=not result
  return result
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
   assert all(node(seat['approachPixel'])in visited for seat in nav['seatApproaches'])
   for candidate in nav['failedCandidates']:
    pa,pb=candidate['candidate'];a,b=point(pa),point(pb);d=(b-a).normalized();n=Vector((-d.y,d.x));length=(b-a).length;hits=[]
    for owner,poly in surfaces:
     q=[Vector(((p.xy-a).dot(d),(p.xy-a).dot(n)))for p in poly]
     if max(p.x for p in q)<=0 or min(p.x for p in q)>=length or max(p.y for p in q)<=-.22 or min(p.y for p in q)>=.22:continue
     for f in [lambda p:p.x,lambda p:length-p.x,lambda p:p.y+.22,lambda p:.22-p.y]:q=clip(q,f,lambda v:v>=0)
     if q:hits.append(dict(owner=owner,clippedTriangle=[[float(v)for v in p]for p in q]))
    assert hits,('FailedShortcutNotReproduced',candidate)
    failedProofs.append(dict(sourceEndpoints=[pa,pb],width=.44,verticalRange=[.04,2.1],passed=False,intersections=len(hits),owners=sorted(set(v['owner']for v in hits)),clippedTriangleEvidence=hits))
  return dict(method='Every saved world triangle clipped to0.04–2.10m body height,complete0.44m wide rectangular sweeps,and conservative32plane0.22m radius cylinders at all endpoints andturns;thin horizontal andslanted surfaces included',eligibleTriangles=len(surfaces),routes=routes,turnVolumes=turns,totalIntersections=0,entryDisplayAllEightSeatsGraphConnected=True if(DATA/'navigation-routes.json').exists()else None,failedShortcutSavedTriangleProofs=failedProofs)
 def export_surfaces(objects,component):
  def clip(poly,value):
   if not poly:return[]
   result=[];previous=poly[-1];pv=value(previous);pin=pv>=0
   for current in poly:
    cv=value(current);cin=cv>=0
    if cin!=pin:result.append(previous+(current-previous)*(pv/(pv-cv)))
    if cin:result.append(current)
    previous,pv,pin=current,cv,cin
   return result
  surfaces=[]
  for obj in objects:
   if obj.type!='MESH':continue
   obj.data.calc_loop_triangles()
   for triangle in obj.data.loop_triangles:
    poly=[obj.matrix_world@obj.data.vertices[i].co for i in triangle.vertices];poly=clip(poly,lambda p:p.z-.04);poly=clip(poly,lambda p:2.10-p.z)
    if poly:surfaces.append(dict(owner=obj.name,triangle=triangle.index,polygon=[[p.x,p.y]for p in poly]))
  write(DATA/'navigation-surfaces.json',dict(componentSha256=sha(component),height=[.04,2.10],surfaces=surfaces,zeroAreaVerticalProjectionsRetained=True))
 def checks(objects,records):
  floor,_=tree([o for o in objects if any(k in o.name for k in['complete_plan_floor','patterned_carpet_tiles','main_door_threshold_floor'])]);ceiling,_=tree([o for o in objects if o.name==PREFIX+'continuous_complete_ceiling']);tops,_=tree([o for o in objects if o.name==PREFIX+'single_curved_warm_wood_conference_tabletop']);wall,_=tree([o for o in objects if any(k in o.name for k in['perimeter_walls','sill_wall','upper_wall','door_lintel'])]);solid,names=tree([o for o in objects if not any(k in o.name for k in['complete_plan_floor','patterned_carpet_tiles','main_door_threshold_floor','ceiling'])])
  feet=[];supports=[]
  assert len(records['seats'])==8
  for seat,source in zip(records['seats'],L['seats']):
   assert seat['sourcePixel']==source['pixel']and math.dist(seat['centre'],source['centre'])<1e-6
   for p in seat['feet']:
    hit=floor.ray_cast(Vector((p[0],p[1],.04)),Vector((0,0,-1)),.08);assert hit[0]is not None and abs(hit[0].z)<1e-4,('UnsupportedChair',p);feet.append([*p,hit[0].z])
  for support in records['tableSupports']:
   p=support['foot'];hit=floor.ray_cast(Vector((p[0],p[1],.04)),Vector((0,0,-1)),.08);assert hit[0]is not None and abs(hit[0].z)<1e-4
   hit=tops.ray_cast(Vector((p[0],p[1],.70)),Vector((0,0,1)),.10);assert hit[0]is not None and abs(hit[0].z-.74)<1e-4;supports.append(dict(foot=support['foot'],tableUnderside=hit[0].z,supportTop=support['top'][2]))
  coverage=[];step=.18;xs=[p[0]for p in L['outline']];ys=[p[1]for p in L['outline']]
  for i in range(math.floor(min(xs)/step),math.ceil(max(xs)/step)):
   for j in range(math.floor(min(ys)/step),math.ceil(max(ys)/step)):
    x,y=(i+.5)*step,(j+.5)*step
    if not inside(x,y):continue
    hit=ceiling.ray_cast(Vector((x,y,1.5)),Vector((0,0,1)),2);assert hit[0]is not None and abs(hit[0].z-HEIGHT)<1e-4,('CeilingCoverageMiss',x,y,list(hit[0])if hit[0]is not None else None);coverage.append([x,y,hit[0].z])
  doorProbes=[]
  for door in records['doors']:
   a,b=Vector(door['a']),Vector(door['b']);u=(b-a).normalized();normal=Vector(door['normal']);c=(a+b)/2
   for offset in[-.22,0,.22]:
    p=c+u*offset-normal*.18
    for z in[.04,.65,1.2,2.1]:
     hit=solid.ray_cast(Vector((*p,z)),Vector((*normal,0)),.36);assert hit[0]is None,('DoorBlocked',door['id'],z,names[hit[2]]if hit[2]is not None else'');doorProbes.append([door['id'],offset,z])
  windowProbes=[]
  for window in L['windows']:
   a,b=point(window['a']),point(window['b']);u=(b-a).normalized();n=Vector((-u.y,u.x))
   for t in[.2,.5,.8]:
    c=a.lerp(b,t)
    for z in[1.1,1.7,2.5]:
     hit=wall.ray_cast(Vector((c.x-n.x*.2,c.y-n.y*.2,z)),Vector((*n,0)),.4);assert hit[0]is None,('UncutWindow',t,z);windowProbes.append([t,z])
  return dict(seatCount=8,sourceSeatCentresUnchanged=True,studentTeacherDistinction='Conference room8attendees;no added teacher chair',chairFootSupportProbes=feet,tableSupportContacts=supports,continuousCeilingCoverage=dict(probeCount=len(coverage),spacingMetres=step,missCount=0,undersideHeight=HEIGHT,pointDigest=hashlib.sha256(json.dumps(coverage).encode()).hexdigest()),realDoorClearRays=doorProbes,doorClearWidths={d['id']:d['clearWidth']for d in records['doors']},realWindowWallApertureRays=windowProbes,allAuthoredComponentsClosed=True)
 def render(scene):
  bpy.context.window.scene=scene;world=bpy.data.worlds.new(PREFIX+'previewWorld');world.use_nodes=True;world.node_tree.nodes['Background'].inputs[0].default_value=(.78,.80,.81,1);world.node_tree.nodes['Background'].inputs[1].default_value=.25;scene.world=world
  lamps=[]
  for i,px in enumerate([[195,153],[355,150],[250,292],[420,290]]):
   p=point(px);ld=bpy.data.lights.new(PREFIX+'previewArea'+str(i),'AREA');ld.energy=100;ld.shape='DISK';ld.size=2;lamp=bpy.data.objects.new(ld.name,ld);scene.collection.objects.link(lamp);lamp.location=(*p,HEIGHT-.18);lamps.append((lamp,ld))
  # A window-facing area light simulates daylight without source photo pixels.
  p=point([477,218]);ld=bpy.data.lights.new(PREFIX+'previewDaylight','AREA');ld.energy=180;ld.shape='RECTANGLE';ld.size=2.5;ld.size_y=1.5;lamp=bpy.data.objects.new(ld.name,ld);scene.collection.objects.link(lamp);lamp.location=(*p,1.95);target=Vector((*point([300,220]),1.2));lamp.rotation_euler=(target-lamp.location).to_track_quat('-Z','Y').to_euler();lamps.append((lamp,ld))
  cd=bpy.data.cameras.new(PREFIX+'previewCamera');camera=bpy.data.objects.new(cd.name,cd);scene.collection.objects.link(camera);scene.camera=camera;cd.lens=19;cd.clip_end=100
  scene.render.engine='BLENDER_EEVEE';scene.eevee.taa_render_samples=24;scene.render.resolution_x=1100;scene.render.resolution_y=800;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='AgX';views=[];cameraChecks=[];savedTree,savedOwners=tree([o for o in scene.objects if o.type=='MESH'])
  for name,pp,tp,z,tz,label in [('window',[153,278],[440,200],1.67,1.45,'CON.7.04会议桌与端窗'),('panels',[438,273],[190,195],1.70,1.45,'CON.7.04木饰面与8席会议桌')]:
   p,t=point(pp),point(tp);camera.location=(*p,z);assert inside(p.x,p.y);eyeProbes=[]
   for direction in[(1,0,0),(-1,0,0),(0,1,0),(0,-1,0),(0,0,1),(0,0,-1)]:
    hit=savedTree.ray_cast(camera.location,Vector(direction),.20);assert hit[0]is None,('CameraNearSavedSurface',name,direction,savedOwners[hit[2]]if hit[2]is not None else'');eyeProbes.append(dict(direction=direction,nearHit=None))
   cameraChecks.append(dict(view=name,sourcePixel=pp,eyeHeight=z,insideSourcePlan=True,actualSavedTriangleNearEyeProbes=eyeProbes,probeDistanceMetres=.20))
   camera.rotation_euler=(Vector((*t,tz))-camera.location).to_track_quat('-Z','Y').to_euler();scene.render.filepath=str(OUT/('built-'+name+'.png'));bpy.ops.render.render(write_still=True);views.append(dict(name='con-704-'+name+'-interior',code='CON',spaceId='con-704',label=label,view=dict(position=[p.x,z,-p.y],target=[t.x,tz,-t.y],fov=86)))
  bpy.data.objects.remove(camera,do_unlink=True);bpy.data.cameras.remove(cd)
  for obj,data in lamps:bpy.data.objects.remove(obj,do_unlink=True);bpy.data.lights.remove(data)
  bpy.data.worlds.remove(world);scene.world=None;return views,cameraChecks
 def run():
  assert sha(BASE)==SHA;bpy.ops.wm.open_mainfile(filepath=str(BASE));update();before=state();assert len(before['objects'])==8283 and len(before['materials'])==2220;assert len(before['rooms'])==31 and len(set().union(*(set(v)for v in before['rooms'].values())))==1273
  scene,col,objects,records,solid=build();update();proof=checks(objects,records);verify_original(before)
  scope='依据LSE同房号历史平面与照片建立CON.7.04独立8人会议室。固定平面8椅位置，保留左侧入口、上下外开门、右端斜窗、木饰面、弧边木桌、黑色扶手会议椅和连续完整天花；比例、竖向尺寸、设备精确位置及来源同期性未核实。'
  space=dict(code='CON',id='con-704',label='CON.7.04木饰面会议室',collection=COLLECTION,gallery='con-704-window-interior',scope=scope,interiorStudy=dict(kind='room-sample',label='CON.7.04木饰面会议室',scope=scope));col['authoringRecord']=json.dumps(space,ensure_ascii=False)
  fingerprints={o.name:object_fingerprint(o)for o in objects};bindings={o.name:[m.name for m in o.data.materials]for o in objects};props={o.name:repr(sorted(o.items()))for o in objects};component=OUT/'component.blend';bpy.data.libraries.write(str(component),{scene},fake_user=True,compress=True)
  # Reopen the full accepted campus and append only the independent collection.
  bpy.ops.wm.open_mainfile(filepath=str(BASE));update();assert state()==before
  with bpy.data.libraries.load(str(component),link=False)as(src,dst):dst.collections=[COLLECTION]
  saved=dst.collections[0];newscene=bpy.data.scenes.new(SCENE);newscene.collection.children.link(saved);update();verify_original(before);assert checks(list(saved.all_objects),records)==proof
  assert all(object_fingerprint(bpy.data.objects[n])==v for n,v in fingerprints.items());assert all(repr(sorted(bpy.data.objects[n].items()))==v for n,v in props.items());assert not any(n in bpy.data.scenes['00_CAMPUS_COMPLETE'].objects for n in fingerprints)
  bpy.ops.wm.open_mainfile(filepath=str(component));update();assert{o.name:object_fingerprint(o)for o in bpy.data.objects}==fingerprints;assert checks(list(bpy.data.objects),records)==proof;assert all(o.users_collection[0].name==COLLECTION and len(o.users_collection)==1 for o in bpy.data.objects);assert not any(o.type in{'LIGHT','CAMERA'}for o in bpy.data.objects)
  export_surfaces(list(bpy.data.objects),component)
  verification=dict(savedComponentReopened=True,appendedToIndependentSceneReopened=True,independentAcceptedObjectsVerified=len(before['objects']),allOriginalMaterialNodesVerified=len(before['materials']),allOriginalModifierStacksVerified=len(before['modifiers']),oldSpacesPreserved=len(before['rooms']),oldSpaceUniqueObjectsPreserved=1273,allOriginalGeometryUVTransformsBindingsNodesModifiersPropsOwnersAndVisibilityPreserved=True,allOriginalSceneMembershipsPreserved=True,noNewRoomObjectInCampus=True,sourceNativeShaUnchanged=sha(BASE)==SHA,sourcePhotoNotUsedAsTexture=True,previewLightsAndCamerasExcluded=True,newObjectsOwnedOnlyByIndependentCollection=True,triangles=sum(len(p.vertices)-2 for o in bpy.data.objects for p in o.data.polygons),routeProofComplete=False)
  audit=dict(version=231,building='CON',room='CON.7.04',baselinePath=str(BASE.relative_to(ROOT)),baselineSha256=SHA,componentPath=str(component.relative_to(ROOT)),componentSha256=sha(component),targetCollection=COLLECTION,destinationCollection=COLLECTION,collectionSpec=dict(kind='independent-room',name=COLLECTION,scene=SCENE),space=space,report=dict(space=space),addedObjects=list(fingerprints),archivedObjects=[],archive=[],changedObjects=[],addedFingerprints=fingerprints,replacementMaterialBindings=bindings,sourceManifest=str((DATA/'sources.json').relative_to(ROOT)),planLayout=str((DATA/'layout.json').relative_to(ROOT)),seatCount=8,teacherSeatCount=0,scaleMetresPerPixel=SCALE,roomAreaSquareMetres=L['roomAreaSquareMetres'],estimatedCeilingHeight=HEIGHT,gallerySuggestions=[],checks=proof,records=records,solidProof=solid,verification=verification,previews=[],beforeEvidence=[PLAN,PHOTO],limitations=json.loads((DATA/'sources.json').read_text())['limitations'])
  write(OUT/'audit.json',audit);print('CON704_ROOM231_GEOMETRY_READY',len(fingerprints),verification,flush=True);bpy.ops.wm.quit_blender()
 def finalize():
  global L
  L=json.loads((DATA/'layout.json').read_text());report=json.loads((OUT/'audit.json').read_text());navigation=json.loads((DATA/'navigation-routes.json').read_text());assert navigation['allEightSourceSeatsReachable'];component=OUT/'component.blend';assert sha(component)==report['componentSha256']==navigation['componentSha256'];proofs=[]
  for repeat in range(2):
   bpy.ops.wm.open_mainfile(filepath=str(component));update();assert{o.name:object_fingerprint(o)for o in bpy.data.objects}==report['addedFingerprints'];computed=checks(list(bpy.data.objects),report['records']);assert all(report['checks'][k]==v for k,v in computed.items());proofs.append(swept_route_surfaces(list(bpy.data.objects)))
  assert proofs[0]==proofs[1]and sha(BASE)==SHA
  scene=bpy.data.scenes[SCENE];views,cameraChecks=render(scene);assert{o.name:object_fingerprint(o)for o in bpy.data.objects}==report['addedFingerprints'];assert not any(o.type in{'LIGHT','CAMERA'}for o in bpy.data.objects)
  report['checks']['wholeRouteSavedMeshSweep']=proofs[0];report['checks']['eyeLevelInteriorCameras']=cameraChecks;report['checks']['continuousAllEightSeatApproaches']=navigation;report['gallerySuggestions']=views;report['space']['interiorView']=views[0]['view'];report['report']['space']=report['space'];report['verification'].update(routeProofComplete=True,completeRouteThinSurfaceSweepReopened=True,routeProofIndependentReopens=2,completeTurnAndEndVolumesReopened=True,allEightFixedSourceSeatsReachable=True,verticalTriangleProjectionsRetained=navigation['verticalTriangleProjectionsRetained']);report['previews']=['built-window.png','built-panels.png'];report['legacyReplacement']=dict(knownExistingRoom='CON.7.04',legacyCollection='CON_PUBLIC_INTERIOR_study',legacyComparison='result/blender/con704-room231/legacy-comparison.json',presentationRule='Replace legacy default CON.7.04 presentation;no duplicate room entry;preserve every original forparent integration archive',previousRealWorkAcknowledged='8seat conference table,timber panel walls andshort endwindow already existed;version160had already corrected window orientation',actualNewWork='Source pixel seat/perimeter registration,three door apertures,continuous ceiling,inside eye-level views,andfull-height saved triangle route proof');write(OUT/'audit.json',report);write(OUT/'verification.json',report['verification']);assert sha(BASE)==SHA and sha(component)==report['componentSha256'];print('CON704_ROOM231_READY',len(report['addedObjects']),len(proofs[0]['routes']),len(proofs[0]['turnVolumes']),report['verification'],flush=True);bpy.ops.wm.quit_blender()
 if __name__=='__main__':run()
