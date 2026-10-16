"""CKK.1.15 independent room from the actual paired historical LSE assets.

Trace the complete room, unequal entrance leaves and six casement windows.
Dimensions without printed measurements remain estimates. No campus is saved.
"""
from pathlib import Path
import hashlib,json,math,sys
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'result/blender/ckk115-room227'
DATA=ROOT/'data/collections/ckk115-room227'
BASE=ROOT/'result/blender/LSE_campus_detailed_v226.blend'
SHA='4e6c1482f97ac61b42e8a344bc503fd2fa86395006a6b43312bd6be21ac214a2'
COLLECTION='CKK115_ROOM227_study'
SCENE='ROOM227_CKK115'
PREFIX='CKK115_R227_'
PLAN='data/collections/interiors/images/a77a94b79770_CKK.1.15.GIF'
PHOTO='data/collections/interiors/images/d18b9bd1ba93_CKK.1.15.jpg'
HEIGHT=3.12
SCALE=.019


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def prepare():
 from shapely.geometry import Polygon,box
 from PIL import Image,ImageDraw
 DATA.mkdir(parents=True,exist_ok=True);OUT.mkdir(parents=True,exist_ok=True)
 def point(p):return[(p[0]-265)*SCALE,(260-p[1])*SCALE]
 outline=[[19,22],[510,22],[510,350],[401,455],[84,455],[84,411],[19,411]]
 polygon=Polygon([point(p)for p in outline]);assert polygon.is_valid
 rows=[dict(id='A',left=87,right=460,top=129,seaty=164,count=10),dict(id='B',left=87,right=460,top=194,seaty=229,count=10),dict(id='C',left=87,right=460,top=261,seaty=296,count=10),dict(id='D',left=125,right=423,top=328,seaty=362,count=8),dict(id='E',left=162,right=386,top=390,seaty=427,count=6)]
 tables=[];seats=[];black={(0,0),(0,3),(0,6),(1,2),(1,5),(2,1),(2,7),(3,4),(4,0)}
 for ri,row in enumerate(rows):
  step=(row['right']-row['left'])/row['count']
  for j in range(row['count']//2):
   a=row['left']+j*2*step;b=a+2*step
   ring=[[a,row['top']],[b,row['top']],[b,row['top']+25],[a,row['top']+25]]
   tables.append(dict(id=row['id']+str(j+1),outline=[point(p)for p in ring],sourceOutline=ring))
  for j in range(row['count']):
   p=[row['left']+(j+.5)*step,row['seaty']]
   seats.append(dict(id=row['id']+str(j+1),pixel=p,centre=point(p),target=point([p[0],p[1]-60]),colour='black'if(ri,j)in black else'red'))
 windows=[dict(id='right1',a=[510,49],b=[510,99]),dict(id='right2',a=[510,138],b=[510,204]),dict(id='right3',a=[510,241],b=[510,289]),dict(id='rear1',a=[87,455],b=[151,455]),dict(id='rear2',a=[188,455],b=[259,455]),dict(id='rear3',a=[290,455],b=[345,455])]
 grid=[];tiles=[]
 def parts(geometry):return[geometry]if geometry.geom_type=='Polygon'else[p for p in geometry.geoms if p.geom_type=='Polygon']
 x0,y0,x1,y1=polygon.bounds
 for axis,lo,hi in [(0,x0,x1),(1,y0,y1)]:
  for i in range(math.ceil(lo/1.2),math.floor(hi/1.2)+1):
   v=i*1.2;stripe=box(v-.003,y0-1,v+.003,y1+1)if axis==0 else box(x0-1,v-.003,x1+1,v+.003);part=polygon.intersection(stripe)
   if not part.is_empty:grid.extend(list(p.exterior.coords)[:-1]for p in parts(part)if p.area>1e-6)
 for i in range(math.floor(x0/.5),math.ceil(x1/.5)):
  for j in range(math.floor(y0/.5),math.ceil(y1/.5)):
   part=polygon.intersection(box(i*.5,j*.5,(i+1)*.5,(j+1)*.5))
   if not part.is_empty:tiles.extend(dict(outline=list(p.exterior.coords)[:-1],material='carpet'+['A','B'][(i+j)%2])for p in parts(part)if p.area>1e-6)
 lights=[point([x,y])for x in [155,365]for y in [105,240,355]]
 layout=dict(room='CKK.1.15',scaleMetresPerPixel=SCALE,scaleBasis='Estimated0.019m/pixel from the49px primary entrance leaf,about0.93m;no printed dimension or area',outlinePixels=outline,outline=[point(p)for p in outline],roomAreaSquareMetres=polygon.area,rows=rows,tables=tables,seats=seats,studentSeatCount=44,windows=windows,door=dict(a=[19,41],b=[19,110],primaryEnd=[19,89],hinge=[19,41],openTip=[68,41]),teacherDesk=dict(a=[323,61],b=[406,105]),teacherSeat=[365,49],ceilingHeight=HEIGHT,ceilingGridParts=grid,carpetTiles=tiles,lights=lights,principalRoutes=[[[19,66],[55,66]],[[55,66],[55,390]],[[55,117],[483,117]],[[483,117],[483,310]]])
 (DATA/'layout.json').write_text(json.dumps(layout,indent=2)+'\n')
 source=json.loads((ROOT/'data/collections/interiors/sources.json').read_text())
 selected=[r for r in source['sources']if r.get('local_path')in [PLAN,PHOTO]];assert len(selected)==2
 manifest=dict(room='CKK.1.15',sources=selected,planSha256=sha(ROOT/PLAN),photoSha256=sha(ROOT/PHOTO),sourceDirectoryPlanTimestamp='2014-03-25 10:08,server listing,not drawing creation',sourceDirectoryPhotoTimestamp='2026-09-12 07:00,server listing,not photograph capture',sourceInterpretation=['Both assets visually verified as actual same-room content,not placeholders.','Five plan rows10/10/10/8/6 yield44student chair symbols and22paired rectangular desks.','White desks,mixed red/black chairs,left front timber entrance,front whiteboard/AV workstation,left display and right high windows match the photograph.','The left front entrance has unequal double leaves;right and rear thick-wall openings with swing arcs are casement windows,not six extra room doors.','Full outline includes rear diagonal corner and rear-left recess;not a rectangular extrapolation.'],limitations=['Asset dates unknown;directory modification timestamps are not photograph capture or drawing creation and do not certify2026 current layout.','Uniform0.019m/pixel scale,3.12mceiling,door/window vertical dimensions,concealed furniture construction and all hidden finishes are estimates.','44plan symbols are historical seats,not certified current capacity;exact red/black chair distribution cannot be assigned uniquely from the oblique photo.','Rear window details and blind arrangements follow visible window type plus plan apertures;rear elevation is not photographed.','Ceiling is complete;panel divisions,dropped beams and six linear lamp positions are simplified estimates from the photograph,not a reflected-ceiling survey.','Independent room,no geographic CKK floor registration,no source photograph published or used as a texture.','0.44mswept body route checks are geometric evidence,not accessibility or egress certification.'])
 (DATA/'sources.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
 im=Image.open(ROOT/PLAN).convert('RGB');d=ImageDraw.Draw(im);d.line(outline+[outline[0]],fill=(220,25,25),width=2)
 for seat in seats:
  x,y=seat['pixel'];d.ellipse((x-2,y-2,x+2,y+2),fill=(20,50,230))
 im.save(DATA/'registered-plan.png')
 print('CKK115_LAYOUT_READY',polygon.area,len(tables),len(seats),flush=True)

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
 def point(p):return Vector(((p[0]-265)*SCALE,(260-p[1])*SCALE))
 def update():
  for scene in bpy.data.scenes:
   for layer in scene.view_layers:layer.update()
 def material(g,key,color,rough=.7,metal=0):
  mat=bpy.data.materials.new(PREFIX+key);mat.use_nodes=True;mat.diffuse_color=(*color,1);shader=mat.node_tree.nodes['Principled BSDF'];shader.inputs['Base Color'].default_value=mat.diffuse_color;shader.inputs['Roughness'].default_value=rough;shader.inputs['Metallic'].default_value=metal;g.materials[key]=mat
 def span(g,family,key,a,b,lo,hi,depth=.14):
  a,b=Vector(a),Vector(b);d=b-a;c=(a+b)/2;g.box(family,key,(*c,(lo+hi)/2),(d.length,depth,hi-lo),math.atan2(d.y,d.x))
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
  scene=bpy.data.scenes.new(SCENE);col=bpy.data.collections.new(COLLECTION);scene.collection.children.link(col);col['roomSample']=True;col['roomCode']='CKK.1.15';g=RoomGeometry(col,PREFIX)
  for key,color,rough,metal in [('plaster',(.73,.73,.68),.86,0),('red',(.49,.025,.035),.58,0),('black',(.016,.020,.019),.74,0),('steel',(.43,.46,.45),.32,.55),('tablewhite',(.82,.82,.76),.58,0),('carpetA',(.14,.16,.16),.94,0),('carpetB',(.17,.19,.19),.94,0),('ceiling',(.79,.79,.74),.88,0),('joint',(.68,.68,.63),.88,0),('windowframe',(.65,.68,.66),.46,0),('glassroom',(.29,.36,.37),.17,0),('blindroom',(.47,.49,.46),.75,0),('doorwood',(.33,.20,.11),.70,0),('boardwhite',(.84,.84,.79),.46,0),('screen',(.006,.008,.010),.40,0),('vision',(.10,.12,.12),.20,0),('cabinet',(.27,.29,.28),.65,0)]:material(g,key,color,rough,metal)
  g.prism('complete_plan_floor','carpetA',L['outline'],-.14,.137)
  for tile in L['carpetTiles']:g.prism('quiet_carpet_tiles',tile['material'],tile['outline'],-.003,.003)
  da,db=point(L['door']['a']),point(L['door']['b']);ws=[(point(w['a']),point(w['b']))for w in L['windows']]
  for a,b in zip(L['outline'],L['outline'][1:]+L['outline'][:1]):
   a,b=Vector(a),Vector(b);d=b-a;events=[(0.,1.,'wall')]
   for u,v,kind in [(da,db,'door')]+[(u,v,'window')for u,v in ws]:
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
    p,q=a+d*s,a+d*e
    if kind!='door':span(g,'perimeter_skirting','cabinet',p,q,0,.085,.035)
    if kind=='wall':span(g,'complete_perimeter_walls','plaster',p,q,.085,HEIGHT)
    elif kind=='door':span(g,'real_door_lintel_wall','plaster',p,q,2.28,HEIGHT)
    else:span(g,'window_sill_wall','plaster',p,q,.085,.82);span(g,'window_upper_wall','plaster',p,q,2.77,HEIGHT)
  for w,(a,b)in zip(L['windows'],ws):
   d=b-a;u=d.normalized();n=Vector((-u.y,u.x));mid=(a+b)/2;inward=n if n.dot(-mid)>0 else-n
   for p in [a,b]:span(g,'window_side_frames','windowframe',p-u*.028,p+u*.028,.81,2.79,.12)
   span(g,'window_sill_frames','windowframe',a,b,.80,.86,.25)
   for z in [.88,2.04,2.75]:span(g,'window_cross_frames','windowframe',a,b,z-.027,z+.027,.09)
   p=(a+b)/2;span(g,'window_centre_mullions','windowframe',p-u*.023,p+u*.023,.88,2.75,.09)
   span(g,'restrained_reflective_window_glass','glassroom',a+inward*.015,b+inward*.015,.88,2.74,.016)
   span(g,'blind_head_boxes','windowframe',a+inward*.105,b+inward*.105,2.72,2.79,.10)
   # Part-raised opaque blinds retain restrained light rather than a fabricated view.
   for z in [1.88+i*.040 for i in range(20)]:span(g,'partial_venetian_blind_slats','blindroom',a+u*.035+inward*.11,b-u*.035+inward*.11,z,z+.013,.034)
  du=(db-da).normalized()
  for p in [da,db]:span(g,'door_jamb_frames','doorwood',p-du*.027,p+du*.027,0,2.31,.18)
  span(g,'door_header_frame','doorwood',da,db,2.25,2.31,.18)
  primary_end=point(L['door']['primaryEnd']);span(g,'closed_secondary_door_leaf','doorwood',primary_end,db,.025,2.25,.046)
  hinge,tip=point(L['door']['hinge']),point(L['door']['openTip']);leaf=tip-hinge;pa,pb=hinge+leaf*.68,hinge+leaf*.82
  for a,b in [(hinge,pa),(pb,tip)]:span(g,'open_primary_door_leaf','doorwood',a,b,.025,2.25,.046)
  for lo,hi in [(.025,.82),(1.92,2.25)]:span(g,'open_primary_door_leaf','doorwood',pa,pb,lo,hi,.046)
  span(g,'door_vision_glass','vision',pa,pb,.82,1.92,.015)
  handle=hinge+leaf*.90;g.tube('door_metal_handles','steel',(*handle,.96),(*handle,1.10),.014)
  # The long front board follows its actual plan stroke;vertical sizes follow photo estimates.
  a,b=point([104,29]),point([343,29]);span(g,'front_whiteboard_frame','windowframe',a,b,.89,2.25,.065);span(g,'front_whiteboard_face','boardwhite',a+Vector((0,-.044)),b+Vector((0,-.044)),.93,2.21,.020);span(g,'whiteboard_pen_tray','windowframe',a+Vector((0,-.075)),b+Vector((0,-.075)),.89,.92,.15)
  a,b=point([170,29]),point([331,29]);span(g,'rolled_projection_screen_housing','windowframe',a,b,2.53,2.64,.095)
  # Wall-mounted display is beside the entrance on the left wall,as photographed.
  a,b=point([25,127]),point([25,192]);span(g,'left_display_frame','black',a,b,1.55,2.31,.10);span(g,'left_blank_teaching_display','screen',a+Vector((.06,0)),b+Vector((.06,0)),1.59,2.27,.021)
  ta,tb=point(L['teacherDesk']['a']),point(L['teacherDesk']['b']);tc=(ta+tb)/2;tw,td=abs(tb.x-ta.x),abs(tb.y-ta.y);g.box('teacher_AV_worktop','tablewhite',(*tc,.855),(tw,td,.05));g.box('teacher_AV_cabinet','cabinet',(*tc,.415),(tw-.15,td-.14,.83));g.box('teacher_monitor_foot','black',(tc.x+.22,tc.y,.897),(.28,.21,.032));g.tube('teacher_monitor_stand','steel',(tc.x+.22,tc.y,.91),(tc.x+.22,tc.y,1.15),.025);g.box('teacher_monitor','screen',(tc.x+.22,tc.y,1.30),(.48,.055,.32));g.box('teacher_control_panel','black',(tc.x-.42,tc.y-.15,.91),(.22,.18,.045))
  tabletop_supports=[]
  for table in L['tables']:
   ring=table['outline'];g.prism('twenty_two_white_row_desks','tablewhite',ring,.72,.045);xs=[p[0]for p in ring];ys=[p[1]for p in ring]
   for x in [min(xs)+.09,max(xs)-.09]:
    for y in [min(ys)+.07,max(ys)-.07]:
     g.tube('desk_steel_legs','steel',(x,y,0),(x,y,.728),.022);tabletop_supports.append(dict(foot=[x,y,0],top=[x,y,.728]))
  seats=[chair(g,s['centre'],s['target'],s['colour'])for s in L['seats']];seats.append(chair(g,point(L['teacherSeat']),tc,teacher=True))
  # A real closed ceiling covers the entire polygon;photo-like panels remain overlays.
  g.prism('continuous_complete_ceiling','ceiling',L['outline'],HEIGHT,.085)
  for ring in L['ceilingGridParts']:g.prism('subtle_ceiling_panel_joints','joint',ring,HEIGHT-.004,.005)
  for py in [170,300]:
   a,b=point([20,py]),point([509,py]);span(g,'photograph_ceiling_cross_beams','plaster',a,b,HEIGHT-.20,HEIGHT,.22)
  for x,y in L['lights']:
   g.box('linear_ceiling_lamp_housings','windowframe',(x,y,HEIGHT-.022),(.20,1.12,.044));g.box('linear_ceiling_diffusers','light',(x,y,HEIGHT-.050),(.15,1.04,.018))
  proj=point([260,160]);g.tube('ceiling_projector_mount','windowframe',(*proj,HEIGHT-.32),(*proj,HEIGHT),.022);g.box('ceiling_projector','plaster',(*proj,HEIGHT-.36),(.38,.28,.10));g.box('projector_lens','screen',(proj.x,proj.y+.145,HEIGHT-.36),(.09,.018,.06))
  objects=g.finish()
  for o in objects:o['roomCode']='CKK.1.15';o['destinationCollection']=COLLECTION;o['scope']='Independent paired historical classroom;not geographic CKK registration or2026 capacity certification'
  return scene,col,objects,dict(seats=seats,tableSupports=tabletop_supports,teacherCabinetCentre=list(tc),door=dict(jambs=[list(da),list(db)],mainJambs=[list(da),list(primary_end)],primaryClearWidth=(primary_end-da).length-.054,totalOpeningWidth=(db-da).length)),g.solid_proof
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
  floor,_=tree([o for o in objects if any(k in o.name for k in ['complete_plan_floor','quiet_carpet_tiles'])]);ceil,_=tree([o for o in objects if o.name==PREFIX+'continuous_complete_ceiling']);solid,owners=tree([o for o in objects if not any(k in o.name for k in ['complete_plan_floor','quiet_carpet_tiles','ceiling','projector'])]);tops,_=tree([o for o in objects if o.name==PREFIX+'twenty_two_white_row_desks'])
  feet=[]
  groups=[('studentchair',[p for s in R['seats']if not s['teacher']for p in s['feet']]),('teacherchair',[p for s in R['seats']if s['teacher']for p in s['feet']]),('desk',[v['foot']for v in R['tableSupports']])]
  tc=R['teacherCabinetCentre'];groups.append(('AVcabinet',[[tc[0]+dx,tc[1]+dy,0]for dx in [-.5,.5]for dy in [-.25,.25]]))
  for kind,points in groups:
   for p in points:
    hit=floor.ray_cast(Vector((p[0],p[1],.04)),Vector((0,0,-1)),.08);assert hit[0]is not None and abs(hit[0].z)<.001,('Unsupportedfoot',kind,p);feet.append(dict(kind=kind,point=p,floorZ=hit[0].z))
  contacts=[]
  for v in R['tableSupports']:
   p=v['top'];hit=tops.ray_cast(Vector((p[0],p[1],.70)),Vector((0,0,1)),.06);assert hit[0]is not None and abs(hit[0].z-.72)<.001;contacts.append([p[0],p[1],hit[0].z])
  door=[];a,b=map(Vector,R['door']['mainJambs']);mid=(a+b)/2;u=(b-a).normalized()
  for side in [-.22,0,.22]:
   for z in [.04,.20,1.2,2.07]:
    p=mid+u*side+Vector((-.3,0));hit=solid.ray_cast(Vector((*p,z)),Vector((1,0,0)),.9);assert hit[0]is None,('Doorblocked',side,z,owners[hit[2]]if hit[2]is not None else None);door.append([side,z])
  routes=[];widths=[]
  for p,q in L['principalRoutes']:
   a,b=point(p),point(q);direction=(b-a).normalized();perp=Vector((-direction.y,direction.x));count=max(2,math.ceil((b-a).length/.14))
   for i in range(count+1):
    c=a.lerp(b,i/count)
    if i==0 and p==[19,66]:continue
    f=floor.ray_cast(Vector((*c,.04)),Vector((0,0,-1)),.08);assert f[0]is not None,('Routeofffloor',p,q,list(c))
    for h in [.20,.65,1.2]:
     start=c-perp*.22;hit=solid.ray_cast(Vector((*start,h)),Vector((*perp,0)),.44);assert hit[0]is None,('Routeblocked',p,q,list(c),h,owners[hit[2]]if hit[2]is not None else None)
     distances=[]
     for sign in [-1,1]:
      hit=solid.ray_cast(Vector((*c,h)),Vector((*(perp*sign),0)),2);distances.append(hit[3]if hit[0]is not None else 2.)
     widths.append(dict(position=list(c),height=h,surfaceGap=sum(distances),centeredWidth=2*min(distances)))
    # Actual ceiling and dropped members must leave2.1m headroom along the route.
    overhead,roofnames=tree([o for o in objects if any(k in o.name for k in ['ceiling','projector'])])if not routes else overhead_pair
    overhead_pair=(overhead,roofnames)
    h=overhead.ray_cast(Vector((*c,.02)),Vector((0,0,1)),HEIGHT+.2);assert h[0]is not None and h[0].z>=2.1;routes.append(dict(position=list(c),headroom=h[0].z,overhead=roofnames[h[2]]))
  coverage=[];step=.20;xs=[p[0]for p in L['outline']];ys=[p[1]for p in L['outline']]
  for i in range(math.floor(min(xs)/step),math.ceil(max(xs)/step)):
   for j in range(math.floor(min(ys)/step),math.ceil(max(ys)/step)):
    x,y=(i+.5)*step,(j+.5)*step
    if not inside(x,y):continue
    hit=ceil.ray_cast(Vector((x,y,1.5)),Vector((0,0,1)),2);assert hit[0]is not None and abs(hit[0].z-HEIGHT)<.001,('Ceilinghole',x,y);coverage.append([x,y,hit[0].z])
  assert len(coverage)>1500
  aperturewalls=[o for o in objects if any(k in o.name for k in ['perimeter_walls','sill_wall','upper_wall','door_lintel'])];walltree,wallnames=tree(aperturewalls);windows=[]
  for w in L['windows']:
   a,b=point(w['a']),point(w['b']);c=(a+b)/2;d=(b-a).normalized();n=Vector((-d.y,d.x))
   for z in [1.10,1.50,2.40]:
    p=c-n*.3;hit=walltree.ray_cast(Vector((*p,z)),Vector((*n,0)),.6);assert hit[0]is None,('Windowwallnotcut',w['id'],z,wallnames[hit[2]]if hit[2]is not None else None);windows.append([w['id'],z])
  return dict(wholeRouteSavedMeshSweep=swept_route_surfaces(objects),studentSeatCount=sum(not s['teacher']for s in R['seats']),teacherSeatCount=sum(s['teacher']for s in R['seats']),deskCount=22,footSupportProbes=feet,deskLegUndersideContacts=contacts,doorwayClearRays=door,primaryDoorClearWidth=R['door']['primaryClearWidth'],totalDoorOpeningWidth=R['door']['totalOpeningWidth'],windowRealWallApertureRays=windows,continuousCeilingCoverage=dict(spacingMetres=step,probeCount=len(coverage),missCount=0,undersideHeight=HEIGHT,pointDigest=hashlib.sha256(json.dumps(coverage).encode()).hexdigest()),routeBodyWidth=.44,routeWidthInterpretation='Reportedminimumgapssampleheights0.20/0.65/1.20monly;complete0.04–2.10mbodyvolumeisverifiedseparatelybywholeRouteSavedMeshSweep;notaccessibilityoregresscertification',minimumCenteredSweptWidth=min(r['centeredWidth']for r in widths),minimumSurfaceGap=min(r['surfaceGap']for r in widths),routeCrossSections=widths,clearRouteProbes=routes,minimumRouteHeadroom=min(r['headroom']for r in routes),routeScope='Main entrance,left aisle,front cross-aisle,right aisle;not every chair pull-out or access/egress certification',allAuthoredComponentsClosed=True)
 def render(scene):
  bpy.context.window.scene=scene;world=bpy.data.worlds.new(PREFIX+'previewWorld');world.use_nodes=True;world.node_tree.nodes['Background'].inputs[0].default_value=(.76,.80,.84,1);world.node_tree.nodes['Background'].inputs[1].default_value=.55;scene.world=world
  ld=bpy.data.lights.new(PREFIX+'previewArea','AREA');ld.energy=1400;ld.shape='DISK';ld.size=7;lamp=bpy.data.objects.new(ld.name,ld);scene.collection.objects.link(lamp);lamp.location=(0,0,HEIGHT-.20)
  cd=bpy.data.cameras.new(PREFIX+'previewCamera');camera=bpy.data.objects.new(cd.name,cd);scene.collection.objects.link(camera);scene.camera=camera;cd.lens=18;cd.clip_end=100
  scene.render.engine='BLENDER_EEVEE';scene.eevee.taa_render_samples=32;scene.render.resolution_x=1200;scene.render.resolution_y=900;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='AgX'
  views=[]
  for name,pp,tp,z,tz,label in [('default',[57,382],[300,80],1.73,1.45,'CKK.1.15排式教室与教学端'),('rear-windows',[60,115],[335,377],1.78,1.45,'CKK.1.15排式座位与转角窗')]:
   p,t=point(pp),point(tp);camera.location=(*p,z);target=Vector((*t,tz));camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler();scene.render.filepath=str(OUT/('built-'+name+'.png'));bpy.ops.render.render(write_still=True);views.append(dict(name='ckk-115-'+name+'-interior',code='CKK',spaceId='ckk-115',label=label,view=dict(position=[p.x,z,-p.y],target=[t.x,tz,-t.y],fov=73.74)))
  for obj in [camera,lamp]:bpy.data.objects.remove(obj,do_unlink=True)
  bpy.data.cameras.remove(cd);bpy.data.lights.remove(ld);return views
 def run():
  assert sha(BASE)==SHA;bpy.ops.wm.open_mainfile(filepath=str(BASE));update();expected=accepted_fingerprints(ROOT/'result/blender/stage226',SHA);original={o.name:object_fingerprint(o)for o in bpy.data.objects};assert original==expected and len(original)==7858
  mats={m.name:material_fingerprint(m)for m in bpy.data.materials};mods={o.name:stable_modifiers(o)for o in bpy.data.objects};rooms=rooms_state();assert len(rooms)==23 and len(set(n for r in rooms for n in r['objects']))==853;members={o.name:sorted(c.name for c in o.users_collection)for o in bpy.data.objects};vis={o.name:o.hide_render for o in bpy.data.objects};props={o.name:dict(o.items())for o in bpy.data.objects}
  scene,col,owned,records,solid=build();update();proof=checks(owned,records);assert proof['studentSeatCount']==44;views=render(scene)
  scope='依据LSE同房号历史平面与实照建立CKK.1.15独立排式教室样本。完整周界保留后角斜切及左后凹口，22张双人桌与5排44个历史学生座位，大小不等双扇入口、六处真实墙窗孔、前端白板和AV台、左墙显示屏及完整连续天花。门宽比例、层高、后窗及家具细节估算，不接地理楼层，不作2026现用容量认证。'
  space=dict(code='CKK',id='ckk-115',label='CKK.1.15排式教室',collection=COLLECTION,gallery=views[0]['name'],scope=scope,interiorView=views[0]['view'],interiorStudy=dict(kind='room-sample',label='CKK.1.15排式教室',scope=scope));col['authoringRecord']=json.dumps(space,ensure_ascii=False)
  fingerprints={o.name:object_fingerprint(o)for o in owned};bindings={o.name:[m.name for m in o.data.materials]for o in owned};component=OUT/'component.blend';bpy.data.libraries.write(str(component),{col},fake_user=True,compress=True)
  bpy.ops.wm.open_mainfile(filepath=str(BASE));update();assert{o.name:object_fingerprint(o)for o in bpy.data.objects}==expected
  with bpy.data.libraries.load(str(component),link=False)as(src,dst):dst.collections=[COLLECTION]
  saved=dst.collections[0];scene=bpy.data.scenes.new(SCENE);scene.collection.children.link(saved);bpy.context.window.scene=scene;update();assert checks(list(saved.all_objects),records)==proof
  assert all(object_fingerprint(bpy.data.objects[n])==v for n,v in fingerprints.items());assert all(object_fingerprint(bpy.data.objects[n])==v for n,v in original.items());assert all(material_fingerprint(bpy.data.materials[n])==v for n,v in mats.items());assert all(stable_modifiers(bpy.data.objects[n])==v for n,v in mods.items());assert rooms_state()==rooms;assert all(sorted(c.name for c in bpy.data.objects[n].users_collection)==v for n,v in members.items());assert all(bpy.data.objects[n].hide_render==v for n,v in vis.items());assert all(dict(bpy.data.objects[n].items())==v for n,v in props.items());assert not any(n in bpy.data.scenes['00_CAMPUS_COMPLETE'].objects for n in fingerprints);assert sha(BASE)==SHA
  verification=dict(savedComponentReopened=True,independentAcceptedObjectsVerified=len(original),allOriginalMaterialNodesVerified=len(mats),allOriginalModifierStacksVerified=len(mods),oldSpacesPreserved=len(rooms),oldSpaceUniqueObjectsPreserved=853,allOriginalMembershipsAndPropertiesUnchanged=True,allSourceGeometryUVTransformsBindingsUnchanged=True,allOriginalVisibilityUnchanged=True,noNewRoomObjectInCampus=True,sourceNativeShaUnchanged=True,sourcePhotoNotUsedAsTexture=True,triangles=sum(len(f.vertices)-2 for o in saved.all_objects for f in o.data.polygons))
  audit=dict(version=227,building='CKK',baselinePath=str(BASE.relative_to(ROOT)),baselineSha256=SHA,componentPath=str(component.relative_to(ROOT)),componentSha256=sha(component),targetCollection=COLLECTION,destinationCollection=COLLECTION,collectionSpec=dict(kind='independent-room',name=COLLECTION,scene=SCENE),space=space,addedObjects=list(fingerprints),archivedObjects=[],changedObjects=[],addedFingerprints=fingerprints,replacementMaterialBindings=bindings,sourceManifest='data/collections/ckk115-room227/sources.json',planLayout='data/collections/ckk115-room227/layout.json',studentSeatCount=44,teacherSeatCount=1,deskCount=22,scaleMetresPerPixel=SCALE,roomAreaSquareMetres=L['roomAreaSquareMetres'],estimatedCeilingHeight=HEIGHT,gallerySuggestions=views,checks=proof,solidProof=solid,verification=verification,previews=['built-default.png','built-rear-windows.png'],beforeEvidence=[PLAN,PHOTO],previewLighting='One temporary area light below the continuous ceiling;no exported lights or private review objects',limitations=json.loads((DATA/'sources.json').read_text())['limitations'])
  (OUT/'audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n');print('CKK115_ROOM227_READY',len(fingerprints),verification,flush=True);bpy.ops.wm.quit_blender()
 def review_saved():
  audit=json.loads((OUT/'audit.json').read_text());component=OUT/'component.blend'
  assert audit['baselineSha256']==SHA and sha(component)==audit['componentSha256']
  # Records come from the prior saved proof,not a new independently moved layout.
  old=audit['checks'];feet=old['footSupportProbes'];student=[r['point']for r in feet if r['kind']=='studentchair'];teacher=[r['point']for r in feet if r['kind']=='teacherchair'];desk=[r['point']for r in feet if r['kind']=='desk']
  assert len(student)==176 and len(teacher)==5 and len(desk)==88
  seats=[dict(teacher=False,feet=student[i:i+4])for i in range(0,176,4)]+[dict(teacher=True,feet=teacher)]
  tc=(point(L['teacherDesk']['a'])+point(L['teacherDesk']['b']))/2
  records=dict(seats=seats,tableSupports=[dict(foot=p,top=[p[0],p[1],.728])for p in desk],teacherCabinetCentre=list(tc),door=dict(jambs=[list(point(L['door']['a'])),list(point(L['door']['b']))],mainJambs=[list(point(L['door']['a'])),list(point(L['door']['primaryEnd']))],primaryClearWidth=old['primaryDoorClearWidth'],totalOpeningWidth=old['totalDoorOpeningWidth']))
  bpy.ops.wm.read_factory_settings(use_empty=True)
  with bpy.data.libraries.load(str(component),link=False)as(src,dst):dst.collections=[COLLECTION]
  saved=dst.collections[0];bpy.context.scene.collection.children.link(saved);update()
  assert{o.name:object_fingerprint(o)for o in saved.all_objects}==audit['addedFingerprints']
  proof=checks(list(saved.all_objects),records)
  for key,value in old.items():assert proof[key]==value,(key,'priorphysicalproofchanged')
  audit['checks']=proof;audit['verification']['completeRouteThinSurfaceSweepReopened']=True
  (OUT/'audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n')
  print('CKK115_SAVED_ROUTE_REVIEW',proof['wholeRouteSavedMeshSweep'],flush=True);bpy.ops.wm.quit_blender()
 if __name__=='__main__':review_saved()if(OUT/'audit.json').exists()else run()
