"""Private SAW233 source-constrained estimated circulation repair.

Open in Blender Text Editor for actual-mesh capture/build; run with the existing
MachineLearning interpreter for planar preparation/proof. All settings are fixed.
Original native and historical sources stay read-only.
"""
from pathlib import Path
import json, hashlib, sys, math
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'result/blender/saw-circulation233'
DATA=ROOT/'data/collections/saw-circulation233'
BASE=ROOT/'result/blender/LSE_campus_detailed_v232.blend'
SHA='1f6ed3da66011e057233697fe8753374a55918d8c4278d56670cbd81192ae2a8'
sys.path.insert(0,str(ROOT/'web/tools'))
def save(name,value):
 OUT.mkdir(parents=True,exist_ok=True);(OUT/name).write_text(json.dumps(value,separators=(',',':'))+'\n')
def capture():
 import bpy
 from integrate_exterior_round194 import update_scene
 assert hashlib.sha256(BASE.read_bytes()).hexdigest()==SHA
 bpy.ops.wm.open_mainfile(filepath=str(BASE));update_scene()
 rows=[]
 public=bpy.data.collections.get('SAW_PUBLIC_INTERIOR_study');public_ids={o.name for o in public.all_objects}if public else set()
 for o in bpy.data.objects:
  if o.type!='MESH' or o.hide_render or not(o.name.startswith(('SAW','SAWFLOOR'))or o.name in public_ids):continue
  v=[list(o.matrix_world@p.co)for p in o.data.vertices]
  if not v:continue
  bounds=[[min(p[i]for p in v),max(p[i]for p in v)]for i in range(3)]
  if bounds[0][1]<-76 or bounds[0][0]>-59 or bounds[1][1]<-2 or bounds[1][0]>18 or bounds[2][0]>20.2 or bounds[2][1]<0:continue
  o.data.calc_loop_triangles()
  rows.append(dict(name=o.name,vertices=v,triangles=[list(t.vertices)for t in o.data.loop_triangles],faces=[list(p.vertices)for p in o.data.polygons],normals=[list(p.normal)for p in o.data.polygons],bounds=bounds,collections=[c.name for c in o.users_collection]))
 save('baseline-surfaces.json',dict(baselineSha256=SHA,spatialBroadPhaseBounds=[[-76,-59],[-2,18],[0,20.2]],scope='All visible SAW-prefixed and public-assembly mesh bounds overlapping the protected circulation proof volume',objects=rows))
 print('SAW233_CAPTURE',len(rows),sum(len(r['triangles'])for r in rows),'actual triangles',flush=True)


def prepare():
 import numpy as np
 import shapely
 from shapely.geometry import Polygon, mapping, shape, LineString
 from shapely.ops import unary_union
 from shapely.geometry.polygon import orient
 import matplotlib
 matplotlib.use('Agg')
 import matplotlib.pyplot as plt
 baseline=json.loads((OUT/'baseline-surfaces.json').read_text());native={r['name']:r for r in baseline['objects']}
 prior=json.loads((ROOT/'result/blender/saw-floors216/surface-plan.json').read_text())
 def horizontal(row):
  v=np.array(row['vertices']);result=[]
  for i,f in enumerate(row['faces']):
   p=v[f]
   if len(p)>2 and np.ptp(p[:,2])<1e-5 and np.cross(p[1]-p[0],p[2]-p[0])[2]>0:
    poly=Polygon(p[:,:2])
    if poly.area>1e-8:result.append(dict(face=i,top=float(p[0,2]),polygon=poly))
  return result
 old=horizontal(native['SAW223_Retained_SAW173_registered_main_treads'])
 reg=json.loads((ROOT/'result/blender/saw-floors216/registration.json').read_text());vectors=json.loads((ROOT/'result/blender/saw-floors216/vectors.json').read_text())
 anchors=np.array([[-65.223399,-15.905616],[-84.252182,28.425],[-55.301,36.609104]])
 def world(points):
  p=np.array(points);a,b,c=anchors;return a+(p[:,0:1]-145)/1200*(b-a)+(p[:,1:2]-400)/785*(c-b)
 cabins=[Polygon(world(np.array(next(c for c in vectors['32']['candidates']if c['index']==i)['pts'][:-1])*1501/595.276))for i in reg['32']['sourceControlCurveIndices']]
 lifts=unary_union(cabins);d=np.array([-.64,.77]);d/=np.linalg.norm(d);n=np.array([d[1],-d[0]]);width=1.4;separation=1.6;going=.31
 def rectangle(a,b):return Polygon([a-n*width/2,a+n*width/2,b+n*width/2,b-n*width/2])
 treads=[];routes=[];landings=[]
 for flight,z0,z1,counts,cross_shift in [(1,3.45,8.1,[16,15],0),(2,8.1,11.1,[10,10],0)]:
  if flight>=3:
   rr=reg['27'];offset=np.array(rr['offset'])*(1501/595.276);matrix=np.array(rr['matrix']);source=np.array([[830.,565.],[790.,475.],[695.,520.]])@matrix+offset;ss,kk,end=world(source);u=(kk-ss)/np.linalg.norm(kk-ss);v=(end-kk)/np.linalg.norm(end-kk);start=ss+u*.8;q=kk-u*.7;r=kk+v*.7;directions=[u,v];normals=[np.array([u[1],-u[0]]),np.array([v[1],-v[0]])];width=1.2;poly=LineString([q,kk,r]).buffer(width/2,cap_style=2,join_style=2);separation=None
  else:
   start=np.array([-68.4,1.6])-n*.45;q=start+d*counts[0]*going;r=q+n*separation;end=r-d*counts[1]*going;directions=[d,-d];normals=[n,n];poly=Polygon([q-n*width/2,r+n*width/2,r+n*width/2+d*width,q-n*width/2+d*width])
  rise=(z1-z0)/sum(counts);index=0;lengths=[float(np.linalg.norm(q-start)),float(np.linalg.norm(end-r))];goings=[L/c for L,c in zip(lengths,counts)]
  for run,(aa,bb,count)in enumerate([(start,q,counts[0]),(r,end,counts[1])]):
   nn=normals[run]
   for i in range(count):
    p0=aa+(bb-aa)*i/count;p1=aa+(bb-aa)*(i+1)/count;index+=1;foot=Polygon([p0-nn*width/2,p0+nn*width/2,p1+nn*width/2,p1-nn*width/2])
    treads.append(dict(flight=flight,run=run,index=index,top=z0+rise*index,bottom0=z0+rise*(index-1)-.18,bottom1=z0+rise*index-.18,going=goings[run],width=width,polygon=foot))
  mid=z0+rise*counts[0];landings.append(dict(flight=flight,top=mid,bottom=mid-.18,polygon=poly))
  routes.append(dict(flight=flight,lowerDatum=z0,upperDatum=z1,counts=counts,riserHeight=rise,width=width,going=min(goings),runGoings=goings,runLengths=lengths,runDirections=[x.tolist()for x in directions],runNormals=[x.tolist()for x in normals],start=start.tolist(),turnArrival=q.tolist(),turnDeparture=r.tolist(),end=end.tolist(),direction=directions[0].tolist(),crossDirection=normals[0].tolist(),landingDepth=width,separation=separation))
 surfaces=treads+landings
 retained=[t for t in old if t['top']<3.4501 or t['top']>11.1001]
 conflicts=[]
 for i,a in enumerate(surfaces):
  if a['polygon'].intersection(lifts).area>1e-7:conflicts.append(dict(kind='fixed_lift',surface=i,area=a['polygon'].intersection(lifts).area))
  for j,b in enumerate(retained):
   area=a['polygon'].intersection(b['polygon']).area
   if area<1e-5:continue
   lo,hi=(a,b)if a['top']<b['top']else(b,a)
   bottom=hi.get('bottom0',hi.get('bottom',hi['top']-.15));gap=bottom-lo['top']
   if gap<2.1:conflicts.append(dict(kind='retained_tread_headroom',surface=i,oldFace=b['face'],newTop=a['top'],oldTop=b['top'],area=area,gap=gap))
  contour=Polygon(next(f for f in prior['floors']if abs(f['datum']-next(r['upperDatum']for r in routes if r['flight']==a['flight']))<.01)['outlineWorld'])
  if a['polygon'].difference(contour).area>1e-7:conflicts.append(dict(kind='outside_slab',surface=i,area=a['polygon'].difference(contour).area))
 for i,a in enumerate(surfaces):
  for j,b in enumerate(surfaces[i+1:],i+1):
   area=a['polygon'].intersection(b['polygon']).area
   if area<1e-5:continue
   lo,hi=(a,b)if a['top']<b['top']else(b,a)
   if abs(a['top']-b['top'])<.00001:continue
   gap=hi.get('bottom0',hi.get('bottom',hi['top']-.15))-lo['top']
   if gap<2.1:conflicts.append(dict(kind='new_stair_headroom',a=i,b=j,area=area,gap=gap))
 floors=[]
 all_surfaces=retained+surfaces
 for datum in [3.45,8.1,11.1]:
  f=next(f for f in prior['floors']if abs(f['datum']-datum)<.01);contour=Polygon(f['outlineWorld'])
  clearance=unary_union([t['polygon']for t in all_surfaces if datum-2.3<t['top']<datum-.001]).buffer(.06,join_style=2)
  arrival=unary_union([t['polygon']for t in all_surfaces if abs(t['top']-datum)<.001])
  floor=shapely.set_precision(contour.difference(lifts.buffer(.03,join_style=2)).difference(clearance).difference(arrival.buffer(.003,join_style=2)),.00001)
  triangles=[]
  for tri in shapely.constrained_delaunay_triangles(floor).geoms:
   p=orient(tri,sign=1);triangles.append(list(p.exterior.coords)[:-1])
  floors.append(dict(datum=datum,triangles=triangles,polygon=mapping(floor),clearance=mapping(clearance),arrivalDistance=arrival.distance(floor),componentCount=len(floor.geoms)if hasattr(floor,'geoms')else 1))
 plan=dict(baselineSha256=SHA,routes=routes,treads=[{**{k:v for k,v in t.items()if k!='polygon'},'polygon':mapping(t['polygon'])}for t in treads],landings=[{**{k:v for k,v in t.items()if k!='polygon'},'polygon':mapping(t['polygon'])}for t in landings],floors=floors,lifts=[mapping(p)for p in cabins],conflicts=conflicts,assumptions=['Two straight runs and full flat U-platforms estimate the missing lower ST03 sequence within the source stair and connected circulation band. Counts, exact widths/angles and local registration remain estimates.','First-to-second4.65m rise is preserved from source041FFLs. Both adjacent connections are coordinated to avoid a new under-2.1m interface beside the repaired flight.'])
 save('plan.json',plan)
 fig,axs=plt.subplots(1,3,figsize=(18,7))
 for ax,datum in zip(axs,[3.45,8.1,11.1]):
  f=next(f for f in prior['floors']if abs(f['datum']-datum)<.01)
  for tri in f['floorTriangles']:ax.fill(*np.array(tri).T,color='#eeeeee',ec='#d3d3d3',lw=.2)
  for t in old:
   if 3.4501<t['top']<11.1001:ax.plot(*np.array(t['polygon'].exterior.coords).T,color='#8a8f96',lw=.7)
  for cabin in cabins:ax.fill(*np.array(cabin.exterior.coords).T,color='#9c2f35',alpha=.65)
  for t in surfaces:ax.fill(*np.array(t['polygon'].exterior.coords).T,color='#16809a'if t['flight']==1 else'#efb159',alpha=.45,ec='#155b6b',lw=.4)
  source=json.loads((ROOT/'result/blender/saw-lower227/source-feasibility.json').read_text())
  for g in source['sourceGroups']:
   for s in g['sections']:ax.plot(*np.array(s['worldEndpoints']).T,color='#7d42aa',lw=1.3)
  ax.plot(*np.array(f['outlineWorld']).T,color='black',lw=1.5);ax.set_xlim(-76,-64);ax.set_ylim(0,12);ax.set_aspect('equal');ax.grid(alpha=.2);ax.set_title(f'Native slab{datum:g}m; purple source stations; grey old treads')
 fig.suptitle('SAW233 source-constrained candidate: blue1-2 / amber2-3; fixed lifts red');fig.tight_layout();fig.savefig(OUT/'candidate-source-native-overlay.png',dpi=140);plt.close(fig)
 print('SAW233_PLAN',len(conflicts),conflicts[:15],[(f['datum'],f['arrivalDistance'],f['componentCount'])for f in floors],flush=True)



COLLECTION='SAW_STRUCTURE173_registered_main_circulation'
PREFIX='SAW233_'

def build():
 import bpy,bmesh
 from mathutils import Vector
 from integrate_exterior_round194 import object_fingerprint,update_scene,set_layer_hidden
 from refine_portsmouth_exterior207 import material_fingerprint
 from build_clm_hongkong_room220 import modifier_payload
 assert hashlib.sha256(BASE.read_bytes()).hexdigest()==SHA
 bpy.ops.wm.open_mainfile(filepath=str(BASE));update_scene()
 assert len(bpy.data.objects)==8502
 original={o.name:object_fingerprint(o)for o in bpy.data.objects}
 members={o.name:sorted(c.name for c in o.users_collection)for o in bpy.data.objects}
 materials={m.name:material_fingerprint(m)for m in bpy.data.materials}
 modifiers={o.name:json.dumps([modifier_payload(m)for m in o.modifiers],sort_keys=True)for o in bpy.data.objects}
 def properties(o):
  def encode(v):
   if hasattr(v,'to_dict'):return {k:encode(x)for k,x in v.to_dict().items()}
   if hasattr(v,'to_list'):return v.to_list()
   if isinstance(v,bpy.types.ID):return [v.bl_rna.identifier,v.name]
   if isinstance(v,(str,int,float,bool))or v is None:return v
   return str(v)
  return json.dumps({k:encode(v)for k,v in o.items()},sort_keys=True)
 props={o.name:properties(o)for o in bpy.data.objects}
 visibility={o.name:o.hide_render for o in bpy.data.objects}
 metadata=json.loads((ROOT/'web/tools/building-metadata.json').read_text());rooms={s['collection']:sorted(o.name for o in bpy.data.collections[s['collection']].all_objects)for s in metadata['spaces']};assert len(rooms)==34
 plan=json.loads((OUT/'plan.json').read_text());assert plan['baselineSha256']==SHA and not plan['conflicts']
 added=[];archived=[];bindings={};retention=[]
 def mesh_object(name,verts,faces,source,uv_records=None):
  me=bpy.data.meshes.new(PREFIX+name);me.from_pydata(verts,[],faces);me.update();src=bpy.data.objects[source]
  for m in src.data.materials:me.materials.append(m)
  if uv_records is None:
   bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free()
   uv=me.uv_layers.new(name='MetricUV')
   for loop in me.loops:
    p=me.vertices[loop.vertex_index].co;uv.data[loop.index].uv=(p.x,p.y)
  else:
   for name0,values in uv_records.items():
    uv=me.uv_layers.new(name=name0)
    for loop,value in zip(uv.data,values):loop.uv=value
  obj=bpy.data.objects.new(PREFIX+name,me);bpy.data.collections[COLLECTION].objects.link(obj)
  obj['destinationCollection']=COLLECTION;obj['evidenceStatus']='Estimated ST03 repair inside historical stair/connecting circulation band, not recovered as-built stair sequence'
  obj['sourceGuideYear']=2014;obj['dimensionStatus']='4.65m first-to-second rise source041; other retained datums, counts, width, angle and landings estimated'
  added.append(obj);bindings[obj.name]=[m.name for m in me.materials];return obj
 def retained(name,keep):
  src=bpy.data.objects[name];selected=[p for p in src.data.polygons if keep(p)]
  if not selected:
   archived.append(name);retention.append(dict(original=name,replacement=None,originalFaces=len(src.data.polygons),retainedFaces=0,reason='All five lower platforms replaced by coordinated original-contour floor surfaces'));return None
  ids=sorted({i for p in selected for i in p.vertices});lookup={v:i for i,v in enumerate(ids)}
  uv={layer.name:[tuple(layer.data[loop].uv)for p in selected for loop in p.loop_indices]for layer in src.data.uv_layers}
  obj=mesh_object('Retained_'+name,[list(src.data.vertices[i].co)for i in ids],[tuple(lookup[i]for i in p.vertices)for p in selected],name,uv);obj.matrix_world=src.matrix_world.copy()
  for a,b in zip(obj.data.polygons,selected):a.material_index=b.material_index
  archived.append(name);retention.append(dict(original=name,replacement=obj.name,originalFaces=len(src.data.polygons),retainedFaces=len(selected),retainedCoordinatesUVMaterialIndicesCopiedExactly=True));return obj
 tread_source='SAW223_Retained_SAW173_registered_main_treads';rail_source='SAW223_Retained_SAW173_main_stair_rails'
 retained(tread_source,lambda p:not 23*6<=p.index<74*6)
 retained('SAW223_Retained_SAW173_flat_anti_slip_nosings',lambda p:not 23*6<=p.index<73*6)
 records=json.loads((ROOT/'result/blender/saw_lower_structure173/audit.json').read_text())['change']['railRecords']
 starts=[r['faceStart']for r in records if r['flight']==1];stop=min(r['faceStart']for r in records if r['flight']==3)
 retained(rail_source,lambda p:not min(starts)<=p.index<stop)
 retained('SAW223_Retained_SAWFLOOR216_coordinated_shared_floor_landings',lambda p:not any(all(z-.181<=bpy.data.objects['SAW223_Retained_SAWFLOOR216_coordinated_shared_floor_landings'].data.vertices[i].co.z<=z+.001 for i in p.vertices)for z in [3.45,8.1,11.1]))
 stair_objects=[]
 def solid(verts,faces,ring,bottom,top):
  off=len(verts);count=len(ring);verts.extend((x,y,z)for z in [bottom,top]for x,y in ring)
  faces.extend([tuple(off+i for i in range(count-1,-1,-1)),tuple(off+count+i for i in range(count))])
  faces.extend((off+i,off+(i+1)%count,off+count+(i+1)%count,off+count+i)for i in range(count))
 for route in plan['routes']:
  vv=[];ff=[];rise=route['riserHeight'];width=route['width'];going=route['going'];d=Vector(route['direction']);n=Vector(route['crossDirection']);mid=route['lowerDatum']+route['counts'][0]*rise
  for run,(a,count,z0)in enumerate([(route['start'],route['counts'][0],route['lowerDatum']),(route['turnDeparture'],route['counts'][1],mid)]):
   vec=Vector(route['runDirections'][run]);n=Vector(route['runNormals'][run]);going=route['runGoings'][run];a=Vector(a);length=count*going;profile=[(0,z0-.18),(length,z0+count*rise-.18),(length,z0+count*rise)]
   for i in range(count-1,-1,-1):
    profile.append((i*going,z0+(i+1)*rise))
    if i>0:profile.append((i*going,z0+i*rise))
   off=len(vv);k=len(profile)
   for side in [-1,1]:
    for distance,z in profile:
     q=a+vec*distance+n*side*width/2;vv.append((q.x,q.y,z))
   ff.extend([tuple(off+i for i in range(k-1,-1,-1)),tuple(off+k+i for i in range(k))]);ff.extend((off+i,off+(i+1)%k,off+k+(i+1)%k,off+k+i)for i in range(k))
  landing=next(t for t in plan['landings']if t['flight']==route['flight']);solid(vv,ff,landing['polygon']['coordinates'][0][:-1],landing['bottom'],landing['top'])
  obj=mesh_object(f'Flight{route["flight"]}_continuous_waists_treads_flat_platform',vv,ff,tread_source);stair_objects.append(obj)
 for f in plan['floors']:
  vv=[];ff=[]
  for tri in f['triangles']:
   off=len(vv);vv.extend((x,y,f['datum'])for x,y in tri);ff.append((off,off+1,off+2))
  src='SAWFLOOR216_registered_floor_'+str(f['datum']);obj=mesh_object('Coordinated_floor_'+str(f['datum']),vv,ff,src);archived.append(src)
 # New supported rails follow both flights. Their posts sit outside the1.4m
 # clear walking strip; flat-platform outer edges have matching continuous rails.
 vv=[];ff=[]
 def tube(a,b,radius=.023):
  a,b=Vector(a),Vector(b);axis=(b-a).normalized();u=axis.cross(Vector((0,0,1)))
  if u.length<.01:u=axis.cross(Vector((1,0,0)))
  u.normalize();v=axis.cross(u);off=len(vv)
  for p in [a,b]:
   for j in range(8):vv.append(tuple(p+radius*(math.cos(j*math.tau/8)*u+math.sin(j*math.tau/8)*v)))
  ff.extend([tuple(off+j for j in range(7,-1,-1)),tuple(off+8+j for j in range(8))]);ff.extend((off+j,off+(j+1)%8,off+8+(j+1)%8,off+8+j)for j in range(8))
 for r in plan['routes']:
  d=Vector(r['direction']);n=Vector(r['crossDirection']);mid=r['lowerDatum']+r['counts'][0]*r['riserHeight']
  for run,(a,count,z0)in enumerate([(r['start'],r['counts'][0],r['lowerDatum']),(r['turnDeparture'],r['counts'][1],mid)]):
   vec=Vector(r['runDirections'][run]);n=Vector(r['runNormals'][run]);run_going=r['runGoings'][run];a=Vector(a)
   for side in [-1,1]:
    points=[]
    for j in range(count+1):
     distance=max(.05,min(count*run_going-.05,j*run_going));q=a+vec*distance+n*side*(r['width']/2+.045);z=z0+distance/run_going*r['riserHeight'];points.append((q.x,q.y,z+1.02))
     if(j%3==0 or j==count):tube((q.x,q.y,z),(q.x,q.y,z+1.02),.018)
    for x,y in zip(points,points[1:]):tube(x,y)
  landing=next(t for t in plan['landings']if t['flight']==r['flight']);ring=[Vector(p)for p in landing['polygon']['coordinates'][0][:-1]]
  signed=sum(a.x*b.y-b.x*a.y for a,b in zip(ring,ring[1:]+ring[:1]));orientation=1 if signed>0 else -1
  from mathutils.geometry import intersect_point_line
  q=Vector(r['turnArrival']);ss=Vector(r['turnDeparture'])
  for aa,bb in zip(ring,ring[1:]+ring[:1]):
   center=(aa+bb)/2
   if r['flight']<=2 and abs((aa-q).dot(d))<.005 and abs((bb-q).dot(d))<.005:continue
   if min((center-q).length,(center-ss).length)<.005:continue
   edge=(bb-aa).normalized();outside=Vector((edge.y,-edge.x))*orientation*.045;x=aa+outside;y=bb+outside
   tube((*x,mid+1.02),(*y,mid+1.02))
   for point in [x,y]:tube((*point,mid),(*point,mid+1.02),.018)
 rails=mesh_object('Supported_stair_platform_handrails',vv,ff,rail_source)
 # Retain visible aperture guard stubs only where the existing lower platforms
 # remain. The rebuilt horizontal slabs have no detached decorative obstructions.
 for name in archived:bpy.data.objects[name].hide_render=True;set_layer_hidden(bpy.data.objects[name],True)
 update_scene()
 fingerprints={o.name:object_fingerprint(o)for o in added}
 solids=[]
 for obj in stair_objects:
  bm=bmesh.new();bm.from_mesh(obj.data);manifold=all(e.is_manifold for e in bm.edges);vol=bm.calc_volume(signed=True);assert manifold and vol>0,(obj.name,manifold,vol);bm.free();solids.append(dict(object=obj.name,closedManifoldComponents=True,positiveVolumeM3=vol))
 component=OUT/'component.blend';bpy.data.libraries.write(str(component),set(added),fake_user=True,compress=True)
 save('component-record.json',dict(addedObjects=list(fingerprints),archivedObjects=archived,addedFingerprints=fingerprints,replacementMaterialBindings=bindings,retention=retention,solids=solids))
 # Independently reload accepted native and append the saved component only.
 bpy.ops.wm.open_mainfile(filepath=str(BASE));update_scene()
 with bpy.data.libraries.load(str(component),link=False)as(available,loaded):loaded.objects=list(fingerprints)
 for obj in loaded.objects:
  for i,name in enumerate(bindings[obj.name]):obj.data.materials[i]=bpy.data.materials[name]
  bpy.data.collections[COLLECTION].objects.link(obj)
 for name in archived:bpy.data.objects[name].hide_render=True;set_layer_hidden(bpy.data.objects[name],True)
 update_scene()
 assert all(object_fingerprint(bpy.data.objects[n])==v for n,v in original.items())
 assert all(object_fingerprint(bpy.data.objects[n])==v for n,v in fingerprints.items())
 assert all(material_fingerprint(bpy.data.materials[n])==v for n,v in materials.items())
 assert all(sorted(c.name for c in bpy.data.objects[n].users_collection)==v for n,v in members.items())
 assert all(json.dumps([modifier_payload(m)for m in bpy.data.objects[n].modifiers],sort_keys=True)==v for n,v in modifiers.items())
 assert all(properties(bpy.data.objects[n])==v for n,v in props.items())
 assert all(sorted(o.name for o in bpy.data.collections[n].all_objects)==v for n,v in rooms.items())
 assert all(bpy.data.objects[n].hide_render==v for n,v in visibility.items()if n not in archived)
 preservation=dict(savedComponentIndependentlyReopened=True,originalObjectsVerified=len(original),originalMaterialsVerified=len(materials),allOriginalGeometryUVTransformsMaterialsModifiersPropertiesOwnersUnchanged=True,protectedSpaces=len(rooms),protectedSpaceObjects=len({n for values in rooms.values()for n in values}),all34RoomMembershipsUnchanged=True,listedVisibilityArchivesOnly=True,upperST04Unchanged=True,baselineBytesUnchanged=hashlib.sha256(BASE.read_bytes()).hexdigest()==SHA)
 save('native-preservation.json',preservation)
 rows=[]
 for object_name in fingerprints:
  obj=bpy.data.objects[object_name];obj.data.calc_loop_triangles();rows.append(dict(name=obj.name,vertices=[list(obj.matrix_world@v.co)for v in obj.data.vertices],faces=[list(p.vertices)for p in obj.data.polygons],triangles=[list(t.vertices)for t in obj.data.loop_triangles]))
 save('reopened-surfaces.json',dict(componentSha256=hashlib.sha256(component.read_bytes()).hexdigest(),objects=rows))
 # The existing registered structure collection is already owned by the one
 # public assembly. Verify the same actual objects serve campus and interior.
 owner_scenes={scene.name for scene in bpy.data.scenes if any(o.name in scene.objects for o in loaded.objects)}
 save('display-ownership.json',dict(destinationCollection=COLLECTION,assembly='SAW_PUBLIC_INTERIOR_study',scenes=sorted(owner_scenes),allNewObjectsInCampus=all(o.name in bpy.data.scenes['00_CAMPUS_COMPLETE'].objects for o in loaded.objects),policy='Same current public assembly is exported for overview/exterior/interior; no detached study collection or duplicate current stair.'))
 render_context(archived,list(fingerprints))
 print('SAW233_SAVED_REOPENED',len(added),len(archived),preservation,flush=True)

def render_context(archived,added):
 import bpy
 from mathutils import Vector
 scene=bpy.data.scenes.new('SAW233_private_context_proof');bpy.context.window.scene=scene
 names=[r['name']for r in json.loads((OUT/'baseline-surfaces.json').read_text())['objects']if r['name'].startswith(('SAW223_','SAWFLOOR216_','SAW_SAW_rear_2_'))]+added
 for name in names:
  o=bpy.data.objects[name]
  if o.name not in scene.objects:scene.collection.objects.link(o)
 cd=bpy.data.cameras.new('SAW233_private_camera');cam=bpy.data.objects.new(cd.name,cd);scene.collection.objects.link(cam);scene.camera=cam;cd.type='ORTHO';cd.ortho_scale=21
 focus=Vector((-69.8,5.2,6.1));cam.location=Vector((-90,-8,17));cam.rotation_euler=(focus-cam.location).to_track_quat('-Z','Y').to_euler()
 scene.render.engine='BLENDER_WORKBENCH';scene.display.shading.light='STUDIO';scene.display.shading.color_type='MATERIAL';scene.display.shading.show_cavity=True;scene.display.shading.show_shadows=True;scene.render.resolution_x=1200;scene.render.resolution_y=900;scene.render.resolution_percentage=100
 for mode in ['before','after']:
  for name in names:
   obj=bpy.data.objects[name]
   obj.hide_render=(name in added)if mode=='before'else(name in archived)
   if 'registered_floor_11.1'in name or 'Coordinated_floor_11.1'in name or 'rear_2_pierced_wall'in name:obj.hide_render=True
  scene.render.filepath=str(OUT/(mode+'-context-section.png'));bpy.ops.render.render(write_still=True)
 for name in archived:bpy.data.objects[name].hide_render=True
 for name in added:bpy.data.objects[name].hide_render=False
 bpy.data.scenes.remove(scene);bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE']



def prove():
 import numpy as np
 from shapely.geometry import Polygon,shape
 from shapely.ops import unary_union
 baseline=json.loads((OUT/'baseline-surfaces.json').read_text());record=json.loads((OUT/'component-record.json').read_text());saved=json.loads((OUT/'reopened-surfaces.json').read_text());plan=json.loads((OUT/'plan.json').read_text())
 new={r['name']:r for r in saved['objects']};all_rows=[r for r in baseline['objects']if r['name']not in record['archivedObjects']]+list(new.values())
 def surfaces(row):
  v=np.array(row['vertices']);result=[]
  for i,f in enumerate(row['faces']):
   q=v[f]
   if len(q)>2 and np.ptp(q[:,2])<1e-5 and np.cross(q[1]-q[0],q[2]-q[0])[2]>0:
    p=Polygon(q[:,:2])
    if p.area>1e-8:result.append(dict(object=row['name'],face=i,top=float(q[0,2]),polygon=p))
  return result
 actual=[t for row in new.values()if 'continuous_waists'in row['name']for t in surfaces(row)]
 expected=plan['treads']+plan['landings'];matches=[]
 for ex in expected:
  p=shape(ex['polygon']);found=[t for t in actual if abs(t['top']-ex['top'])<1e-4 and t['polygon'].symmetric_difference(p).area<.00004]
  assert len(found)==1,(ex,[(t['top'],t['polygon'].area)for t in actual]);t=found[0];t['kind']='tread'if 'run'in ex else 'platform';t['run']=ex.get('run');matches.append(t)
 lift=unary_union([shape(p)for p in plan['lifts']]);after_lift=[];before_lift=[]
 for row in all_rows:
  if not (row['name'].endswith('registered_main_treads')or'continuous_waists'in row['name']):continue
  for t in surfaces(row):
   area=t['polygon'].intersection(lift).area
   if area>1e-5:after_lift.append(dict(object=row['name'],top=t['top'],areaM2=area))
 for row in baseline['objects']:
  if not row['name'].endswith('registered_main_treads'):continue
  for t in surfaces(row):
   area=t['polygon'].intersection(lift).area
   if area>1e-5:before_lift.append(dict(object=row['name'],top=t['top'],areaM2=area))
 # Clip every potentially obstructing actual saved triangle against each full
 # walking-width2.1m vertical prism. This checks the whole surface, not one ray.
 # Positive-area clipping detects both sloping soffits and vertical walls.
 def clip(poly,normal,offset):
  output=[]
  for a,b in zip(poly,poly[1:]+poly[:1]):
   da=float(np.dot(normal,a)-offset);db=float(np.dot(normal,b)-offset)
   if da>=-1e-8:output.append(a)
   if (da>=0)!=(db>=0):output.append(a+(b-a)*(da/(da-db)))
  return output
 def area3(poly):
  if len(poly)<3:return 0
  return sum(np.linalg.norm(np.cross(poly[i]-poly[0],poly[i+1]-poly[0]))/2 for i in range(1,len(poly)-1))
 triangles=[]
 for row in all_rows:
  v=np.array(row['vertices']);tt=v[np.array(row['triangles'])];triangles.append((row['name'],tt,tt.min(1),tt.max(1)))
 conflicts=[];tested=0
 for cell,t in enumerate(matches):
  poly=t['polygon'].buffer(-.0001,join_style=2);ring=np.array(poly.exterior.coords[:-1]);signed=sum(a[0]*b[1]-b[0]*a[1]for a,b in zip(ring,np.roll(ring,-1,axis=0)))
  if signed<0:ring=ring[::-1]
  planes=[]
  for a,b in zip(ring,np.roll(ring,-1,axis=0)):
   edge=b-a;normal=np.array([-edge[1],edge[0],0.]);planes.append((normal,float(np.dot(normal[:2],a))))
  low=t['top']+.005;high=t['top']+2.1;planes.extend([(np.array([0.,0.,1.]),low),(np.array([0.,0.,-1.]),-high)])
  bound=np.array(poly.bounds);minx,miny,maxx,maxy=bound
  for name,tt,tmin,tmax in triangles:
   mask=(tmax[:,0]>minx+1e-6)&(tmin[:,0]<maxx-1e-6)&(tmax[:,1]>miny+1e-6)&(tmin[:,1]<maxy-1e-6)&(tmax[:,2]>low+1e-6)&(tmin[:,2]<high-1e-6)
   for idx in np.where(mask)[0]:
    tested+=1;q=list(tt[idx])
    for normal,offset in planes:
     q=clip(q,normal,offset)
     if len(q)<3:break
    area=area3(q)
    if area>1e-7:conflicts.append(dict(cell=cell,walkObject=t['object'],walkFace=t['face'],walkTop=t['top'],obstacle=name,triangle=int(idx),clippedAreaM2=float(area),heightRange=[float(min(x[2]for x in q)-t['top']),float(max(x[2]for x in q)-t['top'])]))
 # Saved full-width ascent edges and landing joins must meet the intended rise
 # and land at an actual connected floor, with only inherited3mm floor seams.
 routes=[]
 for r in plan['routes']:
  seq=sorted([t for t in matches if t['object'].startswith(f'SAW233_Flight{r["flight"]}_')],key=lambda t:t['top'])
  tread=[t for t in seq if t['kind']=='tread']
  assert len(tread)==sum(r['counts'])
  adjacency=[]
  for a,b in zip(tread,tread[1:]):
   same_run=abs(tread.index(a)+1-r['counts'][0])>.1
   if same_run:adjacency.append(a['polygon'].distance(b['polygon']))
  floor0=unary_union([t['polygon']for row in new.values()if row['name'].endswith(str(r['lowerDatum']))for t in surfaces(row)])
  floor1=unary_union([t['polygon']for row in new.values()if row['name'].endswith(str(r['upperDatum']))for t in surfaces(row)])
  landing=next(t for t in seq if t['polygon'].area>1)
  first=tread[0];last=tread[-1];last_low=tread[r['counts'][0]-1];first_high=tread[r['counts'][0]]
  routes.append(dict(flight=r['flight'],savedTreads=len(tread),actualRise=last['top']-r['lowerDatum'],maximumRiser=float(max(np.diff([r['lowerDatum']]+[t['top']for t in tread]))),minimumWidth=r['width'],actualRunGoings=r['runGoings'],maximumInRunGap=max(adjacency),lowerSupportDistance=first['polygon'].distance(floor0),upperArrivalDistance=last['polygon'].distance(floor1),lowerRunToPlatformDistance=last_low['polygon'].distance(landing['polygon']),upperRunToPlatformDistance=first_high['polygon'].distance(landing['polygon']),flatPlatformArea=landing['polygon'].area))
 proof=dict(baselineSha256=SHA,componentSha256=saved['componentSha256'],savedActualMeshVerified=True,fullWidthHeadroomHeight=2.1,headroomStartOffset=.005,matchedSavedWalkingSurfaces=len(matches),broadPhaseTrianglePairsTested=tested,actualTriangleHeadroomConflicts=conflicts,conflictCount=len(conflicts),beforeLiftConflicts=before_lift,afterLiftConflicts=after_lift,beforeLiftConflictCount=len(before_lift),remainingLiftConflictCount=len(after_lift),routes=routes,method='Every potentially crossing saved triangle is clipped by every full-width tread/platform prism. No single centre-ray substitution; all saved guard/nosing meshes included in the same full-width clearance test.')
 save('saved-route-triangle-proof.json',proof)
 print('SAW233_ACTUAL_PROOF',len(before_lift),len(after_lift),len(conflicts),conflicts[:15],routes,flush=True)
 return proof



def source_overlay():
 import numpy as np
 from PIL import Image,ImageDraw
 from shapely.geometry import Polygon,shape
 from shapely.ops import unary_union
 plan=json.loads((OUT/'plan.json').read_text());baseline=json.loads((OUT/'baseline-surfaces.json').read_text());registration=json.loads((ROOT/'result/blender/saw-floors216/registration.json').read_text());prior=json.loads((ROOT/'result/blender/saw-floors216/surface-plan.json').read_text());source=json.loads((ROOT/'result/blender/saw-lower227/source-feasibility.json').read_text())
 a,b,c=np.array([[-65.223399,-15.905616],[-84.252182,28.425],[-55.301,36.609104]]);matrix=np.column_stack(((b-a)/1200,(c-b)/785));factor=1501/595.276
 def source_points(points,page):
  ground=(np.array(points)-a)@np.linalg.inv(matrix).T+[145,400];r=registration[str(page)];return(ground-np.array(r['offset'])*factor)@np.linalg.inv(r['matrix'])
 zones={28:[(655,479),(779,426),(878,478),(827,622),(805,557),(681,584)],27:[(655,474),(823,447),(976,514),(951,650),(823,650),(805,548),(680,576)]}
 colours={1:'#007f9c',2:'#cf7700',3:'#276f54',4:'#9147a8'};sheet=Image.new('RGB',(1700,1040),'white');dd=ImageDraw.Draw(sheet);dd.text((15,9),'SAW233 source plans and saved-mesh candidate. Historical2014; geometry and step schedules estimated.',fill='black')
 for index,page in enumerate([31,30]):
  level=32-page;im=Image.open(ROOT/f'data/previews/saw_occupants_guide_2014_p{page}.png').convert('RGB');draw=ImageDraw.Draw(im)
  for row in baseline['objects']:
   if not row['name'].endswith('registered_main_treads'):continue
   vv=np.array(row['vertices'])
   for face in row['faces']:
    q=vv[face]
    if np.ptp(q[:,2])<1e-5 and 3.4501<q[0,2]<=18.001 and np.cross(q[1]-q[0],q[2]-q[0])[2]>0:
     pts=source_points(q[:,:2],page);draw.line([tuple(p)for p in pts]+[tuple(pts[0])],fill='#9b9fa5',width=1)
  for t in plan['treads']+plan['landings']:
   if page>=30 and t['flight']>2:continue
   if page<=28 and t['flight']<3:continue
   pts=source_points(shape(t['polygon']).exterior.coords,page);draw.line([tuple(p)for p in pts],fill=colours[t['flight']],width=2)
  for poly in plan['lifts']:
   pts=source_points(shape(poly).exterior.coords,page);draw.line([tuple(p)for p in pts],fill='#b22c31',width=3)
  floor=next(f for f in prior['floors']if f['level']==level);pts=source_points(floor['outlineWorld'],page);draw.line([tuple(p)for p in pts],fill='#111111',width=3)
  if page in zones:draw.line(zones[page]+[zones[page][0]],fill='#d32464',width=2)
  else:
   for group in source['sourceGroups']:
    for line in group['sections']:
     pts=source_points(line['worldEndpoints'],page);draw.line([tuple(p)for p in pts],fill='#d32464',width=2)
  sheet.paste(im.crop((480,385,1005,690)).resize((1680,470)),(10,45+index*485));dd.text((20,28+index*485),f'Guide page{page}, level{level}: blue1-2; ochre2-3; green3-4; violet4-5; magenta source band/stations; grey old; red lifts; black slab edge',fill='black')
 sheet.save(DATA/'source-plan-native-candidate-overlay.png')
 upper=unary_union([shape(t['polygon'])for t in plan['treads']+plan['landings']if t['flight']>=3]);upper_checks=[]
 for page,zone in ([] if len(plan['routes'])==2 else zones.items()):
  polys=[Polygon(source_points(shape(t['polygon']).exterior.coords,page))for t in plan['treads']+plan['landings']if t['flight']>=3];candidate=unary_union(polys);outside=candidate.difference(Polygon(zone)).area;assert outside<.0001
  upper_checks.append(dict(page=page,sourceBandPixels=zone,candidateOutsideBandPixelArea=outside,method='Visual white ST03 and immediately connected public-strip trace; excludes gym/careers colour zones and source lift enclosure. Polygon rounded to raster pixels, not a measured wall survey.'))
 correspondence=dict(upperSourceBandChecks=upper_checks,upperSourceAnchors=None if len(plan['routes'])==2 else dict(referencePage=27,start=[830,565],turn=[790,475],arrival=[695,520],firstRunStartTrimMetres=.8,flatTurnLegsMetres=.7,construction='Two independently directed straight runs with one constant-height L-shaped platform; exact traces and widths estimated.'),sectionFFL=dict(path='data/collections/exteriors/images/saw_archdaily_041.jpg',ground=19.55,first=23.,second=27.65,third=30.65,fourth=33.65,fifth=37.55,sixth=41.45),publishedRiseDifferences=[3.45,4.65,3.,3.,3.9,3.9],interpretation='Accepted lower pair follows published visible diagonal fragments across clipped plan breaks. Upper joint candidates are rejected and recorded separately. Flight divisions, counts, exact positions and platforms are estimates; no as-built stair schedule or2026 state is claimed.',newOfficialLookups=0)
 save('source-correspondence.json',correspondence);return correspondence

def finalize(proof):
 from shapely.geometry import shape,Point,Polygon,box
 from shapely.ops import unary_union,nearest_points
 import numpy as np
 assert proof['conflictCount']==0 and proof['beforeLiftConflictCount']==32 and proof['remainingLiftConflictCount']==11
 plan=json.loads((OUT/'plan.json').read_text());record=json.loads((OUT/'component-record.json').read_text());preservation=json.loads((OUT/'native-preservation.json').read_text());ownership=json.loads((OUT/'display-ownership.json').read_text())
 # Width of the horizontal connecting floor is checked on an eroded real
 # saved support union. End anchors are0.7m beyond each stair front edge.
 rows={r['name']:r for r in json.loads((OUT/'reopened-surfaces.json').read_text())['objects']};links=[]
 baseline=json.loads((OUT/'baseline-surfaces.json').read_text());all_rows=[r for r in baseline['objects']if r['name']not in record['archivedObjects']]+list(rows.values())
 def tread_centres(top):
  row=next(r for r in baseline['objects']if r['name'].endswith('registered_main_treads'));v=np.array(row['vertices']);result=[]
  for face in row['faces']:
   q=v[face]
   if len(q)>2 and np.ptp(q[:,2])<1e-5 and abs(q[0,2]-top)<.0001 and np.cross(q[1]-q[0],q[2]-q[0])[2]>0:result.append(q[:,:2].mean(0))
  assert len(result)==1;return result[0]
 def clip_height(poly,z,above):
  output=[]
  for a,b in zip(poly,poly[1:]+poly[:1]):
   da=(a[2]-z)*(1 if above else -1);db=(b[2]-z)*(1 if above else -1)
   if da>=0:output.append(a)
   if(da>=0)!=(db>=0):output.append(a+(b-a)*da/(da-db))
  return output

 for z in [3.45,8.1,11.1]:
  row=rows['SAW233_Coordinated_floor_'+str(z)];vv=np.array(row['vertices']);floor=unary_union([Polygon(vv[f,:2])for f in row['faces']])
  blockers=[]
  for obstacle in all_rows:
   v=np.array(obstacle['vertices']);tris=v[np.array(obstacle['triangles'])];lo=tris.min(1);hi=tris.max(1)
   mask=(hi[:,2]>z+.01)&(lo[:,2]<z+2.1)&(hi[:,0]>-76)&(lo[:,0]<-59)&(hi[:,1]>-2)&(lo[:,1]<18)
   for triangle in tris[mask]:
    q=clip_height(list(triangle),z+.01,True)
    if len(q)>2:q=clip_height(q,z+2.1,False)
    if len(q)>2:
     polygon=Polygon(np.array(q)[:,:2])
     if polygon.is_valid and polygon.area>1e-8:blockers.append(polygon)
  coplanar=[]
  for support_row in all_rows:
   sv=np.array(support_row['vertices'])
   for face in support_row['faces']:
    qq=sv[face]
    if len(qq)>2 and np.ptp(qq[:,2])<1e-5 and abs(qq[0,2]-z)<.0001 and np.cross(qq[1]-qq[0],qq[2]-qq[0])[2]>0:
     pp=Polygon(qq[:,:2])
     if pp.area>1e-9:coplanar.append(pp)
  floor=unary_union([floor]+coplanar)
  clear=floor.buffer(.005,join_style=2).difference(unary_union(blockers)).intersection(box(-75.9,-1.5,-59.5,17.5))
  support=clear.buffer(-.55,join_style=2)
  regions=list(support.geoms)if hasattr(support,'geoms')else[support]
  incoming=next((r for r in plan['routes']if abs(r['upperDatum']-z)<.001),None);outgoing=next((r for r in plan['routes']if abs(r['lowerDatum']-z)<.001),None);anchors=[]
  if incoming:anchors.append(np.array(incoming['end'])+np.array(incoming['runDirections'][1])*(.5 if incoming['flight']>=3 else .7))
  if outgoing:anchors.append(np.array(outgoing['start'])-np.array(outgoing['runDirections'][0])*.7)
  if z==3.45:
   current=tread_centres(3.45);previous=tread_centres(3.3);direction=current-previous;direction/=np.linalg.norm(direction);anchors.append(current+direction*.8)
  if z==11.1:
   current=tread_centres(11.25);following=tread_centres(11.4);direction=following-current;direction/=np.linalg.norm(direction);anchors.append(current-direction*.8)
  if z==18.:
   spiral=json.loads((ROOT/'result/blender/saw-circulation223/spiral-plan.json').read_text());first=Polygon(spiral['treads'][0]['ring']);second=Polygon(spiral['treads'][1]['ring']);direction=np.array(second.centroid.coords[0])-np.array(first.centroid.coords[0]);direction/=np.linalg.norm(direction);front=(np.array(spiral['treads'][0]['ring'][0])+np.array(spiral['treads'][0]['ring'][-1]))/2;anchors.append(front-direction*.7)
  containing=[[i for i,p in enumerate(regions)if p.covers(Point(a))]for a in anchors]
  links.append(dict(datum=z,minimumCheckedCorridorWidth=1.1,fullHeightTriangleProjectionClearance=2.1,obstacleProjectedTriangleCount=len(blockers),anchorPoints=[a.tolist()for a in anchors],erodedComponentContainingAnchors=containing,sameConnectedClearWidthRegion=bool(set(containing[0]).intersection(*[set(v)for v in containing[1:]]))))
 save('saved-horizontal-floor-links.json',links)
 assert all(l['sameConnectedClearWidthRegion']for l in links),links
 correspondence=source_overlay();refs=json.loads((ROOT/'data/collections/saw-circulation223/sources.json').read_text());p=ROOT/'data/collections/exteriors/images/saw_archdaily_041.jpg';refs.append(dict(path=str(p.relative_to(ROOT)),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),role='Design sectionFFLs; first-to-second4.65m rise',current2026ConditionEstablished=False));(DATA/'sources.json').write_text(json.dumps(refs,indent=2)+'\n')
 save('audit.json',dict(version=233,status='candidate_verified_for_integration',interiorSections=VIEWER_SECTIONS,jointUpperAttempt=dict(status='rejected',diagnostic='joint-upper-rejected/summary.json'),baselinePath=str(BASE.relative_to(ROOT)),baselineSha256=SHA,componentPath=str((OUT/'component.blend').relative_to(ROOT)),componentSha256=hashlib.sha256((OUT/'component.blend').read_bytes()).hexdigest(),addedObjects=record['addedObjects'],archivedObjects=record['archivedObjects'],changedObjects=[],addedFingerprints=record['addedFingerprints'],replacementMaterialBindings=record['replacementMaterialBindings'],destinationCollection=COLLECTION,targetCollection=COLLECTION,interiorCollection='SAW_PUBLIC_INTERIOR_study',replacesInteriorCollection=None,publicObjects=record['addedObjects'],displayOwnership=ownership,verification=preservation,scope='Source-constrained estimated ST03 first-to-second and second-to-third continuous folded connections, two flat platforms, supported rails and three coordinated slab openings. Fixed lifts and accepted fifth-to-sixth ST04 preserved.',sourceRefs=refs,sourceCorrespondence=correspondence,routeProof='saved-route-triangle-proof.json',horizontalSupportProof='saved-horizontal-floor-links.json',previews=['before-context-section.png','after-context-section.png','candidate-source-native-overlay.png','data/collections/saw-circulation233/source-plan-native-candidate-overlay.png'],conflicts=dict(beforeLowerLiftConflicts=32,afterLowerLiftConflicts=11,eliminated=21,remainingFlight='4-to-5',newRoutesFullWidth2Point1MetreActualTriangleHeadroomConflicts=0),limitations=['Historical2014 guide/design section do not establish2026 current condition.','Straight-run directions,31/20counts,1.4m widths,0.31m goings, platform shapes and guard details are estimated and visibly deviate from undocumented original winders.','New candidate stays in historicalST03and its connecting public circulation band, but is not a recovered exact construction layout.','The retained4-to-5connection still has11fixed-cabin conflicts; its joint3-to-5attempt was rejected by the historical fourth-floor public corridor constraint.','Floor surfaces retain inherited thin/slab-study conventions. No compliance or structural engineering certification.','Headroom proof uses every full tread/platform width, with0.1mm XY boundary tolerance to discard shared riser-edge contacts; tests every actual saved obstacle triangle including handrails and nosings.']))
 print('SAW233_FINAL_AUDIT_READY',len(record['addedObjects']),len(record['archivedObjects']),links,flush=True)



VIEWER_SECTIONS=[dict(id='stair-1-2',label='ST03 first-to-second estimated repair',minHeight=3.25,maxHeight=9.2,view=dict(position=[-64.8,6.2,-7.5],target=[-70.0,5.9,-3.9],fov=75)),dict(id='stair-2-3',label='ST03 second-to-third estimated repair',minHeight=7.9,maxHeight=12.2,view=dict(position=[-64.8,9.7,-6.8],target=[-69.5,9.6,-3.2],fov=75))]

def render_saved_views():
 import bpy,bmesh
 from mathutils import Vector
 bpy.ops.wm.read_factory_settings(use_empty=True)
 scene=bpy.context.scene;scene.render.engine='BLENDER_WORKBENCH';scene.display.shading.light='STUDIO';scene.display.shading.color_type='MATERIAL';scene.display.shading.show_cavity=True;scene.display.shading.show_shadows=True;scene.display.shading.background_type='WORLD'
 world=bpy.data.worlds.new('SAW233_private_white_background');world.color=(1,1,1);scene.world=world
 scene.render.resolution_x=1200;scene.render.resolution_y=900;scene.render.resolution_percentage=100
 cd=bpy.data.cameras.new('SAW233_private_view_camera');camera=bpy.data.objects.new(cd.name,cd);scene.collection.objects.link(camera);scene.camera=camera
 materials={}
 for name,color in [('stair',(.55,.58,.57,1)),('floor',(.82,.83,.82,1)),('rail',(.045,.05,.052,1)),('shell',(.75,.76,.73,1))]:
  mat=bpy.data.materials.new('SAW233_private_'+name);mat.diffuse_color=color;materials[name]=mat
 baseline=json.loads((OUT/'baseline-surfaces.json').read_text());record=json.loads((OUT/'component-record.json').read_text());saved=json.loads((OUT/'reopened-surfaces.json').read_text());rows=[r for r in baseline['objects']if r['name']not in record['archivedObjects']]+saved['objects']
 context_view=dict(position=[-88,24,8],target=[-69.8,6.1,-5.2],fov=55)
 contexts=[dict(id=mode+'-context-section',mode=mode,minHeight=0,maxHeight=12.2,view=context_view)for mode in ['before','after']]
 for section in VIEWER_SECTIONS+contexts:
  created=[]
  render_rows=baseline['objects']if section.get('mode')=='before'else rows
  for row in render_rows:
   if section.get('mode')and('rear_2_pierced_wall'in row['name']or row['name']=='SAW233_Coordinated_floor_11.1'):continue
   if any(word in row['name']for word in ['glazing','seal','bead','sill','flashing','mullions','transoms','canopy','shadow','reveal']):continue
   me=bpy.data.meshes.new('SAW233_private_'+row['name']);me.from_pydata(row['vertices'],[],row['faces']);me.update();bm=bmesh.new();bm.from_mesh(me)
   for height,normal in [(section['minHeight'],(0,0,1)),(section['maxHeight'],(0,0,-1))]:
    bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=.00001,plane_co=(0,0,height),plane_no=normal,clear_inner=True,clear_outer=False)
   bm.to_mesh(me);bm.free()
   if not len(me.polygons):bpy.data.meshes.remove(me);continue
   obj=bpy.data.objects.new(me.name,me);scene.collection.objects.link(obj);created.append(obj)
   name=row['name'];kind='rail'if any(v in name for v in ['rail','nosings'])else 'floor'if any(v in name for v in ['floor','landings'])else 'stair'if any(v in name for v in ['treads','waists'])else 'shell';me.materials.append(materials[kind])
  view=section['view'];p=view['position'];t=view['target'];camera.location=Vector((p[0],-p[2],p[1]));target=Vector((t[0],-t[2],t[1]));camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler();cd.type='ORTHO'if section.get('mode')else 'PERSP';cd.ortho_scale=25;cd.angle=math.radians(view['fov']);suffix='.png'if section.get('mode')else '-saved-view.png';scene.render.filepath=str(OUT/(section['id']+suffix));bpy.ops.render.render(write_still=True)
  for obj in created:
   me=obj.data;bpy.data.objects.remove(obj,do_unlink=True);bpy.data.meshes.remove(me)
 save('viewer-sections.json',VIEWER_SECTIONS)
 audit=json.loads((OUT/'audit.json').read_text());audit['interiorSections']=VIEWER_SECTIONS;audit['previews']=list(dict.fromkeys(audit['previews']+['stair-1-2-saved-view.png','stair-2-3-saved-view.png']));audit['privateRender']='Neutral diagnostic materials on saved actual mesh copies, z-clipped at the recommended viewer ranges. No source photograph used as texture.';save('audit.json',audit)
 print('SAW233_NEAR_VIEWS_RENDERED',flush=True)





def verify_frozen_component():
 import bpy,bmesh
 from integrate_exterior_round194 import object_fingerprint
 bpy.ops.wm.read_factory_settings(use_empty=True);record=json.loads((OUT/'component-record.json').read_text());names=record['addedObjects'];component=OUT/'component.blend';audit=json.loads((OUT/'audit.json').read_text());assert hashlib.sha256(component.read_bytes()).hexdigest()==audit['componentSha256']
 with bpy.data.libraries.load(str(component),link=False)as(source,target):target.objects=list(names)
 assert all(object_fingerprint(bpy.data.objects[n])==value for n,value in record['addedFingerprints'].items())
 rows=[];solids=[]
 for name in names:
  obj=bpy.data.objects[name];obj.data.calc_loop_triangles();rows.append(dict(name=name,vertices=[list(obj.matrix_world@v.co)for v in obj.data.vertices],faces=[list(p.vertices)for p in obj.data.polygons],triangles=[list(t.vertices)for t in obj.data.loop_triangles]))
  if 'continuous_waists'in name:
   bm=bmesh.new();bm.from_mesh(obj.data);volume=bm.calc_volume(signed=True);manifold=all(edge.is_manifold for edge in bm.edges);bm.free();assert manifold and volume>0;solids.append(dict(object=name,manifold=True,positiveVolumeM3=volume))
 save('reopened-surfaces.json',dict(componentSha256=audit['componentSha256'],objects=rows));record['solids']=solids;save('component-record.json',record);verification=json.loads((OUT/'native-preservation.json').read_text());verification['finalFrozenComponentReopened']=dict(objects=len(names),allAddedFingerprintsMatched=True,componentSha256=audit['componentSha256'],closedStairSolids=solids);save('native-preservation.json',verification);assert hashlib.sha256(BASE.read_bytes()).hexdigest()==SHA
 print('SAW233_FROZEN_TWO_FLIGHT_COMPONENT_REOPENED',len(names),audit['componentSha256'],flush=True)

if __name__=='__main__':
 try:import bpy
 except ImportError:bpy=None
 if bpy:
  if (OUT/'plan.json').exists():build()
  else:capture()
 elif (OUT/'reopened-surfaces.json').exists():
  proof=prove()
  if not proof['conflictCount']:finalize(proof)
 else:prepare()
