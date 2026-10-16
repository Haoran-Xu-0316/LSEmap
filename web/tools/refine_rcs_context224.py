"""RCS224:completed2021 streetfront inside its accepted context footprint.

The historical front is traced from the official2021reopening photograph.
OSMfront corners andcentral projection registerXY;heights/depths are estimates.
MachineLearning prepares attributed outlines;Blender builds closed solids,
previews and a separately reopened component.Never saves the full campus.
"""
from pathlib import Path
import sys,json,hashlib,math
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'result/blender/rcs-context224'
SOURCE=ROOT/'data/collections/rcs-context224'
BASE=ROOT/'result/blender/LSE_campus_detailed_v223.blend'
SHA='ebe14c658cacb9ef4e19b0fbfd8683610bf53c565f161837d329dfbd0cd9d88b'
PREFIX='RCS224_';COLLECTION='01_CITY_CONTEXT_estimated_heights';OLD='Context_way/1376078547_'
ARCHIVES=[OLD+'wall_0_'+str(i)for i in range(7,17)]+[OLD+'roof']
sys.path.insert(0,str(ROOT/'web/tools'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def packed(v):return hashlib.sha256(json.dumps(v,sort_keys=True).encode()).hexdigest()
def write(p,v):p.write_text(json.dumps(v,indent=2,ensure_ascii=False)+'\n')


def prepare():
 import numpy as np
 from shapely.geometry import Polygon,box,Point
 from shapely.ops import unary_union
 from shapely import constrained_delaunay_triangles
 site=json.loads((ROOT/'result/blender/site_geometry.json').read_text());b=next(b for b in site['buildings']if b['id']=='way/1376078547');ring=np.array(b['rings'][0]);origin=ring[7];ex=(ring[17]-origin)/np.linalg.norm(ring[17]-origin);ey=np.array([ex[1],-ex[0]]);local=np.array([[(p-origin)@ex,(p-origin)@ey]for p in ring]);foot=Polygon(local)
 # One-dimensional projective rectification:two front limits andtheOSM
 # central portico axis,not anorthographic measurement of the photograph.
 pts=[(150,.18),(895,25.10),(1750,49.80)];m=np.array([[p,1,-p*x]for p,x in pts]);abc=np.linalg.solve(m,np.array([x for p,x in pts]));px=[236,333,482,590,696,800,895,997,1101,1213,1314,1442,1563,1682]
 xs=[float((abc[0]*p+abc[1])/(abc[2]*p+1))for p in px]
 openings=[]
 for row,(z0,z1,w)in enumerate([(1.3,4.15,1.30),(6.0,8.8,1.30),(11.45,13.55,1.30),(20.15,22.35,1.38)]):
  for col,x in enumerate(xs):openings.append(dict(kind='door'if row==0 and col==6 else'rect',row=row,column=col,x=x,z0=z0,z1=z1,width=1.55 if row==0 and col==6 else w))
 circles=[dict(x=x,z=17.94,r=.56)for x in xs]
 holes=[box(o['x']-o['width']/2,o['z0'],o['x']+o['width']/2,o['z1'])for o in openings]+[Point(o['x'],o['z']).buffer(o['r'],quad_segs=12)for o in circles]
 wall=box(.18,0,49.8,23.80).difference(unary_union(holes));assert wall.geom_type=='Polygon'and len(wall.interiors)==70
 roof=foot.intersection(box(-100,.68,100,100));frontroof=roof.intersection(box(-100,.68,100,5.2))
 def shape(p):return dict(outer=list(p.exterior.coords)[:-1],holes=[list(r.coords)[:-1]for r in p.interiors],triangles=[list(t.exterior.coords)[:3]for t in constrained_delaunay_triangles(p).geoms],area=p.area)
 data=dict(frame=dict(origin=origin.tolist(),ex=ex.tolist(),ey=ey.tolist()),footprint=shape(foot),footprintSource=b['properties'],roof=shape(roof),frontRoof=shape(frontroof),wall=shape(wall),openings=openings,circles=circles,photoPixels=px,windowXs=xs,rectification=abc.tolist(),columnXs=[16.83+3.30*i for i in range(6)],estimate='OSM footprint/control points are geographic;facade heights,wall depth,column sections,roof strip andframe widths are estimated,not surveyed.',removedHighPorticoRoofAreaM2=foot.difference(roof).area)
 write(OUT/'registration.json',data)
 def world(p):return origin+ex*p[0]+ey*p[1]
 new35=next(b for b in site['buildings']if b.get('code')=='35L');p35=Polygon(new35['rings'][0]);new_world=Polygon([world(p)for p in roof.exterior.coords]);data['roof35LIntersectionM2']=new_world.intersection(p35).area
 write(OUT/'registration.json',data)
 # Code-native diagram records the footprint boundary andsource-supported face.
 def path(coords):return' '.join(f'{(x-4)*8:.2f},{(116-y)*8:.2f}'for x,y in coords)
 front=[world((.18,.28)),world((49.8,.28))]
 svg=f'''<svg xmlns="http://www.w3.org/2000/svg" width="940" height="760" viewBox="0 0 940 760"><rect width="940" height="760" fill="#f6f4ef"/><text x="30" y="35" font-family="sans-serif" font-size="22">RCS224 geographic boundary andstreetfront registration</text><polygon points="{path(b['rings'][0])}" fill="#cdd8dd" stroke="#31576d" stroke-width="2"/><polygon points="{path(new35['rings'][0])}" fill="#e4d2ba" stroke="#956d37" stroke-width="2"/><polyline points="{path(front)}" fill="none" stroke="#b43c32" stroke-width="5"/><text x="120" y="480" font-family="sans-serif" font-size="18">RCS way/1376078547</text><text x="590" y="300" font-family="sans-serif" font-size="18">35L construction retained</text><text x="30" y="700" font-family="sans-serif" font-size="16">Red:photo-supported historical front;blue:accepted RCS boundary;brown:35L,excluded.</text><text x="30" y="725" font-family="sans-serif" font-size="15">Roof behind the facade remains the accepted height estimate;no unseen side wing is detailed.</text></svg>'''
 (OUT/'registration.svg').write_text(svg)
 print('RCS224_PLAN_READY',len(openings),len(circles),foot.area,roof.area,flush=True)


def run():
 import bpy,bmesh
 from mathutils import Vector,Matrix
 from mathutils.bvhtree import BVHTree
 from integrate_exterior_round194 import object_fingerprint,accepted_fingerprints
 from refine_portsmouth_exterior207 import material_fingerprint
 from build_clm_hongkong_room220 import modifier_payload
 from build_room_samples167 import RoomGeometry
 def update():
  for scene in bpy.data.scenes:
   for layer in scene.view_layers:layer.update()
  bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE']
 def state():
  meta=json.loads((ROOT/'web/tools/building-metadata.json').read_text());rooms={r['collection']:sorted(o.name for o in bpy.data.collections[r['collection']].all_objects)for r in meta['spaces']};assert len(rooms)==21 and len(set().union(*(set(v)for v in rooms.values())))==767
  return dict(objects={o.name:object_fingerprint(o)for o in bpy.data.objects},materials={m.name:material_fingerprint(m)for m in bpy.data.materials},modifiers={o.name:packed([modifier_payload(m)for m in o.modifiers])for o in bpy.data.objects},ownership={o.name:sorted(c.name for c in o.users_collection)for o in bpy.data.objects},visibility={o.name:o.hide_render for o in bpy.data.objects},rooms=rooms,roomScenes={c:{s.name:sorted(n for n in ns if n in s.objects)for s in bpy.data.scenes}for c,ns in rooms.items()})
 def verify(before,hidden):
  assert all(object_fingerprint(bpy.data.objects[n])==v for n,v in before['objects'].items())
  assert all(material_fingerprint(bpy.data.materials[n])==v for n,v in before['materials'].items())
  assert all(packed([modifier_payload(m)for m in bpy.data.objects[n].modifiers])==v for n,v in before['modifiers'].items())
  assert all(sorted(c.name for c in bpy.data.objects[n].users_collection)==v for n,v in before['ownership'].items())
  assert all(bpy.data.objects[n].hide_render==(True if n in hidden else v)for n,v in before['visibility'].items())
  assert all(sorted(o.name for o in bpy.data.collections[c].all_objects)==ns for c,ns in before['rooms'].items())
  assert {c:{s.name:sorted(n for n in ns if n in s.objects)for s in bpy.data.scenes}for c,ns in before['rooms'].items()}==before['roomScenes']
 assert sha(BASE)==SHA;bpy.ops.wm.open_mainfile(filepath=str(BASE));update();before=state();assert len(before['objects'])==7737 and before['objects']==accepted_fingerprints(ROOT/'result/blender/stage223',SHA)
 protected=set().union(*(set(v)for v in before['rooms'].values()));assert not protected.intersection(ARCHIVES)
 col=bpy.data.collections[COLLECTION];plan=json.loads((OUT/'registration.json').read_text());frame=plan['frame'];origin=Vector((*frame['origin'],0));ex=Vector((*frame['ex'],0));ey=Vector((*frame['ey'],0))
 def world(p):return origin+ex*p[0]+ey*p[1]+Vector((0,0,p[2]))
 def local(p):q=Vector(p)-origin;return(q.dot(ex),q.dot(ey),q.z)
 g=RoomGeometry(col,PREFIX)
 # New materials are procedural/private-source colors,never source photos.
 for key,color,rough,metal in [('stone',(.69,.68,.63),.72,0),('trim',(.78,.77,.71),.63,0),('frame',(.46,.51,.49),.45,.2),('dark',(.035,.043,.044),.62,.3),('glass',(.09,.15,.18),.24,.28),('back',(.08,.075,.063),.9,0),('roof',(.27,.28,.27),.85,0)]:
  mat=g.materials.get(key)or bpy.data.materials.new(PREFIX+key);mat.use_nodes=True;mat.diffuse_color=(*color,1);bs=mat.node_tree.nodes['Principled BSDF'];bs.inputs['Base Color'].default_value=mat.diffuse_color;bs.inputs['Roughness'].default_value=rough;bs.inputs['Metallic'].default_value=metal;g.materials[key]=mat
 g.materials['proxyRoof']=bpy.data.objects[OLD+'roof'].data.materials[0]
 def box(f,m,c,s):g.box(f,m,c,s)
 def cyl(f,m,x,y,z0,z1,r0,r1=None,n=24,flute=False):
  r1=r0 if r1 is None else r1;vs=[]
  for z,r in [(z0,r0),(z1,r1)]:
   for i in range(n):
    rr=r*(.96 if flute and i%2 else 1);a=i*math.tau/n;vs.append((x+rr*math.cos(a),y+rr*math.sin(a),z))
  g.add(f,m,vs,[tuple(reversed(range(n))),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n)for i in range(n)])
 def ring(f,m,x,z,ri,ro,y0,y1,n=48):
  vs=[(x+r*math.cos(i*math.tau/n),y,z+r*math.sin(i*math.tau/n))for y in [y0,y1]for r in [ri,ro]for i in range(n)];fs=[]
  for i in range(n):
   j=(i+1)%n;fs.extend([(i,j,n+j,n+i),(2*n+i,3*n+i,3*n+j,2*n+j),(i,2*n+i,2*n+j,j),(n+i,n+j,3*n+j,3*n+i)])
  # Winding may be negative for this vertical orientation;reverse once.
  volume=sum(Vector(vs[f[0]]).dot(Vector(vs[f[i]]).cross(Vector(vs[f[i+1]])))/6 for f in fs for i in range(1,len(f)-1))
  g.add(f,m,vs,fs if volume>0 else[tuple(reversed(q))for q in fs])
 def facade(shape):
  # Shared indexed triangulation caps plus each exterior/interior boundary.
  coords=[];lookup={};faces=[]
  def idx(p):
   key=(round(p[0],7),round(p[1],7))
   if key not in lookup:lookup[key]=len(coords);coords.append(key)
   return lookup[key]
  for t in shape['triangles']:faces.append(tuple(idx(p)for p in t))
  loops=[[idx(p)for p in r]for r in [shape['outer']]+shape['holes']];n=len(coords);vs=[(x,y,z)for y in [.28,.68]for x,z in coords];allfaces=[]
  for t in faces:
   area=sum(coords[a][0]*coords[b][1]-coords[b][0]*coords[a][1]for a,b in zip(t,t[1:]+t[:1]));t=t if area>0 else tuple(reversed(t));allfaces.extend([t,tuple(i+n for i in reversed(t))])
  for loop in loops:
   # Match cap boundary direction fromtriangle incidence.
   for a,b in zip(loop,loop[1:]+loop[:1]):
    directed=any(a==t[i]and b==t[(i+1)%3]for t in allfaces[::2]for i in range(3))
    if not directed:a,b=b,a
    allfaces.append((b,a,a+n,b+n))
  g.add('historic_stone_wall_with70_openings','stone',vs,allfaces)
 facade(plan['wall'])
 # All rectangular windows have real400mmdeep reveals andopaque backing.
 for o in plan['openings']:
  x,z0,z1,w=o['x'],o['z0'],o['z1'],o['width'];h=z1-z0;zc=(z0+z1)/2;isdoor=o['kind']=='door'
  box('window_backings','back',(x,1.00,zc),(w+.12,.12,h+.12));box('recessed_glazing','glass',(x,.57,zc),(w-.10,.035,h-.10))
  for side in [-1,1]:
   box('window_sash_frames','frame',(x+side*(w/2-.055),.48,zc),(.085,.10,h));box('window_stone_architraves','trim',(x+side*(w/2+.065),.20,zc),(.13,.16,h+.3))
  for z in [z0+.045,z1-.045]:box('window_sash_frames','frame',(x,.48,z),(w,.10,.09))
  for z in [z0-.12,z1+.12]:box('window_stone_architraves','trim',(x,.25,z),(w+.38,.22,.13))
  box('window_sash_frames','frame',(x,.47,zc),(.065,.10,h))
  for z in [z0+h*.33,z0+h*.67]:box('window_sash_frames','frame',(x,.47,z),(w,.10,.055))
  if isdoor:box('central_entry_door_transom','dark',(x,.40,z1-.65),(w,.14,.08))
 for o in plan['circles']:
  x,z,r=o['x'],o['z'],o['r'];ring('circular_window_carved_surrounds','trim',x,z,r,r+.16,.11,.30)
  # Closed round disks are cylinders rotated into facade depth.
  n=48;vs=[(x+r*.96*math.cos(i*math.tau/n),y,z+r*.96*math.sin(i*math.tau/n))for y in [.47,.51]for i in range(n)];fs=[tuple(range(n)),tuple(reversed(range(n,2*n)))]+[(i,i+n,(i+1)%n+n,(i+1)%n)for i in range(n)]
  g.add('circular_recessed_glazing','glass',vs,fs)
  box('circular_window_backings','back',(x,.98,z),(2*r+.15,.12,2*r+.15));box('circular_window_crossbars','frame',(x,.42,z),(.055,.08,2*r));box('circular_window_crossbars','frame',(x,.42,z),(2*r,.08,.055))
 # Main stringcourses andedgepilasters are bounded inside the footprint.
 for z,h,depth in [(0.45,.45,.20),(4.64,.16,.32),(9.66,.22,.36),(14.75,.16,.34),(15.72,.32,.42),(16.12,.17,.48),(19.15,.14,.24),(23.07,.28,.42),(23.53,.20,.48)]:box('stone_stringcourses','trim',(24.99,.38,z),(49.60,depth,h))
 for x in [.47,9.1,39.6,49.47]:
  box('facade_shallow_pilasters','trim',(x,.16,9.25),(.38,.22,17.6));box('facade_shallow_pilasters','trim',(x,.15,21.1),(.34,.24,3.5))
 # Replace the false24mhigh OSMportico projection with the real low canopy.
 for i in range(5):box('portico_entry_steps','stone',(25.10,-1.05,.10+.10*i),(17.72,3.65-.26*i,.20+.20*i))
 box('portico_floor','stone',(25.10,-.94,.95),(17.72,3.42,.30))
 for x in plan['columnXs']:
  cyl('six_ionic_column_bases','trim',x,-1.98,1.10,1.23,.61,n=24);cyl('six_ionic_column_bases','trim',x,-1.98,1.23,1.46,.53,.46,n=24)
  cyl('six_fluted_ionic_shafts','trim',x,-1.98,1.46,9.12,.43,.365,n=48,flute=True)
  cyl('six_ionic_column_capitals','trim',x,-1.98,9.12,9.35,.48,n=24);box('six_ionic_column_capitals','trim',(x,-1.98,9.44),(1.10,.88,.20))
  for side in [-1,1]:ring('ionic_capital_volute_rims','trim',x+side*.41,9.25,.12,.22,-2.47,-2.30,n=20)
 for z,h,w,d in [(9.64,.22,17.72,3.26),(10.03,.57,17.72,3.26),(10.43,.20,17.72,3.35),(10.73,.40,17.72,3.40),(11.05,.20,17.72,3.45)]:box('portico_low_entablature','trim',(25.10,-1.01,z),(w,d,h))
 # Roofslab retains the accepted rear contour andheight;only the false
 # high portico projection is removed.No unseen roofpitches are invented.
 g.prism('retained_proxy_roof_without_high_portico','proxyRoof',plan['roof']['outer'],23.8,.25)
 g.prism('front_roof_weathering_surface','roof',plan['frontRoof']['outer'],24.05,.045)
 # Photograph supports a continuous pale parapet railing above the facade.
 for z,h in [(23.99,.22),(24.94,.17)]:box('front_roof_balustrade_rails','trim',(24.99,.49,z),(49.6,.40,h))
 for i in range(89):
  x=.55+i*.555
  for z0,z1,r0,r1 in [(24.10,24.20,.10,.12),(24.20,24.43,.12,.075),(24.43,24.67,.075,.12),(24.67,24.85,.12,.10)]:cyl('front_roof_balusters','trim',x,.49,z0,z1,r0,r1,n=8)
 for x in [.6,9.1,16.0,25.0,34.0,39.6,49.4]:box('front_roof_balustrade_piers','trim',(x,.49,24.48),(.42,.44,.78))
 # The front railing follows the visible base;omit vegetation/people/signs.
 for a,b in [(.8,24.0),(26.1,49.2)]:
  for z in [1.15,2.28]:box('front_iron_rails','dark',((a+b)/2,.19,z),(b-a,.055,.055))
  for i in range(round((b-a)/.22)+1):
   x=a+(b-a)*i/round((b-a)/.22);box('front_iron_pickets','dark',(x,.19,1.73),(.025,.025,1.40))
 added=g.finish()
 for o in added:
  for v in o.data.vertices:v.co=world(v.co)
  o.data.update();o['destinationCollection']=COLLECTION;o['evidenceScope']='Official2021completedstreetfront;OSMXY;estimateddimensions;unseenrearretainedproxy'
 newnames=[o.name for o in added];update()
 def tree(objects):
  vs=[];fs=[]
  for o in objects:
   off=len(vs);vs.extend(o.matrix_world@v.co for v in o.data.vertices);fs.extend(tuple(off+i for i in p.vertices)for p in o.data.polygons)
  return BVHTree.FromPolygons(vs,fs)
 def physical():
  active=[bpy.data.objects[n]for n in newnames];wall=tree([o for o in active if 'historic_stone_wall'in o.name]);back=tree([o for o in active if 'backings'in o.name]);openings=[]
  for o in plan['openings']:
   start=world((o['x'],-.1,(o['z0']+o['z1'])/2));direction=ey;assert wall.ray_cast(start,direction,.9)[0]is None
   hit=back.ray_cast(start,direction,1.5);assert hit[0]is not None;openings.append(hit[3])
  for o in plan['circles']:
   start=world((o['x'],-.1,o['z']));assert wall.ray_cast(start,ey,.9)[0]is None;assert back.ray_cast(start,ey,1.5)[0]is not None
  floor=tree([o for o in active if 'portico_floor'in o.name]);gaps=[]
  for x in plan['columnXs']:
   hit=floor.ray_cast(world((x,-1.98,1.2)),Vector((0,0,-1)),.4);assert hit[0]is not None;gaps.append(abs(hit[0].z-1.10))
  coltree=tree([o for o in active if 'shafts'in o.name or'bases'in o.name]);doorx=plan['windowXs'][6];a=world((doorx,-2.65,2.1));assert coltree.ray_cast(a,ey,2.9)[0]is None
  return dict(rectangularWallHolesVerified=len(openings),circularWallHolesVerified=len(plan['circles']),all70GlazingOpeningsHaveOpaqueBacking=True,maximumBackingRayDistanceM=max(openings),columnFootSupportSamples=len(gaps),maximumColumnFootSupportGapM=max(gaps),columnCentres=plan['columnXs'],porticoColumnClearGapM=3.30-.86,centralEntryRayThroughColumnRowClear=True,centralEntryWidthM=1.55,estimatedEntryThresholdAbovePlatformM=.20,canopySoffitM=9.53,porticoFinishedFloorM=1.10,canopyClearanceM=9.53-1.10,roofOriginalMaximumTopM=24.05,retainedRearRoofMaximumTopM=24.05,removedFalseHighPorticoRoofAreaM2=plan['removedHighPorticoRoofAreaM2'],sourceBoundary='Every new meshXYvertex is checked inside the originalRCSfootprint byMachineLearningpostcheck.No35Lintersection.',geometryChecksOnly=True)
 def previews(label):
  scene=bpy.data.scenes.new(PREFIX+'PREVIEW');scene.render.engine='CYCLES';scene.cycles.samples=10;scene.cycles.use_denoising=True;scene.render.resolution_x=1100;scene.render.resolution_y=720;scene.render.resolution_percentage=100;scene.view_settings.view_transform='AgX';worlddata=bpy.data.worlds.new(PREFIX+'WORLD');worlddata.use_nodes=True;worlddata.node_tree.nodes['Background'].inputs[0].default_value=(.78,.82,.87,1);worlddata.node_tree.nodes['Background'].inputs[1].default_value=.8;scene.world=worlddata;copies=[]
  show=[o for o in bpy.data.objects if (o.name.startswith(OLD)or o.name in newnames)and o.type=='MESH']
  for old in show:
   if label=='before'and old.name in newnames or label=='after'and old.name in ARCHIVES:continue
   o=old.copy();o.data=old.data.copy();o.hide_render=False;scene.collection.objects.link(o);copies.append(o)
  camera=bpy.data.objects.new(PREFIX+'CAM',bpy.data.cameras.new(PREFIX+'CAM'));scene.collection.objects.link(camera);scene.camera=camera;camera.data.type='ORTHO';camera.data.clip_end=500
  light=bpy.data.objects.new(PREFIX+'SUN',bpy.data.lights.new(PREFIX+'SUN','SUN'));scene.collection.objects.link(light);light.data.energy=2;light.rotation_euler=(.5,-.35,-.65)
  for tag,pos,target,scale in [('streetfront',(25,-75,17),(25,2,12),62),('oblique',(47,-39,21),(25,0,9),42)]:
   camera.location=world(pos);camera.rotation_euler=(world(target)-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.ortho_scale=scale;scene.render.filepath=str(OUT/(label+'-'+tag+'.png'));bpy.context.window.scene=scene;bpy.ops.render.render(write_still=True)
  bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE']
  for o in copies+[camera,light]:
   data=o.data;bpy.data.objects.remove(o,do_unlink=True)
   if isinstance(data,bpy.types.Mesh)and data.users==0:bpy.data.meshes.remove(data)
  bpy.data.scenes.remove(scene);bpy.data.worlds.remove(worlddata);update()
 checks=physical();previews('before')
 for n in ARCHIVES:bpy.data.objects[n].hide_render=True
 previews('after');verify(before,set(ARCHIVES))
 fingerprints={o.name:object_fingerprint(o)for o in added};bindings={o.name:[m.name for m in o.data.materials]for o in added};component=OUT/'rcs-context224-component.blend';bpy.data.libraries.write(str(component),set(added),fake_user=True,compress=True);digest=sha(component)
 # Export onlynewXYislands for anindependent boundary check.No original
 # mesh orlarge all-source expansion is written.
 coords={o.name:[list(v.co)for v in o.data.vertices]for o in added};write(OUT/'new-vertices-temporary.json',coords)
 bpy.ops.wm.open_mainfile(filepath=str(BASE));update();verify(before,set())
 with bpy.data.libraries.load(str(component),link=False)as(src,dst):dst.objects=list(fingerprints)
 for o in dst.objects:
  col=bpy.data.collections[COLLECTION];col.objects.link(o)
  for i,m in enumerate(bindings[o.name]):
   if m in bpy.data.materials:o.data.materials[i]=bpy.data.materials[m]
 for n in ARCHIVES:bpy.data.objects[n].hide_render=True
 update();verify(before,set(ARCHIVES));assert all(object_fingerprint(bpy.data.objects[n])==v for n,v in fingerprints.items());assert physical()==checks;assert sha(BASE)==SHA and sha(component)==digest
 campus=bpy.data.scenes['00_CAMPUS_COMPLETE'];campus_layer=campus.view_layers[0];assert all(n in campus.objects and bpy.data.objects[n].visible_get(view_layer=campus_layer)for n in fingerprints)
 def webview(pos,target,fov=42):
  p,t=world(pos),world(target);return dict(position=[p.x,p.z,-p.y],target=[t.x,t.z,-t.y],fov=fov)
 views=[dict(code='CAMPUS',name='campus-rcs-streetfront',label='RCS历史街面',view=webview((25,-72,17),(25,2,12),30)),dict(code='CAMPUS',name='campus-rcs-portico',label='RCS六柱入口',view=webview((47,-39,21),(25,0,9),36))]
 verification=dict(savedComponentReopenedAndAppended=True,originalObjectsVerified=7737,originalMaterialNodesVerified=len(before['materials']),protectedSpacesVerified=21,protectedSpaceObjectsVerified=767,originalGeometryUVTransformsBindingsModifiersUnchanged=True,allOriginalCollectionMembershipsUnchanged=True,protectedSpaceSceneMembershipsUnchanged=True,onlyListedOriginalVisibilityChanged=True,contextCollectionAlreadyInNativeCampus=any(c.name==COLLECTION for c in bpy.data.scenes['00_CAMPUS_COMPLETE'].collection.children_recursive),allAddedObjectsPresentAndVisibleInNativeCampus=True,nativeCampusVisibleAddedObjects=len(fingerprints),noFullNativeWritten=True,sourcePhotographsNotUsedAsTextures=True,sourceAndComponentSha256Rechecked=True,addedObjects=len(fingerprints),triangles=sum(sum(len(p.vertices)-2 for p in bpy.data.objects[n].data.polygons)for n in fingerprints),physicalChecks=checks)
 audit=dict(version=224,building='RCS_CONTEXT',baseline=str(BASE.relative_to(ROOT)),baselineSha256=SHA,componentPath=str(component.relative_to(ROOT)),componentSha256=digest,targetCollection=COLLECTION,destinationCollection=COLLECTION,addedObjects=list(fingerprints),archivedObjects=ARCHIVES,changedObjects=[],addedFingerprints=fingerprints,replacementMaterialBindings=bindings,sourceManifest=str((SOURCE/'sources.json').relative_to(ROOT)),gallerySuggestions=views,verification=verification,sourceProperty='way/1376078547;RCS38-43Lincoln\'sInnFields;notLSE35L',changes=['Replace the ten street-facing grayproxy faces by the completed historical stone facade with56rectangular openings and14circular openings.','Replace the false24mhigh centralportico roofprojection with six supported Ionic columns anda low straightentablature;retain the geographic rearroofcontour andproxyheight.','Add recessed opaque glazing,realreveals,internalbackings,sashframes,stringcourses,frontroofbalustrade andboundedentrybase.'],limitations=['2021completionand2023award arepublication/projectdates;photograph capturedatesunknown.NoOctober2026survey isclaimed.','XYuses theacceptedOSMboundary andcentralprojection;photographic bays useestimatedprojectiverectification.Allheights,columnsections,revealdepths,entrancesteps,roofstrip andsmalldetails areestimates.','No interiorroom isclaimed;glazing isopaqueandbacked.No photographs areusedastextures.','Unseen side/rearwalls and rearroof remain the originalheightestimate.The newroofonlyremoves the source-disprovedhighportico projection.','Geometric support,doorwayandboundarychecks arenotstructural/accessibility/firecertification.'],previews=['before-streetfront.png','after-streetfront.png','before-oblique.png','after-oblique.png'])
 write(OUT/'audit.json',audit);write(OUT/'verification.json',verification);write(OUT/'view-suggestions.json',views);print('RCS224_READY',digest,len(fingerprints),len(ARCHIVES),verification['triangles'],flush=True)



def finalize():
 """Independent post-save geographic check;delete the temporary vertex dump."""
 import numpy as np
 from shapely.geometry import Polygon,Point
 p=OUT/'new-vertices-temporary.json'
 if not p.exists():return
 plan=json.loads((OUT/'registration.json').read_text());site=json.loads((ROOT/'result/blender/site_geometry.json').read_text());rcs=next(b for b in site['buildings']if b['id']=='way/1376078547');p35=Polygon(next(b for b in site['buildings']if b.get('code')=='35L')['rings'][0]);poly=Polygon(rcs['rings'][0]);vertices=json.loads(p.read_text());outside=[];inside35=[];distance=[]
 for n,ps in vertices.items():
  for v in ps:
   q=Point(v[:2]);distance.append(q.distance(p35))
   if not poly.buffer(1e-5).covers(q):outside.append((n,list(v),poly.distance(q)))
   if p35.buffer(-1e-5).contains(q):inside35.append((n,list(v)))
 assert not outside and not inside35,(outside[:3],inside35[:3])
 check=dict(newVerticesChecked=sum(map(len,vertices.values())),maximumBoundaryExcursionM=0.0,verticesInside35L=0,minimumNewVertexDistanceTo35LM=min(distance),boundaryToleranceM=.00001,originalRCSFootprintAreaM2=rcs['area'],newRoofAreaM2=plan['roof']['area'],roofFootprint35LIntersectionM2=plan['roof35LIntersectionM2'],newGeometryMinimumZM=min(v[2]for ps in vertices.values()for v in ps),noSourceObjectMoved=True)
 write(OUT/'boundary-check.json',check)
 for name in ['audit.json','verification.json']:
  path=OUT/name;j=json.loads(path.read_text());target=j['verification']if name=='audit.json'else j;target['boundaryChecks']=check;write(path,j)
 p.unlink()
 print('RCS224_BOUNDARY_PASS',json.dumps(check),flush=True)


def verify_campus_membership():
 """Quick explicit post-append native-scene visibility audit.No model saved."""
 import bpy
 audit=json.loads((OUT/'audit.json').read_text());bpy.ops.wm.open_mainfile(filepath=str(BASE))
 with bpy.data.libraries.load(str(ROOT/audit['componentPath']),link=False)as(src,dst):dst.objects=list(audit['addedObjects'])
 col=bpy.data.collections[COLLECTION]
 for o in dst.objects:col.objects.link(o)
 campus=bpy.data.scenes['00_CAMPUS_COMPLETE'];bpy.context.window.scene=campus
 for layer in campus.view_layers:layer.update()
 layer=campus.view_layers[0];present={n:n in campus.objects for n in audit['addedObjects']};visible={n:bpy.data.objects[n].visible_get(view_layer=layer)for n in audit['addedObjects']}
 assert all(present.values())and all(visible.values())
 check=dict(nativeCampusScene=campus.name,nativeCampusViewLayer=layer.name,contextCollectionAlreadyInNativeCampus=any(c.name==COLLECTION for c in campus.collection.children_recursive),nativeCampusPresentAddedObjects=sum(present.values()),nativeCampusVisibleAddedObjects=sum(visible.values()),allAddedObjectsPresentAndVisibleInNativeCampus=True,requiresAdditionalContextCollectionLink=False)
 for name in ['audit.json','verification.json']:
  path=OUT/name;j=json.loads(path.read_text());target=j['verification']if name=='audit.json'else j;target.update(check);write(path,j)
 print('RCS224_CAMPUS_VISIBILITY_PASS',json.dumps(check),flush=True)


if __name__=='__main__':
 if'bpy'in sys.modules:run()
 else:
  prepare();finalize()
