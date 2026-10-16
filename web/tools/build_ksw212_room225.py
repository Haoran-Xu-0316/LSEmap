"""Independent KSW.2.12 sample from the actual paired LSE plan and photograph.

Source area68m² fixes one uniform proportional scale. Heights/finishes and
concealed chair construction are estimates. No original campus is saved.
"""
from pathlib import Path
import json,hashlib,math,sys
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'result/blender/ksw212-room225'
DATA=ROOT/'data/collections/ksw212-room225'
BASE=ROOT/'result/blender/LSE_campus_detailed_v224.blend'
SHA='02714d14231c7413f3202b6d2946ffcb698da9517485afd7124202e60da5a024'
COLLECTION='KSW212_ROOM225_study'
SCENE='ROOM225_KSW212'
PREFIX='KSW212_R225_'
PHOTO='data/collections/interiors/images/16738144b776_KSW.2.12.jpg'
PLAN='data/collections/interiors/images/1872a0d8be23_KSW.2.12.GIF'

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def prepare():
 from shapely.geometry import Polygon,box
 from shapely.ops import unary_union
 # Inner-face source trace. The curved end bay is part of the room,not a corridor.
 outline=[[2,18],[8,18],[8,4],[94,4],[94,14],[207,14],[207,4],[296,4],[296,35],[291,35],[291,42],[296,42],[296,104],[289,104],[289,111],[296,111],[296,139],[291,139],[291,169],[289,169],[289,175],[296,175],[296,238],[289,238],[289,245],[296,245],[296,270],[291,270],[291,301],[289,301],[289,308],[296,308],[296,370],[289,370],[289,381],[261,408]]
 # Rounded projecting bay,centred approximately at(195,463),radius86px.
 arc_angles=sorted(set([-39+i*174/24 for i in range(25)]+[20,55]));arc=[[195+86*math.cos(math.radians(a)),463+86*math.sin(math.radians(a))]for a in arc_angles]
 outline += arc
 outline += [[127,548],[120,548],[120,550],[58,550],[58,543],[49,543],[49,548],[41,548],[41,543],[2,543]]
 polygon=Polygon(outline).buffer(0);assert polygon.geom_type=='Polygon';scale=math.sqrt(68/polygon.area)
 def point(p):return[(p[1]-280)*scale,(p[0]-148)*scale]
 tables=[dict(id='A',centre=[107,86],high=False,outline=[[89,51],[103,52],[122,66],[136,82],[143,100],[139,108],[119,114],[97,117],[80,113],[77,105],[78,84],[83,64]],seats=[[74,61],[66,86],[120,47],[141,69],[103,123],[127,118]]),dict(id='B',centre=[222,80],high=True,outline=[[189,67],[217,48],[236,44],[244,48],[249,70],[251,94],[247,108],[241,111],[221,108],[198,99],[187,89],[184,81]],seats=[[190,61],[215,43],[258,66],[259,91],[191,102],[216,117]]),dict(id='C',centre=[225,199],high=False,outline=[[221,158],[231,161],[247,178],[258,201],[259,213],[254,222],[232,225],[209,225],[193,219],[191,210],[198,187],[210,168]],seats=[[201,162],[184,185],[248,162],[265,188],[209,234],[236,233]]),dict(id='D',centre=[222,335],high=False,outline=[[187,327],[201,315],[220,306],[238,303],[246,307],[250,328],[251,351],[248,365],[239,367],[217,361],[196,348],[184,337]],seats=[[192,312],[216,294],[259,323],[259,348],[192,353],[215,370]]),dict(id='E',centre=[112,370],high=False,outline=[[76,358],[93,348],[118,341],[132,342],[139,352],[141,376],[139,396],[134,409],[126,411],[104,401],[84,387],[72,373]],seats=[[84,341],[109,332],[151,365],[149,391],[78,395],[103,412]]),dict(id='F',centre=[202,459],high=True,outline=[[182,426],[201,428],[225,435],[239,443],[241,453],[230,472],[213,489],[197,497],[188,494],[180,474],[176,451],[177,434]],seats=[[162,447],[164,475],[194,419],[222,427],[241,471],[223,493]])]
 for t in tables:t['worldOutline']=[point(p)for p in t['outline']];t['worldCentre']=point(t['centre']);t['worldSeats']=[point(p)for p in t['seats']]
 loose=[dict(centre=p,target=[120,190]if i<3 else[139,282])for i,p in enumerate([[125,171],[95,193],[141,203],[116,274],[160,267],[143,301]])]
 for c in loose:c['worldCentre']=point(c['centre']);c['worldTarget']=point(c['target'])
 metric=Polygon([point(p)for p in outline]);assert metric.is_valid
 # The photograph shows one continuous acoustic tile ceiling,without long openings.
 x0,y0,x1,y1=metric.bounds;bands=[box(x0-1,y0-1,x1+1,y0+.46),box(x0-1,y1-.46,x1+1,y1+1),box(x0-1,y0-1,x0+.42,y1+1),box(x1-.42,y0-1,x1+1,y1+1)]
 lights=[]
 for x in [-4.2,-1.8,.6,3.0]:
  bands.append(box(x-.34,y0-1,x+.34,y1+1))
  for y in [-1.9,1.55]:
   if metric.buffer(-.45).covers(box(x-.3,y-.3,x+.3,y+.3)):lights.append([x,y])
 ceiling_parts=[metric]
 grid_parts=[]
 for axis,lo,hi in [(0,x0,x1),(1,y0,y1)]:
  for index in range(math.ceil(lo/.60),math.floor(hi/.60)+1):
   coordinate=index*.60
   stripe=box(coordinate-.004,y0-1,coordinate+.004,y1+1)if axis==0 else box(x0-1,coordinate-.004,x1+1,coordinate+.004)
   clipped=metric.intersection(stripe)
   if clipped.is_empty:continue
   for part in ([clipped]if clipped.geom_type=='Polygon'else clipped.geoms):
    if part.geom_type=='Polygon'and part.area>.000001:grid_parts.append(list(part.exterior.coords))
 # These bounds lie on the actual wall/window line or on its simple curve chord.
 windows=[dict(id='right1',a=[296,42],b=[296,104]),dict(id='right2',a=[296,175],b=[296,238]),dict(id='right3',a=[296,308],b=[296,370]),dict(id='end',a=[58,550],b=[120,550]),*[dict(id='bay',a=a,b=b)for a,b,aa,bb in zip(arc,arc[1:],arc_angles,arc_angles[1:])if aa>=20-1e-6 and bb<=55+1e-6]]
 door=dict(a=[2,217],b=[2,259],openTip=[45,217])
 layout=dict(room='KSW.2.12',sourcePlan=PLAN,sourcePhoto=PHOTO,planAreaSquareMetres=68,scaleMetresPerPixel=scale,scaleBasis='Uniform trace scaled to printed68m²;not a measured survey',outlinePixels=outline,outline=[point(p)for p in outline],tables=tables,loose=loose,door=door,windows=windows,ceilingParts=[list(p.exterior.coords)for p in ceiling_parts],ceilingGridParts=grid_parts,lights=lights,studentSeatCount=42,groupedChairs=36,looseChairs=6)
 tiles=[]
 for i in range(math.floor(x0/.5),math.ceil(x1/.5)):
  for j in range(math.floor(y0/.5),math.ceil(y1/.5)):
   part=metric.intersection(box(i*.5,j*.5,(i+1)*.5,(j+1)*.5))
   if not part.is_empty and part.area>.000001:
    for poly in ([part]if part.geom_type=='Polygon'else part.geoms):tiles.append(dict(outline=list(poly.exterior.coords),material='carpet'+['A','B','C'][(i+2*j)%3]))
 layout['carpetTiles']=tiles
 (DATA/'layout.json').write_text(json.dumps(layout,indent=2)+'\n');print('KSW212_PLAN',scale,metric.area,len(tables),len(loose),flush=True)

try:import bpy
except ModuleNotFoundError:
 if __name__=='__main__':prepare()
else:
 from mathutils import Vector
 sys.path.insert(0,str(ROOT/'web/tools'))
 from build_room_samples167 import RoomGeometry
 from integrate_exterior_round194 import object_fingerprint,accepted_fingerprints,update_scene
 from refine_portsmouth_exterior207 import material_fingerprint
 from refine_sal_structure221 import stable_modifiers,rooms_state
 L=json.loads((DATA/'layout.json').read_text());S=L['scaleMetresPerPixel']
 def point(p):return Vector(((p[1]-280)*S,(p[0]-148)*S))
 def material(g,key,color,rough=.7,metal=0):
  m=bpy.data.materials.new(PREFIX+key);m.use_nodes=True;m.diffuse_color=(*color,1);n=m.node_tree.nodes['Principled BSDF'];n.inputs['Base Color'].default_value=m.diffuse_color;n.inputs['Roughness'].default_value=rough;n.inputs['Metallic'].default_value=metal;g.materials[key]=m;return m
 def span(g,family,key,a,b,lo,hi,depth=.14):
  a,b=Vector(a),Vector(b);d=b-a;c=(a+b)/2;g.box(family,key,(*c,(lo+hi)/2),(d.length,depth,hi-lo),math.atan2(d.y,d.x))
 def chair(g,p,target,high=False,loose=False):
  p,t=Vector(p),Vector(target);angle=math.atan2(t.y-p.y,t.x-p.x)+math.pi/2;c,s=math.cos(angle),math.sin(angle);seat=.69 if high else .45
  def at(a,b,z):return(p.x+c*a-s*b,p.y+s*a+c*b,z)
  g.box('dark_chair_seats','cushion',at(0,0,seat),(.43,.43,.05),angle)
  # Real horizontal hand slot in the white back;four closed pieces surround it.
  by=.225;low=seat+.07;top=seat+.49;slotlo=seat+.17;slothi=slotlo+.040
  for x,w in [(-.145,.15),(.145,.15)]:g.box('slotted_white_chair_backs','shell',at(x,by,(low+top)/2),(w,.045,top-low),angle)
  for z,h in [((low+slotlo)/2,slotlo-low),((slothi+top)/2,top-slothi)]:g.box('slotted_white_chair_backs','shell',at(0,by,z),(.14,.045,h),angle)
  feet=[]
  for x in [-.205,.205]:
   for y in [-.205,.205]:
    foot=at(x*1.13,y*1.13,.016);g.tube('chrome_chair_legs','chrome',foot,at(x,y,seat-.025),.016);feet.append(list(foot))
  for x in [-.205,.205]:g.tube('chrome_chair_back_supports','chrome',at(x,.17,seat-.02),at(x,.225,seat+.24),.012)
  if high:
   for y in [-.20,.20]:g.tube('high_chair_footrails','chrome',at(-.23,y,.27),at(.23,y,.27),.012)
  return dict(centre=list(p),target=list(t),high=high,loose=loose,feet=feet,seatHeight=seat)
 def build():
  scene=bpy.data.scenes.new(SCENE);collection=bpy.data.collections.new(COLLECTION);scene.collection.children.link(collection);collection['roomSample']=True;collection['roomCode']='KSW.2.12';g=RoomGeometry(collection,PREFIX)
  for k,col,r,m in [('plaster',(.72,.72,.66),.86,0),('shell',(.77,.79,.76),.48,0),('cushion',(.025,.035,.037),.85,0),('chrome',(.40,.43,.43),.28,.72),('tablewhite',(.78,.79,.75),.55,0),('tablegrey',(.16,.18,.18),.6,0),('carpetA',(.105,.12,.12),.94,0),('carpetB',(.15,.17,.17),.94,0),('carpetC',(.19,.21,.21),.94,0),('ceiling',(.71,.72,.68),.9,0),('grid',(.48,.50,.48),.7,0),('darkframe',(.035,.045,.045),.5,0),('glassroom',(.38,.48,.50),.14,0),('curtain',(.025,.06,.065),.91,0),('doorwood',(.34,.21,.11),.72,0),('screenblack',(.006,.009,.012),.36,0),('vision',(.15,.22,.22),.20,0)]:material(g,k,col,r,m)
  g.prism('complete_plan_floor','carpetA',L['outline'],-.13,.127)
  for tile in L['carpetTiles']:g.prism('source_photo_carpet_tiles',tile['material'],tile['outline'],-.003,.003)
  # Broad alternating tile bands reproduce the photograph's quiet carpet grid.
  from mathutils.geometry import tessellate_polygon
  # Floor pattern is authored geometry,never a source photograph texture.

  door_a,door_b=point(L['door']['a']),point(L['door']['b']);door_mid=(door_a+door_b)/2
  window_segments=[(point(w['a']),point(w['b']))for w in L['windows']]
  # Wall runs split exactly at the planned left doorway and straight window apertures.
  polygon=L['outline'];door_records=[]
  for i,(a,b)in enumerate(zip(polygon,polygon[1:]+polygon[:1])):
   a,b=Vector(a),Vector(b);d=b-a;length=d.length
   if length<.001:continue
   events=[(0.,1.,'wall')]
   candidates=[(door_a,door_b,'door')]+[(u,v,'window')for u,v in window_segments]
   for u,v,kind in candidates:
    if abs(d.cross(u-a))>.0001 or abs(d.cross(v-a))>.0001:continue
    lo,hi=sorted(((u-a).dot(d)/d.length_squared,(v-a).dot(d)/d.length_squared))
    if lo<-.001 or hi>1.001:continue
    updated=[]
    for s,e,k in events:
     if k!='wall'or hi<=s or lo>=e:updated.append((s,e,k));continue
     if s<lo:updated.append((s,lo,'wall'))
     updated.append((max(lo,s),min(hi,e),kind))
     if hi<e:updated.append((hi,e,'wall'))
    events=updated
   for s,e,kind in events:
    p,q=a+d*s,a+d*e
    if kind!='door':span(g,'perimeter_skirting','darkframe',p,q,0,.09,.035)
    if kind=='wall':span(g,'full_perimeter_walls','plaster',p,q,.09,2.91)
    elif kind=='door':span(g,'door_lintel_wall','plaster',p,q,2.23,2.91)
    else:span(g,'window_lower_wall','plaster',p,q,.09,.84);span(g,'window_upper_wall','plaster',p,q,2.68,2.91)
  # Source rounded bay glazing occupies its actual curved run,not the floor centre.
  # The bay's estimated reveal is represented by two adjoining source-trace segments.
  for w in L['windows']:
   a,b=point(w['a']),point(w['b']);d=b-a;u=d.normalized();n=Vector((-u.y,u.x));mid=(a+b)/2;roomcentre=Vector((0,0));inward=n if n.dot(roomcentre-mid)>0 else-n
   for p in [a,b]:span(g,'window_side_frames','white',p-u*.025,p+u*.025,.82,2.70,.105)
   span(g,'window_sills','white',a,b,.80,.86,.23)
   for z in [.87,1.78,2.66]:span(g,'window_cross_frames','white',a,b,z-.026,z+.026,.08)
   for f in ([]if w['id']=='bay'else[1/3,2/3]):
    p=a+d*f;span(g,'window_vertical_frames','white',p-u*.022,p+u*.022,.87,2.66,.08)
   span(g,'restrained_window_glass','glassroom',a+inward*.017,b+inward*.017,.88,2.64,.013)
   # White mullions retain openings;curtain folds sit just inside their jambs.
   for side,p in enumerate([a,b]):
    for j in range(4):
     offset=(j-.5)*.043*(1 if side==0 else-1);c=p+u*offset+inward*(.14+.025*(j%2));span(g,'dark_teal_curtain_folds','curtain',c-u*.027,c+u*.027,.77,2.79,.055)
  for p in [door_a,door_b]:span(g,'door_jambs','doorwood',p-Vector((.027,0)),p+Vector((.027,0)),0,2.26,.16)
  span(g,'door_header','doorwood',door_a,door_b,2.21,2.27,.16)
  # Plan shows the door leaf opening into the room at the upper jamb.
  tip=point(L['door']['openTip']);delta=tip-door_a;pa=door_a+delta*.35;pb=door_a+delta*.47
  for p,q in [(door_a,pa),(pb,tip)]:span(g,'open_door_leaf','doorwood',p,q,.035,2.21,.045)
  for lo,hi in [(.035,.92),(1.88,2.21)]:span(g,'open_door_leaf','doorwood',pa,pb,lo,hi,.045)
  span(g,'door_vision_panel','vision',pa,pb,.92,1.88,.013)
  door_records.append(dict(jambs=[list(door_a),list(door_b)],openLeafTip=list(tip),width=(door_b-door_a).length,clearWidth=(door_b-door_a).length-.054))
  # Two display panels flank the actual plan doorway on the teaching wall.
  for py,width in [(163,1.33),(362,1.42)]:
   x,y=point([2,py]);g.box('two_display_frames','darkframe',(x,y+.105,1.88),(width,.095,.93));g.box('two_blank_teaching_displays','screenblack',(x,y+.162,1.88),(width-.06,.025,.87))
  x,y=point([51,436]);g.box('teaching_AV_cabinet','darkframe',(x,y,.43),(.45,.54,.86));g.box('teaching_AV_worktop','tablegrey',(x,y,.89),(.55,.62,.06));g.box('AV_monitor_stand','chrome',(x,y,1.06),(.07,.06,.28));g.box('AV_monitor','screenblack',(x,y,1.27),(.42,.06,.28))
  seats=[];legs=[]
  for table in L['tables']:
   top=1.035 if table['high']else .755;key='tablegrey'if table['high']else'tablewhite';g.prism('two_high_grey_tables'if table['high']else'four_white_collaboration_tables',key,table['worldOutline'],top-.045,.045);center=Vector(table['worldCentre'])
   for j in range(3):
    angle=j*math.tau/3;direction=Vector((math.cos(angle),math.sin(angle)));p=center+direction*.30;foot=center+direction*.46;g.tube('table_chrome_supports','chrome',(*foot,.025),(*p,top-.035),.025);legs.append(dict(foot=[*foot,.025],top=[*p,top-.035]))
   for p in table['worldSeats']:seats.append(chair(g,p,center,table['high']))
  for c in L['loose']:seats.append(chair(g,c['worldCentre'],c['worldTarget'],loose=True))
  # Full closed ceiling slab covers the entire room projection. Fine8mmribbons
  # express tile joints below the slab;they are not openings or light sources.
  for ring in L['ceilingParts']:g.prism('continuous_acoustic_ceiling','ceiling',ring,2.91,.075)
  for ring in L['ceilingGridParts']:g.prism('fine_ceiling_grid_seams','grid',ring,2.905,.006)
  for x,y in L['lights']:
   g.box('recessed_light_housings','grid',(x,y,2.90),(.62,.62,.06));g.box('ceiling_light_diffusers','light',(x,y,2.863),(.55,.55,.025))
  objects=g.finish()
  for obj in objects:obj['roomCode']='KSW.2.12';obj['destinationCollection']=COLLECTION;obj['scope']='Independent paired-source historical sample;not geographically registered,not2026survey'
  return scene,collection,objects,seats,legs,door_records,g.solid_proof

 def tree(objects):
  from mathutils.bvhtree import BVHTree
  vs=[];fs=[];owners=[]
  for o in objects:
   if o.type!='MESH':continue
   offset=len(vs);vs.extend(o.matrix_world@v.co for v in o.data.vertices);fs.extend(tuple(offset+i for i in p.vertices)for p in o.data.polygons);owners +=[o.name]*len(o.data.polygons)
  return BVHTree.FromPolygons(vs,fs),owners
 def checks(objects,seats,legs,doors):
  floor,_=tree([o for o in objects if o.name in [PREFIX+'complete_plan_floor',PREFIX+'source_photo_carpet_tiles']]);solid,owners=tree([o for o in objects if not any(k in o.name for k in ['complete_plan_floor','source_photo_carpet_tiles','light','ceiling','skirting'])]);feet=[]
  for label,ps in [('chair',[p for s in seats for p in s['feet']]),('table',[r['foot']for r in legs])]:
   for p in ps:
    hit=floor.ray_cast(Vector((p[0],p[1],.04)),Vector((0,0,-1)),.08);assert hit[0]is not None,('Foot outside source room',label,p);feet.append(dict(kind=label,point=p,floorZ=hit[0].z))
  d=doors[0];a,b=map(Vector,d['jambs']);mid=(a+b)/2;door=[]
  for dx in [-.20,0,.20]:
   for z in [.04,.20,1.2,2.07]:
    hit=solid.ray_cast(Vector((mid.x+dx,mid.y-.40,z)),Vector((0,1,0)),1.65);assert hit[0]is None,('Doorway blocked',dx,z,owners[hit[2]]if hit[2]is not None else None);door.append([dx,z])
  paths=[]
  # Source teaching-wall strip and the clear route from the true door into the central commons.
  for p,q in [([25,45],[25,205]),([25,270],[25,410]),([2,238],[72,238]),([72,238],[95,242])]:
   a,b=point(p),point(q);count=max(2,math.ceil((b-a).length/.16))
   for i in range(count+1):
    c=a.lerp(b,i/count);hit=floor.ray_cast(Vector((*c,.04)),Vector((0,0,-1)),.08);assert hit[0]is not None
    # Three swept body-height centreline rays detect furniture,legs and leaf intrusion.
    for h in [.22,.65,1.2]:
     end=c+Vector((.001,0));hit=solid.ray_cast(Vector((c.x-.22,c.y,h)),Vector((1,0,0)),.44);assert hit[0]is None,('Blocked planned route',p,q,list(c),h,owners[hit[2]]if hit[2]is not None else None)
    paths.append(list(c))
  ceiling,_=tree([o for o in objects if o.name==PREFIX+'continuous_acoustic_ceiling']);lights=[]
  for p in L['lights']:
   hit=ceiling.ray_cast(Vector((*p,2.89)),Vector((0,0,1)),.06);assert hit[0]is not None;lights.append(dict(position=p,actualCeilingUnderside=hit[0].z))
  def inside(x,y):
   hit=False;ring=L['outline']
   for a,b in zip(ring,ring[1:]+ring[:1]):
    if (a[1]>y)!=(b[1]>y)and x<(b[0]-a[0])*(y-a[1])/(b[1]-a[1])+a[0]:hit=not hit
   return hit
  xs=[p[0]for p in L['outline']];ys=[p[1]for p in L['outline']];spacing=.20;coverage=[]
  for i in range(math.floor(min(xs)/spacing),math.ceil(max(xs)/spacing)):
   for j in range(math.floor(min(ys)/spacing),math.ceil(max(ys)/spacing)):
    x,y=(i+.5)*spacing,(j+.5)*spacing
    if not inside(x,y):continue
    hit=ceiling.ray_cast(Vector((x,y,1.5)),Vector((0,0,1)),1.5)
    assert hit[0]is not None and abs(hit[0].z-2.91)<.001,('Missing actual ceiling coverage',x,y,hit)
    coverage.append([x,y,hit[0].z])
  assert len(coverage)>1500
  ceiling_proof=dict(method='Upward rays against saved continuous-ceilingmesh,entire roominteriorregulargrid',spacingMetres=spacing,probeCount=len(coverage),missCount=0,actualUndersideHeightRange=[min(p[2]for p in coverage),max(p[2]for p in coverage)],pointDigest=hashlib.sha256(json.dumps(coverage).encode()).hexdigest(),noRoofOpening=True)
  return dict(continuousCeilingCoverage=ceiling_proof,chairCount=len(seats),groupedChairs=sum(not s['loose']for s in seats),looseChairs=sum(s['loose']for s in seats),footSupportProbes=feet,doorwayClearRays=door,doorClearWidth=d['clearWidth'],clearPublicRouteProbes=paths,lightCeilingSupport=lights,closedGeometry=True)
 def render(scene,label):
  bpy.context.window.scene=scene;world=bpy.data.worlds.new(PREFIX+'world');world.use_nodes=True;world.node_tree.nodes['Background'].inputs[0].default_value=(.76,.80,.84,1);world.node_tree.nodes['Background'].inputs[1].default_value=.55;scene.world=world
  ld=bpy.data.lights.new(PREFIX+'area','AREA');ld.energy=700;ld.shape='DISK';ld.size=5;lamp=bpy.data.objects.new(ld.name,ld);scene.collection.objects.link(lamp);lamp.location=(0,0,2.76)
  cd=bpy.data.cameras.new(PREFIX+'camera');camera=bpy.data.objects.new(cd.name,cd);scene.collection.objects.link(camera);scene.camera=camera;cd.lens=19;cd.clip_end=100
  scene.render.engine='BLENDER_EEVEE';scene.eevee.taa_render_samples=32;scene.render.resolution_x=1200;scene.render.resolution_y=900;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='AgX'
  views=[]
  for name,pp,tp,z,tz in [('default',[260,491],[38,205],1.78,1.15),('teaching-wall',[251,258],[2,258],1.76,1.45)]:
   p,t=point(pp),point(tp);camera.location=(*p,z);target=Vector((*t,tz));camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler();scene.render.filepath=str(OUT/(label+'-'+name+'.png'));bpy.ops.render.render(write_still=True)
   views.append(dict(name='ksw-212-'+name+'-interior',label='KSW.2.12协作桌与侧窗'if name=='default'else'KSW.2.12双屏教学墙',view=dict(position=[p.x,z,-p.y],target=[t.x,tz,-t.y],fov=70.85)))
  for o in [camera,lamp]:bpy.data.objects.remove(o,do_unlink=True)
  bpy.data.cameras.remove(cd);bpy.data.lights.remove(ld);return views
 def run():
  assert sha(BASE)==SHA;bpy.ops.wm.open_mainfile(filepath=str(BASE));update_scene();expected=accepted_fingerprints(ROOT/'result/blender/stage224',SHA);original={o.name:object_fingerprint(o)for o in bpy.data.objects};assert original==expected and len(original)==7763
  mats={m.name:material_fingerprint(m)for m in bpy.data.materials};mods={o.name:stable_modifiers(o)for o in bpy.data.objects};rooms=rooms_state();assert len(rooms)==21;members={o.name:sorted(c.name for c in o.users_collection)for o in bpy.data.objects};vis={o.name:o.hide_render for o in bpy.data.objects}
  scene,col,owned,seats,legs,doors,solid=build();update_scene();proof=checks(owned,seats,legs,doors);assert proof['chairCount']==42;views=render(scene,'built')
  scope='依据LSE同房号历史平面与实照建立KSW.2.12独立协作教室样本。按68㎡统一比例描摹完整周界、弧形端窗与真实门洞，保留6组六席三角桌和6个独立座位；两组星号高桌、深色座垫白壳椅、双屏教学墙及侧窗帘按实照估算。层高、家具细节与照片年代差异未实测，不接地理楼层，不表示2026当前全楼。'
  space=dict(code='KSW',id='ksw-212',label='KSW.2.12协作教室',collection=COLLECTION,gallery=views[0]['name'],scope=scope,interiorView=views[0]['view'],interiorStudy=dict(kind='room-sample',label='KSW.2.12协作教室',scope=scope));col['authoringRecord']=json.dumps(space,ensure_ascii=False)
  fingerprints={o.name:object_fingerprint(o)for o in owned};bindings={o.name:[m.name for m in o.data.materials]for o in owned};component=OUT/'component.blend';bpy.data.libraries.write(str(component),{col},fake_user=True,compress=True)
  bpy.ops.wm.open_mainfile(filepath=str(BASE));update_scene();assert{o.name:object_fingerprint(o)for o in bpy.data.objects}==expected
  with bpy.data.libraries.load(str(component),link=False)as(src,dst):dst.collections=[COLLECTION]
  saved=dst.collections[0];scene=bpy.data.scenes.new(SCENE);scene.collection.children.link(saved);bpy.context.window.scene=scene;update_scene();assert checks(list(saved.all_objects),seats,legs,doors)==proof
  assert all(object_fingerprint(bpy.data.objects[n])==v for n,v in fingerprints.items());assert all(object_fingerprint(bpy.data.objects[n])==v for n,v in original.items());assert all(material_fingerprint(bpy.data.materials[n])==v for n,v in mats.items());assert all(stable_modifiers(bpy.data.objects[n])==v for n,v in mods.items());assert rooms_state()==rooms;assert all(sorted(c.name for c in bpy.data.objects[n].users_collection)==v for n,v in members.items());assert all(bpy.data.objects[n].hide_render==v for n,v in vis.items());assert not any(n in bpy.data.scenes['00_CAMPUS_COMPLETE'].objects for n in fingerprints);assert sha(BASE)==SHA
  verification=dict(savedComponentReopened=True,independentAcceptedObjectsVerified=len(original),allOriginalMaterialNodesVerified=len(mats),allOriginalModifierStacksVerified=len(mods),oldSpacesPreserved=len(rooms),oldSpaceUniqueObjectsPreserved=len(set(n for r in rooms for n in r['objects'])),allOriginalMembershipsUnchanged=True,allSourceGeometryUVTransformsBindingsUnchanged=True,allOriginalVisibilityUnchanged=True,noNewRoomObjectInCampus=True,sourceNativeShaUnchanged=True,sourcePhotoNotUsedAsTexture=True,triangles=sum(len(f.vertices)-2 for o in saved.all_objects for f in o.data.polygons))
  old=json.loads((DATA/'ceiling-before-state.json').read_text())['addedFingerprints'];allowed={PREFIX+'sectioned_acoustic_ceiling'}
  assert all(fingerprints.get(n)==v for n,v in old.items()if n not in allowed), 'Unrelatedsamplegeometrychanged'
  verification['allPriorNonCeilingSampleFingerprintsUnchanged']=True
  audit=dict(version=225,building='KSW',baseline=str(BASE.relative_to(ROOT)),baselineSha256=SHA,componentPath=str(component.relative_to(ROOT)),componentSha256=sha(component),targetCollection=COLLECTION,destinationCollection=COLLECTION,collectionSpec=dict(kind='independent-room',name=COLLECTION,scene=SCENE),space=space,addedObjects=list(fingerprints),archivedObjects=[],changedObjects=[],addedFingerprints=fingerprints,replacementMaterialBindings=bindings,sourceManifest='data/collections/ksw212-room225/sources.json',planLayout='data/collections/ksw212-room225/layout.json',studentSeatCount=42,groupedSeats=36,looseSeats=6,scaleMetresPerPixel=S,roomAreaSquareMetres=68,estimatedCeilingHeight=2.91,gallerySuggestions=views,checks=proof,solidProof=solid,verification=verification,previews=['before-ceiling-default.png','built-default.png','built-teaching-wall.png'],previewLighting='One temporaryreviewArea belowtheceilingat2.76m;noexportedlightorprivatepreviewgeometry',ceilingCorrection=dict(beforeComponentSha256=json.loads((DATA/'ceiling-before-state.json').read_text())['componentSha256'],scope='Continuousceilingandfinejoints only;allfurniture,windows,doors,carpetand42seatsheldexact'),limitations=['Plan/photo capture dates unknown;2022recordrefresh is not creation date or2026currentlayout.','Uniform area-based scale,2.91mceiling,0.755/1.035mtables,0.45/0.69mseat heights,window heights and concealed furniture construction are estimates.','42symbols are historical plan seats,not certified current capacity.6loose chairs are kept as independentplanpositions.','The drawing star symbols are interpreted as the photograph-supported grey high-table type;exact equipment and furniture chronology unverified.','Ceiling is a continuous solid slab over the complete roomoutline,with8mmestimatedtilejoints andretainedlights;no longitudinalroofopenings.','Windows use restrained dark reflective finish;no source photograph or fabricatedoutsideview is published as texture.','Independent room shares no old room geometry and is not placed in geographicSAL/KSWpublicfloors.'])
  (OUT/'audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n');print('KSW212_ROOM225_READY',len(fingerprints),verification,flush=True)
 if __name__=='__main__':run()
