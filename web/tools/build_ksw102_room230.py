"""KSW.1.02 historical source-paired independent room, fixed configuration.
Run prepare() in the existing MachineLearning environment, then run() in Blender.
No command-line interface, source textures, campus registration or source edits.
"""
from pathlib import Path
import hashlib,json,math,sys
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'result/blender/ksw102-room230';DATA=ROOT/'data/collections/ksw102-room230'
BASE=ROOT/'result/blender/LSE_campus_detailed_v229.blend'
SHA='2ec7b3a42776f870e99b2a63f83f0736b70a0f2400a145b477f3d80bf54baa18'
COLLECTION='KSW102_ROOM230_study';SCENE='ROOM230_KSW102';PREFIX='KSW102_R230_'
PLAN='data/collections/interiors/images/df9ade333c00_KSW.1.02.gif'
PHOTO='data/collections/interiors/images/db96f6d15221_KSW.1.02.jpg'
SCALE=.025;HEIGHT=2.95

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
def xy(p):return[(p[0]-300)*SCALE,(470-p[1])*SCALE]
def prepare():
 from shapely.geometry import Polygon,box
 from PIL import Image,ImageDraw
 DATA.mkdir(parents=True,exist_ok=True);OUT.mkdir(parents=True,exist_ok=True)
 outline=[[65,374],[187,374],[187,370],[438,370],[438,364],[482,364],[482,370],[498,370],[498,418],[541,418],[541,493],[552,493],[552,552],[340,552],[340,537],[312,537],[312,552],[70,552],[70,425],[65,425]]
 poly=Polygon([xy(p)for p in outline]);assert poly.is_valid
 seats=[]
 for group,ys in [('north',[465,469,470,466,471,466,465,470,467]),('south',[516,522,525,518,522,519,516,524,522])]:
  for i,(x,y)in enumerate(zip([100,140,187,232,277,321,365,409,451],ys)):
   seats.append(dict(id=group+str(i+1),group=group,pixel=[x,y],centre=xy([x,y]),target=xy([x-40,y])))
 windows=[dict(id='window'+str(i+1),a=[a,552],b=[b,552])for i,(a,b)in enumerate([(94,159),(166,217),(225,292),(346,409),(416,461),(469,536)])]
 tiles=[];grid=[];x0,y0,x1,y1=poly.bounds
 def parts(v):return[v]if v.geom_type=='Polygon'else[g for g in getattr(v,'geoms',[])if g.geom_type=='Polygon']
 for i in range(math.floor(x0/.5),math.ceil(x1/.5)):
  for j in range(math.floor(y0/.5),math.ceil(y1/.5)):
   q=poly.intersection(box(i*.5,j*.5,(i+1)*.5,(j+1)*.5))
   if not q.is_empty:tiles.extend(dict(outline=list(t.exterior.coords)[:-1],material='carpet'+str((i+2*j)%3))for t in parts(q)if t.area>1e-8)
 for axis,lo,hi in [(0,x0,x1),(1,y0,y1)]:
  for i in range(math.ceil(lo/.6),math.floor(hi/.6)+1):
   v=i*.6;q=poly.intersection(box(v-.004,y0-1,v+.004,y1+1)if axis==0 else box(x0-1,v-.004,x1+1,v+.004))
   if not q.is_empty:grid.extend(list(t.exterior.coords)[:-1]for t in parts(q)if t.area>1e-8)
 layout=dict(room='KSW.1.02',outlinePixels=outline,outline=[xy(p)for p in outline],roomAreaSquareMetres=poly.area,scaleMetresPerPixel=SCALE,scaleBasis='Estimated0.025m/pixel from44px entry about1.10m and43–47px chair pitch about1.08–1.18m; no printed measured dimensions',studentSeatCount=18,printedCapacity=18,seats=seats,pods=[dict(id=g)for g in ['north','south']],teacherSeatCount=1,door=dict(a=[438,364],b=[482,364],hinge=[482,364],openTip=[482,405]),windows=windows,carpetTiles=tiles,ceilingGridParts=grid,lights=[[180,420],[275,420],[380,420],[470,446]],principalRoutes=[[[460,365],[460,402]],[[460,402],[175,402]],[[175,402],[175,423]]])
 if (DATA/'navigation-routes.json').exists():
  navigation=json.loads((DATA/'navigation-routes.json').read_text())
  if navigation.get('allGroupsReachable'):layout['principalRoutes']=navigation['principalRoutes'];layout['navigationProof']='data/collections/ksw102-room230/navigation-routes.json'
 write(DATA/'layout.json',layout)
 refs=[r for r in json.loads((ROOT/'data/collections/interiors/sources.json').read_text())['sources']if r.get('local_path')in[PLAN,PHOTO]];assert len(refs)==2
 limits=['平面与照片创建日期未知；页面2022年刷新和2026年检索日期均非拍摄或测绘日期，不能证明同期或2026现况。','平面实际可数两排各9把带写字板椅，共18把，恰与印刷18一致；照片透视出现三列视觉叠置，不能证明同期排法，模型座位位置以平面为准。','比例0.025m/像素、层高2.95m、门高2.22m、窗台0.78m、窗顶2.65m、椅壳脚型及隐蔽构造估算。','周界保留后端上侧入口、右端凹凸和下侧小墙垛；下侧多线墙带解释为照片窗侧，六段开口分隔和竖向尺寸为估计。','照片支持绿色塑壳转椅、浅灰轮架、白色独立写字板、灰色拼块地毯、窗侧暖气、白板墙双屏、前端幕与AV台、红色教师椅及连续格栅吊顶；背后设备与精确数量不可完整复核。','照片未显示入口，开启门扇构造按历史平面摆位估算。红色教师椅为照片证据，平面没有独立教师椅符号。','源照片仅供私下核对，不作为纹理、不拷入导出资源；未确认开放复用授权。','独立20Kingsway房间样本，不作楼层或校园地理配准、当前核定容量、疏散或无障碍认证。','0.44m宽、0.04至2.10m高的实际网格扫掠连接入口、教学区及两排各一处座椅后侧接近点；保留失败捷径，不移动源椅位来制造通路。']
 write(DATA/'sources.json',dict(room='KSW.1.02',sources=refs,planSha256=sha(ROOT/PLAN),photoSha256=sha(ROOT/PHOTO),sameRoomPairVerified=True,pairBasis='Identical room identifier and historical page parent; chronological identity unverified',bothImagesActualNotPlaceholder=True,excludedPlaceholder='data/collections/interiors/images/38464fdbc2f8_KSW.1.02.GIF',sourceSeatCount=dict(north=9,south=9,total=18),limitations=limits))
 im=Image.open(ROOT/PLAN).convert('RGB');d=ImageDraw.Draw(im);d.line(outline+[outline[0]],fill=(190,30,30),width=2)
 for s in seats:
  x,y=s['pixel'];d.ellipse((x-3,y-3,x+3,y+3),fill=(30,50,200))
 im.save(DATA/'registered-plan.png');print('KSW102_LAYOUT_READY',poly.area,len(seats),flush=True)

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
 def pixel(p):return[p[0]/SCALE+300,470-p[1]/SCALE]
 start=xy([460,389]);teaching=xy([175,423]);entrance=path(start,teaching);assert entrance
 routes=[[[460,365],[460,389]]]+[[pixel(a),pixel(b)]for a,b in zip(entrance,entrance[1:])];groups=[]
 for pod in layout['pods']:
  candidates=[]
  for seat in [v for v in layout['seats']if v['group']==pod['id']]:
   c,t=seat['centre'],seat['target'];d=[c[0]-t[0],c[1]-t[1]];length=math.hypot(*d);approach=[c[0]+d[0]/length*.60,c[1]+d[1]/length*.60];points=path(teaching,approach)
   if points:candidates.append((sum(math.dist(a,b)for a,b in zip(points,points[1:])),seat,points,approach))
  assert candidates,('GroupNotReachable',pod['id'])
  length,seat,points,approach=min(candidates,key=lambda v:v[0]);segments=[[pixel(a),pixel(b)]for a,b in zip(points,points[1:])];routes.extend(segments);groups.append(dict(group=pod['id'],reachable=True,seatId=seat['id'],seatPixel=seat['pixel'],approachPoint=pixel(approach),distanceBehindChairCentre=.60,lengthFromTeachingPoint=length,continuousPathFromTeachingPoint=[pixel(p)for p in points]))
 failed=LineString([xy([175,492]),xy([435,492])]);nearest=min(zip(shapes,owners),key=lambda item:failed.distance(item[0]));distance=failed.distance(nearest[0]);near=nearest_points(failed,nearest[0])
 assert distance<.22,'Failed shortcut must actually intersect the full-width body'
 diagnosis=dict(candidate=[[175,492],[435,492]],passed=False,bodyWidth=.44,verticalRange=[.04,2.10],nearestSavedMesh=nearest[1],minimumCentrelineToObstruction=distance,maximumSymmetricBodyWidthAtThisCandidate=distance*2,closestSourcePixels=[pixel(list(p.coords)[0])for p in near],intersectedFamilies=sorted(set(owner for shape,owner in zip(shapes,owners)if failed.buffer(.22,cap_style=2).intersects(shape))),reason='Actual saved furniture surfaces intersect the complete body corridor. Candidate retained as a failed shortcut; source furniture remains unchanged.')
 proof=dict(componentSha256=source['componentSha256'],geometryFingerprints=json.loads((OUT/'audit.json').read_text())['addedFingerprints'],principalRoutes=routes,method='Actual saved world triangles clipped to0.04–2.10m,projected to floor. Planar obstacles inflated0.23m;0.10m grid Astar with every edge and simplified segment covered by free space. Final complete0.44m rectangular sweeps are verified in Blender twice.',startPixel=[460,365],teachingPoint=[175,423],bodyProbeWidth=.44,planningRadius=.23,groups=groups,failedCandidates=[diagnosis],allGroupsReachable=True,routeScope='Entrance to teaching point then continuous approaches behind one chair in each of two rows; geometric probe only,not code or accessibility approval')
 layout['principalRoutes']=routes;layout['navigationProof']='data/collections/ksw102-room230/navigation-routes.json';(DATA/'layout.json').write_text(json.dumps(layout,ensure_ascii=False,indent=2)+'\n');(DATA/'navigation-routes.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n');print('TWO_GROUP_PATHS_PREPARED',len(routes),[(v['group'],round(v['lengthFromTeachingPoint'],2))for v in groups],diagnosis)

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
  for s in bpy.data.scenes:
   for layer in s.view_layers:layer.update()
 def span(g,f,key,a,b,lo,hi,depth=.14):
  a,b=Vector(a),Vector(b);d=b-a;c=(a+b)/2;g.box(f,key,(*c,(lo+hi)/2),(d.length,depth,hi-lo),math.atan2(d.y,d.x))
 def chair(g,seat,teacher=False):
  p=Vector(seat['centre']);angle=-math.pi/2;c,s=math.cos(angle),math.sin(angle)
  def at(x,y,z):return(p.x+c*x-s*y,p.y+s*x+c*y,z)
  color='teacherred'if teacher else'green'
  # Continuous concave moulded shell with turned-up seat sides and rounded shoulder.
  profile=[(-.245,.46),(-.12,.445),(.10,.45),(.22,.50),(.265,.65),(.285,.82),(.30,.97)]
  vs=[]
  for skin in [0,1]:
   for j,(py,pz)in enumerate(profile):
    for i in range(7):
     t=(i/6-.5)*2;vs.append(at(t*.25,py+(.04*t*t if j>=3 else 0)+(skin*.022 if j>=3 else 0),pz+(.025*t*t if j<4 else -.055*t*t)-(skin*.022 if j<3 else 0)))
  count=49;faces=[]
  for skin in range(2):
   for j in range(6):
    for i in range(6):
     a=skin*count+j*7+i;f=(a,a+1,a+8,a+7);faces.append(f if skin==0 else tuple(reversed(f)))
  for j in range(6):
   for i in [0,6]:
    a=j*7+i;b=a+7;f=(a,b,b+count,a+count);faces.append(f if i==0 else tuple(reversed(f)))
  for j in [0,6]:
   for i in range(6):
    a=j*7+i;f=(a,a+1,a+1+count,a+count);faces.append(tuple(reversed(f))if j==0 else f)
  g.add('red_teacher_moulded_shell'if teacher else'green_student_moulded_shells',color,vs,faces)
  g.tube('chair_swivel_columns','steel',at(0,0,.12),at(0,0,.45),.041)
  feet=[]
  for i in range(5):
   a=i*math.tau/5;x,y=.29*math.cos(a),.29*math.sin(a)
   g.tube('chair_star_base_arms','lightgrey',at(0,0,.14),at(x,y,.075),.027)
   foot=at(x,y,0);g.tube('chair_floor_contact_castors','dark',foot,at(x,y,.058),.027);feet.append(list(foot))
  tablet=[]
  if not teacher:
   # Integrated writing tablet belongs to each chair, never a group table.
   g.tube('tablet_support_posts','lightgrey',at(-.22,.08,.16),at(-.34,.08,.715),.023)
   g.tube('tablet_support_arms','lightgrey',at(-.34,.08,.715),at(-.20,-.18,.715),.021)
   g.box('eighteen_individual_white_writing_tablets','white',at(-.20,-.18,.745),(.64,.36,.04),angle);tablet=[*at(-.25,-.18,.725)]
  return dict(feet=feet,tabletContact=tablet,teacher=teacher)
 def build():
  scene=bpy.data.scenes.new(SCENE);col=bpy.data.collections.new(COLLECTION);scene.collection.children.link(col);col['roomSample']=True;col['roomCode']='KSW.1.02';g=RoomGeometry(col,PREFIX)
  for key,c in [('green',(.27,.40,.025)),('teacherred',(.70,.014,.028)),('lightgrey',(.59,.62,.60)),('plaster',(.82,.82,.77)),('frontpale',(.56,.57,.32)),('white',(.87,.87,.83)),('carpet0',(.12,.13,.13)),('carpet1',(.23,.24,.23)),('carpet2',(.30,.31,.29)),('ceiling',(.81,.81,.76)),('joint',(.50,.52,.49)),('glassroom',(.30,.38,.40)),('cabinet',(.49,.52,.50)),('screen',(.007,.010,.012)),('wood',(.36,.29,.20))]:
   m=bpy.data.materials.new(PREFIX+key);m.use_nodes=True;m.diffuse_color=(*c,1);m.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=m.diffuse_color;m.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value=.65;g.materials[key]=m
  g.prism('complete_plan_floor','carpet0',L['outline'],-.14,.137)
  for t in L['carpetTiles']:g.prism('patterned_carpet_tiles',t['material'],t['outline'],-.003,.003)
  da,db=point(L['door']['a']),point(L['door']['b'])
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
    if kind=='wall':span(g,'complete_perimeter_walls','frontpale'if aa[0]<75 and bb[0]<75 else'plaster',p,q,0,HEIGHT,.16)
    elif kind=='door':span(g,'real_door_lintel_wall','plaster',p,q,2.22,HEIGHT,.16)
    else:span(g,'window_sill_wall','plaster',p,q,0,.78,.16);span(g,'window_upper_wall','plaster',p,q,2.65,HEIGHT,.16)
    if kind!='door':span(g,'perimeter_skirting','white',p,q,0,.10,.045)
  for w in L['windows']:
   a,b=point(w['a']),point(w['b']);u=(b-a).normalized()
   for p in [a,b]:span(g,'window_jamb_frames','white',p-u*.023,p+u*.023,.78,2.66,.14)
   for z in [.78,1.48,2.62]:span(g,'window_horizontal_frames','white',a,b,z,z+.035,.12)
   span(g,'window_glass','glassroom',a,b,.82,2.62,.012);span(g,'window_sills','white',a+Vector((0,.08)),b+Vector((0,.08)),.75,.79,.26)
   span(g,'window_roller_blind_cassettes','white',a+Vector((0,.08)),b+Vector((0,.08)),2.63,2.72,.11)
   span(g,'window_partial_roller_blinds','white',a+Vector((0,.065)),b+Vector((0,.065)),2.25,2.62,.014)
   span(g,'window_side_radiators','white',a+Vector((0,.14)),b+Vector((0,.14)),.17,.66,.14)
  du=(db-da).normalized()
  for p in [da,db]:span(g,'door_jamb_frames','white',p-du*.025,p+du*.025,0,2.25,.18)
  span(g,'door_header_frame','white',da,db,2.22,2.27,.18);hinge,tip=point(L['door']['hinge']),point(L['door']['openTip']);span(g,'open_inward_door_leaf','wood',hinge,tip,.025,2.21,.045)
  a,b=point([69,387]),point([69,449]);span(g,'front_projection_screen_case','dark',a,b,2.50,2.62,.12);span(g,'front_white_projection_screen','white',a+Vector((.10,0)),b+Vector((.10,0)),.79,2.50,.018)
  for a,b in [([197,375],[310,375]),([329,375],[435,375])]:span(g,'long_white_teaching_boards','white',point(a),point(b),.78,2.45,.035)
  for px in [202,386]:
   p=point([px,374]);g.box('two_wall_display_frames','dark',(p.x,p.y-.075,1.76),(1.24,.09,.76));g.box('two_wall_display_screens','screen',(p.x,p.y-.124,1.76),(1.15,.018,.66))
  tc=point([141,406]);g.box('AV_lectern_floor_plinth','cabinet',(*tc,.045),(.91,.54,.09));g.box('AV_lectern_cabinet','cabinet',(*tc,.51),(.88,.51,.94));g.box('AV_lectern_worktop','lightgrey',(*tc,1.01),(1.06,.67,.055));g.box('AV_monitor_base','dark',(tc.x,tc.y,1.055),(.29,.24,.035));g.tube('AV_monitor_stand','steel',(tc.x,tc.y,1.05),(tc.x,tc.y,1.28),.021);g.box('AV_monitor_screen','screen',(tc.x,tc.y,1.41),(.065,.48,.29));g.box('AV_keyboard','dark',(tc.x-.24,tc.y,1.06),(.14,.43,.027))
  seats=[chair(g,s)for s in L['seats']];seats.append(chair(g,dict(centre=xy([102,415])),True))
  g.prism('continuous_complete_ceiling','ceiling',L['outline'],HEIGHT,.10)
  for ring in L['ceilingGridParts']:g.prism('continuous_ceiling_panel_grid','joint',ring,HEIGHT-.004,.004)
  lights=[]
  for px in L['lights']:
   p=point(px);g.box('ceiling_light_housings','white',(*p,HEIGHT-.027),(.57,.57,.054));g.box('ceiling_light_diffusers','light',(*p,HEIGHT-.059),(.53,.53,.010));lights.append([*p,HEIGHT])
  for px in [[230,486],[425,486]]:
   p=point(px);g.tube('ceiling_round_vent_discs','lightgrey',(*p,HEIGHT-.018),(*p,HEIGHT+.006),.16)
  p=point([190,445]);g.tube('projector_ceiling_hanger','white',(*p,HEIGHT+.01),(*p,2.68),.024);g.box('ceiling_projector','white',(*p,2.61),(.37,.29,.14));g.tube('projector_lens','dark',(p.x-.18,p.y,2.61),(p.x-.23,p.y,2.61),.04)
  objects=g.finish()
  for o in objects:o['roomCode']='KSW.1.02';o['destinationCollection']=COLLECTION;o['scope']='Independent historical room;estimated dimensions;no geographic or2026 registration'
  return scene,col,objects,dict(seats=seats,lecternCentre=list(tc),lightSupports=lights,door=dict(a=list(da),b=list(db),clearWidth=(db-da).length-.05)),g.solid_proof
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
  # Circumscribed32-gon protects the full radius0.22m at turns and end points.
  caps=[]
  for px in sorted({tuple(p)for route in L['principalRoutes']for p in route}):
   centre=point(px);radius=.22/math.cos(math.pi/32)
   ring=[centre+Vector((math.cos(i*math.tau/32),math.sin(i*math.tau/32)))*radius for i in range(32)]
   for owner,poly in surfaces:
    q=[p.xy.copy()for p in poly]
    if max(p.x for p in q)<centre.x-radius or min(p.x for p in q)>centre.x+radius or max(p.y for p in q)<centre.y-radius or min(p.y for p in q)>centre.y+radius:continue
    for a,b in zip(ring,ring[1:]+ring[:1]):
     d=b-a;q=clip(q,lambda p: d.x*(p.y-a.y)-d.y*(p.x-a.x)-1e-7,lambda v:v>=0)
    assert not q,('ActualMeshInTurnOrEndVolume',px,owner)
   caps.append(dict(pixel=px,fullRadius=.22,circumscribedSides=32,height=[.04,2.10],intersections=0))
  return dict(method='All actual saved world triangles clipped to0.04–2.10m and complete0.44m rectangular corridors plus full-radius turning/end volumes; thin tabletops included',eligibleTriangles=len(surfaces),routes=routes,turnAndEndVolumes=caps,totalIntersections=0)
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
  print('KSW_NAVIGATION_SURFACES',len(surfaces),flush=True);bpy.ops.wm.quit_blender()
 def verify_navigation():
  report=json.loads((OUT/'audit.json').read_text());proofs=[]
  for repeat in range(2):
   bpy.ops.wm.open_mainfile(filepath=str(OUT/'component.blend'));update();assert{o.name:object_fingerprint(o)for o in bpy.data.objects}==report['addedFingerprints'];proofs.append(swept_route_surfaces(list(bpy.data.objects)))
  assert proofs[0]==proofs[1]and sha(BASE)==SHA
  report['checks']['wholeRouteSavedMeshSweep']=proofs[0];report['checks']['routeScope']='入口经上侧实际通路连接教学区及两排各一处椅后接近点；0.44m全高网格扫掠及转折末端体积，非规范认证'
  report['checks']['continuousSeatGroupReachability']=json.loads((DATA/'navigation-routes.json').read_text());report['verification']['completeRouteThinSurfaceSweepReopened']=True;report['verification']['routeProofIndependentReopens']=2;report['verification']['completeTurnAndEndVolumesReopened']=True
  (OUT/'audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print('KSW_TWO_GROUP_ROUTE_VERIFIED',len(proofs[0]['routes']),flush=True);bpy.ops.wm.quit_blender()
 def checks(objects,R):
  floor,_=tree([o for o in objects if any(k in o.name for k in ['complete_plan_floor','patterned_carpet_tiles'])]);ceiling,_=tree([o for o in objects if o.name==PREFIX+'continuous_complete_ceiling']);tops,_=tree([o for o in objects if o.name==PREFIX+'eighteen_individual_white_writing_tablets']);solid,names=tree([o for o in objects if not any(k in o.name for k in ['complete_plan_floor','patterned_carpet_tiles','ceiling'])])
  feet=[];tablets=[]
  for seat in R['seats']:
   for p in seat['feet']:
    h=floor.ray_cast(Vector((p[0],p[1],.04)),Vector((0,0,-1)),.08);assert h[0]is not None and abs(h[0].z)<.001,('UnsupportedChairFoot',p);feet.append(dict(point=p,floorZ=h[0].z))
   if seat['tabletContact']:
    p=seat['tabletContact'];h=tops.ray_cast(Vector((p[0],p[1],.70)),Vector((0,0,1)),.08);assert h[0]is not None and abs(h[0].z-.725)<.001;tablets.append(dict(supportTop=.736,tabletUnderside=h[0].z,contactPoint=p))
  p=R['lecternCentre'];h=floor.ray_cast(Vector((*p,.04)),Vector((0,0,-1)),.08);assert h[0]is not None and abs(h[0].z)<.001
  lecternContact=list(h[0]);coverage=[];step=.20;xs=[p[0]for p in L['outline']];ys=[p[1]for p in L['outline']]
  for i in range(math.floor(min(xs)/step),math.ceil(max(xs)/step)):
   for j in range(math.floor(min(ys)/step),math.ceil(max(ys)/step)):
    x,y=(i+.5)*step,(j+.5)*step
    if not inside(x,y):continue
    h=ceiling.ray_cast(Vector((x,y,1.5)),Vector((0,0,1)),2);assert h[0]is not None and abs(h[0].z-HEIGHT)<.001;coverage.append([x,y,h[0].z])
  lamp=[]
  for p in R['lightSupports']:
   h=ceiling.ray_cast(Vector((p[0],p[1],HEIGHT-.10)),Vector((0,0,1)),.15);assert h[0]is not None and abs(h[0].z-p[2])<.001;lamp.append([*p,h[0].z])
  doorway=[];a,b=Vector(R['door']['a']),Vector(R['door']['b']);c=(a+b)/2;u=(b-a).normalized()
  for d in [-.22,0,.22]:
   for z in [.04,.65,1.20,2.1]:
    p=c+u*d+Vector((0,-.25));h=solid.ray_cast(Vector((*p,z)),Vector((0,1,0)),.5);assert h[0]is None,('DoorBlocked',d,z,names[h[2]]if h[2]is not None else'');doorway.append([d,z])
  walltree,_=tree([o for o in objects if any(k in o.name for k in ['perimeter_walls','sill_wall','upper_wall','door_lintel'])]);windows=[]
  for w in L['windows']:
   a,b=point(w['a']),point(w['b']);u=(b-a).normalized();normal=Vector((-u.y,u.x))
   for t in [.2,.5,.8]:
    c=a.lerp(b,t)
    for z in [1.1,1.7,2.5]:
     h=walltree.ray_cast(Vector((c.x-normal.x*.25,c.y-normal.y*.25,z)),Vector((*normal,0)),.5);assert h[0]is None,('UncutWindow',w['id'],t,z);windows.append([w['id'],t,z])
  result=dict(studentSeatCount=18,seatingGroupCount=2,teacherSeatCount=1,writingTabletCount=18,studentFootCount=90,teacherFootCount=5,footSupportProbes=feet,writingTabletSupportContacts=tablets,lecternFloorContact=lecternContact,ceilingLightSupportContacts=lamp,continuousCeilingCoverage=dict(spacingMetres=step,probeCount=len(coverage),missCount=0,undersideHeight=HEIGHT,pointDigest=hashlib.sha256(json.dumps(coverage).encode()).hexdigest()),realDoorOpeningClearRays=doorway,doorClearWidth=R['door']['clearWidth'],realWindowWallApertureRays=windows,wholeRouteSavedMeshSweep=swept_route_surfaces(objects),allAuthoredComponentsClosed=True)
  return result
 def render(scene):
  bpy.context.window.scene=scene;world=bpy.data.worlds.new(PREFIX+'previewWorld');world.use_nodes=True;world.node_tree.nodes['Background'].inputs[0].default_value=(.76,.80,.84,1);world.node_tree.nodes['Background'].inputs[1].default_value=.30;scene.world=world
  lamps=[]
  for i,x in enumerate([-3,1,4]):
   ld=bpy.data.lights.new(PREFIX+'previewArea'+str(i),'AREA');ld.energy=260;ld.shape='DISK';ld.size=3;lamp=bpy.data.objects.new(ld.name,ld);scene.collection.objects.link(lamp);lamp.location=(x,.3,HEIGHT-.22);lamps.append((lamp,ld))
  cd=bpy.data.cameras.new(PREFIX+'previewCamera');camera=bpy.data.objects.new(cd.name,cd);scene.collection.objects.link(camera);scene.camera=camera;cd.lens=19;cd.clip_end=100
  scene.render.engine='BLENDER_EEVEE';scene.eevee.taa_render_samples=24;scene.render.resolution_x=1100;scene.render.resolution_y=750;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='AgX';views=[]
  for name,pp,tp,z,tz,label in [('teaching',[514,491],[110,427],1.66,1.40,'KSW.1.02绿色写字板椅与教学端'),('seating',[178,411],[460,503],1.68,1.32,'KSW.1.02两排写字板椅与侧窗')]:
   p,t=point(pp),point(tp);camera.location=(*p,z);camera.rotation_euler=(Vector((*t,tz))-camera.location).to_track_quat('-Z','Y').to_euler();scene.render.filepath=str(OUT/('built-'+name+'.png'));bpy.ops.render.render(write_still=True);views.append(dict(name='ksw-102-'+name+'-interior',code='KSW',spaceId='ksw-102',label=label,view=dict(position=[p.x,z,-p.y],target=[t.x,tz,-t.y],fov=86)))
  bpy.data.objects.remove(camera,do_unlink=True);bpy.data.cameras.remove(cd)
  for o,d in lamps:bpy.data.objects.remove(o,do_unlink=True);bpy.data.lights.remove(d)
  bpy.data.worlds.remove(world);scene.world=None;return views
 def run():
  assert sha(BASE)==SHA;bpy.ops.wm.open_mainfile(filepath=str(BASE));update();expected=accepted_fingerprints(ROOT/'result/blender/stage229',SHA);original={o.name:object_fingerprint(o)for o in bpy.data.objects};assert original==expected and len(original)==8179
  mats={m.name:material_fingerprint(m)for m in bpy.data.materials};mods={o.name:stable_modifiers(o)for o in bpy.data.objects};rooms=rooms_state();assert len(rooms)==29 and len(set(n for r in rooms for n in r['objects']))==1170;members={o.name:sorted(c.name for c in o.users_collection)for o in bpy.data.objects};vis={o.name:o.hide_render for o in bpy.data.objects};props={o.name:dict(o.items())for o in bpy.data.objects}
  scene,col,owned,records,solid=build();update();proof=checks(owned,records);views=render(scene)
  scope='依据LSE历史同房号平面与照片建立KSW.1.02独立教室。保留凹凸周界、后侧上端入口、下侧窗带、两排共18把带白色写字板的绿色学生椅、红色教师椅、AV台、双显示屏、白板、前端投影幕和连续完整天花。尺度、构造与源间同期性未知，不作地理配准或2026现况认证。'
  space=dict(code='KSW',id='ksw-102',label='KSW.1.02写字板椅教室',collection=COLLECTION,gallery=views[0]['name'],scope=scope,interiorView=views[0]['view'],interiorStudy=dict(kind='room-sample',label='KSW.1.02写字板椅教室',scope=scope));col['authoringRecord']=json.dumps(space,ensure_ascii=False)
  fingerprints={o.name:object_fingerprint(o)for o in owned};bindings={o.name:[m.name for m in o.data.materials]for o in owned};component=OUT/'component.blend';bpy.data.libraries.write(str(component),{col},fake_user=True,compress=True)
  bpy.ops.wm.open_mainfile(filepath=str(BASE));update();assert{o.name:object_fingerprint(o)for o in bpy.data.objects}==expected
  with bpy.data.libraries.load(str(component),link=False)as(src,dst):dst.collections=[COLLECTION]
  saved=dst.collections[0];scene=bpy.data.scenes.new(SCENE);scene.collection.children.link(saved);bpy.context.window.scene=scene;update();assert checks(list(saved.all_objects),records)==proof
  assert all(object_fingerprint(bpy.data.objects[n])==v for n,v in fingerprints.items());assert all(object_fingerprint(bpy.data.objects[n])==v for n,v in original.items());assert all(material_fingerprint(bpy.data.materials[n])==v for n,v in mats.items());assert all(stable_modifiers(bpy.data.objects[n])==v for n,v in mods.items());assert rooms_state()==rooms;assert all(sorted(c.name for c in bpy.data.objects[n].users_collection)==v for n,v in members.items());assert all(bpy.data.objects[n].hide_render==v for n,v in vis.items());assert all(dict(bpy.data.objects[n].items())==v for n,v in props.items());assert not any(n in bpy.data.scenes['00_CAMPUS_COMPLETE'].objects for n in fingerprints);assert sha(BASE)==SHA
  checkpath=OUT/'reopen-check.blend';bpy.data.libraries.write(str(checkpath),{saved},fake_user=True,compress=True);bpy.ops.wm.open_mainfile(filepath=str(checkpath));update();assert{o.name:object_fingerprint(o)for o in bpy.data.objects}==fingerprints;assert checks(list(bpy.data.objects),records)==proof;assert not any(o.type in {'LIGHT','CAMERA'}for o in bpy.data.objects);checkpath.unlink();assert sha(BASE)==SHA
  verification=dict(savedComponentReopened=True,secondSavedComponentReopened=True,independentAcceptedObjectsVerified=len(original),allOriginalMaterialNodesVerified=len(mats),allOriginalModifierStacksVerified=len(mods),oldSpacesPreserved=len(rooms),oldSpaceUniqueObjectsPreserved=1170,allOriginalMembershipsAndPropertiesUnchanged=True,allSourceGeometryUVTransformsBindingsUnchanged=True,allOriginalVisibilityUnchanged=True,noNewRoomObjectInCampus=True,sourceNativeShaUnchanged=True,sourcePhotoNotUsedAsTexture=True,previewLightsAndCamerasExcluded=True,triangles=sum(len(f.vertices)-2 for o in bpy.data.objects for f in o.data.polygons))
  audit=dict(version=230,building='KSW',baselinePath=str(BASE.relative_to(ROOT)),baselineSha256=SHA,componentPath=str(component.relative_to(ROOT)),componentSha256=sha(component),targetCollection=COLLECTION,destinationCollection=COLLECTION,collectionSpec=dict(kind='independent-room',name=COLLECTION,scene=SCENE),space=space,report=dict(space=space),addedObjects=list(fingerprints),archivedObjects=[],archive=[],changedObjects=[],addedFingerprints=fingerprints,replacementMaterialBindings=bindings,sourceManifest='data/collections/ksw102-room230/sources.json',planLayout='data/collections/ksw102-room230/layout.json',studentSeatCount=18,teacherSeatCount=1,writingTabletCount=18,scaleMetresPerPixel=SCALE,roomAreaSquareMetres=L['roomAreaSquareMetres'],estimatedCeilingHeight=HEIGHT,gallerySuggestions=views,checks=proof,solidProof=solid,verification=verification,previews=['built-teaching.png','built-seating.png'],beforeEvidence=[PLAN,PHOTO],limitations=json.loads((DATA/'sources.json').read_text())['limitations'])
  write(OUT/'audit.json',audit);print('KSW102_ROOM230_READY',len(fingerprints),verification,flush=True);bpy.ops.wm.quit_blender()
 if __name__=='__main__':run()
