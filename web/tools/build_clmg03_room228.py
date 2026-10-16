"""CLM.G.03 independent historical room; fixed configuration, no CLI options.

Plan controls the fourteen tablet chairs and irregular perimeter. Photo controls
white-shell/black-seat finishes and teaching equipment. All metric dimensions
are estimates. The accepted complete campus is opened read-only, never saved.
"""
from pathlib import Path
import hashlib,json,math,sys
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'result/blender/clmg03-room228'
DATA=ROOT/'data/collections/clmg03-room228'
BASE=ROOT/'result/blender/LSE_campus_detailed_v227.blend'
SHA='fba3318e79206e20fc9208336fb5e354ffbfcfe4721d31ad7a6a2489511204a0'
COLLECTION='CLMG03_ROOM228_study'
SCENE='ROOM228_CLMG03'
PREFIX='CLMG03_R228_'
PLAN='data/collections/interiors/images/68b24b5feedf_CLM.G.03.GIF'
PHOTO='data/collections/interiors/images/0d8ef8fbc729_CLM.G.03.jpg'
SCALE=.0145
HEIGHT=3.12

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def prepare():
 from shapely.geometry import Polygon,box
 from PIL import Image,ImageDraw
 DATA.mkdir(parents=True,exist_ok=True);OUT.mkdir(parents=True,exist_ok=True)
 def p(q):return[(q[0]-300)*SCALE,(240-q[1])*SCALE]
 # Window recess is a distinct bay, not an extra door or a rectangular room.
 outline=[[94,53],[179,53],[179,83],[375,83],[375,63],[498,63],[498,70],[506,70],[506,355],[494,355],[494,415],[94,415],[94,355],[38,355],[38,80],[94,80]]
 poly=Polygon([p(q)for q in outline]);assert poly.is_valid
 seats=[]
 for i,x in enumerate([201,242,282,323,363,404]):seats.append(dict(id='rear'+str(i+1),pixel=[x,107],target=[x,280]))
 for side,x,target in [('left',117,300),('right',474,300)]:
  for i,y in enumerate([175,217,260]):seats.append(dict(id=side+str(i+1),pixel=[x,y],target=[target,y]))
 seats.extend([dict(id='rear-left-angle',pixel=[144,101],target=[220,290]),dict(id='rear-right-angle',pixel=[463,108],target=[390,290])])
 tiles=[];grid=[];x0,y0,x1,y1=poly.bounds
 def parts(v):return[v]if v.geom_type=='Polygon'else[g for g in v.geoms if g.geom_type=='Polygon']
 for i in range(math.floor(x0/.50),math.ceil(x1/.50)):
  for j in range(math.floor(y0/.50),math.ceil(y1/.50)):
   q=poly.intersection(box(i*.5,j*.5,(i+1)*.5,(j+1)*.5))
   if not q.is_empty:tiles.extend(dict(outline=list(t.exterior.coords)[:-1],material='carpet'+['A','B','C'][(i+2*j)%3])for t in parts(q)if t.area>1e-7)
 for axis,lo,hi in [(0,x0,x1),(1,y0,y1)]:
  for i in range(math.ceil(lo/.6),math.floor(hi/.6)+1):
   v=i*.6;q=poly.intersection(box(v-.002,y0-1,v+.002,y1+1)if axis==0 else box(x0-1,v-.002,x1+1,v+.002))
   if not q.is_empty:grid.extend(list(t.exterior.coords)[:-1]for t in parts(q)if t.area>1e-7)
 layout=dict(room='CLM.G.03',outlinePixels=outline,outline=[p(q)for q in outline],scaleMetresPerPixel=SCALE,scaleBasis='Estimated0.0145m/pixel from70px door approximately1.015m and40px tablet-chair pitch approximately0.58m;no printed dimension',roomAreaSquareMetres=poly.area,studentSeatCount=14,seats=seats,door=dict(a=[506,285],b=[506,355],hinge=[506,355],openTip=[443,355]),windows=[dict(id='left-recess',a=[38,80],b=[38,355])],teacherDesk=dict(a=[140,288],b=[267,356]),teacherSeat=[205,374],ceilingGridParts=grid,carpetTiles=tiles,lights=[[205,200],[400,200],[205,335],[400,335]],principalRoutes=[[[506,320],[420,320]],[[420,320],[320,320]],[[320,320],[320,170]],[[320,320],[320,375]]])
 (DATA/'layout.json').write_text(json.dumps(layout,ensure_ascii=False,indent=2)+'\n')
 source=json.loads((ROOT/'data/collections/interiors/sources.json').read_text());refs=[r for r in source['sources']if r.get('local_path')in[PLAN,PHOTO]];assert len(refs)==2
 manifest=dict(room='CLM.G.03',sources=refs,planSha256=sha(ROOT/PLAN),photoSha256=sha(ROOT/PHOTO),sameRoomPairVerified=True,bothImagesActualNotPlaceholder=True,sourceInterpretation=['Plan markedG.03 has14tablet-chair symbols:rear6,angled corners2,left3,right3,plus teaching desk and teacher chair.','Photo shows white chair shells,black seats,individual white writing tablets,black metal legs,grey-brown patterned carpet,wall-mounted display between two whiteboards,and AV desk beside a deep window reveal.','Teaching end is plan bottom,window wall is plan left,entrance is plan right-bottom. Top recesses and entrance step are retained.','The long parallel strokes at plan bottom are treated as the teaching-board zone,not a second window;the matching photograph shows boards and TV on this wall.','Model follows the plan seating positions;the close photograph does not establish all14positions or exact tablet handedness.','Left parallel jamb lines are modeled as one deep continuous window bay with estimated mullions and solid reveals;not extra doors.'],limitations=['Historical plan creation and photograph capture dates unknown;retrieved2026-09-12 and page refresh2022 do not prove current2026 use or contemporaneous sources.','Scale0.0145m/pixel,ceiling3.12m,door/window vertical dimensions,mullion spacing,deep reveal geometry,hidden finishes and furniture dimensions are estimates.','14is the counted historical diagram seating arrangement,not certified current capacity or egress/accessibility approval.','Photo captures only part of the room;rear/right finishes,door leaf construction and complete ceiling panel layout are inferred.','Plan shows a rectangular teaching desk;photo shows an equipment workstation at the window-side teaching corner.Model retains plan desk footprint with photo-informed workstation equipment.','No ceiling projector is visible in the photograph;display is wall mounted.The visible linear suspended lamp type is repeated at estimated positions below a complete ceiling.','Independent Clement House room,no geographic campus/floor registration,no2026as-built claim.','Source photographs remain private references and are not used as exported textures.'])
 (DATA/'sources.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
 im=Image.open(ROOT/PLAN).convert('RGB');d=ImageDraw.Draw(im);d.line(outline+[outline[0]],fill=(190,30,30),width=2)
 for s in seats:
  x,y=s['pixel'];d.ellipse((x-2,y-2,x+2,y+2),fill=(30,50,200))
 im.save(DATA/'registered-plan.png');print('CLMG03_LAYOUT_READY',poly.area,len(seats),flush=True)

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
 def point(p):return Vector(((p[0]-300)*SCALE,(240-p[1])*SCALE))
 def update():
  for scene in bpy.data.scenes:
   for layer in scene.view_layers:layer.update()
 def material(g,key,color,rough=.7,metal=0):
  m=bpy.data.materials.new(PREFIX+key);m.use_nodes=True;m.diffuse_color=(*color,1);n=m.node_tree.nodes['Principled BSDF'];n.inputs['Base Color'].default_value=m.diffuse_color;n.inputs['Roughness'].default_value=rough;n.inputs['Metallic'].default_value=metal;g.materials[key]=m
 def span(g,family,key,a,b,lo,hi,depth=.14):
  a,b=Vector(a),Vector(b);d=b-a;c=(a+b)/2;g.box(family,key,(*c,(lo+hi)/2),(d.length,depth,hi-lo),math.atan2(d.y,d.x))
 def chair(g,p,target,teacher=False):
  p,t=Vector(p),Vector(target);angle=math.atan2(t.y-p.y,t.x-p.x)+math.pi/2;c,s=math.cos(angle),math.sin(angle)
  def at(x,y,z):return(p.x+c*x-s*y,p.y+s*x+c*y,z)
  g.box('teacher_seat'if teacher else'black_student_seats','black',at(0,0,.46),(.43,.42,.055),angle)
  if teacher:
   g.box('teacher_mesh_style_back','black',at(0,.235,.75),(.47,.065,.48),angle)
   for z in [.58,.64,.70,.76,.82,.88]:g.box('teacher_back_horizontal_ribs','frame',at(0,.194,z),(.43,.02,.015),angle)
   feet=[];g.tube('teacher_pedestal','steel',at(0,0,.09),at(0,0,.435),.026)
   for i in range(5):
    a=i*math.tau/5;x,y=.27*math.cos(a),.27*math.sin(a);g.tube('teacher_castor_wheels','black',at(x-.018,y,.028),at(x+.018,y,.028),.028);g.tube('teacher_spoke_base','black',at(0,0,.11),at(x,y,.055),.022);feet.append(list(at(x,y,0)))
   for x in [-.26,.26]:g.tube('teacher_arm_posts','black',at(x,0,.47),at(x,0,.68),.018);g.box('teacher_armrests','black',at(x,-.02,.69),(.055,.31,.035),angle)
   return dict(teacher=True,feet=feet)
  # One closed curved shell around a genuine circular handhold aperture.
  zcentre=.755;radius=.042
  angles=sorted(set([i*math.tau/40 for i in range(40)]+[math.atan2(z-zcentre,x)%math.tau for x in [-.235,.235]for z in [.50,.91]]));n=len(angles);inner=[];outer=[]
  for a in angles:
   dx,dz=math.cos(a),math.sin(a);limits=[]
   if abs(dx)>1e-8:limits.append(.235/abs(dx))
   if dz>1e-8:limits.append((.91-zcentre)/dz)
   if dz<-1e-8:limits.append((.50-zcentre)/dz)
   r=min(limits);inner.append((radius*dx,zcentre+radius*dz));outer.append((r*dx,zcentre+r*dz))
  vertices=[]
  for depth in [0,.029]:
   for ring in [inner,outer]:
    for x,z in ring:vertices.append(at(x,.23-.038*(x/.235)**2+depth,z))
  faces=[]
  for i in range(n):
   j=(i+1)%n;f=(i,n+i,n+j,j);faces.extend([f,tuple(reversed(tuple(k+2*n for k in f))),(n+j,n+i,3*n+i,3*n+j),(i,j,2*n+j,2*n+i)])
  g.add('white_shell_back_with_circular_handhold','shell',vertices,faces)
  g.box('white_shell_seat_rim','shell',at(0,0,.432),(.46,.44,.025),angle)
  feet=[]
  for x in [-.19,.19]:
   for y in [-.18,.18]:
    foot=at(x*1.14,y*1.2,0);g.tube('student_floor_contact_pads','black',foot,at(x*1.14,y*1.2,.03),.018);g.tube('student_black_metal_legs','frame',at(x*1.14,y*1.2,.025),at(x,y,.43),.014);feet.append(list(foot))
   g.tube('student_back_support','frame',at(x,.15,.43),at(x,.22,.65),.012)
  # Separate tablet writing surface and support arm; no phantom table legs.
  tablet=[[-.23,-.50],[.28,-.50],[.31,-.45],[.31,-.23],[.22,-.18],[-.23,-.23]]
  g.prism('individual_white_writing_tablets','tablet',[at(x,y,0)[:2]for x,y in tablet],.715,.026)
  g.tube('tablet_side_support','frame',at(.25,.08,.43),at(.25,.08,.685),.018);g.tube('tablet_top_support','frame',at(.25,.08,.685),at(.25,-.37,.708),.018)
  g.box('tablet_black_hinge','black',at(.25,-.18,.705),(.09,.15,.035),angle)
  return dict(teacher=False,feet=feet,tabletSupportTop=list(at(.25,-.37,.715)))
 def build():
  scene=bpy.data.scenes.new(SCENE);col=bpy.data.collections.new(COLLECTION);scene.collection.children.link(col);col['roomSample']=True;col['roomCode']='CLM.G.03';g=RoomGeometry(col,PREFIX)
  for k,c,r,m in [('plaster',(.77,.76,.70),.86,0),('shell',(.72,.73,.66),.62,0),('black',(.015,.019,.017),.68,0),('frame',(.035,.042,.039),.42,.35),('steel',(.44,.47,.44),.32,.65),('tablet',(.84,.82,.73),.54,0),('carpetA',(.22,.22,.19),.95,0),('carpetB',(.26,.25,.21),.95,0),('carpetC',(.18,.20,.20),.95,0),('ceiling',(.79,.79,.74),.88,0),('joint',(.72,.72,.67),.9,0),('whiteframe',(.78,.80,.75),.5,0),('glassroom',(.29,.34,.35),.19,0),('blindroom',(.40,.41,.38),.87,0),('doorwood',(.38,.29,.19),.7,0),('boardwhite',(.88,.87,.80),.43,0),('screen',(.008,.011,.012),.24,0),('cabinet',(.57,.59,.54),.67,0)]:material(g,k,c,r,m)
  g.prism('complete_plan_floor','carpetA',L['outline'],-.14,.137)
  for tile in L['carpetTiles']:g.prism('patterned_carpet_tiles',tile['material'],tile['outline'],-.003,.003)
  da,db=point(L['door']['a']),point(L['door']['b']);ws=[(point(w['a']),point(w['b']))for w in L['windows']]
  for a,b in zip(L['outline'],L['outline'][1:]+L['outline'][:1]):
   a,b=Vector(a),Vector(b);d=b-a;events=[(0.,1.,'wall')]
   for u,v,kind in [(da,db,'door')]+[(u,v,'window')for u,v in ws]:
    if abs(d.cross(u-a))>.0001 or abs(d.cross(v-a))>.0001:continue
    lo,hi=sorted(((u-a).dot(d)/d.length_squared,(v-a).dot(d)/d.length_squared))
    if lo<-.001 or hi>1.001:continue
    events=[(0,lo,'wall'),(lo,hi,kind),(hi,1,'wall')]
   for s,e,kind in events:
    if e-s<1e-7:continue
    p,q=a+d*s,a+d*e
    if kind!='door':span(g,'perimeter_skirting','whiteframe',p,q,0,.105,.04)
    if kind=='wall':span(g,'complete_perimeter_walls','plaster',p,q,.105,HEIGHT)
    elif kind=='door':span(g,'real_door_lintel_wall','plaster',p,q,2.25,HEIGHT)
    else:span(g,'window_sill_wall','plaster',p,q,.105,.88);span(g,'window_upper_wall','plaster',p,q,2.90,HEIGHT)
  a,b=ws[0];u=(b-a).normalized();inward=Vector((1,0))
  for p in [a,b]:span(g,'window_jamb_frames','whiteframe',p-u*.026,p+u*.026,.88,2.91,.10)
  for z in [.88,1.02,2.88]:span(g,'window_horizontal_frames','whiteframe',a,b,z,z+.035,.09)
  for t in [.25,.5,.75]:
   p=a.lerp(b,t);span(g,'window_mullions','whiteframe',p-u*.023,p+u*.023,.92,2.90,.09)
  span(g,'window_glass','glassroom',a,b,.92,2.88,.016)
  span(g,'deep_window_sill','whiteframe',point([66,80]),point([66,355]),.86,.91,.812)
  # Recess shelf extends inward only, leaving all chair feet on the main floor.
  # Four broad grey roller blinds stop at mid-height as photographed.
  for i in range(4):
   p,q=a.lerp(b,i/4),a.lerp(b,(i+1)/4);span(g,'roller_blind_fabric','blindroom',p+inward*.085,q+inward*.085,1.93,2.88,.018);span(g,'roller_blind_lower_rails','whiteframe',p+inward*.085,q+inward*.085,1.92,1.945,.028)
  du=(db-da).normalized()
  for p in [da,db]:span(g,'door_jamb_frames','doorwood',p-du*.025,p+du*.025,0,2.28,.17)
  span(g,'door_header_frame','doorwood',da,db,2.23,2.28,.17)
  hinge,tip=point(L['door']['hinge']),point(L['door']['openTip']);span(g,'open_inward_door_leaf','doorwood',hinge,tip,.025,2.23,.045);h=hinge.lerp(tip,.88);g.tube('door_metal_handle','steel',(*h,.97),(*h,1.10),.013)
  # Teaching wall: separate whiteboards flank the actual wall-mounted TV.
  for a,b in [([107,410],[217,410]),([359,410],[441,410])]:
   a,b=point(a),point(b);span(g,'whiteboard_frames','whiteframe',a,b,.78,2.29,.045);span(g,'whiteboard_faces','boardwhite',a+Vector((0,.03)),b+Vector((0,.03)),.81,2.26,.018)
  a,b=point([225,410]),point([352,410]);span(g,'wall_display_black_frame','black',a,b,1.16,2.18,.08);span(g,'blank_teaching_display','screen',a+Vector((0,.048)),b+Vector((0,.048)),1.20,2.14,.016)
  c=point([289,407]);g.box('display_conference_camera','black',(*c,1.09),(.25,.09,.045));g.tube('display_camera_lens','glassroom',(c.x,c.y+.045,1.09),(c.x,c.y+.07,1.09),.018)
  ta,tb=point(L['teacherDesk']['a']),point(L['teacherDesk']['b']);tc=(ta+tb)/2;tw,td=abs(tb.x-ta.x),abs(tb.y-ta.y)
  g.box('teacher_AV_worktop','tablet',(*tc,.755),(tw,td,.045))
  deskfeet=[]
  for x in [tc.x-tw/2+.10,tc.x+tw/2-.10]:
   for y in [tc.y-td/2+.09,tc.y+td/2-.09]:g.box('teacher_desk_steel_legs','cabinet',(x,y,.36625),(.075,.075,.7325));deskfeet.append([x,y,0])
  g.box('AV_desk_front_modesty','cabinet',(tc.x,tc.y+.34,.43),(tw-.12,.035,.49));g.box('AV_computer_base','black',(tc.x-.25,tc.y,.795),(.30,.23,.035));g.tube('AV_monitor_support','frame',(tc.x-.25,tc.y,.81),(tc.x-.25,tc.y,1.03),.021);g.box('AV_monitor','screen',(tc.x-.25,tc.y,1.17),(.47,.06,.30));g.box('AV_keyboard','black',(tc.x-.25,tc.y-.28,.795),(.42,.14,.025));g.box('AV_control_unit','black',(tc.x+.48,tc.y+.08,.81),(.29,.25,.07))
  seats=[chair(g,point(s['pixel']),point(s['target']))for s in L['seats']];seats.append(chair(g,point(L['teacherSeat']),tc,True))
  g.prism('continuous_complete_ceiling','ceiling',L['outline'],HEIGHT,.08)
  for ring in L['ceilingGridParts']:g.prism('subtle_ceiling_panel_joints','joint',ring,HEIGHT-.003,.004)
  # Photo shows a high window reveal/soffit and hanging linear luminaires.
  for y in [110,285]:span(g,'window_reveal_soffit','plaster',point([40,y]),point([94,y]),2.98,HEIGHT,.18)
  for px in L['lights']:
   p=point(px)
   for dy in [-.47,.47]:g.tube('linear_lamp_suspension','steel',(p.x,p.y+dy,HEIGHT-.26),(p.x,p.y+dy,HEIGHT),.006)
   g.box('linear_lamp_housing','whiteframe',(*p,HEIGHT-.28),(.17,1.10,.045));g.box('linear_lamp_diffuser','light',(*p,HEIGHT-.307),(.13,1.04,.014))
  objects=g.finish()
  for o in objects:o['roomCode']='CLM.G.03';o['destinationCollection']=COLLECTION;o['scope']='Independent historical plan-layout classroom;estimated dimensions;no geographic registration or2026capacity claim'
  return scene,col,objects,dict(seats=seats,deskFeet=deskfeet,deskTop=.732,door=dict(a=list(da),b=list(db),clearWidth=(db-da).length-.05)),g.solid_proof

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
  floor,_=tree([o for o in objects if any(k in o.name for k in ['complete_plan_floor','patterned_carpet_tiles'])]);ceiling,_=tree([o for o in objects if o.name==PREFIX+'continuous_complete_ceiling']);solid,names=tree([o for o in objects if not any(k in o.name for k in ['complete_plan_floor','patterned_carpet_tiles','ceiling'])]);tablets,_=tree([o for o in objects if o.name==PREFIX+'individual_white_writing_tablets']);desk,_=tree([o for o in objects if o.name==PREFIX+'teacher_AV_worktop'])
  feet=[]
  for seat in R['seats']:
   for p in seat['feet']:
    hit=floor.ray_cast(Vector((p[0],p[1],.04)),Vector((0,0,-1)),.08);assert hit[0]is not None and abs(hit[0].z)<.001,('UnsupportedChairFoot',p);feet.append(dict(kind='teacher'if seat['teacher']else'student',point=p,floorZ=hit[0].z))
  contacts=[]
  for p in R['deskFeet']:
   f=floor.ray_cast(Vector((p[0],p[1],.04)),Vector((0,0,-1)),.08);assert f[0]is not None and abs(f[0].z)<.001
   t=desk.ray_cast(Vector((p[0],p[1],.71)),Vector((0,0,1)),.06);assert t[0]is not None and abs(t[0].z-.7325)<.001
   contacts.append(dict(foot=p,floorZ=f[0].z,worktopUnderside=t[0].z))
  tablet=[]
  for seat in R['seats']:
   if seat['teacher']:continue
   p=seat['tabletSupportTop'];h=tablets.ray_cast(Vector((p[0],p[1],.69)),Vector((0,0,1)),.05);assert h[0]is not None and abs(h[0].z-.715)<.001;tablet.append(list(h[0]))
  coverage=[];step=.20;xs=[p[0]for p in L['outline']];ys=[p[1]for p in L['outline']]
  for i in range(math.floor(min(xs)/step),math.ceil(max(xs)/step)):
   for j in range(math.floor(min(ys)/step),math.ceil(max(ys)/step)):
    x,y=(i+.5)*step,(j+.5)*step
    if not inside(x,y):continue
    h=ceiling.ray_cast(Vector((x,y,1.5)),Vector((0,0,1)),2);assert h[0]is not None and abs(h[0].z-HEIGHT)<.001,('CeilingHole',x,y);coverage.append([x,y,h[0].z])
  assert len(coverage)>500
  doorway=[];a,b=Vector(R['door']['a']),Vector(R['door']['b']);c=(a+b)/2;u=(b-a).normalized()
  for d in [-.22,0,.22]:
   for z in [.04,.65,1.20,2.1]:
    p=c+u*d+Vector((-.25,0));h=solid.ray_cast(Vector((*p,z)),Vector((1,0,0)),.5);assert h[0]is None,('DoorBlocked',d,z,names[h[2]]if h[2]is not None else'');doorway.append([d,z])
  walltree,wallnames=tree([o for o in objects if any(k in o.name for k in ['perimeter_walls','sill_wall','upper_wall','door_lintel'])]);window=[]
  for w in L['windows']:
   a,b=point(w['a']),point(w['b'])
   for t in [.2,.5,.8]:
    c=a.lerp(b,t)
    for z in [1.2,1.7,2.6]:
     h=walltree.ray_cast(Vector((c.x-.25,c.y,z)),Vector((1,0,0)),.5);assert h[0]is None,('UncutWindow',t,z);window.append([t,z])
  headroom=[]
  overhead,_=tree([o for o in objects if any(k in o.name for k in ['ceiling','lamp_housing','lamp_diffuser'])])
  for pa,pb in L['principalRoutes']:
   a,b=point(pa),point(pb);count=math.ceil((b-a).length/.15)
   for i in range(1,count+1):
    p=a.lerp(b,i/count);f=floor.ray_cast(Vector((*p,.04)),Vector((0,0,-1)),.08);assert f[0]is not None
    h=overhead.ray_cast(Vector((*p,.02)),Vector((0,0,1)),HEIGHT+.2);assert h[0]is not None and h[0].z>2.1;headroom.append(h[0].z)
  return dict(studentSeatCount=14,teacherSeatCount=1,deskCount=1,studentFootCount=56,teacherFootCount=5,footSupportProbes=feet,deskFloorAndWorktopContacts=contacts,tabletSupportContacts=tablet,continuousCeilingCoverage=dict(spacingMetres=step,probeCount=len(coverage),missCount=0,undersideHeight=HEIGHT,pointDigest=hashlib.sha256(json.dumps(coverage).encode()).hexdigest()),realDoorOpeningClearRays=doorway,doorClearWidth=R['door']['clearWidth'],realWindowWallApertureRays=window,wholeRouteSavedMeshSweep=swept_route_surfaces(objects),minimumRouteHeadroom=min(headroom),routeScope='Entrance to middle and teaching-side cross-aisle;0.44m geometric body corridor,not accessibility/egress certification',allAuthoredComponentsClosed=True)
 def render(scene):
  bpy.context.window.scene=scene;world=bpy.data.worlds.new(PREFIX+'previewWorld');world.use_nodes=True;world.node_tree.nodes['Background'].inputs[0].default_value=(.76,.80,.84,1);world.node_tree.nodes['Background'].inputs[1].default_value=.22;scene.world=world
  lightdata=bpy.data.lights.new(PREFIX+'previewArea','AREA');lightdata.energy=350;lightdata.shape='DISK';lightdata.size=5;lamp=bpy.data.objects.new(lightdata.name,lightdata);scene.collection.objects.link(lamp);lamp.location=(0,0,HEIGHT-.38)
  cameraData=bpy.data.cameras.new(PREFIX+'previewCamera');camera=bpy.data.objects.new(cameraData.name,cameraData);scene.collection.objects.link(camera);scene.camera=camera;cameraData.lens=17;cameraData.clip_end=100
  scene.render.engine='BLENDER_EEVEE';scene.eevee.taa_render_samples=32;scene.render.resolution_x=1200;scene.render.resolution_y=900;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='AgX';views=[]
  for name,pp,tp,z,tz,label in [('teaching',[388,155],[220,393],1.64,1.38,'CLM.G.03写字板椅与教学端'),('seating',[399,375],[290,160],1.66,1.25,'CLM.G.03环绕座位与窗湾')]:
   p,t=point(pp),point(tp);camera.location=(*p,z);target=Vector((*t,tz));camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler();scene.render.filepath=str(OUT/('built-'+name+'.png'));bpy.ops.render.render(write_still=True);views.append(dict(name='clm-g03-'+name+'-interior',code='CLM',spaceId='clm-g03',label=label,view=dict(position=[p.x,z,-p.y],target=[t.x,tz,-t.y],fov=76.1)))
  for obj in [camera,lamp]:bpy.data.objects.remove(obj,do_unlink=True)
  bpy.data.cameras.remove(cameraData);bpy.data.lights.remove(lightdata);return views
 def run():
  assert sha(BASE)==SHA;bpy.ops.wm.open_mainfile(filepath=str(BASE));update();expected=accepted_fingerprints(ROOT/'result/blender/stage227',SHA);original={o.name:object_fingerprint(o)for o in bpy.data.objects};assert original==expected and len(original)==7970
  mats={m.name:material_fingerprint(m)for m in bpy.data.materials};mods={o.name:stable_modifiers(o)for o in bpy.data.objects};rooms=rooms_state();assert len(rooms)==25 and len(set(n for r in rooms for n in r['objects']))==964;members={o.name:sorted(c.name for c in o.users_collection)for o in bpy.data.objects};vis={o.name:o.hide_render for o in bpy.data.objects};props={o.name:dict(o.items())for o in bpy.data.objects}
  scene,col,owned,records,solid=build();update();proof=checks(owned,records);views=render(scene)
  scope='依据LSE历史同房号平面与照片建立CLM.G.03独立教室。按平面保留14个写字板椅、教学桌、凹台周界、窗湾及右下入口；照片控制白壳黑座、白写字板、灰褐地毯、教学显示屏、两侧白板与AV设备。尺度、层高、隐藏构造及窗格估算，完整连续天花，不作地理配准或2026现用认证。'
  space=dict(code='CLM',id='clm-g03',label='CLM.G.03写字板教室',collection=COLLECTION,gallery=views[0]['name'],scope=scope,interiorView=views[0]['view'],interiorStudy=dict(kind='room-sample',label='CLM.G.03写字板教室',scope=scope));col['authoringRecord']=json.dumps(space,ensure_ascii=False)
  fingerprints={o.name:object_fingerprint(o)for o in owned};bindings={o.name:[m.name for m in o.data.materials]for o in owned};component=OUT/'component.blend';bpy.data.libraries.write(str(component),{col},fake_user=True,compress=True)
  bpy.ops.wm.open_mainfile(filepath=str(BASE));update();assert{o.name:object_fingerprint(o)for o in bpy.data.objects}==expected
  with bpy.data.libraries.load(str(component),link=False)as(src,dst):dst.collections=[COLLECTION]
  saved=dst.collections[0];scene=bpy.data.scenes.new(SCENE);scene.collection.children.link(saved);bpy.context.window.scene=scene;update();assert checks(list(saved.all_objects),records)==proof
  assert all(object_fingerprint(bpy.data.objects[n])==v for n,v in fingerprints.items());assert all(object_fingerprint(bpy.data.objects[n])==v for n,v in original.items());assert all(material_fingerprint(bpy.data.materials[n])==v for n,v in mats.items());assert all(stable_modifiers(bpy.data.objects[n])==v for n,v in mods.items());assert rooms_state()==rooms;assert all(sorted(c.name for c in bpy.data.objects[n].users_collection)==v for n,v in members.items());assert all(bpy.data.objects[n].hide_render==v for n,v in vis.items());assert all(dict(bpy.data.objects[n].items())==v for n,v in props.items());assert not any(n in bpy.data.scenes['00_CAMPUS_COMPLETE'].objects for n in fingerprints);assert sha(BASE)==SHA
  verification=dict(savedComponentReopened=True,independentAcceptedObjectsVerified=len(original),allOriginalMaterialNodesVerified=len(mats),allOriginalModifierStacksVerified=len(mods),oldSpacesPreserved=len(rooms),oldSpaceUniqueObjectsPreserved=964,allOriginalMembershipsAndPropertiesUnchanged=True,allSourceGeometryUVTransformsBindingsUnchanged=True,allOriginalVisibilityUnchanged=True,noNewRoomObjectInCampus=True,sourceNativeShaUnchanged=True,sourcePhotoNotUsedAsTexture=True,previewLightsAndCamerasExcluded=True,completeRouteThinSurfaceSweepReopened=True,triangles=sum(len(f.vertices)-2 for o in saved.all_objects for f in o.data.polygons))
  audit=dict(version=228,building='CLM',baselinePath=str(BASE.relative_to(ROOT)),baselineSha256=SHA,componentPath=str(component.relative_to(ROOT)),componentSha256=sha(component),targetCollection=COLLECTION,destinationCollection=COLLECTION,collectionSpec=dict(kind='independent-room',name=COLLECTION,scene=SCENE),space=space,report=dict(space=space),addedObjects=list(fingerprints),archivedObjects=[],changedObjects=[],addedFingerprints=fingerprints,replacementMaterialBindings=bindings,sourceManifest='data/collections/clmg03-room228/sources.json',planLayout='data/collections/clmg03-room228/layout.json',studentSeatCount=14,teacherSeatCount=1,deskCount=1,scaleMetresPerPixel=SCALE,roomAreaSquareMetres=L['roomAreaSquareMetres'],estimatedCeilingHeight=HEIGHT,gallerySuggestions=views,checks=proof,solidProof=solid,verification=verification,previews=['built-teaching.png','built-seating.png'],beforeEvidence=[PLAN,PHOTO],previewLighting='One temporary area light below the complete ceiling,excluded from component;no public private-source texture',limitations=json.loads((DATA/'sources.json').read_text())['limitations'])
  (OUT/'audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n');print('CLMG03_ROOM228_READY',len(fingerprints),verification,flush=True);bpy.ops.wm.quit_blender()
 if __name__=='__main__':run()
