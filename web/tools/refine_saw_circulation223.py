"""Source-led SAW fifth-to-sixth spiral connector and main stair review.

Fixed configuration for Blender Text Editor; complete222 native stays read-only.
Historic source registration and all dimensions retain their stated uncertainty.
"""
from pathlib import Path
import hashlib,json,math,sys
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'result/blender/saw-circulation223'
DATA=ROOT/'data/collections/saw-circulation223'
BASE=ROOT/'result/blender/LSE_campus_detailed_v222.blend'
SHA='0d31c829778d88d643d9b4001f28116730862e8703d81cb6ad0429f8113fb50b'
ANCHORS=np.array([[-65.223399,-15.905616],[-84.252182,28.425],[-55.301,36.609104]])
sys.path.insert(0,str(ROOT/'web/tools'))
def save(name,value):
 OUT.mkdir(parents=True,exist_ok=True);(OUT/name).write_text(json.dumps(value,indent=2)+'\n')
def world(points):
 p=np.array(points);a,b,c=ANCHORS
 return a+(p[:,0:1]-145)/1200*(b-a)+(p[:,1:2]-400)/785*(c-b)
def prepare():
 import pdfplumber
 from PIL import Image,ImageDraw
 registration=json.loads((ROOT/'result/blender/saw-floors216/registration.json').read_text())
 records=[]
 with pdfplumber.open(ROOT/'data/documents/saw_occupants_guide_2014.pdf')as pdf:
  for number in [27,26]:
   page=pdf.pages[number-1];factor=1501/page.width;r=registration[str(number)];lines=[]
   for index,line in enumerate(page.lines):
    points=np.array(line['pts'])*factor
    if len(points)==2 and np.min(points[:,0])>740 and np.max(points[:,0])<900 and np.min(points[:,1])>710 and np.max(points[:,1])<870:
     registered=(np.array(line['pts'])@np.array(r['matrix'])+r['offset'])*factor
     lines.append(dict(index=index,pagePixelEndpoints=points.tolist(),registeredPixelEndpoints=registered.tolist(),worldEndpoints=world(registered).tolist()))
   records.append(dict(page=number,level=32-number,lines=lines))
 save('spiral-source-lines.json',records)
 sheet=Image.new('RGB',(1500,800),'white');d=ImageDraw.Draw(sheet)
 for i,record in enumerate(records):
  im=Image.open(ROOT/f'data/previews/saw_occupants_guide_2014_p{record["page"]}.png').convert('RGB');dd=ImageDraw.Draw(im)
  for line in record['lines']:
   pts=line['pagePixelEndpoints'];dd.line([tuple(p)for p in pts],fill='#c9272c',width=1)
  crop=im.crop((730,705,905,885)).resize((700,720));sheet.paste(crop,(i*750,55));d.text((i*750+10,15),f'2014 level{record["level"]}: ST04 source radial lines',fill='black')
 sheet.save(DATA/'spiral-source-lines.png')
 print('SAW223_SOURCE_LINES',[(r['level'],len(r['lines']))for r in records])


def fit_spiral():
 from shapely.geometry import Polygon,mapping
 from shapely.ops import unary_union
 rows=json.loads((OUT/'spiral-source-lines.json').read_text());registration=json.loads((ROOT/'result/blender/saw-floors216/registration.json').read_text());fits=[]
 for row in rows:
  lines=[np.array(v['pagePixelEndpoints'])for v in row['lines']if 33<np.linalg.norm(np.diff(v['pagePixelEndpoints'],axis=0))<35]
  normals=[];offsets=[]
  for a,b in lines:
   d=b-a;normal=np.array([-d[1],d[0]])/np.linalg.norm(d);normals.append(normal);offsets.append(np.dot(normal,a))
  center=np.linalg.lstsq(normals,offsets,rcond=None)[0];radius=np.linalg.norm(np.array(lines)-center,axis=2)
  reg=registration[str(row['page'])];factor=1501/595.276
  pc=center@reg['matrix']+np.array(reg['offset'])*factor
  fits.append(dict(page=row['page'],lineCount=len(lines),centerPagePixels=center.tolist(),registeredCenterPixels=pc.tolist(),innerRadiusPixels=float(np.median(radius.min(1))),outerRadiusPixels=float(np.median(radius.max(1))),maxRadialLineResidualPixels=float(np.max(np.abs(np.array(normals)@center-offsets)))))
 fit=fits[0];reg=registration['27'];factor=1501/595.276;center=np.array(fit['centerPagePixels']);inner=fit['innerRadiusPixels'];outer=fit['outerRadiusPixels']
 def point(radius,angle):
  a=math.radians(angle);source=center+radius*np.array([math.cos(a),math.sin(a)])
  return world([source@reg['matrix']+np.array(reg['offset'])*factor])[0]
 circle=[point(outer+.5,a).tolist()for a in np.linspace(0,360,145)[:-1]]
 # Source p27 shows first visible radials about40,55,...145 degrees;
 # p26 shows the last visible radials60,75,90. A420degree turn in the
 # positive page-angle direction preserves these station orders. Riser count
 #28 and the inherited18/21.9 datums are explicitly estimates.
 start=30.;end=450.;count=28;step=(end-start)/count;rise=3.9/count
 treads=[]
 for i in range(count):
  aa=np.linspace(start+step*i,start+step*(i+1),7)
  ring=[point(inner,a).tolist()for a in aa]+[point(outer,a).tolist()for a in aa[::-1]]
  treads.append(dict(index=i,top=18+rise*(i+1),ring=ring,angleStart=float(aa[0]),angleEnd=float(aa[-1])))
 landing=Polygon([point(inner,a)for a in np.linspace(450,495,19)]+[point(outer+.6,a)for a in np.linspace(495,450,19)])
 widths=[];goings=[];inner_goings=[]
 for a in np.linspace(start,end,169):
  p=point(inner,a);q=point(outer,a);widths.append(float(np.linalg.norm(q-p)))
  r=inner+.5/float(np.linalg.norm(point(inner+1,a)-p))
  goings.append(float(np.linalg.norm(point(r,a+step)-point(r,a))))
  inner_goings.append(float(np.linalg.norm(point(inner,a+step)-p)))
 vectors=json.loads((ROOT/'result/blender/saw-floors216/vectors.json').read_text());factor0=1501/vectors['32']['pageSize'][0]
 cabins=[Polygon(world(np.array(next(c for c in vectors['32']['candidates']if c['index']==i)['pts'][:-1])*factor0))for i in registration['32']['sourceControlCurveIndices']]
 lifts=unary_union(cabins);footprint=unary_union([Polygon(t['ring'])for t in treads]+[landing])
 print('PLAN_CHECK',footprint.intersection(lifts).area,min(widths),min(goings),flush=True)
 assert footprint.intersection(lifts).area<1e-8 and min(widths)>1.0 and min(goings)>.25
 save('spiral-plan.json',dict(baselineSha256=SHA,sourceFits=fits,registeredCenterResidualPixels=float(np.linalg.norm(np.array(fits[0]['registeredCenterPixels'])-fits[1]['registeredCenterPixels'])),centerWorld=point(0,0).tolist(),sourceCenterPagePixels=center.tolist(),innerRadiusPixels=inner,outerRadiusPixels=outer,sourceRegistration=reg,sourceFactor=factor,startAngle=start,endAngle=end,treadCount=count,riserHeight=rise,lowerDatum=18.,upperDatum=21.9,waistThicknessEstimate=.18,wallThicknessEstimate=.09,minimumClearRadialWidthMetres=min(widths),minimumGoingAtHalfMetreFromInnerMetres=min(goings),minimumInnerEdgeGoingMetres=min(inner_goings),turnPitchMetres=3.9*360/(end-start),minimumSelfHeadroomEstimate=3.9*360/(end-start)-.18-rise,treads=treads,landing=mapping(landing),opening=mapping(Polygon(circle)),liftPolygons=[mapping(c)for c in cabins],liftOverlapM2=footprint.intersection(lifts).area,interpretation='ST04 fifth-to-sixth connector is separate from the main stair beside the lifts. Positive page-angle ascent follows visible lower and upper radial station order. Count28 and exact angular endpoints are estimates fitted to approximately15degree source spacings, not a recovered construction schedule.'))
 print('SAW223_SPIRAL_PLAN',min(widths),min(goings),min(inner_goings),fits,flush=True)

COLLECTION='SAW_STRUCTURE173_registered_main_circulation'
PREFIX='SAW223_'
def build_component():
 import bpy,bmesh
 from mathutils import Vector
 from mathutils.bvhtree import BVHTree
 from integrate_exterior_round194 import object_fingerprint,accepted_fingerprints,update_scene
 from refine_portsmouth_exterior207 import material_fingerprint
 from build_clm_hongkong_room220 import modifier_payload
 assert hashlib.sha256(BASE.read_bytes()).hexdigest()==SHA
 bpy.ops.wm.open_mainfile(filepath=str(BASE));update_scene()
 expected=accepted_fingerprints(ROOT/'result/blender/stage222',SHA)
 originals={o.name:object_fingerprint(o)for o in bpy.data.objects};assert originals==expected and len(originals)==7688
 materials={m.name:material_fingerprint(m)for m in bpy.data.materials}
 members={o.name:sorted(c.name for c in o.users_collection)for o in bpy.data.objects}
 modifiers={o.name:json.dumps([modifier_payload(m)for m in o.modifiers],sort_keys=True)for o in bpy.data.objects}
 visibility={o.name:o.hide_render for o in bpy.data.objects}
 metadata=json.loads((ROOT/'web/tools/building-metadata.json').read_text());rooms={s['collection']:sorted(o.name for o in bpy.data.collections[s['collection']].all_objects)for s in metadata['spaces']};assert len(rooms)==21
 plan=json.loads((OUT/'spiral-plan.json').read_text());assert plan['baselineSha256']==SHA
 center=np.array(plan['sourceCenterPagePixels']);reg=plan['sourceRegistration'];factor=plan['sourceFactor'];inner=plan['innerRadiusPixels'];outer=plan['outerRadiusPixels'];rise=plan['riserHeight'];count=plan['treadCount'];start=plan['startAngle'];end=plan['endAngle'];angle_step=(end-start)/count
 def point(radius,angle):
  a=math.radians(angle);source=center+radius*np.array([math.cos(a),math.sin(a)])
  return world([source@reg['matrix']+np.array(reg['offset'])*factor])[0]
 pixels_per_metre=1/np.linalg.norm(point(outer+1,0)-point(outer,0));wall=.09*pixels_per_metre
 r0=inner-wall;r1=outer+wall
 geometry=json.loads((OUT/'geometry-plan.json').read_text())
 added=[];archived=[];bindings={};retention=[]
 def mesh_object(name,vertices,faces,source,uv_records=None):
  mesh=bpy.data.meshes.new(PREFIX+name);mesh.from_pydata(vertices,[],faces);mesh.update()
  src=bpy.data.objects[source]
  for m in src.data.materials:mesh.materials.append(m)
  if uv_records is None:
   uv=mesh.uv_layers.new(name='MetricUV')
   for loop in mesh.loops:
    p=mesh.vertices[loop.vertex_index].co;uv.data[loop.index].uv=(p.x,p.y)
  else:
   for layer_name,records in uv_records.items():
    uv=mesh.uv_layers.new(name=layer_name)
    for loop,value in zip(uv.data,records):loop.uv=value
  obj=bpy.data.objects.new(PREFIX+name,mesh);bpy.data.collections[COLLECTION].objects.link(obj)
  obj['destinationCollection']=COLLECTION;obj['historicalSourceYear']=2014;obj['dimensionStatus']='Estimated native registration; source-derived ST04 location and radial order, not measured construction or2026 current condition'
  added.append(obj);bindings[obj.name]=[m.name for m in mesh.materials];return obj
 def retained(name,face_limit=None,max_height=None):
  src=bpy.data.objects[name];selected=[]
  for p in src.data.polygons:
   if face_limit is not None and p.index>=face_limit:continue
   if max_height is not None and max(src.data.vertices[i].co.z for i in p.vertices)>max_height:continue
   selected.append(p)
  assert selected
  ids=sorted({i for p in selected for i in p.vertices});lookup={v:i for i,v in enumerate(ids)}
  uv={layer.name:[tuple(layer.data[loop].uv)for p in selected for loop in p.loop_indices]for layer in src.data.uv_layers}
  obj=mesh_object('Retained_'+name,[list(src.data.vertices[i].co)for i in ids],[tuple(lookup[i]for i in p.vertices)for p in selected],name,uv)
  obj.matrix_world=src.matrix_world.copy()
  for a,b in zip(obj.data.polygons,selected):a.material_index=b.material_index
  retention.append(dict(original=name,replacement=obj.name,originalFaces=len(src.data.polygons),retainedFaces=len(selected),removedUpperFaces=len(src.data.polygons)-len(selected),lowerCoordinatesUVAndMaterialSlotsCopiedExactly=True))
  archived.append(name);return obj
 retained('SAW173_registered_main_treads',face_limit=120*6)
 retained('SAW173_flat_anti_slip_nosings',face_limit=119*6)
 rails=json.loads((ROOT/'result/blender/saw_lower_structure173/audit.json').read_text())['change']['railRecords'];rail_cut=min(r['faceStart']for r in rails if r['flight']==5)
 retained('SAW173_main_stair_rails',face_limit=rail_cut)
 retained('SAWFLOOR216_coordinated_shared_floor_landings',max_height=18.0001)
 # Rebuild only sixth-floor aperture around the independently located ST04.
 oldfloor=bpy.data.objects['SAWFLOOR216_registered_floor_21.9']
 vv=[];ff=[]
 for triangle in geometry['floorTriangles']:
  off=len(vv);vv.extend((x,y,21.9)for x,y in triangle);ff.append(tuple(off+i for i in range(3)))
 mesh_object('Sixth_floor_ST04_aperture',vv,ff,oldfloor.name);archived.append(oldfloor.name)
 # A single closed stepped waist connects all28 goings. No floating discrete
 # prisms or Z-offset overlays are used. The bottom is a continuous helix.
 vv=[];ff=[];segments=count*6
 for j in range(segments+1):
  a=start+(end-start)*j/segments;bottom=18+rise*j/6-.18
  for r in [r0,r1]:
   x,y=point(r,a);vv.append((x,y,bottom))
 for i in range(count):
  off=len(vv);top=18+rise*(i+1)
  for j in range(7):
   for r in [r0,r1]:
    x,y=point(r,start+angle_step*(i+j/6));vv.append((x,y,top))
  for j in range(6):
   a=off+j*2;b=a+2;low=(i*6+j)*2;next_low=low+2
   ff.extend([(a,a+1,b+1,b),(low,next_low,next_low+1,low+1)])
   if j==0 and i>0:ff.extend([(low,off-2,a,b,next_low),(low+1,next_low+1,b+1,a+1,off-1)])
   else:ff.extend([(low,a,b,next_low),(low+1,next_low+1,b+1,a+1)])
  if i==0:ff.append((0,1,off+1,off))
  else:
   previous=off-2;ff.append((previous,previous+1,off+1,off))
  if i==count-1:ff.append((off+12,off+13,segments*2+1,segments*2))
 stair=mesh_object('ST04_continuous_spiral_waist_and_treads',vv,ff,'SAW173_registered_main_treads')
 def annular_wall(vertices,faces,ra,rb,a0,a1,z_func,top_offset):
  n=max(1,round(abs(a1-a0)/2.5));off=len(vertices)
  for j in range(n+1):
   a=a0+(a1-a0)*j/n;z=z_func(a)
   for h,r in [(z,ra),(z,rb),(z+top_offset,ra),(z+top_offset,rb)]:
    x,y=point(r,a);vertices.append((x,y,h))
  faces.extend([(off,off+2,off+3,off+1),(off+n*4,off+n*4+1,off+n*4+3,off+n*4+2)])
  for j in range(n):
   k=off+4*j;l=k+4
   faces.extend([(k,l,l+2,k+2),(k+1,k+3,l+3,l+1),(k+2,l+2,l+3,k+3),(k,l,l+1,k+1)])
 vv=[];ff=[]
 def step_z(a):return 18+rise*min(count,max(1,math.ceil((a-start)/angle_step-1e-7)))
 # Guard bases follow the continuous soffit plus riser height, remaining in the
 # waist volume rather than spanning unsupported gaps between step prisms.
 smooth_z=lambda a:18+3.9*(a-start)/(end-start)-.05
 annular_wall(vv,ff,r0,inner,start,end,smooth_z,1.12)
 annular_wall(vv,ff,outer,r1,start,end,smooth_z,1.12)
 annular_wall(vv,ff,r0,inner,end,end+45,lambda a:21.9,1.05)
 # The sixth-floor open rim has its own supported guard. Leave only the
 # authored arrival platform's outer edge open into the public floor.
 annular_wall(vv,ff,r1+.15,r1+.15+wall,end+45,end+360,lambda a:21.9,1.05)
 guards=mesh_object('ST04_concrete_guards_and_sixth_floor_rim',vv,ff,'SAW173_registered_main_treads')
 # Closed arrival slab, with exact common radial edge at the last tread.
 vv=[];ff=[]
 for triangle in geometry['landingTriangles']:
  off=len(vv);vv.extend((x,y,z)for z in [21.72,21.9]for x,y in triangle);ff.extend([(off+2,off+1,off),(off+3,off+4,off+5)])
 for a,b in zip(geometry['landingRing'],geometry['landingRing'][1:]+geometry['landingRing'][:1]):
  off=len(vv);vv.extend([(a[0],a[1],21.72),(b[0],b[1],21.72),(b[0],b[1],21.9),(a[0],a[1],21.9)]);ff.append(tuple(off+i for i in range(4)))
 arrival=mesh_object('ST04_sixth_floor_arrival',vv,ff,'SAW173_registered_main_treads')
 # Continuous supported handrails complete the source-visible spiral guard
 # assembly. Dark finish reuses the accepted material; no photo is a texture.
 vv=[];ff=[]
 def tube(a,b,radius=.025):
  a,b=Vector(a),Vector(b);axis=(b-a).normalized();u=axis.cross(Vector((0,0,1)))
  if u.length<.01:u=axis.cross(Vector((1,0,0)))
  u.normalize();v=axis.cross(u);off=len(vv)
  for p in [a,b]:
   for i in range(8):vv.append(tuple(p+radius*(math.cos(i*math.tau/8)*u+math.sin(i*math.tau/8)*v)))
  ff.extend([tuple(off+i for i in range(7,-1,-1)),tuple(off+8+i for i in range(8))])
  for i in range(8):j=(i+1)%8;ff.append((off+i,off+j,off+8+j,off+8+i))
 for radius,wall_radius in [(inner+.045*pixels_per_metre,inner-.015*pixels_per_metre),(outer-.045*pixels_per_metre,outer+.015*pixels_per_metre)]:
  points=[]
  for a in np.linspace(start,end,169):
   x,y=point(radius,a);points.append((x,y,18+3.9*(a-start)/(end-start)+.96))
  for a,b in zip(points,points[1:]):tube(a,b)
  for a in np.linspace(start+5,end-5,15):
   z=18+3.9*(a-start)/(end-start)+.96;p=point(radius,a);q=point(wall_radius,a);tube((*p,z),(*q,z),.012)
 handrails=mesh_object('ST04_continuous_supported_handrails',vv,ff,'SAW173_main_stair_rails')
 def weld_and_check(obj):
  bm=bmesh.new();bm.from_mesh(obj.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-6);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));assert all(e.is_manifold for e in bm.edges),obj.name
  volume=bm.calc_volume(signed=True);assert volume>0;bm.to_mesh(obj.data);bm.free();obj.data.update();return dict(object=obj.name,manifold=True,positiveVolumeM3=volume)
 solids=[weld_and_check(o)for o in [stair,guards,arrival]]
 for name in archived:bpy.data.objects[name].hide_render=True;bpy.data.objects[name].hide_set(True)
 update_scene()
 fingerprints={o.name:object_fingerprint(o)for o in added}
 component=OUT/'component.blend';bpy.data.libraries.write(str(component),set(added),fake_user=True,compress=True)
 save('component-record.json',dict(addedObjects=list(fingerprints),archivedObjects=archived,addedFingerprints=fingerprints,replacementMaterialBindings=bindings,retention=retention,solids=solids))
 # Reopen the complete read-only native and append only the saved component.
 bpy.ops.wm.open_mainfile(filepath=str(BASE));update_scene()
 with bpy.data.libraries.load(str(component),link=False)as(available,loaded):loaded.objects=list(fingerprints)
 for obj in loaded.objects:
  for index,name in enumerate(bindings[obj.name]):obj.data.materials[index]=bpy.data.materials[name]
  bpy.data.collections[COLLECTION].objects.link(obj)
 for name in archived:bpy.data.objects[name].hide_render=True;bpy.data.objects[name].hide_set(True)
 update_scene()
 assert all(object_fingerprint(bpy.data.objects[n])==v for n,v in originals.items())
 assert all(object_fingerprint(bpy.data.objects[n])==v for n,v in fingerprints.items())
 assert all(material_fingerprint(bpy.data.materials[n])==v for n,v in materials.items())
 assert all(sorted(c.name for c in bpy.data.objects[n].users_collection)==v for n,v in members.items())
 assert all(json.dumps([modifier_payload(m)for m in bpy.data.objects[n].modifiers],sort_keys=True)==v for n,v in modifiers.items())
 assert all(sorted(o.name for o in bpy.data.collections[n].all_objects)==v for n,v in rooms.items())
 assert all(bpy.data.objects[n].hide_render==v for n,v in visibility.items()if n not in archived)
 verification=dict(savedComponentReopened=True,originalObjectsVerified=len(originals),originalMaterialsVerified=len(materials),allOriginalFingerprintsUnchanged=True,allOriginalMaterialNodesUnchanged=True,allOriginalModifiersUnchanged=True,allOriginalMembershipUnchanged=True,protectedSpaces=len(rooms),protectedSpaceObjects=len({n for values in rooms.values()for n in values}),protectedSpaceMembershipUnchanged=True,unrelatedVisibilityPreserved=True,nativeBytesUnchanged=hashlib.sha256(BASE.read_bytes()).hexdigest()==SHA)
 save('native-preservation.json',verification)
 # Compact actual saved surfaces are subsequently checked with planar geometry.
 rows=[]
 for name in list(fingerprints)+['SAWFLOOR216_registered_floor_18.0','SAW173_registered_main_treads']:
  obj=bpy.data.objects[name];rows.append(dict(name=name,vertices=[list(obj.matrix_world@v.co)for v in obj.data.vertices],faces=[list(p.vertices)for p in obj.data.polygons],faceNormals=[list(p.normal)for p in obj.data.polygons]))
 save('saved-surfaces.tmp.json',rows)
 print('SAW223_COMPONENT_SAVED_REOPENED',len(fingerprints),len(archived),verification,flush=True)



def prepare_geometry():
 import shapely
 from shapely.geometry import Polygon,shape,mapping
 from shapely.ops import unary_union
 from shapely.geometry.polygon import orient
 plan=json.loads((OUT/'spiral-plan.json').read_text());center=np.array(plan['sourceCenterPagePixels']);reg=plan['sourceRegistration'];factor=plan['sourceFactor'];inner=plan['innerRadiusPixels'];outer=plan['outerRadiusPixels'];end=plan['endAngle']
 def point(radius,angle):
  a=math.radians(angle);source=center+radius*np.array([math.cos(a),math.sin(a)])
  return world([source@reg['matrix']+np.array(reg['offset'])*factor])[0]
 wall=.09/np.linalg.norm(point(outer+1,0)-point(outer,0));r0=inner-wall;r1=outer+wall
 opening=Polygon([point(r1+.15,a)for a in np.linspace(0,360,193)[:-1]])
 landing=Polygon([point(r0,a)for a in np.linspace(end,end+45,31)]+[point(r1+5,a)for a in np.linspace(end+45,end,31)])
 source=json.loads((ROOT/'result/blender/saw-floors216/surface-plan.json').read_text())['floors'][-1]
 native_floor=unary_union([Polygon(t)for t in source['floorTriangles']]);floor=native_floor.difference(opening).difference(landing.buffer(.003,join_style=2))
 assert landing.difference(native_floor).area<1e-7
 def triangles(poly):
  result=[list(orient(t,sign=1).exterior.coords)[:-1]for t in shapely.constrained_delaunay_triangles(poly).geoms if poly.covers(t.representative_point())]
  assert abs(sum(Polygon(t).area for t in result)-poly.area)<1e-7
  return result
 save('geometry-plan.json',dict(floorTriangles=triangles(floor),landingTriangles=triangles(landing),landingRing=list(orient(landing,sign=1).exterior.coords)[:-1],opening=mapping(opening),landing=mapping(landing),originalFloorAreaM2=native_floor.area,newFloorAreaM2=floor.area,landingFloorContactDistanceMetres=floor.distance(landing)))
 print('SAW223_GEOMETRY_PREPARED',floor.area,landing.area,flush=True)



def verify_and_render():
 import bpy
 from mathutils import Vector
 from mathutils.bvhtree import BVHTree
 from refine_street_connections194 import render_review
 from integrate_exterior_round194 import update_scene
 plan=json.loads((OUT/'spiral-plan.json').read_text());record=json.loads((OUT/'component-record.json').read_text())
 center=np.array(plan['sourceCenterPagePixels']);reg=plan['sourceRegistration'];factor=plan['sourceFactor'];inner=plan['innerRadiusPixels'];outer=plan['outerRadiusPixels'];count=plan['treadCount'];rise=plan['riserHeight'];angle_step=(plan['endAngle']-plan['startAngle'])/count
 def point(radius,angle):
  a=math.radians(angle);source=center+radius*np.array([math.cos(a),math.sin(a)])
  return world([source@reg['matrix']+np.array(reg['offset'])*factor])[0]
 vertices=[];faces=[];owners=[]
 for obj in bpy.data.collections['SAW_PUBLIC_INTERIOR_study'].all_objects:
  if obj.type!='MESH' or obj.hide_render:continue
  off=len(vertices);vertices.extend(obj.matrix_world@v.co for v in obj.data.vertices)
  faces.extend(tuple(off+i for i in p.vertices)for p in obj.data.polygons);owners.extend([obj.name]*len(obj.data.polygons))
 tree=BVHTree.FromPolygons(vertices,faces)
 ground=bpy.data.objects['SAWFLOOR216_registered_floor_18.0'];ground_tree=BVHTree.FromPolygons([ground.matrix_world@v.co for v in ground.data.vertices],[tuple(p.vertices)for p in ground.data.polygons])
 probes=[];conflicts=[];base=[]
 for i in range(count):
  for f in [.15,.5,.85]:
   a=plan['startAngle']+angle_step*(i+f)
   for radial in [.2,.5,.8]:
    x,y=point(inner+(outer-inner)*radial,a);z=18+rise*(i+1);hit=tree.ray_cast(Vector((x,y,z+.004)),Vector((0,0,1)),2.101)
    row=dict(step=i,angle=a,radialFraction=radial,point=[float(x),float(y),z],upwardObstruction=None if hit[0]is None else dict(object=owners[hit[2]],gap=hit[0].z-z))
    probes.append(row)
    if hit[0]is not None:conflicts.append(row)
    if i==0:
     support=ground_tree.ray_cast(Vector((x,y,18.1)),Vector((0,0,-1)),.2);assert support[0]is not None and abs(support[0].z-18)<1e-5
     base.append(dict(point=[float(x),float(y)],supportObject=ground.name,supportZ=support[0].z))
 save('saved-headroom-and-support.json',dict(actualSavedHeadroomSamples=len(probes),clearanceThresholdMetres=2.1,obstructions=conflicts,firstTreadActualFifthFloorSupports=base,firstTreadRiserMeetsFloorZ=18,continuousClosedWaist=True,estimatedTurnPitch=plan['turnPitchMetres'],estimatedSelfHeadroomLowerBound=plan['minimumSelfHeadroomEstimate'],rows=probes))
 assert not conflicts,conflicts[:5]
 # Two review scenes use only actual public structure around levels5/6, with
 # all source objects referenced without mesh, material or collection mutation.
 def render_phase(label,names):
  scene=bpy.data.scenes.new('SAW223_REVIEW_'+label);scene.world=bpy.data.scenes['00_CAMPUS_COMPLETE'].world;scene.view_settings.view_transform='AgX'
  for name in names:
   obj=bpy.data.objects[name]
   if not obj.hide_render:scene.collection.objects.link(obj)
  for obj in bpy.data.scenes['00_CAMPUS_COMPLETE'].objects:
   if obj.type=='LIGHT':scene.collection.objects.link(obj)
  bpy.context.window.scene=scene
  views=[('upper-connector',(-55,3,23),(-61.82,11.23,20.1),10),('sixth-arrival',(-57,5,29),(-61.82,11.23,21.1),10)]
  for title,position,target,scale in views:render_review(scene,OUT/(label+'-'+title+'.png'),position,target,scale)
  bpy.data.scenes.remove(scene)
 # Render actual after geometry now. A baseline reopen then provides identical
 # camera/light before views; geometry checks above refer to saved component.
 names=record['addedObjects']+['SAWFLOOR216_registered_floor_18.0']
 render_phase('after',names)
 bpy.ops.wm.open_mainfile(filepath=str(BASE));update_scene()
 names=['SAW173_registered_main_treads','SAW173_main_stair_rails','SAW173_flat_anti_slip_nosings','SAWFLOOR216_coordinated_shared_floor_landings','SAWFLOOR216_registered_floor_18.0','SAWFLOOR216_registered_floor_21.9']
 render_phase('before',names)
 print('SAW223_SAVED_HEADROOM_AND_RENDERS',len(probes),len(base),flush=True)



def finalize():
 from shapely.geometry import Polygon,shape,Point
 from shapely.ops import unary_union
 from PIL import Image,ImageDraw
 actual={r['name']:r for r in json.loads((OUT/'saved-surfaces.tmp.json').read_text())};plan=json.loads((OUT/'spiral-plan.json').read_text());record=json.loads((OUT/'component-record.json').read_text());geometry=json.loads((OUT/'geometry-plan.json').read_text());preservation=json.loads((OUT/'native-preservation.json').read_text());headroom=json.loads((OUT/'saved-headroom-and-support.json').read_text())
 def tops(name):
  row=actual[name];v=np.array(row['vertices']);levels={}
  for f,n in zip(row['faces'],row['faceNormals']):
   p=v[f]
   if n[2]>.99 and np.ptp(p[:,2])<1e-5:
    poly=Polygon(p[:,:2])
    if poly.is_valid and poly.area>1e-9:levels.setdefault(round(float(p[0,2]),5),[]).append(poly)
  return {z:unary_union(polygons)for z,polygons in levels.items()}
 cabins=unary_union([shape(v)for v in plan['liftPolygons']]);old=tops('SAW173_registered_main_treads');lower=tops(PREFIX+'Retained_SAW173_registered_main_treads');new=tops(PREFIX+'ST04_continuous_spiral_waist_and_treads')
 conflicts=[dict(top=z,overlapM2=p.intersection(cabins).area)for z,p in old.items()if p.intersection(cabins).area>.0001]
 remaining=[dict(top=z,overlapM2=p.intersection(cabins).area)for z,p in lower.items()if p.intersection(cabins).area>.0001]
 eliminated=[r for r in conflicts if r['top']>18.0001]
 new_collisions=[dict(top=z,overlapM2=p.intersection(cabins).area)for z,p in new.items()if p.intersection(cabins).area>.0001]
 assert len(conflicts)==38 and len(remaining)==32 and len(eliminated)==6 and not new_collisions and len(new)==28 and len(lower)==120
 assert set(lower)=={z for z in old if z<=18.0001}
 assert all(lower[z].symmetric_difference(old[z]).area<1e-8 for z in lower)
 arrival=tops(PREFIX+'ST04_sixth_floor_arrival')[21.9];floor=tops(PREFIX+'Sixth_floor_ST04_aperture')[21.9];stair_end=new[21.9]
 assert arrival.distance(stair_end)<1e-5 and arrival.intersection(stair_end).area<1e-5
 assert floor.distance(arrival)<.0031 and floor.intersection(arrival).area<1e-6
 assert all(a.distance(b)<1e-5 for a,b in zip(list(new.values()),list(new.values())[1:]))
 # Projected guard feet must meet actual saved waist or actual saved floor.
 center=np.array(plan['sourceCenterPagePixels']);reg=plan['sourceRegistration'];factor=plan['sourceFactor'];inner=plan['innerRadiusPixels'];outer=plan['outerRadiusPixels'];end=plan['endAngle'];start=plan['startAngle'];rise=plan['riserHeight']
 def point(radius,angle):
  a=math.radians(angle);source=center+radius*np.array([math.cos(a),math.sin(a)])
  return world([source@reg['matrix']+np.array(reg['offset'])*factor])[0]
 ppm=1/np.linalg.norm(point(outer+1,0)-point(outer,0));wall=.09*ppm;r0=inner-wall;r1=outer+wall
 waist_support=0;rim_support=0;landing_support=0
 for i in range(28):
  angle=start+(end-start)*(i+.5)/28;top=18+rise*(i+1);bottom=18+rise*(i+.5)-.18;guard_base=18+rise*(i+.5)-.05
  assert bottom<guard_base<top
  for r in [(r0+inner)/2,(outer+r1)/2]:
   level=min(new,key=lambda z:abs(z-top));assert abs(level-top)<.00002
   assert new[level].buffer(.00001).covers(Point(point(r,angle)));waist_support+=1
 for a in np.linspace(end+45+.5,end+360-.5,127):
  assert floor.buffer(.00001).covers(Point(point(r1+.15+wall/2,a)));rim_support+=1
 for a in np.linspace(end+.5,end+45-.5,19):
  assert arrival.buffer(.00001).covers(Point(point((r0+inner)/2,a)));landing_support+=1
 clear=[]
 for a in np.linspace(start,end,169):clear.append(float(np.linalg.norm(point(outer-.045*ppm,a)-point(inner+.045*ppm,a))-.05))
 assert min(clear)>1.0
 connectivity=dict(actualSavedTreadCount=len(new),retainedLowerTreads=len(lower),adjacentTreadContactCount=27,allAdjacentStepsSharePlanEdges=True,actualLastTreadToArrivalDistanceM=arrival.distance(stair_end),arrivalToRetainedSixthFloorSeamM=floor.distance(arrival),arrivalOverlapWithFloorM2=floor.intersection(arrival).area,guardWaistSupportSamples=waist_support,guardRimFloorSupportSamples=rim_support,guardLandingSupportSamples=landing_support,netClearWidthBetweenHandrailsMetres=min(clear),minimumGoingAtHalfMetreFromInnerWallMetres=plan['minimumGoingAtHalfMetreFromInnerMetres'],minimumInnerWinderGoingMetres=plan['minimumInnerEdgeGoingMetres'],riserHeightMetres=rise,headroomSamples=headroom['actualSavedHeadroomSamples'],headroomObstructions=len(headroom['obstructions']),minimumCheckedHeadroomMetres=2.1,analyticSelfHeadroomLowerBoundMetres=plan['minimumSelfHeadroomEstimate'])
 save('saved-connectivity.json',connectivity)
 save('conflict-delta.json',dict(originalTreadCabinConflicts=38,eliminatedUpperFlightConflicts=eliminated,remainingLowerFlightConflicts=remaining,newSpiralCabinConflicts=new_collisions,remainingConflictCount=32,scope='Only fifth-to-sixth ST04 has been replaced. Lower120 treads retain their exact original projected surfaces and32known cabin conflicts; no whole-main-stair acceptance.'))
 # Source overlays clearly separate the displaced old upper flight from ST04.
 registration=json.loads((ROOT/'result/blender/saw-floors216/registration.json').read_text());matrix=np.column_stack(((ANCHORS[1]-ANCHORS[0])/1200,(ANCHORS[2]-ANCHORS[1])/785))
 sheet=Image.new('RGB',(1400,850),'white');d=ImageDraw.Draw(sheet)
 for i,page in enumerate([27,26]):
  im=Image.open(ROOT/f'data/previews/saw_occupants_guide_2014_p{page}.png').convert('RGB');dd=ImageDraw.Draw(im);r=registration[str(page)];inv=np.linalg.inv(r['matrix'])
  def pixels(points):
   registered=(np.array(points)-ANCHORS[0])@np.linalg.inv(matrix).T+np.array([145,400])
   return (registered-np.array(r['offset'])*factor)@inv
  for z,p in old.items():
   if z<=18.0001:continue
   for part in p.geoms if hasattr(p,'geoms')else[p]:dd.line([tuple(v)for v in pixels(part.exterior.coords)],fill='#c42e32',width=2)
  for radius in [inner,outer]:
   world_ring=[point(radius,a)for a in np.linspace(0,360,145)]
   dd.line([tuple(pixel)for pixel in pixels(world_ring)],fill='#006a98',width=3)
  crop=im.crop((470,430,1040,1010)).resize((690,700));sheet.paste(crop,(i*700,90));d.text((i*700+12,12),f'2014 level{32-page}: RED removed false flight; BLUE real ST04',fill='black')
  d.text((i*700+12,38),'Source guide position; dimensions and full riser schedule estimated',fill='black')
 sheet.save(DATA/'source-position-comparison.png')
 refs=[]
 catalogue=json.loads((ROOT/'data/catalogue.json').read_text())['records']
 for id in ['exteriors:saw_archdaily_031','exteriors:saw_archdaily_036','exteriors:saw_archdaily_061','exteriors:saw_archdaily_041']:
  row=next(v for v in catalogue if v['id']==id);refs.append(dict(path=row['local_file'],sourceUrl=row['url'],parentUrl=row['parent_url'],sha256=row['sha256'],sourceType='Architect published design drawing, not certified as-built',publicationDate='2014-10-14',current2026ConditionEstablished=False))
 for path,url,kind,date in [('data/documents/saw_occupants_guide_2014.pdf','https://info.lse.ac.uk/staff/divisions/estates-division/Assets/Documents/SAW/Final-Web-version-of-Occupants-Guide.pdf','Official2014 guide: pp26/27 ST04 and fixed dual lift controls','2014'),('data/collections/saw-circulation223/official-building-boards.pdf','https://info.lse.ac.uk/staff/divisions/estates-division/Assets/Documents/SAW/Combined-final-boards-for-web.pdf','Official board p9, text credited O’Donnell & Tuomey: explicit fifth-to-sixth spiral change; photograph not floor-labelled','PDF creation2015-01-16; displayed board date unknown')]:
  refs.append(dict(path=path,sourceUrl=url,sha256=hashlib.sha256((ROOT/path).read_bytes()).hexdigest(),sourceType=kind,date=date,current2026ConditionEstablished=False))
 (DATA/'sources.json').write_text(json.dumps(refs,indent=2)+'\n')
 component=OUT/'component.blend';audit=dict(version=223,status='accepted_partial_fifth_to_sixth_connector',baselinePath=str(BASE.relative_to(ROOT)),baselineSha256=SHA,componentPath=str(component.relative_to(ROOT)),componentSha256=hashlib.sha256(component.read_bytes()).hexdigest(),targetCollection=COLLECTION,destinationCollection=COLLECTION,interiorCollection='SAW_PUBLIC_INTERIOR_study',replacesInteriorCollection=None,**record,verification=preservation,connectivity=connectivity,conflictDelta='conflict-delta.json',scope='Correct only the historical fifth-to-sixth ST04 spiral to its separately registered position, with continuous closed stair waist, walls, supported handrails, arrival slab and sixth-floor opening. Keep lowerG-to-fifth120treads unchanged; their32known lift conflicts remain unresolved.',sourceRefs=refs,sourceProof='data/collections/saw-circulation223/source-position-comparison.png',sourceCenterFit=plan['sourceFits'],interiorSections=[dict(id='5',view=dict(position=[-55,23,-3],target=[-61.819,19.8,-11.234],fov=50)),dict(id='6',view=dict(position=[-57,28,-5],target=[-61.819,21.9,-11.234],fov=50))],previews=['before-upper-connector.png','after-upper-connector.png','before-sixth-arrival.png','after-sixth-arrival.png'],limitations=['Historical2014/2015 source does not establish current2026 condition.','28risers,420degree total rotation, exact entrance/arrival angles and inherited18/21.9m native datums are estimates constrained by visible approximately15degree source radials; this is not a recovered construction schedule.','Inner winder going is0.165m; minimum0.278m going is evaluated0.5m from inner wall. These are model measurements, not access or compliance certification.','Wall/waist/guard/rail dimensions and finish are estimates; no source photograph is used as a texture.','Fifth floor is retained as the actual departure support; no unsupported opening into fourth floor is invented.','The old northern main-stair aperture is retained without enlargement; its exact agreement with the unresolvedG-to-fifth lower route remains unaccepted. Lower landings/guards and32cabin conflicts require separate reconstruction.'])
 audit['sourceRelativeDatums']=dict(architectSection='data/collections/exteriors/images/saw_archdaily_041.jpg',groundFFL=19.550,fifthFFL=37.550,sixthFFL=41.450,relativeFifth=18.,relativeSixth=21.9,storeyRise=3.9,status='Published design-section values support the retained relative heights; not surveyed current condition or a verified absolute site datum.')
 save('audit.json',audit);print('SAW223_ACCEPTED_PARTIAL',audit['componentSha256'],connectivity,flush=True)

if __name__=='__main__':
 try:import bpy
 except ModuleNotFoundError:
  prepare();fit_spiral();prepare_geometry()
  if (OUT/'saved-surfaces.tmp.json').exists():finalize()
 else:build_component();verify_and_render()
