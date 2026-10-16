"""Build the independent MAR.1.08 historical tiered classroom component.

Fixed paths and editor-friendly configuration. Source photos are private review
references only. The immutable complete campus is never saved by this script.
"""
from pathlib import Path
import hashlib,json,math,sys
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'result/blender/mar108-room228'
DATA=ROOT/'data/collections/mar108-room228'
BASE=ROOT/'result/blender/LSE_campus_detailed_v227.blend'
SHA='fba3318e79206e20fc9208336fb5e354ffbfcfe4721d31ad7a6a2489511204a0'
COLLECTION='MAR108_ROOM228_study'
SCENE='ROOM228_MAR108'
PREFIX='MAR108_R228_'
PLAN='data/collections/interiors/images/226e23859b8d_MAR.1.08.gif'
PHOTO='data/collections/interiors/images/814902a90e20_MAR.1.08.jpg'
SCALE=.036
HEIGHT=4.50
REVIEW_SAVED_ONLY=False

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def xy(p):return[(p[0]-318)*SCALE,(480-p[1])*SCALE]
def prepare():
 from shapely.geometry import Polygon,box
 from PIL import Image,ImageDraw
 DATA.mkdir(parents=True,exist_ok=True);OUT.mkdir(parents=True,exist_ok=True)
 outline=[[150,292],[326,292],[326,280],[430,280],[430,292],[474,292],[486,327],[486,529],[499,544],[462,583],[462,623],[430,623],[399,623],[347,667],[248,667],[192,623],[150,623]]
 room=Polygon([xy(p)for p in outline]);assert room.is_valid
 def polygons(shape):return[shape]if shape.geom_type=='Polygon'else[p for p in shape.geoms if p.geom_type=='Polygon']
 # The terrace heights are estimates from the photograph. All strips form
 # one floor field. The cross aisle and side aisles contain physical steps.
 first=room.intersection(Polygon([xy(p)for p in [[150,292],[499,292],[499,590],[319,590],[319,402],[280,402],[280,590],[150,590]]]))
 second=room.intersection(Polygon([xy(p)for p in [[150,292],[499,292],[499,590],[365,590],[365,361],[229,361],[229,590],[150,590]]]))
 third=room.intersection(Polygon([xy(p)for p in [[150,292],[499,292],[499,590],[400,590],[400,322],[193,322],[193,590],[150,590]]]))
 fourth=room.intersection(Polygon([xy(p)for p in [[414,292],[499,292],[499,520],[449,520]]]))
 # Intermediate150mm rises create real stairs in the empty cross aisle.
 tiers=[dict(height=0.,parts=[list(room.exterior.coords)[:-1]])]
 for z,shape in [(.30,first),(.60,second),(.90,third),(1.20,fourth)]:
  # Slabs extend down to the base and overlap; no hidden unsupported skins.
  tiers.append(dict(height=z,parts=[list(p.exterior.coords)[:-1]for p in polygons(shape)]))
 tables=[]
 def table(name,pixels,z):
  poly=Polygon([xy(p)for p in pixels]);inner=poly.buffer(-.065,join_style=2);assert not inner.is_empty
  supports=[list(p)for part in polygons(inner)for p in list(part.exterior.coords)[:-1]]
  from shapely.geometry import Point
  floors=[max([0]+[height for height,shape in[(.3,first),(.6,second),(.9,third),(1.2,fourth)]if shape.covers(Point(p))])for p in supports]
  tables.append(dict(id=name,pixels=pixels,outline=[xy(p)for p in pixels],floor=z,supportPoints=supports,supportFloors=floors))
 table('outerU',[[185,445],[199,328],[210,322],[298,317],[391,323],[410,445],[420,445],[405,320],[394,311],[298,305],[206,310],[190,320],[174,445]],.90)
 table('innerU',[[216,445],[229,368],[240,361],[298,355],[358,362],[370,445],[382,445],[371,359],[360,351],[298,343],[237,350],[219,359],[204,445]],.60)
 table('centralU',[[275,445],[281,414],[312,414],[317,445],[327,445],[319,403],[276,403],[266,445]],.30)
 for name,x,z in [('leftOuter',181,.90),('leftInner',216,.60),('rightInner',370,.60),('rightOuter',407,.90)]:
  table(name,[[x,475],[x+11,475],[x+7,568],[x-4,573]],z)
 table('leftFan',[[254,491],[274,488],[253,546],[253,574],[242,579],[243,543]],.30)
 table('rightFan',[[322,488],[342,491],[354,543],[355,579],[344,574],[344,546]],.30)
 table('rightLong',[[428,336],[439,336],[466,503],[454,503]],1.20)
 seats=[]
 def seat(name,p,target,z):seats.append(dict(id=name,pixel=p,centre=xy(p),target=xy(target),floor=z))
 for i,x in enumerate([211,228,245,262,279,296,313,330,347,364,381]):seat('outerRear'+str(i),[x,311-4*math.sin(i*math.pi/10)],[x,350],.90)
 for side,x in [('L',184),('R',410)]:
  for i,y in enumerate([334,352,370,388,406,424,442]):
   px=x+(-1 if side=='L'else 1)*(y-334)*.11;seat('outer'+side+str(i),[px,y],[298,y],.90)
 for i,x in enumerate([244,262,280,298,316,334,352]):seat('innerRear'+str(i),[x,348-4*math.sin(i*math.pi/6)],[x,386],.60)
 for side,x in [('L',217),('R',375)]:
  for i,y in enumerate([369,387,405,423,441]):
   px=x+(-1 if side=='L'else 1)*(y-369)*.10;seat('inner'+side+str(i),[px,y],[298,y],.60)
 for side,x in [('L',265),('R',332)]:
  for i,y in enumerate([417,437]):seat('central'+side+str(i),[x,y],[298,y],.30)
 for name,x,z in [('leftOuter',168,.90),('leftInner',203,.60),('rightInner',389,.60),('rightOuter',425,.90)]:
  for i,y in enumerate([486,505,524,543,562]):seat(name+str(i),[x,y],[x+(30 if x<298 else-30),y],z)
 for side in ['L','R']:
  for i,y in enumerate([506,527,548,570]):
   x=244-(y-506)*.08 if side=='L' else 354+(y-506)*.04;seat('fan'+side+str(i),[x,y],[298,y],.30)
 for i,y in enumerate([346,364,382,400,418,436,454,472,490]):seat('rightLong'+str(i),[449+(y-346)*.16,y],[400,y],1.20)
 assert len(seats)==83
 doors=[dict(id='frontLeft',a=[162,623],b=[192,623],hinge=[162,623],tip=[162,649]),dict(id='frontRight',a=[399,623],b=[430,623],hinge=[430,623],tip=[430,649])]
 windows=[dict(id='rearHigh',a=[326,280],b=[430,280],sill=2.55,head=4.08),dict(id='rightBand',a=[486,341],b=[486,487],sill=2.0,head=3.86)]
 # Stairs align to the cross aisle,with intermediate150mm rises. Each region
 # continues to the next terrace; no floating independent stair objects.
 stairs=[]
 for side,coords in [('left',[(280,286,.15),(229,235,.45),(193,199,.75)]),('right',[(313,319,.15),(359,365,.45),(394,400,.75),(434,440,1.05)])]:
  for a,b,z in coords:stairs.append(dict(id=side+str(z),outline=[xy(p)for p in [[a,451],[b,451],[b,470],[a,470]]],height=z))
 # Front access stairs share a flat landing before the rows.
 for x0,x1 in [(229,280),(319,365)]:
  stairs.append(dict(id='frontFan'+str(x0),outline=[xy(p)for p in [[x0,595],[x1,595],[x1,590],[x0,590]]],height=.15))
 layout=dict(room='MAR.1.08',scaleMetresPerPixel=SCALE,scaleBasis='Estimated0.036m/pixel from30px front entrance about1.08m and18px seat pitch about0.648m; no printed measured dimension',outlinePixels=outline,outline=[xy(p)for p in outline],roomAreaSquareMetres=room.area,estimatedCeilingHeight=HEIGHT,terraces=tiers,stairs=stairs,tables=tables,seats=seats,studentSeatCount=83,printedPlanCapacity=87,seatCountInterpretation='83visible student chair symbols traced:outerU25,innerU17,central4,lowerbanks20,fans8,rightlong9. Printedcapacity87doesnotmatchvisiblecount;fouradditionalpositionsarenotinvented.',doors=doors,windows=windows,teacherSeat=xy([251,639]),teacherDesk=xy([251,616]),principalRoutes=[[[177,622],[177,600]],[[177,600],[298,600]],[[298,600],[298,460]],[[211,460],[426,460]]])
 (DATA/'layout.json').write_text(json.dumps(layout,ensure_ascii=False,indent=2)+'\n')
 source=json.loads((ROOT/'data/collections/interiors/sources.json').read_text());refs=[r for r in source['sources']if r.get('local_path')in[PLAN,PHOTO]];assert len(refs)==2
 limitations=['两幅历史素材的创建与拍摄日期未知；网页2022年刷新时间与2026年检索时间均不是测绘或拍摄日期。','比例0.036m/像素、层高4.50m、四级台地0.30m、0.60m、0.90m、1.20m以及家具与隐藏构造均为估算。','平面标注容量87，可逐组辨认的学生座椅为83个；未补造其余4个位置，两者均不代表当前认证容量。','平面控制马蹄桌、前侧分组、中央四席、门与周界；照片控制家具类型与饰面，斜视照片不足以证明全部83个位置或同时期布局。','后部高窗与右侧连续窗带依据平面多线框架解释，照片未显示其被遮挡的立面，窗高与窗框细节为估算。','天花连续完整；木条间距、设备吊架与灯具位置为照片支持的简化估算。','独立Marshall教室研究样本，不代表地理楼层配准、全楼覆盖、2026年竣工测绘、无障碍或疏散认证。','源照片仅供私下核对，不作为发布纹理；带实体台阶的通道只作几何检查，不作认证净宽声明。']
 manifest=dict(room='MAR.1.08',building='Marshall Building',sources=refs,planSha256=sha(ROOT/PLAN),photoSha256=sha(ROOT/PHOTO),sameRoomPairVerified=True,bothImagesActualNotPlaceholder=True,sourceDates='Creation/capture dates unknown',sourceInterpretation=['Plan explicitly labelsMarshallBuilding,floor1,room1.08,capacity87. Actual drawing and actual room photograph,notplaceholders.','Both show tiered horseshoe desks,front split fan and central grouped tables. Photo taken toward front teaching wall with twin black teaching displays,central projection and woodslats.','Exact captured layout chronology is unknown;one coherent plan-layout sample withphoto-informed finishes is authored.'],limitations=limitations)
 (DATA/'sources.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
 im=Image.open(ROOT/PLAN).convert('RGB');d=ImageDraw.Draw(im);d.line(outline+[outline[0]],fill=(210,25,25),width=2)
 for s in seats:
  x,y=s['pixel'];d.ellipse((x-2,y-2,x+2,y+2),fill=(20,50,210))
 im.save(DATA/'registered-plan.png');print('MAR108_LAYOUT_READY',len(seats),room.area,flush=True)
try:import bpy
except ModuleNotFoundError:
 if __name__=='__main__':prepare()
else:
 from mathutils import Vector
 from mathutils.bvhtree import BVHTree
 sys.path.insert(0,str(ROOT/'web/tools'))
 from build_room_samples167 import RoomGeometry
 from integrate_exterior_round194 import object_fingerprint,accepted_fingerprints
 from refine_portsmouth_exterior207 import material_fingerprint
 from refine_sal_structure221 import stable_modifiers,rooms_state
 L=json.loads((DATA/'layout.json').read_text())
 def update():
  for s in bpy.data.scenes:
   for layer in s.view_layers:layer.update()
 def point(p):return Vector(xy(p))
 def material(g,key,color,rough=.7,metal=0):
  m=bpy.data.materials.new(PREFIX+key);m.use_nodes=True;m.diffuse_color=(*color,1);n=m.node_tree.nodes['Principled BSDF'];n.inputs['Base Color'].default_value=m.diffuse_color;n.inputs['Roughness'].default_value=rough;n.inputs['Metallic'].default_value=metal;g.materials[key]=m
 def span(g,family,key,a,b,lo,hi,depth=.14):
  a,b=Vector(a),Vector(b);d=b-a;c=(a+b)/2;g.box(family,key,(*c,(lo+hi)/2),(d.length,depth,hi-lo),math.atan2(d.y,d.x))
 def chair(g,s,teacher=False):
  p,t=Vector(s['centre']),Vector(s['target']);z=s['floor'];angle=math.atan2(t.y-p.y,t.x-p.x)+math.pi/2;c,sn=math.cos(angle),math.sin(angle)
  def at(x,y,h):return(p.x+c*x-sn*y,p.y+sn*x+c*y,z+h)
  g.box('black_taskchair_seats','seatblack',at(0,0,.47),(.47,.43,.06),angle)
  # Open framed mesh back has individual horizontal dark mesh strips.
  for x in [-.235,.235]:g.tube('taskchair_back_frames','frame',at(x,.22,.48),at(x,.28,.99),.019)
  for h,y in [(.50,.223),(.98,.28)]:g.tube('taskchair_back_frames','frame',at(-.235,y,h),at(.235,y,h),.019)
  for i in range(18):
   h=.51+i*.025;y=.224+(h-.50)*.115;g.box('dark_mesh_back_weave','mesh',at(0,y,h),(.435,.016,.017),angle)
  for x in [-.27,.27]:
   g.tube('taskchair_arm_supports','frame',at(x,.04,.45),at(x,.04,.66),.018);g.box('taskchair_armrests','frame',at(x,0,.67),(.055,.31,.035),angle)
  g.tube('taskchair_pedestals','frame',at(0,0,.12),at(0,0,.45),.032);feet=[]
  for i in range(5):
   a=i*math.tau/5;x,y=.27*math.cos(a),.27*math.sin(a);g.tube('taskchair_star_bases','frame',at(0,0,.14),at(x,y,.07),.024);g.tube('taskchair_casters','frame',at(x-.016,y,.03),at(x+.016,y,.03),.03);feet.append(list(at(x,y,.03)))
  return dict(centre=list(p),floor=z,teacher=teacher,feet=feet)
 def build():
  scene=bpy.data.scenes.new(SCENE);col=bpy.data.collections.new(COLLECTION);scene.collection.children.link(col);col['roomSample']=True;col['roomCode']='MAR.1.08';g=RoomGeometry(col,PREFIX)
  for key,c,r,m in [('plaster',(.74,.75,.71),.85,0),('carpet',(.25,.28,.27),.98,0),('wood',(.58,.46,.31),.68,0),('woodlight',(.72,.64,.48),.65,0),('edge',(.76,.75,.66),.62,0),('top',(.115,.14,.145),.63,0),('frame',(.018,.023,.025),.57,0),('seatblack',(.025,.033,.036),.85,0),('mesh',(.060,.071,.073),.9,0),('ceiling',(.12,.13,.13),.92,0),('screen',(.025,.030,.040),.42,0),('projection',(.64,.67,.69),.8,0),('glassroom',(.14,.20,.22),.25,0),('metal',(.38,.41,.40),.35,.55),('exit',(.07,.52,.25),.7,0)]:material(g,key,c,r,m)
  g.prism('complete_plan_base_floor','carpet',L['outline'],-.15,.15)
  for tier in L['terraces'][1:]:
   for ring in tier['parts']:g.prism('continuous_stepped_terraces','carpet',ring,0,tier['height'])
  for stair in L['stairs']:g.prism('physical_access_steps','carpet',stair['outline'],0,stair['height'])
  # Perimeter segmentation creates actual door and high window apertures.
  for aa,bb in zip(L['outlinePixels'],L['outlinePixels'][1:]+L['outlinePixels'][:1]):
   a,b=point(aa),point(bb);d=b-a;events=[(0.,1.,'wall',None)]
   for item,kind in [(i,'door')for i in L['doors']]+[(i,'window')for i in L['windows']]:
    u,v=point(item['a']),point(item['b'])
    if abs(d.cross(u-a))>1e-5 or abs(d.cross(v-a))>1e-5:continue
    lo,hi=sorted(((u-a).dot(d)/d.length_squared,(v-a).dot(d)/d.length_squared))
    if lo<-.001 or hi>1.001:continue
    new=[]
    for s,e,k,it in events:
     if k!='wall'or hi<=s or lo>=e:new.append((s,e,k,it));continue
     if s<lo:new.append((s,lo,'wall',None))
     new.append((max(lo,s),min(hi,e),kind,item))
     if hi<e:new.append((hi,e,'wall',None))
    events=new
   for s,e,kind,item in events:
    p,q=a+d*s,a+d*e
    if kind=='wall':span(g,'complete_perimeter_walls','plaster',p,q,0,HEIGHT,.18)
    elif kind=='door':span(g,'actual_door_lintels','plaster',p,q,2.35,HEIGHT,.18)
    else:span(g,'actual_window_sill_walls','plaster',p,q,0,item['sill'],.18);span(g,'actual_window_head_walls','plaster',p,q,item['head'],HEIGHT,.18)
  for w in L['windows']:
   a,b=point(w['a']),point(w['b']);d=b-a;u=d.normalized()
   for p in [a,b]:span(g,'perimeter_glazing_jambs','metal',p-u*.035,p+u*.035,w['sill']-.03,w['head']+.03,.20)
   for z in [w['sill'],w['head']]:span(g,'perimeter_glazing_rails','metal',a,b,z-.035,z+.035,.20)
   count=max(2,round(d.length/1.25))
   for i in range(1,count):
    p=a+d*i/count;span(g,'glazing_mullions','metal',p-u*.026,p+u*.026,w['sill'],w['head'],.12)
   span(g,'perimeter_glass','glassroom',a,b,w['sill'],w['head'],.016)
  for door in L['doors']:
   a,b=point(door['a']),point(door['b']);u=(b-a).normalized()
   for p in [a,b]:span(g,'door_jamb_frames','frame',p-u*.025,p+u*.025,0,2.36,.20)
   span(g,'door_header_frames','frame',a,b,2.30,2.37,.20);span(g,'open_door_leaves','frame',point(door['hinge']),point(door['tip']),.02,2.30,.045)
   p=(a+b)/2;g.box('illuminated_exit_signs','exit',(*p,2.52),(.45,.08,.19))
  # Photo acoustic timber slats occupy the photographed sidewall; vertical
  # geometry has real support against the plaster,not a photograph texture.
  for py in range(305,591,3):
   x,y=point([150,py]);g.box('photo_timber_acoustic_wall_slats','wood',(x+.105,y,2.70),(.055,.027,3.58))
  supports=[];contacts=[]
  for table in L['tables']:
   ring=table['outline'];z=table['floor'];g.prism('continuous_dark_tabletops','edge',ring,z+.73,.055);g.prism('recessed_dark_worktops','top',ring,z+.785,.009)
   # Supports at polygon vertices sit inside theworktop. Solid timber panels
   # follow the table centreline on the teaching side,as photographed.
   centre=sum((Vector(p)for p in ring),Vector((0,0)))/len(ring)
   for i,p in enumerate(table['supportPoints']):
    p=Vector(p)
    if i%2 and len(ring)>8:continue
    fz=table['supportFloors'][i];g.box('table_steel_floor_pads','frame',(*p,fz+.0125),(.075,.075,.025));g.tube('table_vertical_steel_supports','frame',(*p,fz+.02),(*p,z+.746),.025);supports.append(dict(foot=[p.x,p.y,fz+.0125],floor=fz,top=[p.x,p.y,z+.746]))
   # Paired boundary vertices define consistent12mm panels underneath edges.
   for a,b in zip(ring,ring[1:]+ring[:1]):
    a,b=Vector(a),Vector(b)
    if(b-a).length<.45:continue
    a,b=a.lerp(centre,.05),b.lerp(centre,.05);span(g,'photo_timber_desk_modesty_panels','woodlight',a,b,z+.13,z+.725,.035)
  seats=[chair(g,s)for s in L['seats']]
  seats.append(chair(g,dict(centre=L['teacherSeat'],target=xy([251,590]),floor=0),True))
  x,y=L['teacherDesk'];g.box('teaching_lectern_cabinet','woodlight',(x,y,.54),(.98,.65,1.08));g.box('lectern_dark_worktop','top',(x,y,1.11),(1.02,.69,.06));g.box('lectern_monitor_foot','frame',(x,y,1.15),(.24,.20,.025));g.tube('lectern_monitor_stand','frame',(x,y,1.15),(x,y,1.32),.025);g.box('lectern_monitor','screen',(x,y,1.46),(.48,.065,.30))
  a,b=point([251,667]),point([345,667]);span(g,'front_projection_screen_frame','edge',a+Vector((0,.13)),b+Vector((0,.13)),.90,3.35,.10);span(g,'front_projection_screen','projection',a+Vector((0,.19)),b+Vector((0,.19)),.99,3.25,.025)
  for aa,bb in [([196,626],[245,665]),([349,665],[397,625])]:
   a,b=point(aa),point(bb);span(g,'front_black_teaching_displays','screen',a+Vector((0,.16)),b+Vector((0,.16)),1.95,3.15,.075)
  g.prism('complete_continuous_ceiling','ceiling',L['outline'],HEIGHT,.13)
  # Clipped slat polygons cover the whole ceiling field without artificialholes.
  from mathutils.geometry import tessellate_polygon
  # Slats run along nativeX. Outline scanline intersections are computed here
  # from a prepared room boundary through straightline clipping.
  def crossings(y):
   xs=[]
   for a,b in zip(L['outline'],L['outline'][1:]+L['outline'][:1]):
    if(a[1]<=y<b[1])or(b[1]<=y<a[1]):xs.append(a[0]+(y-a[1])*(b[0]-a[0])/(b[1]-a[1]))
   return sorted(xs)
  miny=min(p[1]for p in L['outline']);maxy=max(p[1]for p in L['outline'])
  for i in range(math.ceil((maxy-miny)/.15)):
   y=miny+.06+i*.15;cs=crossings(y)
   for a,b in zip(cs[::2],cs[1::2]):g.box('photo_continuous_timber_ceiling_slats','woodlight',((a+b)/2,y,HEIGHT-.055),(b-a,.042,.11))
  for x,y in [xy([210,330]),xy([390,330]),xy([210,460]),xy([390,460]),xy([230,590]),xy([370,590])]:g.box('below_ceiling_light_housings','frame',(x,y,HEIGHT-.085),(.18,.18,.14));g.box('below_ceiling_light_diffusers','light',(x,y,HEIGHT-.161),(.14,.14,.025))
  for px,py in [(298,540),(298,355)]:
   x,y=xy([px,py]);g.tube('projector_hangers','metal',(x,y,HEIGHT+.015),(x,y,3.83),.028);g.box('photo_ceiling_projectors','frame',(x,y,3.78),(.54,.42,.18));g.tube('projector_lenses','metal',(x,y-.20,3.78),(x,y-.245,3.78),.055)
  x,y=xy([407,546]);g.tube('relay_display_ceiling_mount','frame',(x,y,HEIGHT+.01),(x,y,3.28),.035);g.box('photo_suspended_relay_display','screen',(x,y,3.05),(.96,.09,.58))
  objects=g.finish()
  for o in objects:o['roomCode']='MAR.1.08';o['destinationCollection']=COLLECTION;o['scope']='IndependenthistoricalMarshallroom;estimatedtiers,not2026surveyorgeographicregistration'
  return scene,col,objects,dict(seats=seats,supports=supports),g.solid_proof
 def tree(objects):
  vs=[];fs=[];owners=[]
  for o in objects:
   if o.type!='MESH':continue
   off=len(vs);vs.extend(o.matrix_world@v.co for v in o.data.vertices);fs.extend(tuple(off+i for i in p.vertices)for p in o.data.polygons);owners.extend([o.name]*len(o.data.polygons))
  return BVHTree.FromPolygons(vs,fs),owners
 def inside(x,y):
  flag=False;ring=L['outline']
  for a,b in zip(ring,ring[1:]+ring[:1]):
   if(a[1]>y)!=(b[1]>y)and x<(b[0]-a[0])*(y-a[1])/(b[1]-a[1])+a[0]:flag=not flag
  return flag
 def body_volume_checks(objects,floor):
  """Clip actual saved world triangles through full route body volumes.

  Every0.12mcell follows its physical stair/floor level. Vertical bounds cover
  thin tabletops as well as chair backs; floor/riser surfaces are separately
  verified by the support rays,not counted as furniture obstructions.
  """
  def clip(poly,axis,value,positive):
   if not poly:return[]
   result=[];a=poly[-1];av=(a[axis]-value)*positive
   for b in poly:
    bv=(b[axis]-value)*positive
    if(av>=0)!=(bv>=0):result.append(a+(b-a)*(av/(av-bv)))
    if bv>=0:result.append(b)
    a,av=b,bv
   return result
  surfaces=[]
  for o in objects:
   if any(k in o.name for k in ['base_floor','stepped_terraces','access_steps','ceiling','light','projector']):continue
   o.data.calc_loop_triangles()
   for tri in o.data.loop_triangles:
    vs=[o.matrix_world@o.data.vertices[i].co for i in tri.vertices];surfaces.append((o.name,vs,[min(v[a]for v in vs)for a in range(3)],[max(v[a]for v in vs)for a in range(3)]))
  cells=[];candidate_count=0
  for pp,qq in L['principalRoutes']:
   a,b=point(pp),point(qq);count=math.ceil((b-a).length/.12);u=(b-a).normalized();n=Vector((-u.y,u.x))
   for i in range(count):
    aa,bb=a.lerp(b,i/count),a.lerp(b,(i+1)/count);c=(aa+bb)/2;hit=floor.ray_cast(Vector((*c,1.5)),Vector((0,0,-1)),1.7);assert hit[0]is not None;z=hit[0].z
    corners=[p+n*k for p in [aa,bb]for k in [-.22,.22]];lo=[min(p.x for p in corners)+1e-6,min(p.y for p in corners)+1e-6,z+.04];hi=[max(p.x for p in corners)-1e-6,max(p.y for p in corners)-1e-6,z+2.10]
    # All current principal routes are axis aligned.
    assert abs(u.x)<1e-5 or abs(u.y)<1e-5
    for owner,poly,mn,mx in surfaces:
     if any(mx[j]<=lo[j]or mn[j]>=hi[j]for j in range(3)):continue
     candidate_count+=1;q=poly
     for j in range(3):q=clip(q,j,lo[j],1);q=clip(q,j,hi[j],-1)
     assert not q,('ActualMeshInRouteBodyVolume',pp,qq,owner,[list(p)for p in q])
    cells.append(dict(sourceEndpoints=[pp,qq],start=list(aa),end=list(bb),width=.44,floorZ=z,verticalRange=[z+.04,z+2.10]))
  return dict(method='Allactualworldmeshtrianglesclippedtofull0.44mwide0.04–2.10mbodyvolumescellsfollowingphysicalfloorandstairs',cellCount=len(cells),eligibleTriangles=len(surfaces),candidateTriangles=candidate_count,totalIntersections=0,cells=cells)
 def checks(objects,R):
  floor,names=tree([o for o in objects if any(k in o.name for k in ['base_floor','stepped_terraces','access_steps'])]);tops,_=tree([o for o in objects if o.name==PREFIX+'continuous_dark_tabletops']);ceil,_=tree([o for o in objects if o.name==PREFIX+'complete_continuous_ceiling']);solid,owners=tree([o for o in objects if not any(k in o.name for k in ['base_floor','stepped_terraces','access_steps','ceiling','light','projector'])])
  feet=[]
  for kind,points in [('chair',[(p,s['floor'])for s in R['seats']for p in s['feet']]),('table',[(s['foot'],s['floor'])for s in R['supports']])]:
   for p,z in points:
    h=floor.ray_cast(Vector((p[0],p[1],z+.10)),Vector((0,0,-1)),.18);assert h[0]is not None and abs(h[0].z-z)<1e-4,('Unsupportedfoot',kind,p,z,h)
    feet.append(dict(kind=kind,point=p,actualFloorZ=h[0].z,actualContactZ=p[2]-(.03 if kind=='chair'else.0125)))
  contacts=[]
  for s in R['supports']:
   p=s['top'];h=tops.ray_cast(Vector((p[0],p[1],p[2]-.04)),Vector((0,0,1)),.06);assert h[0]is not None;contacts.append([p[0],p[1],h[0].z])
  doors=[]
  for door in L['doors']:
   a,b=point(door['a']),point(door['b']);c=(a+b)/2
   for shift in [-.30,0,.30]:
    for z in [.05,.65,1.2,2.2]:
     h=solid.ray_cast(Vector((c.x+shift,c.y-.30,z)),Vector((0,1,0)),.60);assert h[0]is None,('Doorblocked',door['id'],shift,z,owners[h[2]]if h[2]is not None else None);doors.append([door['id'],shift,z])
  coverage=[];step=.22
  for i in range(math.floor(min(p[0]for p in L['outline'])/step),math.ceil(max(p[0]for p in L['outline'])/step)):
   for j in range(math.floor(min(p[1]for p in L['outline'])/step),math.ceil(max(p[1]for p in L['outline'])/step)):
    x,y=(i+.5)*step,(j+.5)*step
    if not inside(x,y):continue
    h=ceil.ray_cast(Vector((x,y,2.0)),Vector((0,0,1)),3);assert h[0]is not None and abs(h[0].z-HEIGHT)<1e-5;coverage.append([x,y,h[0].z])
  routes=[];width=.44
  for pp,qq in L['principalRoutes']:
   a,b=point(pp),point(qq);u=(b-a).normalized();n=Vector((-u.y,u.x));count=math.ceil((b-a).length/.12)
   for i in range(count+1):
    c=a.lerp(b,i/count);h=floor.ray_cast(Vector((*c,1.5)),Vector((0,0,-1)),1.7);assert h[0]is not None
    z=h[0].z;head=ceil.ray_cast(Vector((*c,z+.05)),Vector((0,0,1)),5);assert head[0]is not None and head[0].z-z>2.10
    for height in [.10,.45,.70,1.15,1.70,2.05]:
     p=c-n*width/2;hit=solid.ray_cast(Vector((*p,z+height)),Vector((*n,0)),width);assert hit[0]is None,('Routeblocked',pp,qq,list(c),z,height,owners[hit[2]]if hit[2]is not None else None)
    routes.append(dict(position=list(c),actualFloorZ=z,headroom=head[0].z-z))
  # Actual wall apertures are checked independently of their glazing material.
  walls,_=tree([o for o in objects if any(k in o.name for k in ['perimeter_walls','sill_walls','head_walls','door_lintels'])]);openings=[]
  for w in L['windows']:
   a,b=point(w['a']),point(w['b']);c=(a+b)/2;d=(b-a).normalized();n=Vector((-d.y,d.x))
   for f in [.25,.5,.75]:
    z=w['sill']+(w['head']-w['sill'])*f;hit=walls.ray_cast(Vector((*(c-n*.3),z)),Vector((*n,0)),.6);assert hit[0]is None;openings.append([w['id'],z])
  assert len(coverage)>2500
  return dict(wholeRouteSavedMeshSweep=body_volume_checks(objects,floor),studentSeatCount=83,teacherSeatCount=1,printedCapacity=87,visibleSymbolDiscrepancy=4,footSupportProbes=feet,tableSupportUndersideContacts=contacts,doorwayClearRays=doors,doorClearWidths=[(point(d['b'])-point(d['a'])).length-.05 for d in L['doors']],windowWallApertureRays=openings,continuousCeilingCoverage=dict(spacingMetres=step,probeCount=len(coverage),missCount=0,undersideHeight=HEIGHT,pointDigest=hashlib.sha256(json.dumps(coverage).encode()).hexdigest()),clearRouteProbes=routes,principalRouteBodyWidth=width,minimumRouteHeadroom=min(r['headroom']for r in routes),routeInterpretation='0.44mbodysampledacrossactualsurfacesat6heightswithphysicalstairs;notacertifiedroutewidth,accessibilityoregressassessment',closedGeometry=True)
 def render(scene):
  bpy.context.window.scene=scene;w=bpy.data.worlds.new(PREFIX+'previewWorld');w.use_nodes=True;w.node_tree.nodes['Background'].inputs[0].default_value=(.75,.79,.83,1);w.node_tree.nodes['Background'].inputs[1].default_value=.4;scene.world=w
  lights=[]
  for px,py in [(240,360),(395,390),(260,570),(400,570)]:
   ld=bpy.data.lights.new(PREFIX+'previewArea','AREA');ld.energy=550;ld.shape='DISK';ld.size=4;o=bpy.data.objects.new(ld.name,ld);scene.collection.objects.link(o);o.location=(*xy([px,py]),HEIGHT-.24);lights.append((o,ld))
  cd=bpy.data.cameras.new(PREFIX+'previewCamera');cam=bpy.data.objects.new(cd.name,cd);scene.collection.objects.link(cam);scene.camera=cam;cd.lens=19;cd.clip_end=100
  scene.render.engine='CYCLES';scene.cycles.samples=16;scene.cycles.use_denoising=True;scene.render.resolution_x=1200;scene.render.resolution_y=900;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='AgX';views=[]
  for name,pp,tp,z,tz,label in [('default',[465,315],[278,610],2.70,1.55,'MAR.1.08阶梯马蹄教室与教学端'),('front',[298,635],[298,365],1.78,1.90,'MAR.1.08完整阶梯座席与木条天花')]:
   p,t=point(pp),point(tp);cam.location=(*p,z);cam.rotation_euler=(Vector((*t,tz))-cam.location).to_track_quat('-Z','Y').to_euler();scene.render.filepath=str(OUT/('built-'+name+'.png'));bpy.ops.render.render(write_still=True);views.append(dict(name='mar-108-'+name+'-interior',code='MAR',spaceId='mar-108',label=label,view=dict(position=[p.x,z,-p.y],target=[t.x,tz,-t.y],fov=70.61)))
  bpy.data.objects.remove(cam,do_unlink=True);bpy.data.cameras.remove(cd)
  for o,ld in lights:bpy.data.objects.remove(o,do_unlink=True);bpy.data.lights.remove(ld)
  return views
 def run():
  assert sha(BASE)==SHA;bpy.ops.wm.open_mainfile(filepath=str(BASE));update();expected=accepted_fingerprints(ROOT/'result/blender/stage227',SHA);assert len(expected)==7970 and{o.name for o in bpy.data.objects}==set(expected)
  mats={m.name:material_fingerprint(m)for m in bpy.data.materials};mods={o.name:stable_modifiers(o)for o in bpy.data.objects};rooms=rooms_state();assert len(rooms)==25;room_count=len(set(n for r in rooms for n in r['objects']));assert room_count==964;members={o.name:sorted(c.name for c in o.users_collection)for o in bpy.data.objects};vis={o.name:o.hide_render for o in bpy.data.objects};props={o.name:dict(o.items())for o in bpy.data.objects};scenes={s.name:sorted(o.name for o in s.objects)for s in bpy.data.scenes}
  scene,col,owned,records,solid=build();update();proof=checks(owned,records);views=render(scene)
  scope='依据LSE同房号历史平面与实照建立MAR.1.08独立阶梯马蹄形教室。平面控制完整周界、两处前门、马蹄桌、中央四席、前侧分组与右长排；实照控制浅木挡板、深灰桌面、黑网背椅、木条天花和教学设备。可辨座椅83席，与图示容量87存在4席差异。比例、台阶、层高、窗高和隐藏构造为估算；两图拍摄年代未知，不作2026现状、全楼覆盖或地理楼层配准。'
  space=dict(code='MAR',id='mar-108',label='MAR.1.08阶梯教室',collection=COLLECTION,gallery=views[0]['name'],interiorView=views[0]['view'],interiorStudy=dict(kind='room-sample',label='MAR.1.08阶梯教室',scope=scope),scope=scope);col['authoringRecord']=json.dumps(space,ensure_ascii=False)
  fingerprints={o.name:object_fingerprint(o)for o in owned};bindings={o.name:[m.name for m in o.data.materials]for o in owned};component=OUT/'component.blend';bpy.data.libraries.write(str(component),{col,scene},fake_user=True,compress=True)
  bpy.ops.wm.open_mainfile(filepath=str(BASE));update()
  with bpy.data.libraries.load(str(component),link=False)as(src,dst):dst.collections=[COLLECTION]
  saved=dst.collections[0];s=bpy.data.scenes.new(SCENE);s.collection.children.link(saved);bpy.context.window.scene=s;update();assert checks(list(saved.all_objects),records)==proof
  assert all(object_fingerprint(bpy.data.objects[n])==v for n,v in fingerprints.items());assert all(object_fingerprint(bpy.data.objects[n])==v for n,v in expected.items());assert all(material_fingerprint(bpy.data.materials[n])==v for n,v in mats.items());assert all(stable_modifiers(bpy.data.objects[n])==v for n,v in mods.items());assert rooms_state()==rooms;assert all(sorted(c.name for c in bpy.data.objects[n].users_collection)==v for n,v in members.items());assert all(bpy.data.objects[n].hide_render==v for n,v in vis.items());assert all(dict(bpy.data.objects[n].items())==v for n,v in props.items());assert all(sorted(o.name for o in bpy.data.scenes[n].objects)==v for n,v in scenes.items());assert not any(n in bpy.data.scenes['00_CAMPUS_COMPLETE'].objects for n in fingerprints);assert sha(BASE)==SHA;assert not any(o.type in{'LIGHT','CAMERA'}for o in saved.all_objects)
  verification=dict(savedComponentReopened=True,sourceFingerprintMethod='Acceptedstage227fingerprintsboundtoverifiednativeSHA;all7970sourceobjectscheckedaftersavedappend',independentAcceptedObjectsVerified=len(expected),allOriginalMaterialNodesVerified=len(mats),allOriginalModifierStacksVerified=len(mods),oldSpacesPreserved=len(rooms),oldSpaceUniqueObjectsPreserved=room_count,allOriginalMembershipsPropertiesScenesUnchanged=True,allSourceGeometryUVTransformsBindingsUnchanged=True,allOriginalVisibilityUnchanged=True,noNewRoomObjectInCampus=True,sourceNativeShaUnchanged=True,sourcePhotoNotUsedAsTexture=True,noExportedPreviewLightsOrCameras=True,triangles=sum(len(p.vertices)-2 for o in saved.all_objects for p in o.data.polygons))
  audit=dict(version=228,building='MAR',baselinePath=str(BASE.relative_to(ROOT)),baselineSha256=SHA,componentPath=str(component.relative_to(ROOT)),componentSha256=sha(component),targetCollection=COLLECTION,destinationCollection=COLLECTION,collectionSpec=dict(kind='independent-room',name=COLLECTION,scene=SCENE),space=space,report=dict(space=space),addedObjects=list(fingerprints),archivedObjects=[],changedObjects=[],addedFingerprints=fingerprints,replacementMaterialBindings=bindings,sourceManifest='data/collections/mar108-room228/sources.json',planLayout='data/collections/mar108-room228/layout.json',studentSeatCount=83,teacherSeatCount=1,printedPlanCapacity=87,scaleMetresPerPixel=SCALE,roomAreaSquareMetres=L['roomAreaSquareMetres'],estimatedCeilingHeight=HEIGHT,gallerySuggestions=views,checks=proof,solidProof=solid,verification=verification,previews=['built-default.png','built-front.png'],beforeEvidence=[PLAN,PHOTO],previewLighting='Fourtemporaryarealightsat4.26mbelowcomplete4.50mceiling;noneexported',limitations=json.loads((DATA/'sources.json').read_text())['limitations'])
  (OUT/'audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n');print('MAR108_ROOM228_READY',len(fingerprints),verification,flush=True)
 def verify_saved_component():
  audit=json.loads((OUT/'audit.json').read_text());component=OUT/'component.blend'
  assert sha(BASE)==SHA and sha(component)==audit['componentSha256']
  bpy.ops.wm.open_mainfile(filepath=str(component));update()
  assert SCENE in bpy.data.scenes and COLLECTION in bpy.data.scenes[SCENE].collection.children
  assert {o.name:object_fingerprint(o)for o in bpy.data.objects}==audit['addedFingerprints']
  assert set(o.name for o in bpy.data.scenes[SCENE].objects)==set(audit['addedObjects'])
  assert not any(o.type in{'LIGHT','CAMERA'}for o in bpy.data.objects)
  assert len(bpy.data.images)==0 or all(i.source!='FILE'for i in bpy.data.images)
  assert sha(BASE)==SHA
  # Convert the collection library to a normal standalone room document.
  # Only authored room data are loaded here;the campus is not in this file.
  bpy.context.window.scene=bpy.data.scenes[SCENE]
  for scene in list(bpy.data.scenes):
   if scene.name!=SCENE and not scene.objects:bpy.data.scenes.remove(scene)
  bpy.ops.wm.save_as_mainfile(filepath=str(component),compress=True)
  audit['componentSha256']=sha(component)
  bpy.ops.wm.open_mainfile(filepath=str(component));update()
  assert bpy.context.scene.name==SCENE
  assert {o.name:object_fingerprint(o)for o in bpy.data.objects}==audit['addedFingerprints']
  assert sha(BASE)==SHA
  audit['verification']['componentOpenedAsStandaloneMainfile']=True
  audit['verification']['componentStandaloneScene']=SCENE
  audit['verification']['componentStandaloneObjectCount']=len(bpy.data.objects)
  (OUT/'audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n')
  print('MAR108_STANDALONE_REOPENED',len(bpy.data.objects),audit['componentSha256'],flush=True)
 if __name__=='__main__':
  if not REVIEW_SAVED_ONLY:run()
  verify_saved_component()
