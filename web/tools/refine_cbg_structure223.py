"""Register CBG's LG-G-1-2 academic stair and continuous public galleries.

MachineLearning prepares fixed architect-plan traces;Blender authors a bounded
component and checks it against the accepted campus.No full native is saved.
2016copyright drawings published with the completed2019 project in2021 are
not certified as-built surveys;Z and construction sections remain estimates.
"""
from pathlib import Path
import sys,json,hashlib,math
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'result/blender/cbg-structure223'
SOURCE=ROOT/'data/collections/cbg-structure223'
BASE=ROOT/'result/blender/LSE_campus_detailed_v222.blend'
SHA='0d31c829778d88d643d9b4001f28116730862e8703d81cb6ad0429f8113fb50b'
PREFIX='CBG223_';COLLECTION='CBG_PUBLIC_INTERIOR_study';P='CBG203_WING_retained_CBG202_CBG_D_'
STEP=25/6
GROUND='CBG203_ROOF_CBG203_WING_retained_CBG202_CBG_D_roof_and_ground_plates'
TFLOOR='CBG203_ROOF_CBG203_WING_retained_CBG202_CBG_D_tower_floor_plates'
TGALLERY='CBG203_ROOF_CBG203_WING_retained_CBG202_CBG_D_tower_front_galleries'
FLOOR='CBG203_WING_registered_lower_gallery_plates'
STAIR_KEYS=['academic_stair_blue_stringers','academic_stair_dark_nosings','academic_stair_handrail_posts','academic_stair_handrails','academic_stair_landings','academic_stair_oak_treads','academic_stair_seating_terraces']
GUARD_KEYS=['gallery_guard_pale_vertical_slots','gallery_guard_solid_edges','gallery_guard_top_handhold']
STRUCTURE_KEYS=['atrium_blue_I_columns','atrium_blue_transfer_beams','atrium_bolt_heads','atrium_bolted_connection_plates']
ARCHIVES=[P+k for k in STAIR_KEYS+GUARD_KEYS+STRUCTURE_KEYS]+[P+'atrium_end_bridges',FLOOR,GROUND,TFLOOR,TGALLERY]
sys.path.insert(0,str(ROOT/'web/tools'))


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def prepare():
 import numpy as np
 from shapely.geometry import Polygon,box
 from shapely.ops import unary_union
 from shapely import constrained_delaunay_triangles
 from PIL import Image,ImageDraw
 mapping=json.loads((ROOT/'result/blender/cbg-georegistration202/rebuild-mapping.json').read_text());reg=json.loads((ROOT/'result/blender/cbg-georegistration202/registration.json').read_text())['fixed_true_scale_similarity']
 f=mapping['frame'];org=np.array(f['origin_G7_SW_world']);ex=np.array(f['x_unit_SW']);ey=np.array(f['y_unit_SE_rear']);rot=np.array(reg['rotation_row_matrix_after_y_flip']);tr=np.array(reg['translation_world'])
 def local(p):
  q=20/285*(np.array(p)*[1,-1])@rot+tr-org
  return [float(q@ex),float(q@ey)]
 # Plan1/2 inner atrium edge,not the arbitrary205 y=-7.5 cut.
 void_px=[(455,596),(795,596),(797,711),(451,671)]
 lg_px=[(883,645),(1141,655),(1137,752),(876,722)]
 void=Polygon([local(p)for p in void_px]);lg=Polygon([local(p)for p in lg_px])
 outer=Polygon(mapping['houghton_teaching_block']['GIS_polygon_local']);raw_void=void;void=void.intersection(outer.buffer(-.04));plate=outer.difference(void).buffer(0)
 assert plate.geom_type=='Polygon'and len(plate.interiors)==1
 tower=Polygon([(-42,0),(0,0),(0,15.94),(-42,18.26)])
 connector=box(-.2,-2.5,1.05,6.15).difference(outer).difference(tower).buffer(0)
 if connector.geom_type!='Polygon':connector=max(connector.geoms,key=lambda p:p.area)
 assert connector.geom_type=='Polygon'
 def shape(p):return dict(outer=list(p.exterior.coords),holes=[list(r.coords)for r in p.interiors],triangles=[list(t.exterior.coords)[:3]for t in constrained_delaunay_triangles(p).geoms],area=p.area)
 # Five visibleHcolumn marks at the academic stair's inner edge.
 columns_px=[(455,615),(540,622),(626,626),(712,632),(797,637)]
 data=dict(registration='Reuse202 externalOLD/STC/PAN controls,scale20m/285px;all new drawings have the same1700x1201 site backdrop',sourceDate='2016 drawing copyright;2021 publication with completed2019 project;not certifiedasbuilt',sourceVoidClippedAtAcceptedInterfaceM2=raw_void.difference(void).area,plate=shape(plate),connector=shape(connector),atrium=shape(void),lgOpening=shape(lg),columns=[local(p)for p in columns_px],voidPixels=void_px,lgPixels=lg_px,estimatedLevelDatums=dict(LG=-STEP-.005,G=-.005,first=STEP-.005,second=2*STEP-.005),route=[dict(name='LG-G',x0=-14.8,x1=-6.4,z0=-STEP-.005,z1=-.005),dict(name='G-1',x0=.45,x1=11.7,z0=-.005,z1=STEP-.005),dict(name='1-2',x0=12.7,x1=24.1,z0=STEP-.005,z1=2*STEP-.005)])
 (OUT/'plan-layout.json').write_text(json.dumps(data,indent=2)+'\n')
 im=Image.open(SOURCE/'level1-plan-rshp.jpg').convert('RGB');d=ImageDraw.Draw(im)
 d.line(void_px+[void_px[0]],fill='#bf4636',width=4)
 for n,p in enumerate(columns_px):d.ellipse((p[0]-6,p[1]-6,p[0]+6,p[1]+6),outline='#2166a1',width=3);d.text((p[0]+7,p[1]-15),f'C{n+1}',fill='#154f80')
 d.text((300,370),'RSHP plan1: red atrium boundary / blue5 column axes;private registration evidence',fill='#253e4b')
 im.save(OUT/'plan1-registration.png')
 im=Image.open(SOURCE/'ground-plan-rshp.jpg').convert('RGB');d=ImageDraw.Draw(im);d.line(lg_px+[lg_px[0]],fill='#bf4636',width=4);d.text((700,570),'Ground opening towardsLG;source route,estimated stair dimensions',fill='#253e4b');im.save(OUT/'ground-opening-registration.png')
 sources=dict(retrieved='2026-10-16',drawings=json.loads((SOURCE/'plan-sources.json').read_text()),officialAwardDrawings=json.loads((SOURCE/'drawing-sources.json').read_text()),primaryReferences=[dict(url='https://rshp.com/projects/education/lse-centre-building/',role='Completed2019 architect account;academic stair and stepped double-height spaces;prefabricated frame and slabs'),dict(url='https://info.lse.ac.uk/staff/divisions/estates-division/lse-estate/development-projects/centre-buildings-redevelopment',role='LSE confirms public basement/ground/first/second levels'),dict(path='data/collections/exteriors/images/cbg_rshp_023.jpg',sha256=sha(ROOT/'data/collections/exteriors/images/cbg_rshp_023.jpg'),url='https://rshp.com/assets/crops/3x5.d4bbf657.10190_n22645.jpg',role='Built academic stair;oak seating centre,side treads,blueframe,white guards;capture date unknown'),dict(path='data/collections/exteriors/images/cbg_rshp_024.jpg',sha256=sha(ROOT/'data/collections/exteriors/images/cbg_rshp_024.jpg'),url='https://rshp.com/assets/crops/3x2.1d9a5615.10190_n22643.jpg',role='Built second-floor atrium;continuous side gallery and bridge;capture date unknown')],limits=['Published completed-project drawings carry2016 copyright;publication2021 is not a drawing or photograph capture date.','Do not use source photographs as public textures.','Existing external envelope and tower floors3+ retained;lower public registration only.'])
 (SOURCE/'sources.json').write_text(json.dumps(sources,indent=2)+'\n');print('CBG223_PLAN_READY',plate.area,void.area,lg.area,flush=True)


def run():
 import bpy,bmesh
 from mathutils import Vector,Matrix
 from mathutils.bvhtree import BVHTree
 from integrate_exterior_round194 import object_fingerprint,accepted_fingerprints
 from refine_portsmouth_exterior207 import material_fingerprint
 from build_clm_hongkong_room220 import modifier_payload
 from build_room_samples167 import RoomGeometry
 from refine_cbg_roof203 import frame,trim_object,volume_planes
 from refine_cbg_roof_envelope import components
 from refine_ground_orientation199 import closed_islands
 def update():
  for scene in bpy.data.scenes:
   for layer in scene.view_layers:layer.update()
  bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE']
 def state():
  meta=json.loads((ROOT/'web/tools/building-metadata.json').read_text());rooms={r['collection']:sorted(o.name for o in bpy.data.collections[r['collection']].all_objects)for r in meta['spaces']}
  assert len(rooms)==21 and len(set().union(*(set(v)for v in rooms.values())))==767
  return dict(objects={o.name:object_fingerprint(o)for o in bpy.data.objects},materials={m.name:material_fingerprint(m)for m in bpy.data.materials},modifiers={o.name:hashlib.sha256(json.dumps([modifier_payload(m)for m in o.modifiers],sort_keys=True).encode()).hexdigest()for o in bpy.data.objects},ownership={o.name:sorted(c.name for c in o.users_collection)for o in bpy.data.objects},visibility={o.name:o.hide_render for o in bpy.data.objects},rooms=rooms,roomScenes={c:{s.name:sorted(n for n in names if n in s.objects)for s in bpy.data.scenes}for c,names in rooms.items()})
 def verify(before,hidden):
  assert all(object_fingerprint(bpy.data.objects[n])==v for n,v in before['objects'].items())
  assert all(material_fingerprint(bpy.data.materials[n])==v for n,v in before['materials'].items())
  for n,v in before['modifiers'].items():assert hashlib.sha256(json.dumps([modifier_payload(m)for m in bpy.data.objects[n].modifiers],sort_keys=True).encode()).hexdigest()==v,n
  assert all(sorted(c.name for c in bpy.data.objects[n].users_collection)==v for n,v in before['ownership'].items())
  assert all(bpy.data.objects[n].hide_render==(True if n in hidden else v)for n,v in before['visibility'].items())
  assert all(sorted(o.name for o in bpy.data.collections[c].all_objects)==names for c,names in before['rooms'].items())
  assert {c:{s.name:sorted(n for n in names if n in s.objects)for s in bpy.data.scenes}for c,names in before['rooms'].items()}==before['roomScenes']
 def tree(objects):
  vs=[];fs=[]
  for o in objects:
   off=len(vs);vs.extend(o.matrix_world@v.co for v in o.data.vertices);fs.extend(tuple(off+i for i in p.vertices)for p in o.data.polygons)
  return BVHTree.FromPolygons(vs,fs)
 assert sha(BASE)==SHA;bpy.ops.wm.open_mainfile(filepath=str(BASE));update();before=state();assert before['objects']==accepted_fingerprints(ROOT/'result/blender/stage222',SHA)and len(before['objects'])==7688
 assert all(not bpy.data.objects[n].hide_render for n in ARCHIVES)
 protected=set().union(*(set(v)for v in before['rooms'].values()));assert not protected.intersection(ARCHIVES)
 col=bpy.data.collections[COLLECTION];campus_linked=all(n in bpy.data.scenes['00_CAMPUS_COMPLETE'].objects for n in [FLOOR,TFLOOR])
 assert campus_linked
 local,world=frame(json.loads((ROOT/'result/blender/cbg-georegistration202/rebuild-mapping.json').read_text()));plan=json.loads((OUT/'plan-layout.json').read_text())
 added=[];records=[]
 def clone(name,tag):
  src=bpy.data.objects[name];o=src.copy();o.data=src.data.copy();o.name=PREFIX+tag;o['originalObject']=name;col.objects.link(o);o.hide_render=False;o.hide_set(False);added.append(o);return o
 def retain_above(name,height,tag):
  o=clone(name,tag);bm=bmesh.new();bm.from_mesh(o.data)
  gone=[v for v in bm.verts if (o.matrix_world@v.co).z<height];bmesh.ops.delete(bm,geom=gone,context='VERTS');bm.to_mesh(o.data);bm.free();o.data.update();return o
 # Retain the provisional third gallery/bridge/guard exactly beyond this scope.
 retain_above(FLOOR,10,'retained_third_gallery')
 retain_above(P+'atrium_end_bridges',10,'retained_third_end_bridges')
 for k in GUARD_KEYS:retain_above(P+k,10,'retained_third_'+k)
 # The two public tower floors/front galleries must meet the same teaching
 # datums;all vertices,UVs and modifiers of upper floors remain in the copy.
 level_adjustments=[]
 for name,tag in [(TFLOOR,'aligned_tower_floor1_2'),(TGALLERY,'aligned_tower_gallery1_2')]:
  src=bpy.data.objects[name];o=clone(name,tag)
  for ids in components(src.data):
   ps=[src.matrix_world@src.data.vertices[i].co for i in ids];top=max(p.z for p in ps);level=round(top/(52.2/13))
   if level not in [1,2]or not 2<top<9:continue
   shift=level*STEP-.005-top
   for i in ids:
    p=src.matrix_world@src.data.vertices[i].co;p.z+=shift;o.data.vertices[i].co=o.matrix_world.inverted()@p
   level_adjustments.append(dict(source=name,level=level,oldTop=top,newTop=level*STEP-.005,verticalShift=shift))
  o.data.update()
 # Cut the actual ground slab only inside the plan'sLG stair opening.
 cut=trim_object(bpy.data.objects[GROUND],local,world,[volume_planes(plan['lgOpening']['outer'][:-1],-.4,.15)])
 assert cut is not None
 o,cutproof=cut;assert not cutproof['skippedIslands'];o.name=PREFIX+'ground_with_registered_LG_opening';o.data.name=o.name;o['originalObject']=GROUND;col.objects.link(o);added.append(o)
 g=RoomGeometry(col,PREFIX)
 def mat(key,source):g.materials[key]=bpy.data.objects[source].data.materials[0]
 for key,source in [('blue',P+'academic_stair_blue_stringers'),('oak',P+'academic_stair_oak_treads'),('dark',P+'academic_stair_handrails'),('pale',P+'gallery_guard_solid_edges'),('slab',FLOOR),('finish',P+'academic_stair_landings')]:mat(key,source)
 def slab(name,shape,z,h,material):
  vs=[];faces=[];lookup={}
  def idx(x,y,z):
   p=(round(x,6),round(y,6),round(z,6))
   if p not in lookup:lookup[p]=len(vs);vs.append(world(p))
   return lookup[p]
  for tri in shape['triangles']:
   a=[idx(*p,z)for p in tri];b=[idx(*p,z+h)for p in tri];faces.extend([tuple(reversed(a)),tuple(b)])
  for ring in [shape['outer']]+shape['holes']:
   for a,b in zip(ring,ring[1:]):faces.append((idx(*a,z),idx(*b,z),idx(*b,z+h),idx(*a,z+h)))
  mesh=bpy.data.meshes.new(PREFIX+name);mesh.from_pydata(vs,[],faces);mesh.materials.append(g.materials[material]);mesh.update();bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));assert all(len(e.link_faces)==2 for e in bm.edges);assert bm.calc_volume()>0;bm.to_mesh(mesh);bm.free()
  uv=mesh.uv_layers.new(name='MetricSurfaceUV')
  for p in mesh.polygons:
   for li in p.loop_indices:
    v=local(mesh.vertices[mesh.loops[li].vertex_index].co);uv.data[li].uv=(v.x,v.y)
  o=bpy.data.objects.new(PREFIX+name,mesh);col.objects.link(o);added.append(o);return o
 for level in [1,2]:slab('source_floor'+str(level),plan['plate'],level*STEP-.275,.27,'slab')
 for level in [0,1,2]:slab('source_floor'+str(level)+'_interface_joint',plan['connector'],level*STEP-.275,.27,'slab')
 # Five source-plan column axes replace the inherited stretched six-bay row.
 for x,y in plan['columns']:
  g.box('five_source_column_webs','blue',(x,y,8.2),(.14,.40,16.4))
  g.box('five_column_footplates','blue',(x,y,-.005),(.46,.56,.03))
  for dy in [-.22,.22]:g.box('five_source_column_flanges','blue',(x,y+dy,8.2),(.40,.055,16.4))
  for z in [STEP-.205,2*STEP-.205,3*STEP-.205,4*STEP-.205]:
   g.box('source_cross_beams','blue',(x,y-1.2,z),(.32,2.4,.40))
 # Same inherited model scale,now along source routes and correctLG-G-1-2levels.
 def centre_y(x):return 2.88-.54*max(0,min(1,x/24.1))if x>=0 else 3.85
 def width(x):return 3.78-.61*max(0,min(1,x/24.1))if x>=0 else 3.9
 walk=[];seat_support=[]
 def prism(family,material,outline,z,h):g.prism(family,material,outline,z,h)
 for flight,row in enumerate(plan['route']):
  a,b,z0,z1=row['x0'],row['x1'],row['z0'],row['z1'];N=26;rise=(z1-z0)/N
  for i in range(N):
   xa=a+(b-a)*i/N;xb=a+(b-a)*(i+1)/N;z=z0+(i+1)*rise
   ya,yb=centre_y(xa),centre_y(xb);wa,wb=width(xa),width(xb);side=.95
   for sign in [-1,1]:
    poly=[(xa,ya+sign*wa/2),(xb,yb+sign*wb/2),(xb,yb+sign*(wb/2-side)),(xa,ya+sign*(wa/2-side))]
    prism('academic_oak_treads','oak',poly,z-.12,.12)
    g.box('dark_tread_nosings','dark',((xa+xb)/2,(ya+yb)/2+sign*((wa+wb)/4-side/2),z+.003),(min(.035,xb-xa),side,.006))
   walk.append(dict(flight=flight,step=i+1,local=[(xa+xb)/2,(ya+yb)/2-(wa+wb)/4+side/2,z],rise=rise))
  # Middle seating is stepped in groups,as the built photograph clearly shows.
  for i in range(0,N,3):
   xa=a+(b-a)*i/N;xb=a+(b-a)*min(i+3,N)/N;z=z0+min(i+3,N)*rise;cy=centre_y((xa+xb)/2);w=width((xa+xb)/2)-1.9
   thickness=(min(i+3,N)-i)*rise+.12;bottom=z-thickness
   g.box('central_oak_seating','oak',((xa+xb)/2,cy,z-thickness/2),(xb-xa,w,thickness))
   # A transverse member links the seating unit to both continuous side
   # stringers;the underside follows the flight rather than dangling to its
   # starting floor under every higher seat.
   g.box('continuous_blue_stringers','blue',(xa+.07,cy,z0+i*rise-.17),(.14,width(xa)-.15,.30))
   seat_support.append([xa+.07,cy,bottom])
  for sign in [-1,1]:
   pa=Vector((a,centre_y(a)+sign*(width(a)/2-.08),z0-.17));pb=Vector((b,centre_y(b)+sign*(width(b)/2-.08),z1-.17))
   # Closed rectangular pitch beam with true sloped support under every tread.
   axis=(pb-pa).normalized();side=Vector((0,.07,0));depth=axis.cross(side.normalized()).normalized()*.13
   vs=[p+s*side+t*depth for p in [pa,pb]for s,t in [(-1,-1),(1,-1),(1,1),(-1,1)]]
   g.add('continuous_blue_stringers','blue',vs,[(3,2,1,0),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)])
   g.tube('stair_handrails','dark',(a,pa.y,z0+1.04),(b,pb.y,z1+1.04),.025)
   for i in range(0,N+1,2):
    t=i/N;x=a+(b-a)*t;y=centre_y(x)+sign*(width(x)/2-.08);z=z0+(z1-z0)*t
    g.tube('stair_guard_posts','dark',(x,y,z),(x,y,z+1.04),.018)
 # Source ground opening leads into the ground floor before the next flight.
 pads=[('LG_approach',-16.,-14.8,3.85,3.9,-STEP-.005),('G_arrival',-6.4,-5.1,3.85,3.9,-.005),('G_departure',-.55,.45,centre_y(.45),width(.45),-.005),('first_midlanding',11.7,12.7,centre_y(12.2),width(12.2),STEP-.005),('second_exit',24.1,25.3,centre_y(24.1),width(24.1),2*STEP-.005)]
 for tag,a,b,y,w,z in pads:g.box(tag,'finish',((a+b)/2,y,z-.10),(b-a,w,.20))
 # First-floor side connection crosses only the source-defined atrium;the
 # end-floor paths are already continuous parts of the new perforated plates.
 x=12.2;edge_y=-1.35+(x-24.26)/(.44-24.26)*(-2.656+1.35);stair_y=centre_y(x)-width(x)/2
 g.box('first_gallery_connection','finish',(x,(edge_y+stair_y+.25)/2,STEP-.105),(3.0,stair_y-edge_y+.25,.20))
 g.box('first_bridge_support_beam','blue',(x,(edge_y+stair_y)/2,STEP-.255),(.25,stair_y-edge_y+.10,.30))
 # White slotted guards follow actual plan edges,with the stair exit and bridge
 # kept open.Side connections use rails rather than a sheet across their doors.
 for level in [1,2]:
  ring=plan['atrium']['outer']
  for a,b in zip(ring,ring[1:]):
   a,b=Vector((*a,0)),Vector((*b,0));d=b-a;length=d.length;n=max(1,math.ceil(length/.14))
   for j in range(n+1):
    p=a.lerp(b,j/n);near_bridge=level==1 and abs(p.x-12.2)<1.60 and p.y<-.5
    near_exit=level==2 and p.x>23.7 and p.y>.65
    if near_bridge or near_exit:continue
    g.box('source_gallery_slots','pale',(p.x,p.y,level*STEP+.50),(.045,.06,1.01),math.atan2(d.y,d.x))
   for k in range(n):
    p=a.lerp(b,(k+.5)/n)
    if (level==1 and abs(p.x-12.2)<1.60 and p.y<-.5)or(level==2 and p.x>23.7 and p.y>.65):continue
    g.box('source_gallery_handrails','dark',(p.x,p.y,level*STEP+1.04),(length/n+.002,.05,.05),math.atan2(d.y,d.x))
 for sx in [-1.5,1.5]:g.tube('first_bridge_handrails','dark',(x+sx,edge_y,STEP+1.04),(x+sx,stair_y+.25,STEP+1.04),.025)
 batch=g.finish()
 for o in batch:
  for v in o.data.vertices:v.co=world(v.co)
  o.data.update();added.append(o)
 for o in added:o['destinationCollection']=COLLECTION;o['buildingCode']='CBG';o['scope']='Source-supported lower publicLG-G-1-2stair and1/2 galleries;estimated dimensions;upper tower retained'
 newnames=[o.name for o in added]
 def physical():
  active=[o for o in col.all_objects if o.type=='MESH'and not o.hide_render and o.name not in ARCHIVES]
  floors=tree([o for o in active if any(k in o.name for k in ['source_floor','aligned_tower_','G_arrival','G_departure','first_midlanding','second_exit','first_gallery_connection','ground_with_'])])
  support=tree([o for o in active if 'continuous_blue_stringers'in o.name])
  overhead=tree([o for o in active if any(k in o.name for k in ['floor','plate','beam','landing'])])
  stair_probes=[]
  for row in walk:
   x,y,z=row['local'];p=world((x,y,z));hit=support.ray_cast(p,Vector((0,0,-1)),.5)
   # A near-edge pitchline lies immediately beneath the closed side treads.
   near_y=centre_y(x)-width(x)/2+.08;q=world((x,near_y,z));hit=support.ray_cast(q,Vector((0,0,-1)),.5);assert hit[0]is not None,(row,'unsupported tread')
   roof=overhead.ray_cast(p+Vector((0,0,.20)),Vector((0,0,1)),60)
   clearance=None if roof[0]is None else roof[0].z-z
   assert clearance is None or clearance>2.0,(row,clearance)
   stair_probes.append(dict(flight=row['flight'],step=row['step'],stringerDrop=z-hit[0].z,headroom=clearance))
  joins=[]
  for tag,a,b,y,w,z in pads:
   if tag=='LG_approach':continue
   p=world(((a+b)/2,y,z+.05));hit=floors.ray_cast(p,Vector((0,0,-1)),.15);assert hit[0]is not None;joins.append(dict(name=tag,finishedDatum=z,actualTop=hit[0].z,gap=abs(z-hit[0].z)))
  # Check the actual door-like bridge route across its full width at regular
  # stations;these are geometry probes,not access or fire certification.
  route=[]
  for t in range(11):
   y=edge_y+(stair_y-edge_y)*t/10
   for dx in [-.5,0,.5]:
    p=world((12.2+dx,y,STEP+.045));hit=floors.ray_cast(p,Vector((0,0,-1)),.12);assert hit[0]is not None
    route.append(abs(hit[0].z-(STEP-.005)))
  hole_probe=world((-18,4,.10));groundtree=tree([bpy.data.objects[PREFIX+'ground_with_registered_LG_opening']]);assert groundtree.ray_cast(hole_probe,Vector((0,0,-1)),.5)[0]is None
  obstacles=tree([o for o in active if any(k in o.name for k in ['column','flange','handrail','guard','slots'])]);detour=[(12.2,edge_y-.08),(11.4,edge_y-.08),(11.4,stair_y+.20),(12.2,stair_y+.20),(12.2,centre_y(12.2))];route_hits=0
  for a,b in zip(detour,detour[1:]):
   a,b=world((*a,STEP+1.035)),world((*b,STEP+1.035));delta=b-a;hit=obstacles.ray_cast(a,delta.normalized(),delta.length)
   assert hit[0]is None,('column/guard blocks first-floor exit',list(a),list(b),hit);route_hits+=1
  column_tree=tree([o for o in active if any(k in o.name for k in ['registered_teaching_floor_plates','ground_with_','source_floor0_interface'])]);column_gaps=[]
  for x,y in plan['columns']:
   hit=column_tree.ray_cast(world((x,y,.08)),Vector((0,0,-1)),.2);assert hit[0]is not None;column_gaps.append(abs(hit[0].z+.005))
  for x,y,z in seat_support:
   hit=support.ray_cast(world((x,y,z+.15)),Vector((0,0,-1)),.4);assert hit[0]is not None and -.15<z-hit[0].z<.20
  return dict(firstBridgeColumnAvoidanceSegments=route_hits,seatingCrossSupportSamples=len(seat_support),columnBaseSupportSamples=len(column_gaps),maximumColumnBaseDatumGapM=max(column_gaps),stairTreads=stair_probes,joins=joins,bridgeDoorwaySamples=len(route),bridgeSideRailClearWidthM=2.95,bridgeDeckWidthM=3.0,landingHandrailEndGapM=.95,maximumBridgeFinishedGapM=max(route),groundOpeningProbeClear=True,all78RisersSupported=True,minimumMeasuredHeadroomM=min(r['headroom']for r in stair_probes if r['headroom']is not None),riseM=STEP/26,estimatedMainFlightGoingM=(11.7-.45)/26,sourceColumnAxes=5)
 def previews(label):
  scene=bpy.data.scenes.new(PREFIX+'REVIEW');scene.render.engine='CYCLES';scene.cycles.samples=10;scene.cycles.use_denoising=True;scene.render.resolution_x=1100;scene.render.resolution_y=800;scene.render.resolution_percentage=100;scene.view_settings.view_transform='AgX'
  worlddata=bpy.data.worlds.new(PREFIX+'WORLD');worlddata.use_nodes=True;worlddata.node_tree.nodes['Background'].inputs[0].default_value=(.78,.82,.88,1);worlddata.node_tree.nodes['Background'].inputs[1].default_value=.8;scene.world=worlddata;copies=[]
  for old in list(col.all_objects):
   if old.type!='MESH'or old.hide_render or not old.data.vertices:continue
   if label=='before'and old.name in newnames:continue
   if label=='after'and old.name in ARCHIVES:continue
   o=old.copy();o.data=old.data.copy();o.data.transform(old.matrix_world);o.matrix_world=Matrix.Identity(4);bm=bmesh.new();bm.from_mesh(o.data)
   for height,outer in [(11.35,True),(-4.5,False)]:bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=.000001,plane_co=(0,0,height),plane_no=(0,0,1),clear_outer=outer,clear_inner=not outer)
   bm.to_mesh(o.data);bm.free()
   if not o.data.polygons:bpy.data.objects.remove(o);continue
   scene.collection.objects.link(o);copies.append(o)
  camera=bpy.data.objects.new(PREFIX+'CAM',bpy.data.cameras.new(PREFIX+'CAM'));scene.collection.objects.link(camera);scene.camera=camera;camera.data.type='ORTHO';camera.data.clip_end=500
  light=bpy.data.objects.new(PREFIX+'SUN',bpy.data.lights.new(PREFIX+'SUN','SUN'));scene.collection.objects.link(light);light.data.energy=2;light.rotation_euler=(.4,-.3,-.5)
  for tag,pos,target,scale in [('academic-stair',(-4,4.7,1.65),(14,2.4,5.0),44),('public-route',(34,30,36),(6,-1,4),64)]:
   if tag=='academic-stair':camera.data.type='PERSP';camera.data.lens=21
   else:
    camera.data.type='ORTHO'
    for copy in copies:
     bm=bmesh.new();bm.from_mesh(copy.data);bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=.000001,plane_co=(0,0,7.75),plane_no=(0,0,1),clear_outer=True);bm.to_mesh(copy.data);bm.free()
   camera.location=world(pos);camera.rotation_euler=(world(target)-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.ortho_scale=scale;scene.render.filepath=str(OUT/(label+'-'+tag+'.png'));bpy.context.window.scene=scene;bpy.ops.render.render(write_still=True)
  bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE']
  for o in copies+[camera,light]:
   data=o.data;bpy.data.objects.remove(o,do_unlink=True)
   if isinstance(data,bpy.types.Mesh)and data.users==0:bpy.data.meshes.remove(data)
  bpy.data.scenes.remove(scene);bpy.data.worlds.remove(worlddata);update()
 checks=physical();previews('before')
 for n in ARCHIVES:bpy.data.objects[n].hide_render=True
 previews('after');verify(before,set(ARCHIVES))
 fingerprints={o.name:object_fingerprint(o)for o in added};bindings={o.name:[m.name for m in o.data.materials]for o in added};component=OUT/'cbg-structure223-component.blend';bpy.data.libraries.write(str(component),set(added),fake_user=True,compress=True);digest=sha(component)
 bpy.ops.wm.open_mainfile(filepath=str(BASE));update();verify(before,set())
 with bpy.data.libraries.load(str(component),link=False)as(available,loaded):loaded.objects=list(fingerprints)
 for o in loaded.objects:
  for i,n in enumerate(bindings[o.name]):o.data.materials[i]=bpy.data.materials[n]
  col=bpy.data.collections[COLLECTION];col.objects.link(o);o.hide_render=False;o.hide_set(False)
 for n in ARCHIVES:bpy.data.objects[n].hide_render=True
 update();verify(before,set(ARCHIVES));assert all(object_fingerprint(bpy.data.objects[n])==v for n,v in fingerprints.items());assert physical()==checks;assert sha(BASE)==SHA and sha(component)==digest
 def web(p):q=world(p);return[q.x,q.z,-q.y]
 view=dict(position=web((-5,9,2.0)),target=web((15,2.5,5.0)),fov=65)
 sections=[]
 for id,z in [('LG',-STEP),('G',0),('1',STEP),('2',STEP*2)]:
  sections.append(dict(id=id,label=id+'层：公共楼梯与连廊',minHeight=z-.30,maxHeight=z+3.50,scope='Source-supported lower public route;estimated vertical datums and construction,not a current survey',view=dict(position=web((30,18,z+20)),target=web((8,-1,z+1)),fov=50)))
 suggestions=dict(interiorView=view,interiorSections=sections,gallerySuggestions=[dict(name='cbg-academic-route-interior',label='CBG公共学术梯',view=view),dict(name='cbg-level1-structure-interior',label='CBG一层楼板与连桥',sectionId='1',view=sections[2]['view'])])
 verification=dict(savedComponentReopenedAndAppended=True,originalObjectsVerified=7688,originalMaterialNodesVerified=len(before['materials']),protectedSpacesVerified=21,protectedSpaceObjectsVerified=767,originalGeometryUVsTransformsBindingsAndModifiersUnchanged=True,allOriginalCollectionMembershipsUnchanged=True,protectedSpaceSceneMembershipsUnchanged=True,onlyListedOriginalVisibilityChanged=True,publicCollectionAlreadyInNativeCampus=campus_linked,noFullNativeWritten=True,sourcePhotographsNotUsedAsTextures=True,sourceAndComponentSha256Rechecked=True,addedObjects=len(added),triangles=sum(sum(len(p.vertices)-2 for p in bpy.data.objects[n].data.polygons)for n in fingerprints),physicalChecks=checks)
 audit=dict(version=223,building='CBG',baseline=str(BASE.relative_to(ROOT)),baselineSha256=SHA,componentPath=str(component.relative_to(ROOT)),componentSha256=digest,targetCollection=COLLECTION,destinationCollection=COLLECTION,interiorCollection=COLLECTION,replacesInteriorCollection=COLLECTION,sameCollectionPartialReplacement=True,addedObjects=list(fingerprints),archivedObjects=ARCHIVES,changedObjects=[],addedFingerprints=fingerprints,replacementMaterialBindings=bindings,sourceManifest=str((SOURCE/'sources.json').relative_to(ROOT)),publicViewSuggestion=suggestions,publicCollectionAlreadyInNativeCampus=campus_linked,sourceFloorOuterContour205Preserved=True,towerLowerFloorAdjustments=level_adjustments,groundOpeningCut=cutproof,newPublicPlateAreaEach=plan['plate']['area'],boundedInterfaceJointAreaM2=plan['connector']['area'],sourceAtriumVoidArea=plan['atrium']['area'],verification=verification,changes=['Replace the misplacedG-1-2-3academic stair by the source-supportedLG-G-1-2route,including the actual ground opening and a boundedLG arrival pad.','Replace the1/2gallery floor gap by closed plates around the traced source void;connect first-floor landing to side gallery and second-floor exit directly into the floor.','Use five source column axes and closed blue pitch stringers beneath all78risers.','Align only tower floors/front galleries1/2to the same public floor datums;retain all tower floors3+and accepted exterior geometry.'],limitations=['Drawings have2016copyright and were published with the completed2019project in2021.They are not certifiedasbuilt,or evidence of current fitout.','Route and openings follow traced plan landmarks;slab thickness270mm,4.1667m low-wing pitch,26risers per flight,LG pad,3m bridge deck wrapping the source column,and support/guard sections are geometric estimates;the landing handrail end gap is0.95m,not an access compliance claim.','Three-storey public route is corrected;the retained provisional third gallery,upper baffles,upper low-wing roof/floors and tower3+still need a separate whole-building vertical survey.','Only a boundedLG stair approach is modeled,not an invented complete basement or auditorium.','Geometry support/headroom/doorway checks are not structural,accessibility,fire or current-condition certification.','No independentCBGroom was moved into these geographic plates.'],previews=['before-public-route.png','after-public-route.png','before-academic-stair.png','after-academic-stair.png'])
 (OUT/'audit.json').write_text(json.dumps(audit,indent=2,ensure_ascii=False)+'\n');(OUT/'verification.json').write_text(json.dumps(verification,indent=2)+'\n');(OUT/'view-suggestions.json').write_text(json.dumps(suggestions,indent=2,ensure_ascii=False)+'\n');print('CBG223_READY',digest,len(fingerprints),len(ARCHIVES),verification['triangles'],checks['minimumMeasuredHeadroomM'],flush=True)


if __name__=='__main__':
 try:import bpy
 except ImportError:prepare()
 else:run()
