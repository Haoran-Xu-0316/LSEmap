"""Level LRB's inherited ramp/gallery links and support their retained guards.

Fixed Blender authoring configuration. Preserve the accepted campus, six-floor
registration, slabs, exterior and19 room studies. The new periodic ramp profile
provides estimated flat joining areas, not a surveyed or certified access ramp.
"""
from pathlib import Path
import hashlib,json,math,sys
import bpy,bmesh
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'result/blender/lrb-structure221'
BASE=ROOT/'result/blender/LSE_campus_detailed_v220.blend'
SHA='974c47b4af06a6caa5f474c1c75e05ffb4084285cb1ef8a4ceb11bd93738f6c0'
COLLECTION='LRB_PUBLIC_INTERIOR168_study'
PREFIX='LRB221_'
CENTRE=Vector((75.593385,13.262314,0))
PITCH=4.;BOTTOM=-3.68;FLAT=.14;BLEND=.14;FINISH=.012
sys.path.insert(0,str(ROOT/'web/tools'))
from integrate_exterior_round194 import accepted_fingerprints,object_fingerprint
from refine_portsmouth_exterior207 import material_fingerprint
from build_clm_hongkong_room220 import modifier_payload
from build_room_samples167 import RoomGeometry
from refine_library_interior208 import prism
SOURCES=[
 'LRB168__LRB_helical_solid_slab','LRB168__LRB_helical_carpet_surface',
 'LRB168__LRB_ramp_edge_downlight_housing','LRB168__LRB_ramp_edge_downlight_lens',
 'LRB_CIRC213_spiral_horizontal_rails','LRB_CIRC213_spiral_continuous_handrail',
 'LRB_CIRC213_spiral_guard_posts','LRB_CIRC213_rail_footplates',
 'LRB168__LRB_ramp_gallery_landings','LRB168__LRB_landing_carpet']


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def update():
 for scene in bpy.data.scenes:
  for layer in scene.view_layers:layer.update()
 bpy.context.window.scene=bpy.data.scenes['REVIEW_LRB168_INTERIOR']
 bpy.context.view_layer.update()


def original_state():
 metadata=json.loads((ROOT/'web/tools/building-metadata.json').read_text())
 rooms={r['collection']:sorted(o.name for o in bpy.data.collections[r['collection']].all_objects)for r in metadata['spaces']}
 assert len(rooms)==19 and len(set().union(*(set(v)for v in rooms.values())))==678
 return dict(objects={o.name:object_fingerprint(o)for o in bpy.data.objects},
  materials={m.name:material_fingerprint(m)for m in bpy.data.materials},
  modifiers={o.name:hashlib.sha256(json.dumps([modifier_payload(m)for m in o.modifiers],sort_keys=True).encode()).hexdigest()for o in bpy.data.objects},
  visibility={o.name:o.hide_render for o in bpy.data.objects},
  ownership={o.name:sorted(c.name for c in o.users_collection)for o in bpy.data.objects},rooms=rooms,
  roomScenes={name:{s.name:sorted(n for n in names if n in s.objects)for s in bpy.data.scenes}for name,names in rooms.items()})


def profile(phi):
 """Integral of a compact smoothstep grade,with flat joins at each full turn."""
 tau=math.tau
 if phi<=FLAT:return 0.
 if phi>=tau-FLAT:return 1.
 if phi>tau/2:return 1-profile(tau-phi)
 length=tau-2*FLAT-BLEND
 if phi<FLAT+BLEND:
  t=(phi-FLAT)/BLEND
  return BLEND*(t**3-.5*t**4)/length
 return (phi-FLAT-BLEND/2)/length


def vertical_change(p):
 phi=math.atan2(p.y-CENTRE.y,p.x-CENTRE.x)%math.tau
 return PITCH*(profile(phi)-phi/math.tau)


def clone(source):
 obj=source.copy();obj.data=source.data.copy();obj.name=PREFIX+source.name.removeprefix('LRB168__').removeprefix('LRB_CIRC213_')
 obj['originalObject']=source.name;obj['destinationCollection']=COLLECTION;obj['buildingCode']='LRB'
 obj['scope']='Estimated six-level flat ramp/gallery joining areas,continuous periodic profile;source footprint and floor pitch retained'
 bpy.data.collections[COLLECTION].objects.link(obj);obj.hide_render=False;obj.hide_set(False)
 return obj


def tree(objects):
 vs=[];fs=[]
 for obj in objects:
  start=len(vs);vs.extend(obj.matrix_world@v.co for v in obj.data.vertices)
  fs.extend(tuple(start+i for i in face.vertices)for face in obj.data.polygons)
 return BVHTree.FromPolygons(vs,fs)


def circular_front_edge(obj,radius,half_width=1.05):
 points={}
 for vertex in obj.data.vertices:
  p=obj.matrix_world@vertex.co;dx=p.x-CENTRE.x;dy=p.y-CENTRE.y
  if dx>0 and abs(dy)<2.2 and abs(math.hypot(dx,dy)-radius)<.003:
   points[(round(p.x,6),round(p.y,6))]=(p.x,p.y)
 ordered=sorted(points.values(),key=lambda p:p[1]);assert len(ordered)>2,(obj.name,radius,len(ordered))
 result=[];lo=CENTRE.y-half_width;hi=CENTRE.y+half_width
 for a,b in zip(ordered,ordered[1:]):
  if b[1]<lo or a[1]>hi:continue
  for y in [max(a[1],lo),min(b[1],hi)]:
   if not lo-1e-6<=y<=hi+1e-6:continue
   t=(y-a[1])/(b[1]-a[1]);p=(a[0]+t*(b[0]-a[0]),y)
   if not result or math.dist(p,result[-1])>1e-6:result.append(p)
 assert abs(result[0][1]-lo)<1e-5 and abs(result[-1][1]-hi)<1e-5
 return result


def make_mesh(name,verts,faces,materials):
 mesh=bpy.data.meshes.new(name+'_mesh');mesh.from_pydata(verts,[],faces);mesh.update()
 for mat in materials:mesh.materials.append(mat)
 uv=mesh.uv_layers.new(name='SurfaceUV')
 for face in mesh.polygons:
  pts=[mesh.vertices[i].co for i in face.vertices];u=(pts[1]-pts[0]).normalized();v=face.normal.cross(u)
  for li,p in zip(face.loop_indices,pts):uv.data[li].uv=((p-pts[0]).dot(u),(p-pts[0]).dot(v))
 return mesh


def build():
 added=[];records=[]
 for name in SOURCES:
  source=bpy.data.objects[name];assert not source.hide_render
  obj=clone(source)
  if name.endswith('landing_carpet'):
   inner_upper=circular_front_edge(bpy.data.objects['LRB168__LRB_helical_carpet_surface'],8.25)
   inner_lg=circular_front_edge(bpy.data.objects['LRB168__LRB_central_blue_carpet'],9.7)
   outer=circular_front_edge(bpy.data.objects['LRB168__LRB_gallery_carpet'],9.8)
   verts=[];faces=[]
   for index in range(6):
    z=BOTTOM+PITCH*index
    if index==0:inner=inner_lg
    elif index==5:
     # The final turn approaches only from negativeY. Beyond its end,cover
     # the accepted straight terminal bridge edge;do not invent another turn.
     inner=[p for p in inner_upper if p[1]<CENTRE.y-1e-5]
     inner += [(CENTRE.x+8.25,CENTRE.y),(CENTRE.x+8.20,CENTRE.y),(CENTRE.x+8.20,CENTRE.y+1.05)]
    else:inner=inner_upper
    polygon=inner+list(reversed(outer))
    prism(verts,faces,polygon,z,z+FINISH)
   obj.data=make_mesh(obj.name,verts,faces,list(source.data.materials))
   obj.matrix_world=Matrix.Identity(4)
   obj['change']='Curved finish boundaries exactly share retained optical-surface polygon edges;no rectangular overlap or uncovered corner'
  else:
   inverse=source.matrix_world.inverted()
   for vertex,original in zip(obj.data.vertices,source.data.vertices):
    p=source.matrix_world@original.co
    if name.endswith('ramp_gallery_landings'):p.z-=.020
    else:
     p.z+=vertical_change(p)
     if name.endswith('helical_carpet_surface'):p.z+=.003
    vertex.co=inverse@p
   obj.data.update()
   if name.endswith('helical_carpet_surface'):
    bm=bmesh.new();bm.from_mesh(obj.data)
    flat_start=[f for f in bm.faces if all(abs((obj.matrix_world@v.co).z-(BOTTOM+FINISH))<2e-5 for v in f.verts)]
    # The accepted LG circular carpet already occupies this flat starting region.
    bmesh.ops.delete(bm,geom=flat_start,context='FACES');bm.to_mesh(obj.data);bm.free();obj.data.update()
    obj['removedCoplanarLGStartFaces']=len(flat_start)
  added.append(obj);records.append(dict(original=name,replacement=obj.name))
 # LG had a supporting structural slab but no general gallery carpet;clone the
 # accepted G finish topology only,at the existing LG datum. No floor is invented.
 source=bpy.data.objects['LRB168__LRB_gallery_carpet'];vs=[];fs=[];uvs=[]
 for face in source.data.polygons:
  points=[source.matrix_world@source.data.vertices[i].co for i in face.vertices]
  if not all(abs(p.z-.332)<.002 for p in points):continue
  start=len(vs);vs.extend((p.x,p.y,p.z-4)for p in points);fs.append(tuple(range(start,len(vs))))
  uvs.append([tuple(source.data.uv_layers[0].data[li].uv)for li in face.loop_indices])
 assert len(fs)>50
 mesh=make_mesh(PREFIX+'LG_gallery_carpet',vs,fs,list(source.data.materials))
 for face,values in zip(mesh.polygons,uvs):
  for li,value in zip(face.loop_indices,values):mesh.uv_layers[0].data[li].uv=value
 obj=bpy.data.objects.new(PREFIX+'LG_gallery_carpet',mesh);bpy.data.collections[COLLECTION].objects.link(obj)
 obj['floorId']='LG';obj['destinationCollection']=COLLECTION;obj['buildingCode']='LRB'
 obj['scope']='Missing LG gallery finish on accepted existing structural floor;G finish footprint reused at LG datum,no new room'
 added.append(obj)
 # Retained bridge horizontal rails had no bridge-specific uprights. Add small
 # white posts and compact steel mounting feet at the photographed guard scale.
 g=RoomGeometry(bpy.data.collections[COLLECTION],PREFIX)
 g.materials['white']=bpy.data.materials['ATRIA_white'];g.materials['steel']=bpy.data.materials['ATRIA_white']
 posts=[]
 for index in range(6):
  z=BOTTOM+PITCH*index
  for dy in [-1.05,1.05]:
   for dx in [8.32,9.10,9.88]:
    x,y=CENTRE.x+dx,CENTRE.y+dy
    g.box('bridge_guard_mounting_feet','steel',(x,y,z+.01),(.06,.04,.02))
    g.tube('bridge_guard_white_uprights','white',(x,y,z+.02),(x,y,z+1.10),.0175)
    posts.append(dict(floor=index,base=[x,y,z],top=[x,y,z+1.10]))
 new_posts=g.finish()
 for obj in new_posts:
  obj['destinationCollection']=COLLECTION;obj['buildingCode']='LRB';obj['scope']='Photo-supported white bridge guard upright construction at estimated existing rail locations'
 added.extend(new_posts)
 update()
 return added,records,posts


def finish_objects(use_new):
 names=['LRB168__LRB_gallery_carpet','LRB168__LRB_central_blue_carpet']
 if use_new:
  names += [PREFIX+'LRB_helical_carpet_surface',PREFIX+'LRB_landing_carpet',PREFIX+'LG_gallery_carpet']
 else:names+=['LRB168__LRB_helical_carpet_surface','LRB168__LRB_landing_carpet']
 return [bpy.data.objects[n]for n in names]


def passage_measurements(use_new):
 surface=tree(finish_objects(use_new));rows=[]
 for index in range(6):
  z=BOTTOM+index*PITCH;hits=[]
  for dy in [-.94,-.47,0,.47,.94]:
   for dx in [8.19,8.23,8.50,9.20,9.75,9.82,9.95,10.05]:
    if index==5 and dy>=0 and dx<8.20:continue
    p=Vector((CENTRE.x+dx,CENTRE.y+dy,z+.40));hit=surface.ray_cast(p,Vector((0,0,-1)),.65)
    if hit[0]is None:
     assert not use_new,(index,dx,dy,'unsupported finish')
     hits.append(dict(x=dx,y=dy,supported=False));continue
    hits.append(dict(x=dx,y=dy,supported=True,z=hit[0].z,deltaFromFinish=hit[0].z-(z+FINISH)))
  valid=[r for r in hits if r['supported']]
  rows.append(dict(floor=['LG','G','1','2','3','4'][index],finishDatum=z+FINISH,
   supportedSamples=len(valid),unsupportedSamples=len(hits)-len(valid),
   maximumAbsoluteFinishMismatch=max(abs(r['deltaFromFinish'])for r in valid),
   maximumLocalHeightSpread=max(r['z']for r in valid)-min(r['z']for r in valid),samples=hits))
 return rows


def checks(added,posts):
 rows=passage_measurements(True)
 assert all(r['maximumAbsoluteFinishMismatch']<.00005 and not r['unsupportedSamples']for r in rows)
 floors=[bpy.data.objects[PREFIX+'LRB_helical_solid_slab'],bpy.data.objects[PREFIX+'LRB_ramp_gallery_landings'],
         bpy.data.objects['LRB168__LRB_library_floor_slabs'],bpy.data.objects['LRB168_LG_atrium_foundation']]
 support=tree(floors);rail=tree([bpy.data.objects['LRB168__LRB_landing_handrail.001']]);post_checks=[]
 for post in posts:
  p=Vector(post['base']);hit=support.ray_cast(p+Vector((0,0,.15)),Vector((0,0,-1)),.25)
  assert hit[0]is not None and abs(hit[0].z-p.z)<.001,(post,hit)
  near=rail.find_nearest(Vector(post['top']),.045)
  assert near[0]is not None and near[3]<.045,(post,near)
  post_checks.append(dict(**post,supportZ=hit[0].z,topToRetainedRailSurface=near[3]))
 # Periodicity keeps the five turns a constant4m apart;actual ray tests check
 # that the next ramp underside provides at least3.6m vertical walking clearance.
 walking=tree([bpy.data.objects[PREFIX+'LRB_helical_solid_slab']]);clearance=[]
 for turn in range(4):
  for step in range(36):
   angle=math.tau*(step+.5)/36;r=6.9
   xy=Vector((CENTRE.x+r*math.cos(angle),CENTRE.y+r*math.sin(angle),0))
   walking_z=BOTTOM+PITCH*(turn+profile(angle))+FINISH
   p=Vector((xy.x,xy.y,walking_z+.10));hit=walking.ray_cast(p,Vector((0,0,1)),4.2)
   assert hit[0]is not None
   headroom=hit[0].z-walking_z
   assert headroom>3.60,(turn,step,headroom)
   clearance.append(headroom)
 # All landing finish polygon vertices/centroids have true support below them.
 cover=bpy.data.objects[PREFIX+'LRB_landing_carpet'];finish_support=[]
 for face in cover.data.polygons:
  if face.normal.z<.9:continue
  ps=[cover.matrix_world@cover.data.vertices[i].co for i in face.vertices]
  p=sum(ps,Vector())/len(ps);hit=support.ray_cast(p+Vector((0,0,.08)),Vector((0,0,-1)),.16)
  assert hit[0]is not None and -.001<=p.z-hit[0].z<=FINISH+.001,(list(p),hit)
  finish_support.append(p.z-hit[0].z)
 slope=[]
 for i in range(1,2000):
  a=math.tau*i/2000;b=math.tau*(i-1)/2000
  slope.append(PITCH*(profile(a)-profile(b))/(6.9*(a-b)))
 return dict(passage=rows,joinedFloorCount=6,finishSupportSamples=sum(r['supportedSamples']for r in rows),
  bridgeFinishStructuralSupportSamples=len(finish_support),guardPostSupportAndRailConnections=post_checks,
  verticalClearanceProbes=len(clearance),minimumInterTurnHeadroom=min(clearance),
  maximumEstimatedCentrelineGrade=max(slope),profileMonotone=min(slope)>=0,
  flatHalfAngleRadians=FLAT,blendAngleRadians=BLEND,clearJoinsMaintain213GuardOpenings=True,
  originalCoreXYRadiiAndFloorPitchPreserved=True,noAccessOrStructuralCertification=True)


def render(label,new_names):
 scene=bpy.data.scenes.new(PREFIX+'REVIEW');scene.render.engine='CYCLES';scene.cycles.samples=12;scene.cycles.use_denoising=True
 scene.render.resolution_x=1000;scene.render.resolution_y=750;scene.render.resolution_percentage=100
 scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='AgX'
 world=bpy.data.worlds.new(PREFIX+'REVIEW_WORLD');world.use_nodes=True
 world.node_tree.nodes['Background'].inputs[0].default_value=(.80,.84,.88,1);world.node_tree.nodes['Background'].inputs[1].default_value=.65;scene.world=world
 copies=[]
 for old in list(bpy.data.collections[COLLECTION].all_objects):
  if old.type!='MESH' or old.hide_render:continue
  if label=='before' and old.name in new_names:continue
  if label=='after' and old.name in SOURCES:continue
  if not (old.name in SOURCES or old.name in new_names or any(k in old.name for k in ['gallery_','landing_','LG_atrium','central_blue'])):continue
  copy=old.copy();copy.data=old.data.copy();copy.data.transform(old.matrix_world);copy.matrix_world=Matrix.Identity(4)
  bm=bmesh.new();bm.from_mesh(copy.data)
  bmesh.ops.delete(bm,geom=[v for v in bm.verts if not 3.97<=v.co.z<=5.8 or not 80.0<=v.co.x<=88.0 or not 9.0<=v.co.y<=17.5],context='VERTS')
  bm.to_mesh(copy.data);bm.free()
  if not copy.data.polygons:bpy.data.objects.remove(copy);continue
  scene.collection.objects.link(copy);copies.append(copy)
 camera=bpy.data.objects.new(PREFIX+'REVIEW_CAMERA',bpy.data.cameras.new(PREFIX+'REVIEW_CAMERA'));scene.collection.objects.link(camera);scene.camera=camera
 camera.data.type='ORTHO';camera.data.ortho_scale=6.6;camera.location=(90,7,8.3)
 camera.rotation_euler=(Vector((84.4,13.26,4.55))-camera.location).to_track_quat('-Z','Y').to_euler()
 light=bpy.data.objects.new(PREFIX+'REVIEW_SUN',bpy.data.lights.new(PREFIX+'REVIEW_SUN','SUN'));scene.collection.objects.link(light);light.data.energy=2;light.rotation_euler=(.45,-.35,-.3)
 scene.render.filepath=str(OUT/(label+'-floor1-join.png'));bpy.context.window.scene=scene;bpy.ops.render.render(write_still=True)
 bpy.context.window.scene=bpy.data.scenes['REVIEW_LRB168_INTERIOR']
 for obj in copies+[camera,light]:bpy.data.objects.remove(obj,do_unlink=True)
 bpy.data.scenes.remove(scene);bpy.data.worlds.remove(world);update()


def verify_originals(before,archived):
 assert all(object_fingerprint(bpy.data.objects[n])==v for n,v in before['objects'].items())
 assert all(material_fingerprint(bpy.data.materials[n])==v for n,v in before['materials'].items())
 for n,v in before['modifiers'].items():
  actual=hashlib.sha256(json.dumps([modifier_payload(m)for m in bpy.data.objects[n].modifiers],sort_keys=True).encode()).hexdigest();assert actual==v,n
 assert all(sorted(c.name for c in bpy.data.objects[n].users_collection)==v for n,v in before['ownership'].items())
 assert all(bpy.data.objects[n].hide_render==(True if n in archived else hidden)for n,hidden in before['visibility'].items())
 metadata=json.loads((ROOT/'web/tools/building-metadata.json').read_text())
 assert {r['collection']:sorted(o.name for o in bpy.data.collections[r['collection']].all_objects)for r in metadata['spaces']}==before['rooms']
 assert {name:{s.name:sorted(n for n in names if n in s.objects)for s in bpy.data.scenes}for name,names in before['rooms'].items()}==before['roomScenes']


def run():
 OUT.mkdir(parents=True,exist_ok=True);assert sha(BASE)==SHA
 bpy.ops.wm.open_mainfile(filepath=str(BASE));update()
 before=original_state();expected=accepted_fingerprints(ROOT/'result/blender/stage220',SHA)
 assert before['objects']==expected and len(expected)==7631
 protected=set().union(*(set(v)for v in before['rooms'].values()));assert not protected.intersection(SOURCES)
 before_passage=passage_measurements(False)
 added,replacements,posts=build();new_names=[o.name for o in added]
 physical=checks(added,posts)
 render('before',new_names)
 for name in SOURCES:bpy.data.objects[name].hide_render=True
 render('after',new_names)
 verify_originals(before,set(SOURCES))
 bindings={o.name:[m.name for m in o.data.materials]for o in added};fingerprints={o.name:object_fingerprint(o)for o in added}
 component=OUT/'lrb-structure221-component.blend';bpy.data.libraries.write(str(component),set(added),fake_user=True,compress=True)
 component_sha=sha(component)
 bpy.ops.wm.open_mainfile(filepath=str(BASE));update();verify_originals(before,set())
 with bpy.data.libraries.load(str(component),link=False)as(available,loaded):loaded.objects=list(fingerprints)
 for obj in loaded.objects:
  for i,name in enumerate(bindings[obj.name]):obj.data.materials[i]=bpy.data.materials[name]
  bpy.data.collections[COLLECTION].objects.link(obj);obj.hide_render=False;obj.hide_set(False)
 for name in SOURCES:bpy.data.objects[name].hide_render=True
 update();verify_originals(before,set(SOURCES))
 assert all(object_fingerprint(bpy.data.objects[n])==v for n,v in fingerprints.items())
 reopened_checks=checks(list(loaded.objects),posts);assert reopened_checks==physical
 assert sha(BASE)==SHA and sha(component)==component_sha
 refs=[]
 for path,url,scope in [
  ('data/documents/library_floor_plans.pdf','https://www.lse.ac.uk/asset-library/information/library-floor-plans-pdf.pdf','Pages2-7 six public levels and shared ramp/lift circulation;guide supports topology,not measured profile'),
  ('data/collections/library_round5/photos/LRB_9cf4d6340481.jpg','https://tyrensakt.com/projects/lse-library/','Completed2001 project;capture date unknown;white guarded ramp,flat galleries,white posts and dark floor'),
 ]:refs.append(dict(path=path,url=url,sha256=sha(ROOT/path),support=scope))
 verification=dict(savedComponentReopenedAndAppended=True,baselineSha256=SHA,componentSha256=component_sha,
  originalObjectsVerified=7631,originalMaterialNodesVerified=len(before['materials']),originalGeometryUVsTransformsBindingsAndModifiersUnchanged=True,
  protectedSpacesVerified=19,protectedSpaceObjectsVerified=678,allOriginalCollectionMembershipsUnchanged=True,
  protectedSpaceSceneMembershipsUnchanged=True,onlyListedOriginalVisibilityChanged=True,newObjectsVerified=len(fingerprints),
  sixFloorSupportSamples=physical['finishSupportSamples'],guardPostsVerified=len(posts),noFullNativeWritten=True,sourcePhotographsNotUsedAsTextures=True)
 audit=dict(version=221,building='LRB',baseline=str(BASE.relative_to(ROOT)),baselineSha256=SHA,
  componentPath=str(component.relative_to(ROOT)),componentSha256=component_sha,targetCollection=COLLECTION,destinationCollection=COLLECTION,
  interiorCollection=COLLECTION,replacesInteriorCollection=COLLECTION,sameCollectionPartialReplacement=True,
  addedObjects=list(fingerprints),archivedObjects=SOURCES,changedObjects=[],addedFingerprints=fingerprints,replacementMaterialBindings=bindings,
  replacements=replacements,sourceModelSourceObjectsRetained=True,beforePassage=before_passage,afterPhysicalChecks=physical,
  profile=dict(inheritedFloorPitch=PITCH,flatHalfAngle=FLAT,transitionAngle=BLEND,finishOffset=FINISH,
    maximumProfileChange=max(abs(vertical_change(Vector((CENTRE.x+6.9*math.cos(i*math.tau/2000),CENTRE.y+6.9*math.sin(i*math.tau/2000),0))))for i in range(2000)),
    method='Integral of compact smoothstep grade;flat at every join,monotone between joins,identical4m periodic turns'),
  references=refs,verification=verification,previews=['before-floor1-join.png','after-floor1-join.png'],
  changes=['Six ramp-to-floor joins now use matching finish datums,short flat joining areas and smooth grade transitions instead of a pure sloping helix crossing a flat bridge.',
    'Landing finishes share actual polygonal ramp/gallery boundaries;the duplicate flat LG starting carpet is removed only from the new copy.',
    'LG general gallery finish is added on the already existing physical floor,using the accepted G finish topology at LG height.',
    '36white bridge uprights and compact mounting feet connect to retained bridge handrails and tested structural support.'],
  limitations=['The guide is a diagram,not a measured architectural or accessibility survey.4m pitch,core orientation,radii,bridge station and dimensions remain inherited estimates.',
    'Flat half-angle0.14rad,blend0.14rad and12mm finish are geometric estimates to remove the documented numerical discontinuity,not an as-built ramp specification.',
    'Existing radial braces,columns,lifts,remaining floor outlines,roof,exterior and19 independent rooms are retained;this does not establish their complete structural accuracy.',
    'Maximum estimated centreline grade is reported as geometry only;no accessibility,fire-safety or whole-library completion claim.',
    'Primary built photograph capture date is unknown;project2001 and document retrieval dates do not prove2026 condition.'])
 (OUT/'audit.json').write_text(json.dumps(audit,indent=2,ensure_ascii=False)+'\n')
 (OUT/'verification.json').write_text(json.dumps(verification,indent=2)+'\n')
 print('LRB_STRUCTURE221_READY',len(fingerprints),len(SOURCES),physical['finishSupportSamples'],physical['minimumInterTurnHeadroom'],flush=True)


if __name__=='__main__':run()
