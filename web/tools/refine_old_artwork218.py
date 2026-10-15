"""Photo-guided shallow plastic-mesh Final Sale, using actual open geometry.

The undated engineer photograph controls front silhouettes. All depth, rear
shape and pixel-to-metre registration remain authoring estimates. Private
photographs are inspection evidence only and never become public textures.
Fixed configuration; run with the existing MachineLearning Python environment.
"""
from pathlib import Path
import hashlib,json,math,sys
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'result/blender/old-artwork218'
BASE=ROOT/'result/blender/LSE_campus_detailed_v217.blend'
SHA='daac71eaf581c94e544fe7098e51f897273223a981bd8f1b4b637d56d4469423'
PREFIX='OLDART218_'
SOURCES=dict(figures='OLD_NEXT_EXTERIOR154_V111_lattice_figures',products='OLD_NEXT_EXTERIOR154_V111_lattice_products',display_frame='OLD_NEXT_EXTERIOR154_D5_finalsale84_display_frame',containers='OLD_NEXT_EXTERIOR154_D5_finalsale84_containers')
# Coordinates refer to private reference-engineer-crop.jpg, not a texture UV.
FIGURES=[
 dict(name='left walking shopper',head=(122,219,11,12),depth=35.77,outline=[(112,232),(130,232),(141,246),(140,264),(134,280),(140,293),(138,315),(129,334),(138,346),(125,367),(123,384),(144,397),(145,404),(130,406),(114,397),(104,378),(105,355),(99,376),(95,394),(108,401),(100,407),(85,399),(78,385),(85,363),(91,344),(77,337),(71,325),(81,310),(85,286),(92,263),(99,247)],folds=[[(125,237),(100,272),(87,313)],[(134,258),(110,299),(81,329)],[(137,304),(113,332),(94,342)],[(128,341),(112,364),(120,389)]],arms=[[(132,245),(142,263),(140,278),(156,291)],[(107,246),(113,268),(132,286),(153,300)]]),
 dict(name='partly occluded rear shopper',head=(198,223,10,12),depth=35.65,outline=[(187,237),(202,237),(213,250),(215,269),(205,285),(195,296),(187,317),(190,337),(182,358),(175,381),(191,396),(190,403),(176,405),(165,395),(161,381),(168,357),(169,335),(160,311),(169,291),(173,268),(177,250)],folds=[[(191,240),(176,280),(166,307)],[(204,256),(187,301),(179,347)]],arms=[]),
 dict(name='front basket shopper',head=(232,226,11,12),depth=35.79,outline=[(225,239),(237,238),(241,251),(239,267),(247,279),(244,291),(231,297),(226,315),(233,338),(225,358),(220,382),(225,395),(242,397),(242,404),(229,407),(215,401),(207,388),(208,372),(212,349),(205,329),(198,348),(190,371),(186,390),(202,399),(199,405),(185,405),(172,394),(178,375),(186,347),(190,325),(192,302),(194,283),(205,258),(214,244)],folds=[[(227,244),(210,271),(198,294)],[(237,278),(217,306),(216,333)],[(225,334),(213,356),(216,383)],[(203,325),(189,367)]],arms=[[(216,250),(205,267),(213,279),(231,287)],[(236,251),(231,270),(242,286)]]),
 dict(name='central reaching shopper',head=(285,190,12,13),depth=35.75,outline=[(271,204),(292,203),(310,195),(322,183),(330,169),(332,156),(338,145),(343,146),(341,161),(340,176),(332,194),(321,210),(312,225),(315,247),(308,265),(306,282),(317,298),(315,318),(306,332),(307,338),(296,339),(292,329),(300,312),(292,302),(280,319),(275,341),(273,359),(268,372),(260,372),(253,362),(256,340),(252,321),(250,300),(248,278),(253,255),(258,235),(258,217),(254,205),(255,192),(260,182),(262,174),(268,176),(266,190),(267,202)],folds=[[(330,185),(310,211),(263,243)],[(313,218),(279,253),(253,271)],[(302,248),(278,288),(264,343)],[(295,276),(278,309),(270,357)],[(270,212),(268,236)]],arms=[]),
 dict(name='raised arms shopper',head=(425,156,12,13),depth=35.76,outline=[(413,170),(405,173),(396,163),(392,146),(388,131),(386,116),(381,110),(377,112),(380,126),(381,145),(385,164),(394,180),(405,187),(412,196),(409,213),(396,225),(389,241),(381,253),(385,268),(395,279),(387,294),(381,306),(386,312),(396,309),(402,298),(410,290),(413,279),(420,284),(424,306),(426,330),(425,345),(435,352),(441,348),(440,338),(442,317),(440,296),(444,275),(441,255),(441,235),(435,218),(439,199),(442,187),(453,178),(463,169),(469,158),(472,144),(468,134),(465,134),(463,147),(457,158),(445,168),(434,172)],folds=[[(438,212),(417,223),(397,239)],[(438,229),(419,249),(393,263)],[(437,246),(425,274),(431,320)],[(409,232),(396,257),(407,277)],[(410,182),(429,186)]],arms=[]),
 dict(name='right basket shopper',head=(482,219,11,13),depth=35.78,outline=[(472,232),(489,232),(497,244),(500,262),(509,280),(518,297),(516,307),(506,309),(499,294),(493,282),(497,307),(507,328),(522,348),(528,358),(522,365),(510,367),(506,381),(500,394),(486,405),(476,406),(477,399),(490,388),(493,369),(484,349),(475,364),(473,384),(469,399),(458,404),(447,403),(445,399),(456,394),(461,381),(463,362),(457,340),(461,318),(459,297),(462,278),(458,263),(459,249),(465,241)],folds=[[(479,237),(465,260),(462,275)],[(493,258),(474,288),(466,318)],[(495,292),(484,320),(515,355)],[(472,312),(475,341),(467,383)],[(485,331),(498,364),(497,388)]],arms=[[(468,248),(462,269),(476,279),(491,276)],[(492,245),(496,265),(491,283),(500,307)]])]


def make_plan():
 from shapely.geometry import Polygon,LineString,Point
 from shapely.ops import unary_union
 from PIL import Image,ImageDraw
 OUT.mkdir(parents=True,exist_ok=True)
 Image.open(ROOT/'data/collections/campus_photos_round2/images/OLD/OLD_old_webbyates_01.jpg').crop((680,265,1275,735)).save(OUT/'reference-engineer-crop.jpg')
 Image.open(ROOT/'data/collections/old-user-reference/final-sale-front.jpg').crop((60,80,955,663)).save(OUT/'reference-artist-crop.jpg')
 # Preserve the inherited protective arch envelope and do not resize the artwork
 # to catalogue dimensions. Image registration is a visual estimate.
 x0=-85.22667121887207; sx=5.4565112590789795/504; sz=3.318953514099121/359
 def point(x,y,d):return [x0+(x-62)*sx,d,3.576046943664551+(421-y)*sz]
 batches={k:dict(vertices=[],faces=[])for k in SOURCES};stats=[]
 def strip(role,coords,width,depth,surface=None):
  if len(coords)<2:return
  verts=batches[role]['vertices'];faces=batches[role]['faces'];start=len(verts)
  # Resample the line so the actual mesh can follow shallow garment folds.
  line=LineString(coords);count=max(1,math.ceil(line.length/4));pts=[line.interpolate(i/count,normalized=True)for i in range(count+1)]
  for i,p in enumerate(pts):
   prev=pts[max(0,i-1)];nxt=pts[min(count,i+1)];dx=nxt.x-prev.x;dy=nxt.y-prev.y;length=max(.0001,math.hypot(dx,dy));nx=-dy/length*width/2;ny=dx/length*width/2
   for sign in [-1,1]:
    x=p.x+nx*sign;y=p.y+ny*sign;d=surface(x,y)if surface else depth;verts.append(point(x,y,d))
  for i in range(count):j=start+2*i;faces.append([j,j+1,j+3,j+2])
 def lines(geometry):
  if geometry.is_empty:return []
  if geometry.geom_type=='LineString':return [geometry]
  if hasattr(geometry,'geoms'):return [line for geom in geometry.geoms for line in lines(geom)]
  return []
 def lattice(role,polygon,depth,pitch=1.65,width=.28,folds=(),seed=0):
  polygon=polygon.buffer(0)
  minx,miny,maxx,maxy=polygon.bounds
  paths=[LineString(path)for path in folds]
  def surface(x,y):
   distance=polygon.boundary.distance(Point(x,y));dome=(.075 if seed==0 else -.035)*min(1,distance/10)
   ridge=sum(.026*math.exp(-path.distance(Point(x,y))**2/16)for path in paths)
   return depth+dome+ridge
  for vertical in [True,False]:
   low,high=(minx,maxx)if vertical else(miny,maxy)
   for i in range(math.floor(low/pitch),math.ceil(high/pitch)+1):
    p=(i+seed*.5)*pitch
    if role=='figures':
     low_axis,high_axis=(miny-1,maxy+1)if vertical else(minx-1,maxx+1)
     count=max(2,math.ceil((high_axis-low_axis)/4))
     axis=[low_axis+(high_axis-low_axis)*j/count for j in range(count+1)]
     guide=LineString([(p+1.5*math.sin(a*.047+p*.011),a)if vertical else(a,p+.65*math.sin(a*.059+p*.013))for a in axis])
    else:guide=LineString([(p,miny-1),(p,maxy+1)]if vertical else[(minx-1,p),(maxx+1,p)])
    for clipped in lines(guide.intersection(polygon)):
     strip(role,list(clipped.coords),width,depth,surface)
  for ring in [polygon.exterior,*polygon.interiors]:strip(role,list(ring.coords),.45,depth,surface)
  for path in paths:
   for clipped in lines(path.intersection(polygon)):strip(role,list(clipped.coords),.62,depth,surface)
  stats.append(dict(role=role,pixelArea=polygon.area,gridPitchPixels=pitch,strandWidthPixels=width,nominalOpenAreaFraction=(1-width/pitch)**2,estimatedFrontDepth=depth+.127 if seed==0 else depth))
 # Bodies are rebuilt from each photo silhouette; no prior ellipsoid/tube cage.
 reference=Image.open(OUT/'reference-engineer-crop.jpg').convert('RGB');draw=ImageDraw.Draw(reference)
 colors=['#e44936','#1aa6b6','#d6a21b','#8e66c1','#268041','#246bbb']
 for index,figure in enumerate(FIGURES):
  body=Polygon(figure['outline']).buffer(0);hx,hy,rx,ry=figure['head'];head=Polygon([(hx+rx*x,hy+ry*y)for x,y in [(-.85,-.45),(-.55,-.92),(.02,-1),(.63,-.76),(.88,-.39),(1,-.08),(.78,.12),(.72,.62),(.25,.98),(-.4,.87),(-.86,.44)]])
  # Thin neck joins and photo-visible arms; no speculative occluded limb forms.
  neck=LineString([(hx,hy+ry-2),(hx,hy+ry+8)]).buffer(3)
  arm_shapes=[LineString(a).buffer(3.2,cap_style='round',join_style='round')for a in figure['arms']]
  silhouette=unary_union([body,head,neck,*arm_shapes]).buffer(0)
  if silhouette.geom_type!='Polygon':silhouette=max(silhouette.geoms,key=lambda p:p.area)
  lattice('figures',silhouette,figure['depth'],folds=figure['folds'])
  lattice('figures',silhouette,figure['depth']-.045,seed=1)
  # Sparse actual side ties close the shallow relief without an opaque rim.
  edge=silhouette.exterior;verts=batches['figures']['vertices'];faces=batches['figures']['faces']
  for i in range(math.floor(edge.length/5)):
   a=edge.interpolate(i*5);b=edge.interpolate(i*5+.4);start=len(verts)
   verts.extend([point(a.x,a.y,figure['depth']),point(b.x,b.y,figure['depth']),point(b.x,b.y,figure['depth']-.045),point(a.x,a.y,figure['depth']-.045)]);faces.append([start,start+1,start+2,start+3])
  draw.line(list(silhouette.exterior.coords),fill=colors[index],width=2);draw.text((hx-5,hy-6),str(index+1),fill=colors[index])
  for fold in figure['folds']:draw.line(fold,fill=colors[index],width=1)
 reference.save(OUT/'reference-silhouette-registration.jpg')
 # Background shelf dividers: low profile structural strips, not a solid panel.
 for x,top in [(155,180),(165,132),(277,91),(398,85),(407,91),(537,202)]:
  strip('display_frame',[(x,top),(x,407)],3,35.51)
 for a,b,y in [(172,393,131),(168,395,173),(115,396,215),(97,396,269),(85,395,320),(83,396,374),(409,478,172),(409,515,222),(409,536,273),(409,537,325),(409,536,374)]:
  strip('display_frame',[(a,y),(b,y)],2.2,35.52)
 # Non-repeating traced product groups follow visible shelves. Bottle, carton
 # and folded-bag families vary in height/width and omit figure-occluded areas.
 products=[]
 def bottle(x,base,w,h):return[(x,base),(x,base-h*.65),(x+w*.28,base-h*.83),(x+w*.28,base-h),(x+w*.68,base-h),(x+w*.68,base-h*.83),(x+w,base-h*.65),(x+w,base)]
 def bag(x,base,w,h,k):return[(x,base),(x+w*.06,base-h*.45),(x+w*.22,base-h*.71),(x+w*.17,base-h*.95),(x+w*.39,base-h),(x+w*.58,base-h*.72),(x+w*.87,base-h*.81),(x+w,base-h*.19),(x+w*.93,base)]if k%2 else[(x,base),(x+w*.1,base-h*.55),(x+w*.42,base-h),(x+w*.57,base-h*.83),(x+w*.81,base-h*.77),(x+w,base-h*.1)]
 rows=[(129,[(190,15,22,'bag'),(213,25,15,'bag'),(243,21,34,'bag'),(286,8,24,'bottle'),(298,12,31,'box'),(313,11,35,'box'),(330,9,27,'bottle'),(344,13,32,'bottle'),(362,12,25,'bottle'),(377,9,22,'box')]),(170,[(180,9,24,'bottle'),(207,11,18,'bottle'),(228,13,32,'box'),(251,11,24,'bottle'),(290,14,24,'bag'),(310,16,33,'bag'),(329,16,28,'bag'),(351,14,30,'bag'),(369,15,24,'bag'),(416,8,29,'bottle'),(430,9,25,'bottle'),(444,12,27,'box')]),(212,[(111,14,18,'box'),(130,12,16,'box'),(179,8,19,'bottle'),(201,14,15,'box'),(317,18,23,'bag'),(341,20,20,'bag'),(364,20,23,'bag'),(449,19,17,'bag'),(476,16,17,'bag'),(502,9,18,'box')]),(267,[(127,7,29,'bottle'),(145,8,25,'bottle'),(175,8,31,'bottle'),(196,13,22,'box'),(312,16,27,'box'),(334,12,32,'bottle'),(352,12,35,'bottle'),(370,16,30,'bag'),(418,12,22,'bottle'),(439,12,25,'bottle'),(514,9,23,'box')]),(318,[(111,18,20,'bag'),(135,15,23,'bag'),(169,14,22,'box'),(317,13,29,'box'),(337,18,25,'bag'),(359,16,32,'bag'),(379,12,23,'bag'),(416,15,23,'box'),(439,17,26,'bag')]),(372,[(111,23,22,'bag'),(137,15,21,'bag'),(294,17,28,'bag'),(315,22,36,'bag'),(341,20,25,'bag'),(365,24,36,'bag'),(413,13,13,'box'),(429,14,22,'box'),(447,15,14,'box'),(515,12,16,'box')])]
 for y,items in rows:
  for index,(x,w,h,kind)in enumerate(items):
   contour=bottle(x,y,w,h)if kind=='bottle'else bag(x,y,w,h,index)if kind=='bag'else[(x,y),(x,y-h),(x+w,y-h),(x+w,y)]
   angle=([-23,12,-14,24,-8][index%5]if kind=='bag'and y>=212 else [-5,3,8,-3][index%4]if kind=='bottle'and y>=267 else 0)
   if kind=='box'and y==372 and index%2:
    contour=[(x,y),(x,y-h*.55),(x+w*1.45,y-h*.55),(x+w*1.45,y)]
   theta=math.radians(angle);cx=x+w/2
   contour=[(cx+(px-cx)*math.cos(theta)-(py-y)*math.sin(theta),y+(px-cx)*math.sin(theta)+(py-y)*math.cos(theta))for px,py in contour]
   lattice('products',Polygon(contour),35.58,pitch=2.0,width=.29)
   products.append(dict(kind=kind,x=x,base=y,width=w,height=h,photoGuidedTiltEstimateDegrees=angle))
 # Open trapezoidal baskets and true wheeled shopping trolley, in front of robes.
 def basket(corners,depth):
  for i in range(4):strip('containers',[corners[i],corners[(i+1)%4]],.85,depth)
  a,b,c,d=corners
  for t in [.15,.3,.45,.6,.75,.9]:
   lerp=lambda p,q:(p[0]+(q[0]-p[0])*t,p[1]+(q[1]-p[1])*t)
   strip('containers',[lerp(a,d),lerp(b,c)],.38,depth)
   strip('containers',[lerp(a,b),lerp(d,c)],.38,depth)
 basket([(149,309),(211,305),(204,341),(154,346)],35.91)
 for path in [[(152,346),(203,385)],[(204,341),(160,385)],[(150,307),(145,298),(134,292)],[(160,385),(203,385)]]:strip('containers',path,.85,35.91)
 for cx,cy in [(161,391),(206,390)]:strip('containers',[(cx+3.2*math.cos(t),cy+3.2*math.sin(t))for t in [i*2*math.pi/16 for i in range(17)]],1.1,35.92)
 basket([(201,291),(247,290),(244,319),(205,320)],35.92)
 strip('containers',[(205,291),(211,282),(233,282),(244,290)],.6,35.92)
 basket([(478,319),(522,312),(527,342),(482,349)],35.92)
 strip('containers',[(483,318),(493,309),(510,307),(521,312)],.65,35.92)
 report=dict(registration=dict(imageCrop='reference-engineer-crop.jpg',imageGlassBounds=[62,62,566,421],modelGlassWidth=5.4565112590789795,modelGlassHeight=3.318953514099121,method='Approximate front-photo registration to inherited protected glazing envelope; not a survey',depth='Shallow 2.5D estimates: background35.51m, products35.58m, figure skin35.57–35.91m, baskets35.92m in facade normal coordinates'),figures=[dict(name=f['name'],head=f['head'],outline=f['outline'],folds=f['folds'],estimatedDepth=f['depth'])for f in FIGURES],products=products,latticePatches=stats)
 (OUT/'shape-plan.json').write_text(json.dumps(report,indent=2)+'\n')
 (OUT/'geometry.json').write_text(json.dumps(batches,separators=(',',':')))
 print('SHAPE_PLAN_READY',sum(len(b['faces'])*2 for b in batches.values()),flush=True)


def run_blender():
 import bpy
 from mathutils import Vector
 sys.path.insert(0,str(ROOT/'web/tools'))
 from integrate_exterior_round194 import accepted_fingerprints,object_fingerprint
 from refine_portsmouth_exterior207 import material_fingerprint
 def update():
  for scene in bpy.data.scenes:
   for layer in scene.view_layers:layer.update()
 def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
 assert sha(BASE)==SHA
 bpy.ops.wm.open_mainfile(filepath=str(BASE));bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE'];update()
 expected=accepted_fingerprints(ROOT/'result/blender/stage217',SHA);actual={o.name:object_fingerprint(o)for o in bpy.data.objects}
 assert expected==actual,[n for n in expected if expected[n]!=actual.get(n)][:20]
 mats={m.name:material_fingerprint(m)for m in bpy.data.materials};visibility={o.name:o.hide_render for o in bpy.data.objects}
 metadata=json.loads((ROOT/'web/tools/building-metadata.json').read_text());rooms={o.name for space in metadata['spaces']for o in bpy.data.collections[space['collection']].all_objects}
 assert len(rooms)==623 and not rooms.intersection(SOURCES.values())
 right=Vector((.47449132800102234,.8802601099014282,0));normal=Vector((.8802601099014282,-.47449132800102234,0))
 glass=bpy.data.objects['OLD_NEXT_ARTWORK_front_glazing'];glass_pts=[glass.matrix_world@v.co for v in glass.data.vertices];glass_d=min(p.dot(normal)for p in glass_pts)
 def render(label,oblique):
  scene=bpy.data.scenes.new(PREFIX+'review');scene.collection.children.link(bpy.data.collections['OLD_EXTERIOR'])
  world=bpy.data.worlds.new(scene.name);world.use_nodes=True;world.node_tree.nodes['Background'].inputs['Color'].default_value=(.82,.85,.88,1);world.node_tree.nodes['Background'].inputs['Strength'].default_value=.65;scene.world=world
  lamp=bpy.data.lights.new(scene.name,'AREA');lamp.energy=650;lamp.shape='DISK';lamp.size=5
  light=bpy.data.objects.new(scene.name+'_light',lamp);scene.collection.objects.link(light)
  target=right*(-82.50)+normal*35.75+Vector((0,0,5.2));light.location=target+normal*5-right*3+Vector((0,0,5));light.rotation_euler=(target-light.location).to_track_quat('-Z','Y').to_euler()
  cd=bpy.data.cameras.new(scene.name);camera=bpy.data.objects.new(scene.name+'_camera',cd);scene.collection.objects.link(camera);scene.camera=camera
  camera.location=target+normal*(9 if oblique else 10)+right*(4.5 if oblique else 0)+Vector((0,0,.3));camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler();cd.type='ORTHO';cd.ortho_scale=6.3;cd.clip_end=500
  scene.render.engine='BLENDER_EEVEE';scene.eevee.taa_render_samples=64;scene.render.resolution_x=1200;scene.render.resolution_y=800;scene.render.resolution_percentage=100;scene.view_settings.view_transform='AgX';scene.render.image_settings.file_format='PNG';scene.render.filepath=str(OUT/(label+('-oblique'if oblique else'-front')+'.png'))
  bpy.ops.render.render(write_still=True,scene=scene.name)
  for o in [camera,light]:bpy.data.objects.remove(o,do_unlink=True)
  bpy.data.scenes.remove(scene);bpy.data.worlds.remove(world);bpy.data.cameras.remove(cd);bpy.data.lights.remove(lamp);bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE'];update()
 def triangles(obj):obj.data.calc_loop_triangles();return len(obj.data.loop_triangles)
 original_count=sum(triangles(bpy.data.objects[n])for n in SOURCES.values())
 for oblique in [False,True]:
  path=OUT/('before'+('-oblique'if oblique else'-front')+'.png')
  if not path.exists():render('before',oblique)
 geometry=json.loads((OUT/'geometry.json').read_text());added=[];bounds=[]
 for role,source_name in SOURCES.items():
  source=bpy.data.objects[source_name];assert not source.hide_render
  mesh=bpy.data.meshes.new(PREFIX+role);local=geometry[role];world=[list(right*p[0]+normal*p[1]+Vector((0,0,p[2])))for p in local['vertices']];mesh.from_pydata(world,[],local['faces']);mesh.update()
  obj=bpy.data.objects.new(PREFIX+role,mesh);bpy.data.collections['OLD_EXTERIOR'].objects.link(obj)
  for m in source.data.materials:mesh.materials.append(m)
  obj['originalObject']=source_name;obj['destinationCollection']='OLD_EXTERIOR';obj['scope']='Photo-guided shallow open plastic-mesh sculpture; depth and rear shape estimated; no texture photograph';added.append(obj)
  source.hide_render=True;source.hide_set(True)
  depths=[p[1]for p in local['vertices']];xs=[p[0]for p in local['vertices']];zs=[p[2]for p in local['vertices']]
  assert max(depths)<glass_d-.035
  bounds.append(dict(object=obj.name,width=max(xs)-min(xs),height=max(zs)-min(zs),depth=max(depths)-min(depths),frontGlassClearance=glass_d-max(depths),triangles=triangles(obj)))
 update();new_count=sum(triangles(o)for o in added);assert new_count<=original_count
 assert all(object_fingerprint(bpy.data.objects[n])==v for n,v in actual.items());assert all(material_fingerprint(bpy.data.materials[n])==v for n,v in mats.items())
 for oblique in [False,True]:render('after',oblique)
 fingerprints={o.name:object_fingerprint(o)for o in added};bindings={o.name:[m.name for m in o.data.materials]for o in added}
 component=OUT/'component.blend';bpy.data.libraries.write(str(component),set(added),fake_user=True,compress=True)
 bpy.ops.wm.open_mainfile(filepath=str(BASE));bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE'];update();assert all(object_fingerprint(bpy.data.objects[n])==v for n,v in expected.items())
 with bpy.data.libraries.load(str(component),link=False)as(available,loaded):loaded.objects=list(fingerprints)
 for obj in loaded.objects:
  for index,name in enumerate(bindings[obj.name]):obj.data.materials[index]=bpy.data.materials[name]
  bpy.data.collections['OLD_EXTERIOR'].objects.link(obj)
 for n in SOURCES.values():bpy.data.objects[n].hide_render=True;bpy.data.objects[n].hide_set(True)
 update();assert all(object_fingerprint(bpy.data.objects[n])==v for n,v in expected.items());assert all(object_fingerprint(bpy.data.objects[n])==v for n,v in fingerprints.items());assert all(material_fingerprint(bpy.data.materials[n])==v for n,v in mats.items());assert all(bpy.data.objects[n].hide_render==v for n,v in visibility.items()if n not in SOURCES.values())
 verification=dict(savedComponentReopened=True,acceptedSourceFingerprintsVerified=len(expected),originalMaterialsVerified=len(mats),sourceGeometryUVsMaterialNodesUnchanged=True,independentRoomObjectsVerified=len(rooms),unrelatedVisibilityPreserved=True,sourceFileUnchanged=sha(BASE)==SHA,actualGeometryNotTransparentShader=True,originalTriangles=original_count,replacementTriangles=new_count,triangleReductionFraction=1-new_count/original_count,referencePhotographsUsedAsPublicTextures=False)
 references=[dict(path=str(p.relative_to(ROOT)),sha256=sha(p),captureDate='unknown',publication='Private source evidence; never a public texture')for p in [ROOT/'data/collections/campus_photos_round2/images/OLD/OLD_old_webbyates_01.jpg',ROOT/'data/collections/old-user-reference/final-sale-front.jpg',ROOT/'data/collections/old-user-reference/final-sale-side.jpg']]
 audit=dict(work=dict(title='Final Sale',artist='Recycle Group',material='Plastic mesh',catalogueYear=2014,sourceManifest='data/collections/old-user-reference/final-sale-sources.json',catalogueDimensionsNotUsedToResizeArch=True),version=218,baselineSha256=SHA,baseline=str(BASE.relative_to(ROOT)),componentPath=str(component.relative_to(ROOT)),componentSha256=sha(component),targetCollection='OLD_EXTERIOR',destinationCollection='OLD_EXTERIOR',addedObjects=list(fingerprints),archivedObjects=list(SOURCES.values()),addedFingerprints=fingerprints,replacementMaterialBindings=bindings,materialBindings=bindings,changedObjects=[],verification=verification,objects=bounds,references=references,shapePlan='shape-plan.json',previews=['before-front.png','after-front.png','before-oblique.png','after-oblique.png'],limitations=['Undated photographs support front silhouette and pose, not present-day measured state.','Pixel registration, shallow curvature, mesh strand size, depth and unseen reverse surfaces are estimates.','Only visible/recognisable limbs are formed; this is a source-guided2.5D reconstruction rather than complete sculptural anatomy.','Inherited arch opening and protective glass are untouched.','Six distinct figure shapes, shopping trolley and two held baskets are geometric, not a photographic texture; products vary through three source-visible silhouette families.'])
 (OUT/'audit.json').write_text(json.dumps(audit,indent=2)+'\n');(OUT/'verification.json').write_text(json.dumps(verification,indent=2)+'\n');print('OLDART218_REOPENED',sha(component),new_count,original_count,flush=True)

if __name__=='__main__':
 try:import bpy
 except ModuleNotFoundError:
  import subprocess
  make_plan()
  with(OUT/'build.log').open('w')as log:
   subprocess.run(['/Applications/Blender.app/Contents/MacOS/Blender','--background','--python-exit-code','1','--python',str(Path(__file__).resolve())],stdout=log,stderr=subprocess.STDOUT,check=True)
  removed=[]
  for name in ['geometry.json','build.log','component.blend1']:
   candidate=OUT/name
   if candidate.exists():candidate.unlink();removed.append(name)
  (OUT/'cleanup.json').write_text(json.dumps(dict(removedOwnedTemporaryFiles=removed,blenderProcessExited=True,unrelatedFilesRemoved=False),indent=2)+'\n')
 else:run_blender()
