"""CKK.1.10 independent historical U-table classroom, fixed editor configuration.

Reuses accepted CKK.1.10/CKK.1.15 geometry and saved full-height sweep methods.
Keep all18plan chair centres. Door display angle,dimensions and unseen finishes
remain estimates;no geographic floor registration or present-capacity claim.
"""
from pathlib import Path
import hashlib,json,math,sys
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'result/blender/ckk110-room234';DATA=ROOT/'data/collections/ckk110-room234'
BASE=ROOT/'result/blender/LSE_campus_detailed_v233.blend'
SHA='b1d01b4b74a7f9e33d9bab25e73f51f39361659b9236ca98c34056137d8b6660'
COLLECTION='CKK110_ROOM234_study';SCENE='ROOM234_CKK110';PREFIX='CKK110_R234_'
PLAN='data/collections/interiors/images/0300d0c1919b_CKK.1.10.GIF'
PHOTO='data/collections/interiors/images/4f031ab96f78_CKK.1.10.jpg'
SCALE=.015;HEIGHT=3.05

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
def prepare():
 from shapely.geometry import Polygon,box
 from PIL import Image,ImageDraw
 DATA.mkdir(parents=True,exist_ok=True);OUT.mkdir(parents=True,exist_ok=True)
 metadata=json.loads((ROOT/'web/tools/building-metadata.json').read_text());assert not any(r.get('id')=='ckk-110'or'CKK.1.10'in r.get('label','')for r in metadata['spaces'])
 assert not any('CKK.1.10'in str(b.get('interiorStudy',{}))for b in metadata['buildings'])
 write(DATA/'deduplication.json',dict(metadataSha256=sha(ROOT/'web/tools/building-metadata.json'),spacesChecked=len(metadata['spaces']),defaultBuildingStudiesChecked=len(metadata['buildings']),duplicateRoomFound=False))
 def p(q):return[(q[0]-270)*SCALE,(265-q[1])*SCALE]
 outline=[[29,35],[510,35],[510,117],[553,117],[553,177],[510,177],[510,313],[552,313],[552,409],[510,409],[510,499],[29,499]]
 polygon=Polygon([p(q)for q in outline]);assert polygon.is_valid
 students=[]
 for group,x,tx in [('left',99,130),('right',480,443)]:
  for i,y in enumerate([147,200,252,305,357,408]):students.append(dict(id=group+str(i+1),group=group,pixel=[x,y],target=[tx,y],colour='black'if(group,i)in{('left',0),('right',3)}else'red'))
 for i,x in enumerate([151,203,255,307,359,410]):students.append(dict(id='lower'+str(i+1),group='lower',pixel=[x,419],target=[x,389],colour='black'if i==2 else'red'))
 tables=[]
 for group,x0,x1 in [('left',113,143),('right',428,458)]:
  for i,(a,b)in enumerate([(126,220),(220,315),(315,409)]):tables.append(dict(id=group+str(i+1),a=[x0,a],b=[x1,b]))
 for i,(a,b)in enumerate([(143,238),(238,333),(333,428)]):tables.append(dict(id='lower'+str(i+1),a=[a,378],b=[b,409]))
 tiles=[];x0,y0,x1,y1=polygon.bounds
 for i in range(math.floor(x0/.5),math.ceil(x1/.5)):
  for j in range(math.floor(y0/.5),math.ceil(y1/.5)):
   q=polygon.intersection(box(i*.5,j*.5,(i+1)*.5,(j+1)*.5))
   if q.is_empty:continue
   parts=[q]if q.geom_type=='Polygon'else[g for g in q.geoms if g.geom_type=='Polygon'];tiles.extend(dict(outline=list(t.exterior.coords)[:-1],material='carpet'+str((i+2*j)%3))for t in parts if t.area>1e-8)
 ingress=[[29,398],[60,398]]
 routes=[dict(group='left',points=ingress+[[60,200]],approach=[60,200],seatIds=['left2']),dict(group='right',points=ingress+[[60,65],[480,65],[480,110]],approach=[480,110],seatIds=['right1']),dict(group='lower',points=ingress+[[65,430],[115,458],[115,465],[260,465]],approach=[260,465],seatIds=['lower3']),dict(group='teacher',points=ingress+[[60,65],[155,65],[155,101]],approach=[155,101],seatIds=['teacher'])]
 # Source controls the jambs and unequal leaves.135degree display is an estimate,
 # not a claim that the current door hardware permits that full opening angle.
 tip=[29+64/math.sqrt(2),431+64/math.sqrt(2)]
 layout=dict(room='CKK.1.10',outlinePixels=outline,outline=[p(q)for q in outline],scaleMetresPerPixel=SCALE,scaleBasis='Estimated0.015m/pixel from64px main door leaf about0.96m;no printed measured dimensions',roomAreaSquareMetres=polygon.area,carpetTiles=tiles,studentSeatCount=18,students=students,tables=tables,teacherDesk=dict(a=[143,126],b=[249,182]),teacherSeat=[195,101],door=dict(a=[29,337],b=[29,431],secondaryEnd=[29,367],hinge=[29,431],openTip=tip,displayAngleDegrees=135,displayStateEstimated=True),windows=[dict(id='frontRightBay',a=[553,117],b=[553,177]),dict(id='rearRightBay',a=[552,313],b=[552,409])],ceilingLights=[[150,90],[365,90],[150,245],[365,245],[150,450],[365,450]],projector=[330,220],routePaths=routes)
 write(DATA/'layout.json',layout)
 refs=[r for r in json.loads((ROOT/'data/collections/interiors/sources.json').read_text())['sources']if r.get('local_path')in[PLAN,PHOTO]];assert len(refs)==2
 assert all(r['source_type']in['historical_room_photo','historical_room_plan']for r in refs)
 assert all(sha(ROOT/r['local_path'])==r['sha256']for r in refs)
 limitations=['官方历史平面明确标注1.10，官方照片和平面文件同为CKK.1.10。实际目检均非占位图，18个学生椅位为左6、右6、后6，另有1教师椅。','平面创建、照片拍摄日期未知，归档及检索时间不能证明两图同期或2026现况；18为图中数椅，不是现用核定容量。','平面控制完整周界、两处右侧外凸窗湾、左侧不等双叶入口、U形工作台与教师桌椅；照片控制白桌、红黑椅、灰地毯、浅墙、投影白板、AV设备、矩形灯和连续带梁天花。','尺度0.015m每像素、层高3.05m、窗台窗顶、门高、细窗格、桌椅及隐藏构造均为估计。椅色分配为照片支持的混色估计，未冒充图中每一椅的精确颜色。','门洞与铰点按平面保留，主门扇约135度打开只为独立研究的展示状态估计，不证明当前门控可达该角度；图中90度弧线不作唯一运行状态。','保留18个来源椅位，不为通道移动桌椅。全高0.44m几何走廊只连接三组和教师席各一处接近点，不证明每个座位可达或无障碍疏散合规。','完整天花、下挂梁和所有灯具投影支承保留，未用去顶或拆墙掩饰拥挤；无照片纹理、虚构外窗景或校园楼层接入。','独立CKK.1.10历史教室样本，不作为完整CKK室内覆盖、实测空间或2026现状认证。']
 write(DATA/'sources.json',dict(room='CKK.1.10',sources=refs,planSha256=sha(ROOT/PLAN),photoSha256=sha(ROOT/PHOTO),sameRoomPairVerified=True,bothImagesActualNotPlaceholder=True,sourceSeatCount=dict(left=6,right=6,lower=6,totalStudents=18,teacher=1),limitations=limitations))
 im=Image.open(ROOT/PLAN).convert('RGB');d=ImageDraw.Draw(im);d.line(outline+[outline[0]],fill=(190,30,30),width=2)
 for s in students:
  x,y=s['pixel'];d.ellipse((x-3,y-3,x+3,y+3),fill=(30,50,200))
 im.save(DATA/'registered-plan.png');print('CKK110_LAYOUT_READY',polygon.area,len(students),flush=True)

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
 def point(p):return Vector(((p[0]-270)*SCALE,(265-p[1])*SCALE))
 def update():
  for s in bpy.data.scenes:
   for layer in s.view_layers:layer.update()
 def material(g,key,c,rough=.7,metal=0):
  m=bpy.data.materials.new(PREFIX+key);m.use_nodes=True;m.diffuse_color=(*c,1);n=m.node_tree.nodes['Principled BSDF'];n.inputs['Base Color'].default_value=m.diffuse_color;n.inputs['Roughness'].default_value=rough;n.inputs['Metallic'].default_value=metal;g.materials[key]=m
 def span(g,f,key,a,b,lo,hi,depth=.14):
  a,b=Vector(a),Vector(b);d=b-a;c=(a+b)/2;g.box(f,key,(*c,(lo+hi)/2),(d.length,depth,hi-lo),math.atan2(d.y,d.x))
 def chair(g,p,target,colour='red',teacher=False):
  p,t=Vector(p),Vector(target);angle=math.atan2(t.y-p.y,t.x-p.x)+math.pi/2;c,s=math.cos(angle),math.sin(angle)
  def at(x,y,z):return(p.x+c*x-s*y,p.y+s*x+c*y,z)
  height=.47 if teacher else .45
  g.box('teacher_black_seat'if teacher else'row_'+colour+'_seat','black'if teacher else colour,at(0,0,height),(.46,.43,.05),angle)
  if teacher:g.box('teacher_task_chair_back','black',at(0,.24,.76),(.51,.08,.53),angle)
  else:
   ring=[]
   for i in range(9):
    x=-.23+i*.46/8;ring.append(at(x,.232-.030*(x/.23)**2,0)[:2])
   for i in reversed(range(9)):
    x=-.23+i*.46/8;ring.append(at(x,.210-.030*(x/.23)**2,0)[:2])
   g.prism('row_'+colour+'_curved_backs',colour,ring,.48,.40)
  feet=[]
  if teacher:
   g.tube('teacher_chair_pedestal','steel',at(0,0,.12),at(0,0,.445),.028)
   for i in range(5):
    a=math.tau*i/5;x,y=.27*math.cos(a),.27*math.sin(a);foot=at(x,y,.03);g.tube('teacher_casters','black',at(x-.014,y,.03),at(x+.014,y,.03),.03);g.tube('teacher_chair_base','black',at(0,0,.13),at(x,y,.065),.022);feet.append(list(foot))
  else:
   for x in [-.19,.19]:
    for y in [-.19,.19]:
     p0=at(x*1.08,y*1.08,0);g.tube('chair_floor_feet','steel',p0,at(x*1.08,y*1.08,.06),.015);g.tube('chair_steel_legs','steel',at(x*1.08,y*1.08,.055),at(x,y,.425),.015);feet.append(list(p0))
   for x in [-.19,.19]:g.tube('chair_back_supports','steel',at(x,.15,.42),at(x,.21,.65),.011)
  return dict(centre=list(p),teacher=teacher,colour=colour,feet=feet)
 def build():
  scene=bpy.data.scenes.new(SCENE);col=bpy.data.collections.new(COLLECTION);scene.collection.children.link(col);col['roomSample']=True;col['roomCode']='CKK.1.10';g=RoomGeometry(col,PREFIX)
  for key,c,r,m in [('plaster',(.76,.76,.70),.87,0),('red',(.49,.025,.035),.64,0),('black',(.016,.020,.019),.74,0),('whiteworktop',(.81,.81,.75),.5,0),('steel',(.48,.50,.48),.33,.65),('dark',(.018,.023,.021),.62,0),('carpet0',(.15,.16,.16),.95,0),('carpet1',(.16,.17,.17),.95,0),('carpet2',(.17,.18,.18),.95,0),('ceiling',(.81,.81,.76),.90,0),('frame',(.80,.80,.75),.52,0),('glassroom',(.22,.27,.29),.19,0),('blindroom',(.77,.77,.72),.86,0),('doorwood',(.38,.29,.19),.73,0),('pinorange',(.60,.19,.025),.95,0),('pingrey',(.25,.27,.25),.95,0),('screenwhite',(.85,.85,.79),.5,0),('screenblack',(.009,.012,.012),.32,0),('avcabinet',(.43,.46,.43),.6,0)]:material(g,key,c,r,m)
  g.prism('complete_plan_floor','carpet0',L['outline'],-.14,.137)
  for tile in L['carpetTiles']:g.prism('checker_carpet_tiles',tile['material'],tile['outline'],-.003,.003)
  da,db=point(L['door']['a']),point(L['door']['b']);windows=[(point(w['a']),point(w['b']))for w in L['windows']]
  for a,b in zip(L['outline'],L['outline'][1:]+L['outline'][:1]):
   a,b=Vector(a),Vector(b);d=b-a;events=[(0.,1.,'wall')]
   for u,v,kind in [(da,db,'door')]+[(u,v,'window')for u,v in windows]:
    if abs(d.cross(u-a))>.0001 or abs(d.cross(v-a))>.0001:continue
    lo,hi=sorted(((u-a).dot(d)/d.length_squared,(v-a).dot(d)/d.length_squared))
    if lo<-.001 or hi>1.001:continue
    updated=[]
    for s,e,k in events:
     if k!='wall'or hi<=s or lo>=e:updated.append((s,e,k));continue
     if s<lo:updated.append((s,lo,'wall'))
     updated.append((max(s,lo),min(e,hi),kind))
     if hi<e:updated.append((hi,e,'wall'))
    events=updated
   for s,e,kind in events:
    if e-s<1e-7:continue
    p,q=a+d*s,a+d*e
    if kind!='door':span(g,'perimeter_skirting','frame',p,q,0,.10,.04)
    if kind=='wall':span(g,'complete_perimeter_walls','plaster',p,q,.10,HEIGHT)
    elif kind=='door':span(g,'true_door_lintel','plaster',p,q,2.24,HEIGHT)
    else:span(g,'high_window_lower_wall','plaster',p,q,.10,.88);span(g,'high_window_upper_wall','plaster',p,q,2.78,HEIGHT)
  for a,b in windows:
   u=(b-a).normalized();inward=Vector((-1,0))
   for p in [a,b]:span(g,'high_window_jamb_frames','frame',p-u*.027,p+u*.027,.88,2.81,.12)
   for z in [.90,2.0,2.76]:span(g,'high_window_horizontal_frames','frame',a,b,z,z+.035,.10)
   p=(a+b)/2;span(g,'high_window_mullions','frame',p-u*.022,p+u*.022,.935,2.76,.08)
   span(g,'high_window_glass','glassroom',a,b,.935,2.76,.016);span(g,'deep_high_window_sills','frame',a+inward*.10,b+inward*.10,.85,.90,.36)
  u=(db-da).normalized()
  for p in [da,db]:span(g,'door_jamb_frames','doorwood',p-u*.025,p+u*.025,0,2.27,.17)
  span(g,'door_header_frame','doorwood',da,db,2.22,2.27,.17);secondary=point(L['door']['secondaryEnd']);span(g,'closed_secondary_door_leaf','doorwood',da,secondary,.025,2.22,.043);hinge,tip=point(L['door']['hinge']),point(L['door']['openTip']);span(g,'open_inward_door_leaf','doorwood',hinge,tip,.025,2.22,.043);p=hinge.lerp(tip,.87);g.tube('door_metal_handle','steel',(*p,.98),(*p,1.11),.013)
  supports=[];topcontacts=[]
  def table(record,teacher=False):
   a,b=point(record['a']),point(record['b']);cx,cy=(a+b)/2;w,d=abs(b.x-a.x),abs(b.y-a.y);g.box('teacher_white_worktop'if teacher else'U_shape_white_tabletops','whiteworktop',(cx,cy,.75),(w,d,.045));feet=[]
   for x in [cx-w/2+.08,cx+w/2-.08]:
    for y in [cy-d/2+.08,cy+d/2-.08]:
     g.box('table_floor_contact_pads','dark',(x,y,.0125),(.04,.04,.025));g.tube('table_silver_legs','steel',(x,y,.02),(x,y,.734),.020);feet.append([x,y,0]);topcontacts.append([x,y,.7275])
   supports.extend(feet)
  for t in L['tables']:table(t)
  table(L['teacherDesk'],True);seats=[chair(g,point(s['pixel']),point(s['target']),s['colour'])for s in L['students']];tc=point([195,150]);seats.append(chair(g,point(L['teacherSeat']),tc,teacher=True))
  # Teaching wall is the plan's upper edge;the same-room photo controls equipment.
  a,b=point([164,35]),point([469,35]);inward=Vector((0,-.065))
  span(g,'teaching_whiteboard','screenwhite',a+inward,b+inward,.95,2.02,.035)
  span(g,'projection_screen_case','dark',a,b,2.44,2.52,.10);span(g,'projection_screen_surface','screenwhite',a+Vector((0,-.09)),b+Vector((0,-.09)),1.12,2.44,.018)
  span(g,'projection_screen_bottom_bar','dark',a+Vector((0,-.10)),b+Vector((0,-.10)),1.10,1.14,.03)
  p=point([194,145]);g.box('AV_monitor_base','dark',(*p,.79),(.32,.23,.025));g.tube('AV_monitor_stand','dark',(*p,.79),(*p,1.03),.024);g.box('AV_monitor_black_screen','screenblack',(p.x,p.y+.015,1.16),(.43,.065,.29));g.box('AV_keyboard','dark',(p.x,p.y-.25,.79),(.40,.14,.022));p=point([231,145]);g.box('AV_control_console','dark',(*p,.82),(.22,.28,.10))
  g.prism('continuous_complete_ceiling','ceiling',L['outline'],HEIGHT,.08)
  # Complete photographed-type plaster ceiling,downstand beams and rectangular lamps.
  for py in [180,360]:
   a,b=point([29,py]),point([510,py]);span(g,'photograph_guided_ceiling_beams','ceiling',a,b,HEIGHT-.22,HEIGHT,.32)
  lampanchors=[]
  for px in L['ceilingLights']:
   p=point(px);g.box('linear_lamp_housings','frame',(*p,HEIGHT-.055),(1.15,.30,.08));g.box('linear_lamp_diffusers','light',(*p,HEIGHT-.104),(1.09,.25,.022))
   for dx in [-.44,.44]:g.tube('linear_lamp_ceiling_supports','steel',(p.x+dx,p.y,HEIGHT-.020),(p.x+dx,p.y,HEIGHT+.012),.007);lampanchors.append([p.x+dx,p.y])
  p=point(L['projector']);g.tube('projector_ceiling_hanger','frame',(*p,2.69),(*p,HEIGHT+.015),.024);g.box('suspended_projector_body','frame',(*p,2.64),(.36,.29,.14));g.tube('projector_lens','dark',(p.x,p.y+.14,2.64),(p.x,p.y+.205,2.64),.04)
  objects=g.finish()
  for o in objects:o['roomCode']='CKK.1.10';o['destinationCollection']=COLLECTION;o['scope']='Independent same-room historical plan and photo;18student seats;estimated dimensions;not2026survey or geographic floor'
  return scene,col,objects,dict(seats=seats,tableFeet=supports,tableContacts=topcontacts,lampAnchors=lampanchors,projector=list(p),door=dict(a=list(secondary),b=list(db),clearWidth=(db-secondary).length-.05)),g.solid_proof
 def tree(objects):
  from mathutils.bvhtree import BVHTree
  vs=[];fs=[];owners=[]
  for o in objects:
   off=len(vs);vs.extend(o.matrix_world@v.co for v in o.data.vertices);fs.extend(tuple(off+i for i in f.vertices)for f in o.data.polygons);owners.extend([o.name]*len(o.data.polygons))
  return BVHTree.FromPolygons(vs,fs),owners
 def inside(x,y):
  answer=False
  for a,b in zip(L['outline'],L['outline'][1:]+L['outline'][:1]):
   if(a[1]>y)!=(b[1]>y)and x<(b[0]-a[0])*(y-a[1])/(b[1]-a[1])+a[0]:answer=not answer
  return answer
 def clip(poly,value):
  if not poly:return[]
  result=[];previous=poly[-1];pv=value(previous);pin=pv>=0
  for current in poly:
   cv=value(current);cin=cv>=0
   if cin!=pin:result.append(previous+(current-previous)*(pv/(pv-cv)))
   if cin:result.append(current)
   previous,pv,pin=current,cv,cin
  return result
 def route_sweep(objects):
  surfaces=[]
  for o in objects:
   if any(k in o.name for k in ['complete_plan_floor','checker_carpet_tiles']):continue
   o.data.calc_loop_triangles()
   for tri in o.data.loop_triangles:
    poly=[o.matrix_world@o.data.vertices[i].co for i in tri.vertices]
    if max(p.z for p in poly)<.04 or min(p.z for p in poly)>2.10:continue
    poly=clip(clip(poly,lambda p:p.z-.04),lambda p:2.10-p.z)
    if poly:surfaces.append((o.name,poly))
  groups=[];failures=[]
  for route in L['routePaths']:
   segments=[]
   for pa,pb in zip(route['points'],route['points'][1:]):
    a,b=point(pa),point(pb);d=(b-a).normalized();n=Vector((-d.y,d.x));length=(b-a).length;hits=[]
    for owner,poly in surfaces:
     q=[Vector(((p.xy-a).dot(d),(p.xy-a).dot(n)))for p in poly]
     if max(p.x for p in q)<=1e-6 or min(p.x for p in q)>=length-1e-6 or max(p.y for p in q)<=-.22+1e-6 or min(p.y for p in q)>=.22-1e-6:continue
     for f in [lambda p:p.x-1e-6,lambda p:length-1e-6-p.x,lambda p:p.y+.22-1e-6,lambda p:.22-1e-6-p.y]:q=clip(q,f)
     if q:hits.append(owner)
    record=dict(sourceEndpoints=[pa,pb],length=length,width=.44,verticalRange=[.04,2.10],intersectionObjects=sorted(set(hits)));segments.append(record)
    if hits:failures.append(dict(group=route['group'],**record))
   caps=[]
   for pp in route['points'][1:]:
    centre=point(pp);hits=[]
    for owner,poly in surfaces:
     q=[p.xy-centre for p in poly]
     if max(p.x for p in q)<=-.22+1e-6 or min(p.x for p in q)>=.22-1e-6 or max(p.y for p in q)<=-.22+1e-6 or min(p.y for p in q)>=.22-1e-6:continue
     for f in [lambda p:p.x+.22-1e-6,lambda p:.22-1e-6-p.x,lambda p:p.y+.22-1e-6,lambda p:.22-1e-6-p.y]:q=clip(q,f)
     if q:hits.append(owner)
    cap=dict(sourcePoint=pp,bodySquareWidth=.44,verticalRange=[.04,2.10],intersectionObjects=sorted(set(hits)));caps.append(cap)
    if hits:failures.append(dict(group=route['group'],cornerCap=cap))
   groups.append(dict(group=route['group'],connectedPolyline=route['points'],approach=route['approach'],seatIds=route['seatIds'],segments=segments,turnAndEndpointBodyCaps=caps,passed=all(not s['intersectionObjects']for s in segments+caps)))
  report=dict(method='Everyactualworldtriangleclippedto0.04–2.10mheightandcomplete0.44mwiderectangularcorridors;horizontalworktopsandchairsincluded',eligibleTriangles=len(surfaces),groups=groups,totalFailedSegments=len(failures),failures=failures)
  if failures:
   history=DATA/'failed-route-diagnostics.json';prior=json.loads(history.read_text())if history.exists()else[];prior.append(report);write(history,prior)
  assert not failures,('ActualSavedBodyCorridorBlocked',failures)
  return report
 def checks(objects,R):
  floor,_=tree([o for o in objects if any(k in o.name for k in ['complete_plan_floor','checker_carpet_tiles'])]);ceiling,_=tree([o for o in objects if o.name==PREFIX+'continuous_complete_ceiling']);solid,owners=tree([o for o in objects if not any(k in o.name for k in ['complete_plan_floor','checker_carpet_tiles','ceiling'])]);tops,_=tree([o for o in objects if any(k in o.name for k in ['white_tabletops','white_worktop'])]);walls,_=tree([o for o in objects if any(k in o.name for k in ['perimeter_walls','window_lower_wall','window_upper_wall','true_door_lintel'])])
  overhead,_=tree([o for o in objects if any(k in o.name for k in ['ceiling','lamp','projector'])])
  feet=[]
  for kind,ps in [('chair',[p for s in R['seats']for p in s['feet']]),('table',R['tableFeet'])]:
   for p in ps:
    hit=floor.ray_cast(Vector((p[0],p[1],.04)),Vector((0,0,-1)),.08);assert hit[0]is not None and abs(hit[0].z)<.001,('UnsupportedFoot',kind,p);feet.append(dict(kind=kind,point=p,floorZ=hit[0].z))
  contacts=[]
  for p in R['tableContacts']:
   hit=tops.ray_cast(Vector((p[0],p[1],.70)),Vector((0,0,1)),.07);assert hit[0]is not None and abs(hit[0].z-.7275)<.001;contacts.append([p[0],p[1],hit[0].z])
  coverage=[];step=.20;xs=[p[0]for p in L['outline']];ys=[p[1]for p in L['outline']]
  for i in range(math.floor(min(xs)/step),math.ceil(max(xs)/step)):
   for j in range(math.floor(min(ys)/step),math.ceil(max(ys)/step)):
    x,y=(i+.5)*step,(j+.5)*step
    if not inside(x,y):continue
    hit=ceiling.ray_cast(Vector((x,y,1.5)),Vector((0,0,1)),2);assert hit[0]is not None and abs(hit[0].z-HEIGHT)<.001,('CeilingHole',x,y);coverage.append([x,y,hit[0].z])
  assert len(coverage)>1000
  doorway=[];a,b=Vector(R['door']['a']),Vector(R['door']['b']);c=(a+b)/2;u=(b-a).normalized()
  for side in [-.22,0,.22]:
   for z in [.04,.65,1.20,2.10]:
    normal=Vector((-u.y,u.x));p=c+u*side-normal*.25;hit=solid.ray_cast(Vector((*p,z)),Vector((*normal,0)),.50);assert hit[0]is None,('DoorBlocked',side,z,owners[hit[2]]if hit[2]is not None else None);doorway.append([side,z])
  windows=[]
  for w in L['windows']:
   a,b=point(w['a']),point(w['b']);u=(b-a).normalized();normal=Vector((-u.y,u.x))
   for t in [.2,.5,.8]:
    p=a.lerp(b,t)
    for z in [1.20,1.70,2.55]:
     hit=walls.ray_cast(Vector((p.x-normal.x*.25,p.y-normal.y*.25,z)),Vector((*normal,0)),.50);assert hit[0]is None,('UncutWindow',w['id'],t,z);windows.append([w['id'],t,z])
  lamps=[]
  for p in R['lampAnchors']:
   hit=ceiling.ray_cast(Vector((*p,HEIGHT-.04)),Vector((0,0,1)),.08);assert hit[0]is not None;lamps.append([*p,hit[0].z])
  hanger=next(o for o in objects if o.name==PREFIX+'projector_ceiling_hanger');assert min(v.co.z for v in hanger.data.vertices)<2.71 and max(v.co.z for v in hanger.data.vertices)>HEIGHT
  routes=route_sweep(objects);paths=[]
  for route in L['routePaths']:
   for pa,pb in zip(route['points'],route['points'][1:]):
    a,b=point(pa),point(pb);n=Vector((-(b-a).y,(b-a).x)).normalized();count=math.ceil((b-a).length/.15)
    for k in range(1,count+1):
     p=a.lerp(b,k/count)
     for side in [-.22,0,.22]:
      q=p+n*side;hit=floor.ray_cast(Vector((*q,.04)),Vector((0,0,-1)),.08);assert hit[0]is not None;h=overhead.ray_cast(Vector((*q,.04)),Vector((0,0,1)),HEIGHT+.10);assert h[0]is not None and h[0].z>2.1;paths.append([q.x,q.y,h[0].z])
  approaches=[]
  for route in L['routePaths']:
   p=point(route['approach']);candidates=[point(L['teacherSeat'])]if route['group']=='teacher'else[point(s['pixel'])for s in L['students']if s['id']in route['seatIds']];distance=min((p-q).length for q in candidates);assert distance<.75;approaches.append(dict(group=route['group'],distanceToNearestSeatCentre=distance))
  return dict(studentSeatCount=18,teacherSeatCount=1,UWorktopModules=9,teacherDeskCount=1,footSupportProbes=feet,tableLegToWorktopContacts=contacts,continuousCeilingCoverage=dict(spacingMetres=step,probeCount=len(coverage),missCount=0,undersideHeight=HEIGHT,pointDigest=hashlib.sha256(json.dumps(coverage).encode()).hexdigest()),realDoorClearRays=doorway,doorClearWidth=R['door']['clearWidth'],realWindowWallApertureRays=windows,lightCeilingSupportProbes=lamps,projectorHangerJoinsCeilingAndBody=True,wholeRouteSavedMeshSweep=routes,fullWidthRouteFloorAndHeadroomProbeCount=len(paths),minimumRouteCeilingHeadroom=min(p[2]for p in paths),groupApproachDistances=approaches,allAuthoredComponentsClosed=True)
 def render(scene):
  bpy.context.window.scene=scene;world=bpy.data.worlds.new(PREFIX+'previewWorld');world.use_nodes=True;world.node_tree.nodes['Background'].inputs[0].default_value=(.76,.80,.84,1);world.node_tree.nodes['Background'].inputs[1].default_value=.25;scene.world=world
  ld=bpy.data.lights.new(PREFIX+'previewArea','AREA');ld.energy=650;ld.shape='DISK';ld.size=5;lamp=bpy.data.objects.new(ld.name,ld);scene.collection.objects.link(lamp);lamp.location=(0,0,HEIGHT-.22)
  washdata=bpy.data.lights.new(PREFIX+'previewCeilingWash','AREA');washdata.energy=220;washdata.shape='DISK';washdata.size=5;wash=bpy.data.objects.new(washdata.name,washdata);scene.collection.objects.link(wash);wash.location=(0,0,HEIGHT-.45);wash.rotation_euler=(math.pi,0,0)
  cd=bpy.data.cameras.new(PREFIX+'previewCamera');camera=bpy.data.objects.new(cd.name,cd);scene.collection.objects.link(camera);scene.camera=camera;cd.lens=17;cd.clip_end=100
  scene.render.engine='BLENDER_EEVEE';scene.eevee.taa_render_samples=24;scene.render.resolution_x=1200;scene.render.resolution_y=900;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='AgX';views=[]
  for name,pp,tp,z,tz,label in [('teaching',[95,465],[300,85],1.65,1.35,'CKK.1.10十八席U形桌与教学端'),('seating',[350,95],[260,410],1.65,1.28,'CKK.1.10来源椅位、两窗湾与完整天花')]:
   p,t=point(pp),point(tp);camera.location=(*p,z);target=Vector((*t,tz));camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler();cd.sensor_fit='VERTICAL';cd.lens=cd.sensor_height/(2*math.tan(math.radians(80)/2));scene.render.filepath=str(OUT/('built-'+name+'.png'));bpy.ops.render.render(write_still=True);views.append(dict(name='ckk-110-'+name+'-interior',code='CKK',spaceId='ckk-110',label=label,view=dict(position=[p.x,z,-p.y],target=[t.x,tz,-t.y],fov=80)))
  for o in [camera,lamp,wash]:bpy.data.objects.remove(o,do_unlink=True)
  bpy.data.cameras.remove(cd);bpy.data.lights.remove(ld);bpy.data.lights.remove(washdata);return views
 def run():
  assert sha(BASE)==SHA;bpy.ops.wm.open_mainfile(filepath=str(BASE));update();expected=accepted_fingerprints(ROOT/'result/blender/stage233',SHA);assert len(expected)==8529 and{o.name:object_fingerprint(o)for o in bpy.data.objects}==expected
  mats={m.name:material_fingerprint(m)for m in bpy.data.materials};assert len(mats)==2311;mods={o.name:stable_modifiers(o)for o in bpy.data.objects};rooms=rooms_state();assert len(rooms)==34 and len(set(n for r in rooms for n in r['objects']))==1433;members={o.name:sorted(c.name for c in o.users_collection)for o in bpy.data.objects};vis={o.name:o.hide_render for o in bpy.data.objects};props={o.name:dict(o.items())for o in bpy.data.objects}
  scene,col,objects,records,solid=build();update();proof=checks(objects,records);views=[dict(name='ckk-110-teaching-interior',view=dict(position=[-2.625,1.65,3.0],target=[.45,1.35,-2.7],fov=80))]
  scope='依据LSE官方同房号历史平面及照片建立CKK.1.10独立U形教室。保留左6、右6、后6共18个学生椅位及1教师席、U桌、两处右窗湾和左侧不等双叶门。完整带梁天花、真实门窗洞、家具及投影支承，尺寸和门叶展示角度估算；不作校园楼层配准、现用容量或2026现况认证。'
  space=dict(code='CKK',id='ckk-110',label='CKK.1.10U形教室',collection=COLLECTION,gallery=views[0]['name'],scope=scope,interiorView=views[0]['view'],interiorStudy=dict(kind='room-sample',label='CKK.1.10U形教室',scope=scope));col['authoringRecord']=json.dumps(space,ensure_ascii=False)
  fingerprints={o.name:object_fingerprint(o)for o in objects};bindings={o.name:[m.name for m in o.data.materials]for o in objects};component=OUT/'component.blend';bpy.data.libraries.write(str(component),{col,scene},fake_user=True,compress=True)
  bpy.ops.wm.open_mainfile(filepath=str(BASE));update();assert{o.name:object_fingerprint(o)for o in bpy.data.objects}==expected
  with bpy.data.libraries.load(str(component),link=False)as(src,dst):dst.collections=[COLLECTION]
  saved=dst.collections[0];scene=bpy.data.scenes.new(SCENE);scene.collection.children.link(saved);bpy.context.window.scene=scene;update();assert checks(list(saved.all_objects),records)==proof
  views=render(scene)
  assert all(object_fingerprint(bpy.data.objects[n])==v for n,v in fingerprints.items());assert all(object_fingerprint(bpy.data.objects[n])==v for n,v in expected.items());assert all(material_fingerprint(bpy.data.materials[n])==v for n,v in mats.items());assert all(stable_modifiers(bpy.data.objects[n])==v for n,v in mods.items());assert rooms_state()==rooms;assert all(sorted(c.name for c in bpy.data.objects[n].users_collection)==v for n,v in members.items());assert all(bpy.data.objects[n].hide_render==v for n,v in vis.items());assert all(dict(bpy.data.objects[n].items())==v for n,v in props.items());assert not any(n in bpy.data.scenes['00_CAMPUS_COMPLETE'].objects for n in fingerprints);assert sha(BASE)==SHA;assert all(o.parent is None and not o.constraints for o in saved.all_objects)
  verification=dict(savedComponentReopened=True,independentAcceptedObjectsVerified=8529,allOriginalMaterialNodesVerified=2311,allOriginalModifierStacksVerified=len(mods),oldSpacesPreserved=34,oldSpaceUniqueObjectsPreserved=1433,allOriginalMembershipsPropertiesVisibilityUnchanged=True,allSourceGeometryUVTransformsBindingsUnchanged=True,noNewRoomObjectInCampus=True,allOwnedObjectsParentlessNoConstraints=True,sourceNativeShaUnchanged=True,sourcePhotoNotUsedAsTexture=True,previewLightsAndCamerasExcluded=True,completeGroupRoutesRecheckedAfterReopen=True,triangles=sum(len(f.vertices)-2 for o in saved.all_objects for f in o.data.polygons))
  audit=dict(version=234,building='CKK',baseline=str(BASE.relative_to(ROOT)),baselineSha256=SHA,componentPath=str(component.relative_to(ROOT)),componentSha256=sha(component),targetCollection=COLLECTION,destinationCollection=COLLECTION,collectionSpec=dict(kind='independent-room',name=COLLECTION,scene=SCENE),space=space,addedObjects=list(fingerprints),archivedObjects=[],changedObjects=[],addedFingerprints=fingerprints,replacementMaterialBindings=bindings,sourceManifest='data/collections/ckk110-room234/sources.json',planLayout='data/collections/ckk110-room234/layout.json',studentSeatCount=18,teacherSeatCount=1,scaleMetresPerPixel=SCALE,roomAreaSquareMetres=L['roomAreaSquareMetres'],estimatedCeilingHeight=HEIGHT,gallerySuggestions=views,checks=proof,solidProof=solid,verification=verification,previews=['built-teaching.png','built-seating.png'],beforeEvidence=[PLAN,PHOTO],previewLighting='Temporary650Wdownward area and220Wceiling wash;all lights/cameras excluded from saved component;complete ceiling remains physical',limitations=json.loads((DATA/'sources.json').read_text())['limitations'])
  history=DATA/'failed-route-diagnostics.json'
  audit['retainedFailedRouteDiagnostics']=dict(path=str(history.relative_to(ROOT)),attemptCount=len(json.loads(history.read_text())),interpretation='An early lower-group diagonal was blocked by retained chair surfaces. The final path detours below the last left chair and around the displayed door leaf;no source furniture is moved. Final groups are independently rechecked on saved meshes.')if history.exists()else None
  write(OUT/'audit.json',audit);print('CKK110_ROOM234_READY',len(fingerprints),verification,flush=True)
 def verify_saved():
  report=json.loads((OUT/'audit.json').read_text());component=OUT/'component.blend';expected_sha=report['componentSha256']
  bpy.ops.wm.open_mainfile(filepath=str(component));update();assert sha(component)==expected_sha
  assert {o.name:object_fingerprint(o)for o in bpy.data.objects}==report['addedFingerprints']
  scene=bpy.data.scenes.get(SCENE);assert scene is not None and COLLECTION in scene.collection.children
  assert set(scene.objects.keys())==set(report['addedObjects'])and all(o.type=='MESH'for o in scene.objects)
  assert all([m.name for m in o.data.materials]==report['replacementMaterialBindings'][o.name]for o in scene.objects)
  assert route_sweep(list(scene.objects))==report['checks']['wholeRouteSavedMeshSweep']
  floor,_=tree([o for o in scene.objects if any(k in o.name for k in ['complete_plan_floor','checker_carpet_tiles'])])
  for sample in report['checks']['footSupportProbes']:
   p=sample['point'];hit=floor.ray_cast(Vector((p[0],p[1],.04)),Vector((0,0,-1)),.08);assert hit[0]is not None and abs(hit[0].z)<.001
  assert sha(BASE)==SHA and sha(component)==expected_sha
  report['verification'].update(standaloneSavedComponentOpened=True,independentSceneAnd52MeshMembershipVerified=True,standaloneMaterialBindingsVerified=True,standaloneFullHeightRoutesAnd117SupportsReplayed=True)
  write(OUT/'audit.json',report);write(OUT/'verification.json',report['verification']);print('CKK110_STANDALONE_VERIFIED',expected_sha,flush=True)
 if __name__=='__main__':verify_saved()if(OUT/'audit.json').exists()else run()
