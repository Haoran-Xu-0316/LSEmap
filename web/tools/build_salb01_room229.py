"""SAL.B.01 independent historical room from same-number LSE plan and photo.

Fixed configuration for Blender Text Editor; no command-line options. The plan
controls20student chairs, U-tables and the irregular outline. Photo controls
red upholstery, white worktops, pinboard, AV equipment and carpet. Dimensions,
window vertical geometry and ceiling layout are estimates, not a2026survey.
"""
from pathlib import Path
import hashlib,json,math,sys
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'result/blender/salb01-room229';DATA=ROOT/'data/collections/salb01-room229'
BASE=ROOT/'result/blender/LSE_campus_detailed_v228.blend'
SHA='0ddf5bb3791d146690d2af1f44b4cb6b113930cf687bc30d1cb916d84f4f066b'
PLAN='data/collections/interiors/images/2b112a1d751a_SAL.B.01.GIF';PHOTO='data/collections/interiors/images/85ccd9603a51_SAL.B.01.jpg'
COLLECTION='SALB01_ROOM229_study';SCENE='ROOM229_SALB01';PREFIX='SALB01_R229_';SCALE=.0185;HEIGHT=3.02

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
def prepare():
 from shapely.geometry import Polygon,box
 DATA.mkdir(parents=True,exist_ok=True);OUT.mkdir(parents=True,exist_ok=True)
 def p(q):return[(q[0]-294)*SCALE,(190-q[1])*SCALE]
 outline=[[28,48],[119,48],[119,22],[210,22],[210,46],[559,46],[559,319],[463,319],[463,363],[356,363],[356,319],[204,319],[204,363],[103,363],[103,319],[28,319]]
 polygon=Polygon([p(q)for q in outline]);assert polygon.is_valid
 students=[]
 for group,y,ty in [('upper',90,121),('lower',275,244)]:
  for i,x in enumerate([143,179,217,254,291,327,363,400]):students.append(dict(id=group+str(i+1),group=group,pixel=[x,y],target=[x,ty]))
 for i,y in enumerate([126,163,201,237]):students.append(dict(id='left'+str(i+1),group='left',pixel=[79,y],target=[111,y]))
 tables=[]
 for group,y0,y1 in [('upper',108,134),('lower',230,258)]:
  for i,(a,b)in enumerate([(124,234),(234,345),(345,419)]):tables.append(dict(id=group+str(i+1),a=[a,y0],b=[b,y1]))
 for i,(a,b)in enumerate([(108,183),(183,258)]):tables.append(dict(id='left'+str(i+1),a=[99,a],b=[124,b]))
 tiles=[];x0,y0,x1,y1=polygon.bounds
 for i in range(math.floor(x0/.50),math.ceil(x1/.50)):
  for j in range(math.floor(y0/.50),math.ceil(y1/.50)):
   q=polygon.intersection(box(i*.5,j*.5,(i+1)*.5,(j+1)*.5))
   if q.is_empty:continue
   parts=[q]if q.geom_type=='Polygon'else[g for g in q.geoms if g.geom_type=='Polygon']
   tiles.extend(dict(outline=list(t.exterior.coords)[:-1],material='carpet'+str((i+2*j)%3))for t in parts if t.area>1e-8)
 ingress=[[149.5,22],[149.5,63]]
 routes=[dict(group='upper',points=ingress+[[434,63],[434,90]],approach=[434,90],seatIds=['upper8']),dict(group='lower',points=ingress+[[434,63],[434,275]],approach=[434,275],seatIds=['lower8']),dict(group='left',points=ingress+[[434,63],[434,303],[47,303],[47,220]],approach=[47,220],seatIds=['left3','left4']),dict(group='teacher',points=ingress+[[434,63],[434,190],[520,190],[520,230]],approach=[520,230],seatIds=['teacher'])]
 layout=dict(room='SAL.B.01',outlinePixels=outline,outline=[p(q)for q in outline],scaleMetresPerPixel=SCALE,scaleBasis='Estimated0.0185m/pixel from51px door approximately0.9435m and37px chair pitch approximately0.6845m; no printed dimensions',roomAreaSquareMetres=polygon.area,carpetTiles=tiles,studentSeatCount=20,students=students,tables=tables,teacherDesk=dict(a=[456,211],b=[497,305]),teacherSeat=[515,257],door=dict(a=[124,22],b=[175,22],hinge=[124,22],openTip=[124,73]),windows=[dict(id='bay1',a=[105,363],b=[202,363]),dict(id='bay2',a=[358,363],b=[461,363])],ceilingLights=[[220,182],[350,182],[485,182]],projector=[345,182],routePaths=routes)
 write(DATA/'layout.json',layout)
 refs=[r for r in json.loads((ROOT/'data/collections/interiors/sources.json').read_text())['sources']if r.get('local_path')in[PLAN,PHOTO]];assert len(refs)==2
 manifest=dict(room='SAL.B.01',sources=refs,planSha256=sha(ROOT/PLAN),photoSha256=sha(ROOT/PHOTO),sameRoomPairVerified=True,bothImagesActualNotPlaceholder=True,sourceSeatCount=dict(upperLongSide=8,lowerLongSide=8,leftShortSide=4,totalStudents=20,teacher=1),interpretation=['Plan is explicitlyB.01; both official assets have identicalSAL.B.01room identifiers.','Plan shows20student chairs around a U-shaped table and one independent teacher chair/desk at the right teaching end.','Photo confirms whiteU-shaped worktops,red upholstered chairs,silver legs,grey checker carpet,striped orange/grey left pinboard,teaching screen,AV desk and suspended projector.','Plan upper-left entrance projection and both lower projecting bays are retained. Two lower-bay outer faces are interpreted as high basement windows,consistent with the high right-hand window reveal in the photo;exact heights and mullions are estimated.','Right-wall short parallel line is the teaching-board/screen zone,not an extra door.'],limitations=['Plan creation and photograph capture dates unknown;retrieval2026-09-12 does not establish contemporaneous sources or current2026condition.','Scale0.0185m/pixel,3.02mceiling,window sill/head heights,door construction,furniture dimensions and unseen finishes are estimates.','20student chairs are counted in the historical plan,not certified current seating capacity or egress/accessibility approval.','Photo captures only part of the room;plan controls all20positions and room perimeter.The two source orientations are matched byU-table and right-end teaching station.','Basement window heights and bay joinery are photo-informed estimates,not measured openings;no exterior-floor registration.','Full-height0.44m geometric corridors connect the entrance to one approach point for each of the three student seating groups and teacher chair;not every individual seat or accessibility certification.','Private source photographs are not embedded in materials or exported textures.','Independent Salisbury House room sample;no geographic campus/floor registration or2026as-built claim.'])
 write(DATA/'sources.json',manifest);print('SALB01_PLAN_READY',polygon.area,len(students),flush=True)

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
 def point(p):return Vector(((p[0]-294)*SCALE,(190-p[1])*SCALE))
 def update():
  for s in bpy.data.scenes:
   for layer in s.view_layers:layer.update()
 def material(g,key,c,rough=.7,metal=0):
  m=bpy.data.materials.new(PREFIX+key);m.use_nodes=True;m.diffuse_color=(*c,1);n=m.node_tree.nodes['Principled BSDF'];n.inputs['Base Color'].default_value=m.diffuse_color;n.inputs['Roughness'].default_value=rough;n.inputs['Metallic'].default_value=metal;g.materials[key]=m
 def span(g,f,key,a,b,lo,hi,depth=.14):
  a,b=Vector(a),Vector(b);d=b-a;c=(a+b)/2;g.box(f,key,(*c,(lo+hi)/2),(d.length,depth,hi-lo),math.atan2(d.y,d.x))
 def chair(g,p,target,teacher=False):
  p,t=Vector(p),Vector(target);angle=math.atan2(t.y-p.y,t.x-p.x)+math.pi/2;c,s=math.cos(angle),math.sin(angle)
  def at(x,y,z):return(p.x+c*x-s*y,p.y+s*x+c*y,z)
  g.box('red_upholstered_seats','red',at(0,0,.46),(.46,.43,.055),angle);g.box('red_upholstered_backs','red',at(0,.235,.735),(.46,.05,.47),angle)
  feet=[]
  for x in [-.19,.19]:
   for y in [-.18,.18]:
    foot=at(x*1.14,y*1.18,0);g.tube('chair_floor_contact_pads','dark',foot,at(x*1.14,y*1.18,.025),.017);g.tube('silver_chair_legs','steel',at(x*1.14,y*1.18,.02),at(x,y,.4325),.014);feet.append(list(foot))
   g.tube('chair_back_supports','steel',at(x,.15,.43),at(x,.23,.66),.013)
  return dict(teacher=teacher,centre=list(p),feet=feet)
 def build():
  scene=bpy.data.scenes.new(SCENE);col=bpy.data.collections.new(COLLECTION);scene.collection.children.link(col);col['roomSample']=True;col['roomCode']='SAL.B.01';g=RoomGeometry(col,PREFIX)
  for key,c,r,m in [('plaster',(.76,.76,.70),.87,0),('red',(.54,.025,.018),.7,0),('whiteworktop',(.81,.81,.75),.5,0),('steel',(.48,.50,.48),.33,.65),('dark',(.018,.023,.021),.62,0),('carpet0',(.27,.28,.25),.95,0),('carpet1',(.35,.35,.30),.95,0),('carpet2',(.40,.40,.35),.95,0),('ceiling',(.81,.81,.76),.90,0),('frame',(.80,.80,.75),.52,0),('glassroom',(.22,.27,.29),.19,0),('blindroom',(.77,.77,.72),.86,0),('doorwood',(.38,.29,.19),.73,0),('pinorange',(.60,.19,.025),.95,0),('pingrey',(.25,.27,.25),.95,0),('screenwhite',(.85,.85,.79),.5,0),('screenblack',(.009,.012,.012),.32,0),('avcabinet',(.43,.46,.43),.6,0)]:material(g,key,c,r,m)
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
    else:span(g,'high_window_lower_wall','plaster',p,q,.10,1.82);span(g,'high_window_upper_wall','plaster',p,q,2.86,HEIGHT)
  for a,b in windows:
   u=(b-a).normalized()
   for p in [a,b]:span(g,'high_window_jamb_frames','frame',p-u*.027,p+u*.027,1.82,2.89,.12)
   for z in [1.84,2.84]:span(g,'high_window_horizontal_frames','frame',a,b,z,z+.035,.10)
   for t in [1/3,2/3]:
    p=a.lerp(b,t);span(g,'high_window_mullions','frame',p-u*.023,p+u*.023,1.87,2.84,.08)
   span(g,'high_window_glass','glassroom',a,b,1.88,2.84,.016);span(g,'deep_high_window_sills','frame',a+Vector((0,.13)),b+Vector((0,.13)),1.79,1.84,.36);span(g,'high_roller_blinds','blindroom',a+Vector((0,.075)),b+Vector((0,.075)),2.62,2.84,.018)
  u=(db-da).normalized()
  for p in [da,db]:span(g,'door_jamb_frames','doorwood',p-u*.025,p+u*.025,0,2.27,.17)
  span(g,'door_header_frame','doorwood',da,db,2.22,2.27,.17);hinge,tip=point(L['door']['hinge']),point(L['door']['openTip']);span(g,'open_inward_door_leaf','doorwood',hinge,tip,.025,2.22,.043);p=hinge.lerp(tip,.87);g.tube('door_metal_handle','steel',(*p,.98),(*p,1.11),.013)
  supports=[];topcontacts=[]
  def table(record,teacher=False):
   a,b=point(record['a']),point(record['b']);cx,cy=(a+b)/2;w,d=abs(b.x-a.x),abs(b.y-a.y);g.box('teacher_white_worktop'if teacher else'U_shape_white_tabletops','whiteworktop',(cx,cy,.75),(w,d,.045));feet=[]
   for x in [cx-w/2+.08,cx+w/2-.08]:
    for y in [cy-d/2+.08,cy+d/2-.08]:
     g.box('table_floor_contact_pads','dark',(x,y,.0125),(.04,.04,.025));g.tube('table_silver_legs','steel',(x,y,.02),(x,y,.734),.020);feet.append([x,y,0]);topcontacts.append([x,y,.7275])
   supports.extend(feet)
  for t in L['tables']:table(t)
  table(L['teacherDesk'],True);seats=[chair(g,point(s['pixel']),point(s['target']))for s in L['students']];tc=point([(L['teacherDesk']['a'][0]+L['teacherDesk']['b'][0])/2,257]);seats.append(chair(g,point(L['teacherSeat']),tc,True))
  # Teacher wall is native+X, opposite the short U-table bridge.
  a,b=point([554,128]),point([554,209]);span(g,'projection_screen_case','dark',a,b,2.48,2.56,.10);span(g,'unrolled_white_projection_screen','screenwhite',a+Vector((-.058,0)),b+Vector((-.058,0)),1.16,2.48,.018);span(g,'projection_screen_bottom_bar','dark',a+Vector((-.07,0)),b+Vector((-.07,0)),1.15,1.18,.035)
  for px in range(230,411,30):
   a,b=point([px,50]),point([px+30,50]);span(g,'striped_orange_grey_pinboard','pinorange'if(px//30)%2==0 else'pingrey',a,b,.90,2.34,.035)
  a,b=point([538,250]),point([538,301]);span(g,'low_radiator','frame',a,b,.24,.72,.12)
  p=point([481,250]);g.box('AV_monitor_base','dark',(*p,.79),(.30,.25,.035));g.tube('AV_monitor_stand','dark',(*p,.80),(*p,1.04),.023);g.box('AV_monitor_black_screen','screenblack',(p.x-.03,p.y,1.19),(.065,.47,.30));g.box('AV_keyboard','dark',(p.x-.19,p.y-.19,.79),(.14,.42,.025));p=point([481,283]);g.box('AV_control_box','dark',(*p,.82),(.29,.32,.10))
  g.prism('continuous_complete_ceiling','ceiling',L['outline'],HEIGHT,.08)
  # Three photographed-type strips and a genuine suspended projector.
  lampanchors=[]
  for px in L['ceilingLights']:
   p=point(px);g.box('linear_lamp_housings','frame',(*p,HEIGHT-.055),(.12,3.65,.08));g.box('linear_lamp_diffusers','light',(*p,HEIGHT-.104),(.09,3.59,.022))
   for dy in [-1.45,1.45]:g.tube('linear_lamp_ceiling_supports','steel',(p.x,p.y+dy,HEIGHT-.020),(p.x,p.y+dy,HEIGHT+.012),.007);lampanchors.append([p.x,p.y+dy])
  p=point(L['projector']);g.tube('projector_ceiling_hanger','frame',(*p,2.69),(*p,HEIGHT+.015),.024);g.box('suspended_projector_body','frame',(*p,2.64),(.36,.29,.14));g.tube('projector_lens','dark',(p.x+.15,p.y,2.64),(p.x+.205,p.y,2.64),.04)
  objects=g.finish()
  for o in objects:o['roomCode']='SAL.B.01';o['destinationCollection']=COLLECTION;o['scope']='Independent same-room historical plan and photo;20student seats;estimated dimensions;not2026survey or geographic floor'
  return scene,col,objects,dict(seats=seats,tableFeet=supports,tableContacts=topcontacts,lampAnchors=lampanchors,projector=list(p),door=dict(a=list(da),b=list(db),clearWidth=(db-da).length-.05)),g.solid_proof
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
  report=dict(method='Everyactualsavedworldtriangleclippedto0.04–2.10mheightandcomplete0.44mwiderectangularcorridors;horizontalworktopsandchairsincluded',eligibleTriangles=len(surfaces),groups=groups,totalFailedSegments=len(failures),failures=failures)
  if failures:
   history=DATA/'failed-route-diagnostics.json';prior=json.loads(history.read_text())if history.exists()else[];prior.append(report);write(history,prior)
  assert not failures,('ActualSavedBodyCorridorBlocked',failures)
  return report
 def checks(objects,R):
  floor,_=tree([o for o in objects if any(k in o.name for k in ['complete_plan_floor','checker_carpet_tiles'])]);ceiling,_=tree([o for o in objects if o.name==PREFIX+'continuous_complete_ceiling']);solid,owners=tree([o for o in objects if not any(k in o.name for k in ['complete_plan_floor','checker_carpet_tiles','ceiling'])]);tops,_=tree([o for o in objects if any(k in o.name for k in ['white_tabletops','white_worktop'])]);walls,_=tree([o for o in objects if any(k in o.name for k in ['perimeter_walls','window_lower_wall','window_upper_wall','true_door_lintel'])])
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
  assert len(coverage)>1200
  doorway=[];a,b=Vector(R['door']['a']),Vector(R['door']['b']);c=(a+b)/2;u=(b-a).normalized()
  for side in [-.22,0,.22]:
   for z in [.04,.65,1.20,2.10]:
    p=c+u*side+Vector((0,.25));hit=solid.ray_cast(Vector((*p,z)),Vector((0,-1,0)),.50);assert hit[0]is None,('DoorBlocked',side,z,owners[hit[2]]if hit[2]is not None else None);doorway.append([side,z])
  windows=[]
  for w in L['windows']:
   a,b=point(w['a']),point(w['b'])
   for t in [.2,.5,.8]:
    p=a.lerp(b,t)
    for z in [1.95,2.30,2.70]:
     hit=walls.ray_cast(Vector((p.x,p.y-.25,z)),Vector((0,1,0)),.50);assert hit[0]is None,('UncutWindow',w['id'],t,z);windows.append([w['id'],t,z])
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
      q=p+n*side;hit=floor.ray_cast(Vector((*q,.04)),Vector((0,0,-1)),.08);assert hit[0]is not None;h=ceiling.ray_cast(Vector((*q,.04)),Vector((0,0,1)),HEIGHT+.10);assert h[0]is not None and h[0].z>2.1;paths.append([q.x,q.y,h[0].z])
  approaches=[]
  for route in L['routePaths']:
   p=point(route['approach']);candidates=[point(L['teacherSeat'])]if route['group']=='teacher'else[point(s['pixel'])for s in L['students']if s['id']in route['seatIds']];distance=min((p-q).length for q in candidates);assert distance<.75;approaches.append(dict(group=route['group'],distanceToNearestSeatCentre=distance))
  return dict(studentSeatCount=20,teacherSeatCount=1,UWorktopModules=8,teacherDeskCount=1,footSupportProbes=feet,tableLegToWorktopContacts=contacts,continuousCeilingCoverage=dict(spacingMetres=step,probeCount=len(coverage),missCount=0,undersideHeight=HEIGHT,pointDigest=hashlib.sha256(json.dumps(coverage).encode()).hexdigest()),realDoorClearRays=doorway,doorClearWidth=R['door']['clearWidth'],realWindowWallApertureRays=windows,lightCeilingSupportProbes=lamps,projectorHangerJoinsCeilingAndBody=True,wholeRouteSavedMeshSweep=routes,fullWidthRouteFloorAndHeadroomProbeCount=len(paths),minimumRouteCeilingHeadroom=min(p[2]for p in paths),groupApproachDistances=approaches,allAuthoredComponentsClosed=True)
 def render(scene):
  bpy.context.window.scene=scene;world=bpy.data.worlds.new(PREFIX+'previewWorld');world.use_nodes=True;world.node_tree.nodes['Background'].inputs[0].default_value=(.76,.80,.84,1);world.node_tree.nodes['Background'].inputs[1].default_value=.25;scene.world=world
  ld=bpy.data.lights.new(PREFIX+'previewArea','AREA');ld.energy=650;ld.shape='DISK';ld.size=5;lamp=bpy.data.objects.new(ld.name,ld);scene.collection.objects.link(lamp);lamp.location=(0,0,HEIGHT-.22)
  cd=bpy.data.cameras.new(PREFIX+'previewCamera');camera=bpy.data.objects.new(cd.name,cd);scene.collection.objects.link(camera);scene.camera=camera;cd.lens=17;cd.clip_end=100
  scene.render.engine='BLENDER_EEVEE';scene.eevee.taa_render_samples=24;scene.render.resolution_x=1200;scene.render.resolution_y=900;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='AgX';views=[]
  for name,pp,tp,z,tz,label in [('default',[135,184],[498,177],1.68,1.40,'SAL.B.01红椅U形桌与教学端'),('seating',[522,184],[191,185],1.68,1.35,'SAL.B.01二十席与入口窗湾')]:
   p,t=point(pp),point(tp);camera.location=(*p,z);target=Vector((*t,tz));camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler();scene.render.filepath=str(OUT/('built-'+name+'.png'));bpy.ops.render.render(write_still=True);views.append(dict(name='sal-b01-'+name+'-interior',code='SAL',spaceId='sal-b01',label=label,view=dict(position=[p.x,z,-p.y],target=[t.x,tz,-t.y],fov=76.1)))
  for o in [camera,lamp]:bpy.data.objects.remove(o,do_unlink=True)
  bpy.data.cameras.remove(cd);bpy.data.lights.remove(ld);return views
 def run():
  assert sha(BASE)==SHA;bpy.ops.wm.open_mainfile(filepath=str(BASE));update();expected=accepted_fingerprints(ROOT/'result/blender/stage228',SHA);assert len(expected)==8074 and{o.name:object_fingerprint(o)for o in bpy.data.objects}==expected
  mats={m.name:material_fingerprint(m)for m in bpy.data.materials};assert len(mats)==2141;mods={o.name:stable_modifiers(o)for o in bpy.data.objects};rooms=rooms_state();assert len(rooms)==27 and len(set(n for r in rooms for n in r['objects']))==1068;members={o.name:sorted(c.name for c in o.users_collection)for o in bpy.data.objects};vis={o.name:o.hide_render for o in bpy.data.objects};props={o.name:dict(o.items())for o in bpy.data.objects}
  scene,col,objects,records,solid=build();update();proof=checks(objects,records);views=render(scene)
  scope='依据LSE同房号历史平面与实照建立SAL.B.01独立研讨室。平面控制20学生席、1教师席、U形桌、右端教学桌、左上入口投影及两处窗湾；照片控制红色软包椅、白桌、灰方块地毯、橙灰条纹板、幕布和悬挂投影。尺度、层高、隐藏构造和高窗竖向几何估算，完整连续天花，入口至三组学生席和教师席接近点通过0.44米宽全高实体扫掠。不接校园楼层，不代表2026现状或通行认证。'
  space=dict(code='SAL',id='sal-b01',label='SAL.B.01U形研讨室',collection=COLLECTION,gallery=views[0]['name'],scope=scope,interiorView=views[0]['view'],interiorStudy=dict(kind='room-sample',label='SAL.B.01U形研讨室',scope=scope));col['authoringRecord']=json.dumps(space,ensure_ascii=False)
  fingerprints={o.name:object_fingerprint(o)for o in objects};bindings={o.name:[m.name for m in o.data.materials]for o in objects};component=OUT/'component.blend';bpy.data.libraries.write(str(component),{col},fake_user=True,compress=True)
  bpy.ops.wm.open_mainfile(filepath=str(BASE));update();assert{o.name:object_fingerprint(o)for o in bpy.data.objects}==expected
  with bpy.data.libraries.load(str(component),link=False)as(src,dst):dst.collections=[COLLECTION]
  saved=dst.collections[0];scene=bpy.data.scenes.new(SCENE);scene.collection.children.link(saved);bpy.context.window.scene=scene;update();assert checks(list(saved.all_objects),records)==proof
  assert all(object_fingerprint(bpy.data.objects[n])==v for n,v in fingerprints.items());assert all(object_fingerprint(bpy.data.objects[n])==v for n,v in expected.items());assert all(material_fingerprint(bpy.data.materials[n])==v for n,v in mats.items());assert all(stable_modifiers(bpy.data.objects[n])==v for n,v in mods.items());assert rooms_state()==rooms;assert all(sorted(c.name for c in bpy.data.objects[n].users_collection)==v for n,v in members.items());assert all(bpy.data.objects[n].hide_render==v for n,v in vis.items());assert all(dict(bpy.data.objects[n].items())==v for n,v in props.items());assert not any(n in bpy.data.scenes['00_CAMPUS_COMPLETE'].objects for n in fingerprints);assert sha(BASE)==SHA;assert all(o.parent is None and not o.constraints for o in saved.all_objects)
  verification=dict(savedComponentReopened=True,independentAcceptedObjectsVerified=8074,allOriginalMaterialNodesVerified=2141,allOriginalModifierStacksVerified=len(mods),oldSpacesPreserved=27,oldSpaceUniqueObjectsPreserved=1068,allOriginalMembershipsPropertiesVisibilityUnchanged=True,allSourceGeometryUVTransformsBindingsUnchanged=True,noNewRoomObjectInCampus=True,allOwnedObjectsParentlessNoConstraints=True,sourceNativeShaUnchanged=True,sourcePhotoNotUsedAsTexture=True,previewLightsAndCamerasExcluded=True,completeGroupRoutesRecheckedAfterReopen=True,triangles=sum(len(f.vertices)-2 for o in saved.all_objects for f in o.data.polygons))
  audit=dict(version=229,building='SAL',baseline=str(BASE.relative_to(ROOT)),baselineSha256=SHA,componentPath=str(component.relative_to(ROOT)),componentSha256=sha(component),targetCollection=COLLECTION,destinationCollection=COLLECTION,collectionSpec=dict(kind='independent-room',name=COLLECTION,scene=SCENE),space=space,addedObjects=list(fingerprints),archivedObjects=[],changedObjects=[],addedFingerprints=fingerprints,replacementMaterialBindings=bindings,sourceManifest='data/collections/salb01-room229/sources.json',planLayout='data/collections/salb01-room229/layout.json',studentSeatCount=20,teacherSeatCount=1,scaleMetresPerPixel=SCALE,roomAreaSquareMetres=L['roomAreaSquareMetres'],estimatedCeilingHeight=HEIGHT,gallerySuggestions=views,checks=proof,solidProof=solid,verification=verification,previews=['built-default.png','built-seating.png'],beforeEvidence=[PLAN,PHOTO],limitations=json.loads((DATA/'sources.json').read_text())['limitations'])
  history=DATA/'failed-route-diagnostics.json'
  audit['retainedFailedRouteDiagnostics']=dict(path=str(history.relative_to(ROOT)),attemptCount=len(json.loads(history.read_text())),interpretation='Originalleft-group shortcut stays blocked by the inward door leaf and perimeter corner. Finalleft-group route goes around the right end and behind the lower seating row;allfour finalgroup routes pass actualsavedmesh fullheightbody volumes and cornercaps.')if history.exists()else None
  write(OUT/'audit.json',audit);print('SALB01_ROOM229_READY',len(fingerprints),verification,flush=True)
 if __name__=='__main__':run()
