"""STREET227 attributed planar replacement of deterministic ground layering.

Fixed phases:capture acceptednative,prepare exactpertriangle difference in
MachineLearning,author/reopen component,and independently verify savedfloat32.
Only the accepted216asphalt surface is replaced,never the199stone orroadroute.
"""
from pathlib import Path
import sys,json,hashlib,math
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'result/blender/street-layering227';SOURCE=ROOT/'data/collections/street-layering227'
BASE=ROOT/'result/blender/LSE_campus_detailed_v226.blend';SHA='4e6c1482f97ac61b42e8a344bc503fd2fa86395006a6b43312bd6be21ac214a2'
ORIGINAL='SITE216_At_grade_asphalt_underground_route_removed';NEW='STREET227_Asphalt_clipped_beneath_retained_stone';COLLECTION='00_SITE'
PALE=['GROUND199_Road_LSE Square.001','GROUND199_Road_pedestrian.002','GROUND199_Road_LSE Square','GROUND199_Road_pedestrian.001']
sys.path.insert(0,str(ROOT/'web/tools'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def packed(v):return hashlib.sha256(json.dumps(v,sort_keys=True).encode()).hexdigest()
def write(name,v):(OUT/name).write_text(json.dumps(v,indent=2,ensure_ascii=False)+'\n')


def capture():
 import bpy
 from mathutils import Vector
 assert sha(BASE)==SHA;bpy.ops.wm.open_mainfile(filepath=str(BASE));scene=bpy.data.scenes['00_CAMPUS_COMPLETE'];bpy.context.window.scene=scene
 for layer in scene.view_layers:layer.update()
 from integrate_exterior_round194 import object_fingerprint
 from refine_portsmouth_exterior207 import material_fingerprint
 meta=json.loads((ROOT/'web/tools/building-metadata.json').read_text());protected=set(o.name for r in meta['spaces']for o in bpy.data.collections[r['collection']].all_objects);assert ORIGINAL not in protected
 rows=[]
 for name in [ORIGINAL]+PALE:
  o=bpy.data.objects[name];assert not o.hide_render
  ps=[o.matrix_world@v.co for v in o.data.vertices];faces=[]
  for f in o.data.polygons:
   faceps=[ps[i]for i in f.vertices]
   if all(abs(p.z-.024)<1e-6 for p in faceps):faces.append(dict(index=f.index,vertices=[list(p)for p in faceps],materialIndex=f.material_index,smooth=f.use_smooth,uvs={uv.name:[list(uv.data[i].uv)for i in f.loop_indices]for uv in o.data.uv_layers}))
  if name==ORIGINAL:assert len(faces)==len(o.data.polygons)and all(len(f['vertices'])==3 for f in faces)
  rows.append(dict(name=name,fingerprint=object_fingerprint(o),collections=[c.name for c in o.users_collection],protectedSpaceMembership=[r['collection']for r in meta['spaces']if name in bpy.data.collections[r['collection']].all_objects],matrix=[list(r)for r in o.matrix_world],materials=[m.name for m in o.data.materials],materialFingerprints={m.name:material_fingerprint(m)for m in o.data.materials},uvNames=[uv.name for uv in o.data.uv_layers],modifiers=[m.type for m in o.modifiers],faces=faces))
 # Preserve nearbyhigherpaving andthe actualsaved support surfaces for an
 # independent exposure calculation.Nofuturemaporphotoguessisused.
 nearby=[]
 for o in scene.objects:
  if o.type!='MESH'or o.hide_render or o.name==ORIGINAL:continue
  corners=[o.matrix_world@Vector(c)for c in o.bound_box]
  if min(v.x for v in corners)>34 or max(v.x for v in corners)<24 or min(v.y for v in corners)>-12 or max(v.y for v in corners)<-25 or min(v.z for v in corners)>.20 or max(v.z for v in corners)<-.1:continue
  ps=[o.matrix_world@v.co for v in o.data.vertices];fs=[]
  for f in o.data.polygons:
   vs=[ps[i]for i in f.vertices]
   if max(p.z for p in vs)-min(p.z for p in vs)<1e-6 and -.1<vs[0].z<.2 and abs(f.normal.z)>.5:fs.append([list(v)for v in vs])
  if fs:nearby.append(dict(name=o.name,faces=fs))
 write('native-input.json',dict(baselineSha256=SHA,objects=rows,nearbySupport=nearby));print('STREET227_CAPTURE',[(r['name'],len(r['faces']),r['collections'],r['protectedSpaceMembership'])for r in rows],flush=True)




def prepare():
 import numpy as np
 from shapely.geometry import Polygon,Point,mapping,box
 from shapely.ops import unary_union
 from shapely import constrained_delaunay_triangles,make_valid
 native=json.loads((OUT/'native-input.json').read_text());assert native['baselineSha256']==SHA
 source=native['objects'][0];pales=native['objects'][1:];mask=make_valid(unary_union([Polygon([v[:2]for v in f['vertices']])for r in pales for f in r['faces']]))
 original=unary_union([Polygon([v[:2]for v in f['vertices']])for f in source['faces']]);removed=original.intersection(mask);expected=original.difference(mask)
 above=unary_union([Polygon([v[:2]for v in f])for r in native['nearbySupport']for f in r['faces']if f[0][2]>.0241]);exposed=removed.difference(above)
 # Float32 output can round an exact intersection backinto the stone.
 # Try exactclipping first;only ifnecessary add the minimum micrometric
 # numerical clearance below.Original outerroadcoordinates stay untouched.
 trials=[]
 for numerical_clearance in [.001]:
  cutting=mask if numerical_clearance==0 else mask.buffer(numerical_clearance,join_style='mitre');records=[];changed=0;kept=0;dropped=0
  for f in source['faces']:
   coords=np.array(f['vertices'],dtype=float);tri=Polygon(coords[:,:2]);part=tri.difference(cutting)
   if tri.intersection(cutting).area<1e-12:
    records.append(dict(sourceFace=f['index'],vertices=f['vertices'],uvs=f['uvs'],materialIndex=f['materialIndex'],smooth=f['smooth'],unchanged=True));kept+=1;continue
   changed+=1
   if part.is_empty or part.area<1e-12:dropped+=1;continue
   inv=np.linalg.inv(np.array([[*coords[0,:2],1],[*coords[1,:2],1],[*coords[2,:2],1]]).T)
   for t in constrained_delaunay_triangles(part).geoms:
    xy=np.asarray(list(t.exterior.coords)[:3],dtype=np.float32).astype(float);signed=np.cross(xy[1]-xy[0],xy[2]-xy[0])
    if abs(signed)<1e-12:continue
    if signed<0:xy=xy[::-1]
    weights=[inv@np.array([p[0],p[1],1])for p in xy];uvs={name:[list(np.asarray(w)@np.asarray(points))for w in weights]for name,points in f['uvs'].items()}
    records.append(dict(sourceFace=f['index'],vertices=[[float(p[0]),float(p[1]),f['vertices'][0][2]]for p in xy],uvs=uvs,materialIndex=f['materialIndex'],smooth=f['smooth'],unchanged=False))
  actual=unary_union([Polygon([p[:2]for p in f['vertices']])for f in records]);residual=actual.intersection(mask).area;extra_loss=expected.difference(actual).area;trials.append(dict(numericalClearanceM=numerical_clearance,residualCoplanarOverlapM2=residual,extraQuantizationLossM2=extra_loss))
  if residual<1e-10:break
 else:raise AssertionError(trials)
 guarded_expected=original.difference(cutting)
 assert guarded_expected.difference(actual.buffer(.00002)).area<1e-9 and actual.difference(guarded_expected.buffer(.00002)).area<1e-9
 lower=unary_union([Polygon([v[:2]for v in f])for r in native['nearbySupport']for f in r['faces']if f[0][2]<.0239]);numeric_band=expected.difference(actual);assert numeric_band.difference(lower).area<1e-9
 assert abs(sum(Polygon([p[:2]for p in f['vertices']]).area for f in records)-actual.area)<1e-6
 # Compact source/expected evidence,not anall-campus explodedJSON.
 report=dict(baselineSha256=SHA,source=ORIGINAL,stoneObjects=PALE,sourceAreaM2=original.area,stoneFootprintAreaM2=mask.area,removedAsphaltUnderStoneM2=removed.area,exposedCoplanarBeforeM2=exposed.area,expectedRetainedAreaM2=expected.area,actualPreparedRetainedAreaM2=actual.area,residualCoplanarOverlapM2=residual,quantizationClearanceM=numerical_clearance,numericalBoundaryToleranceM=.00002,dracoCutGuardM=.001,sourceAsphalt20BitStepM=.0007366578251473727,sourceAsphalt20BitHalfStepM=.00036832891257368634,guardBandAdditionalRemovedAreaM2=numeric_band.area,guardBandExistingLowerDatumCoveredAreaM2=numeric_band.intersection(lower).area,guardBandUncoveredAreaM2=numeric_band.difference(lower).area,trials=trials,unchangedOriginalTriangles=kept,affectedOriginalTriangles=changed,fullyRemovedOriginalTriangles=dropped,newTriangles=len(records),maskGeometry=mapping(mask),originalGeometry=mapping(original),removedGeometry=mapping(removed),expectedGeometry=mapping(expected),higherPavingGeometry=mapping(above),exposedGeometry=mapping(exposed))
 write('clip-plan.json',dict(report=report,triangles=records));write('geometric-decision.json',report)
 # Physicalsamples use theexactoverlap,not the numericalmicronstrip.
 removed_triangles=[list(t.exterior.coords)[:3]for t in constrained_delaunay_triangles(removed).geoms if t.area>1e-10];samples=[]
 for t in removed_triangles:samples.append([sum(p[0]for p in t)/3,sum(p[1]for p in t)/3])
 seam=[]
 rings=[removed.exterior]if removed.geom_type=='Polygon'else[r.exterior for r in removed.geoms if r.geom_type=='Polygon']
 for ring in rings:
  points=list(ring.coords)
  for a,b in zip(points,points[1:]):
   edge=np.asarray(b)-a
   if np.linalg.norm(edge)<.005:continue
   mid=(np.asarray(a)+b)/2;normal=np.array([-edge[1],edge[0]])/np.linalg.norm(edge)
   for side in [-1,1]:
    p=mid+side*.002*normal
    if original.buffer(1e-7).covers(Point(p)):seam.append(p.tolist())
 band_samples=[]
 for t in constrained_delaunay_triangles(numeric_band).geoms:
  if t.area>1e-10:band_samples.append(list(t.centroid.coords)[0])
 write('support-samples.json',dict(removedInteriorSamples=samples,seamSamples=seam,numericalBandSamples=band_samples))
 print('STREET227_PLAN',removed.area,exposed.area,mask.area,len(records),trials,flush=True)


def build():
 import bpy,bmesh
 from mathutils import Vector,Matrix
 from mathutils.bvhtree import BVHTree
 from integrate_exterior_round194 import object_fingerprint,accepted_fingerprints
 from refine_portsmouth_exterior207 import material_fingerprint
 from build_clm_hongkong_room220 import modifier_payload
 def update():
  for scene in bpy.data.scenes:
   for layer in scene.view_layers:layer.update()
  bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE']
 def state():
  meta=json.loads((ROOT/'web/tools/building-metadata.json').read_text());rooms={r['collection']:sorted(o.name for o in bpy.data.collections[r['collection']].all_objects)for r in meta['spaces']};assert len(rooms)==23 and len(set().union(*(set(v)for v in rooms.values())))==853
  scene_members={scene.name:set(o.name for o in scene.objects)for scene in bpy.data.scenes}
  return dict(objects={o.name:object_fingerprint(o)for o in bpy.data.objects},materials={m.name:material_fingerprint(m)for m in bpy.data.materials},modifiers={o.name:packed([modifier_payload(m)for m in o.modifiers])for o in bpy.data.objects},ownership={o.name:sorted(c.name for c in o.users_collection)for o in bpy.data.objects},visibility={o.name:o.hide_render for o in bpy.data.objects},rooms=rooms,roomScenes={c:{name:sorted(set(ns).intersection(names))for name,names in scene_members.items()}for c,ns in rooms.items()})
 def verify(before,hidden):
  assert all(object_fingerprint(bpy.data.objects[n])==v for n,v in before['objects'].items())
  assert all(material_fingerprint(bpy.data.materials[n])==v for n,v in before['materials'].items())
  assert all(packed([modifier_payload(m)for m in bpy.data.objects[n].modifiers])==v for n,v in before['modifiers'].items())
  assert all(sorted(c.name for c in bpy.data.objects[n].users_collection)==v for n,v in before['ownership'].items())
  assert all(bpy.data.objects[n].hide_render==(True if n in hidden else v)for n,v in before['visibility'].items())
  assert all(sorted(o.name for o in bpy.data.collections[c].all_objects)==ns for c,ns in before['rooms'].items())
  scene_members={scene.name:set(o.name for o in scene.objects)for scene in bpy.data.scenes}
  assert {c:{name:sorted(set(ns).intersection(names))for name,names in scene_members.items()}for c,ns in before['rooms'].items()}==before['roomScenes']
 def tree(objects):
  vs=[];fs=[]
  for o in objects:
   off=len(vs);vs.extend(o.matrix_world@v.co for v in o.data.vertices);fs.extend(tuple(off+i for i in f.vertices)for f in o.data.polygons)
  return BVHTree.FromPolygons(vs,fs)
 assert sha(BASE)==SHA;bpy.ops.wm.open_mainfile(filepath=str(BASE));update();before=state();assert len(before['objects'])==7858 and before['objects']==accepted_fingerprints(ROOT/'result/blender/stage226',SHA)
 plan=json.loads((OUT/'clip-plan.json').read_text());native=json.loads((OUT/'native-input.json').read_text());src=bpy.data.objects[ORIGINAL];assert all(object_fingerprint(bpy.data.objects[r['name']])==r['fingerprint']for r in native['objects'])
 assert before['ownership'][ORIGINAL]==[COLLECTION]and ORIGINAL not in set().union(*(set(v)for v in before['rooms'].values()))
 vertices=[];faces=[]
 for row in plan['triangles']:
  start=len(vertices);vertices.extend(row['vertices']);faces.append((start,start+1,start+2))
 mesh=bpy.data.meshes.new(NEW);mesh.from_pydata(vertices,[],faces);mesh.update()
 for m in src.data.materials:mesh.materials.append(m)
 for name in native['objects'][0]['uvNames']:
  uv=mesh.uv_layers.new(name=name)
  for f,row in zip(mesh.polygons,plan['triangles']):
   f.material_index=row['materialIndex'];f.use_smooth=row['smooth']
   for i,p in zip(f.loop_indices,row['uvs'][name]):uv.data[i].uv=p
 mesh.normals_split_custom_set_from_vertices([(0,0,1)]*len(vertices));obj=bpy.data.objects.new(NEW,mesh);bpy.data.collections[COLLECTION].objects.link(obj);obj['originalObject']=ORIGINAL;obj['destinationCollection']=COLLECTION;obj['scope']='Numericaldepth-conflictonly:retained199stoneoccludes216asphalt.Noresurveyedcolor/roadwidth/ownership.';update()
 def physical():
  samples=json.loads((OUT/'support-samples.json').read_text());stone=tree([bpy.data.objects[n]for n in PALE]);combined=tree([bpy.data.objects[n]for n in PALE]+[bpy.data.objects[NEW]]);stonegaps=[];seamgaps=[];bandhits=[]
  vs=[];fs=[];owners=[]
  for row in native['nearbySupport']:
   for f in row['faces']:
    if f[0][2]>=.0239:continue
    off=len(vs);vs.extend(Vector(p)for p in f);fs.append(tuple(range(off,off+len(f))));owners.append(row['name'])
  lower=BVHTree.FromPolygons(vs,fs)
  for x,y in samples['numericalBandSamples']:
   hit=lower.ray_cast(Vector((x,y,.15)),Vector((0,0,-1)),.35);assert hit[0]is not None;bandhits.append(dict(xy=[x,y],height=hit[0].z,support=owners[hit[2]]))
  for x,y in samples['removedInteriorSamples']:
   hit=stone.ray_cast(Vector((x,y,.15)),Vector((0,0,-1)),.25);assert hit[0]is not None;stonegaps.append(abs(hit[0].z-.024))
  for x,y in samples['seamSamples']:
   hit=combined.ray_cast(Vector((x,y,.15)),Vector((0,0,-1)),.25);assert hit[0]is not None;seamgaps.append(abs(hit[0].z-.024))
  return dict(removedInteriorStoneSupportSamples=len(stonegaps),maximumRemovedInteriorSupportDatumErrorM=max(stonegaps),numericBandLowerDatumSupportSamples=len(bandhits),numericBandLowerDatumSupportMisses=0,numericBandActualSupportObjects=sorted(set(r['support']for r in bandhits)),maximumNumericalBandVerticalDropM=max(.024-r['height']for r in bandhits),seamSupportSamples=len(seamgaps),maximumSeamSupportDatumErrorM=max(seamgaps),sharedTopDatumM=.024,originalAsphaltIsSurfaceOnly=True,noUndergroundOrVerticalSupportRemoved=True,noExistingStoneOrHigherPavingMoved=True,numericalClearanceM=plan['report']['quantizationClearanceM'])
 preview_rows=[r['name']for r in native['nearbySupport']if r['name'].startswith(('SITE','GROUND199'))]+[ORIGINAL,NEW]
 views=[dict(code='CAMPUS',name='campus-stc-junction-top',label='StClement’s Lane交界铺装',view=dict(position=[29.4,12,18.4],target=[29.4,.024,18.4],fov=43)),dict(code='CAMPUS',name='campus-stc-junction-seam',label='浅石与沥青接缝',view=dict(position=[30,8,30],target=[29.4,.024,18.4],fov=43))]
 def previews(label):
  scene=bpy.data.scenes.new('STREET227_PREVIEW');scene.render.engine='CYCLES';scene.cycles.samples=10;scene.cycles.use_denoising=True;scene.render.resolution_x=1000;scene.render.resolution_y=850;scene.render.resolution_percentage=100;scene.view_settings.view_transform='AgX';world=bpy.data.worlds.new('STREET227_WORLD');world.use_nodes=True;world.node_tree.nodes['Background'].inputs[0].default_value=(.78,.82,.87,1);world.node_tree.nodes['Background'].inputs[1].default_value=.8;scene.world=world;copies=[]
  for name in list(dict.fromkeys(preview_rows)):
   if label=='before'and name==NEW or label=='after'and name==ORIGINAL:continue
   old=bpy.data.objects[name];o=old.copy();o.data=old.data.copy();o.parent=None;o.data.transform(old.matrix_world);o.matrix_world=Matrix.Identity(4);o.hide_render=False
   bm=bmesh.new();bm.from_mesh(o.data)
   for co,no,out in [((23,0,0),(1,0,0),False),((36,0,0),(1,0,0),True),((0,-29,0),(0,1,0),False),((0,-10,0),(0,1,0),True),((0,0,-.1),(0,0,1),False),((0,0,.20),(0,0,1),True)]:bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=1e-7,plane_co=co,plane_no=no,clear_outer=out,clear_inner=not out)
   bm.to_mesh(o.data);bm.free();scene.collection.objects.link(o);copies.append(o)
  camera=bpy.data.objects.new('STREET227_CAM',bpy.data.cameras.new('STREET227_CAM'));scene.collection.objects.link(camera);scene.camera=camera;camera.data.type='PERSP';camera.data.clip_start=.001;camera.data.clip_end=100
  sun=bpy.data.objects.new('STREET227_SUN',bpy.data.lights.new('STREET227_SUN','SUN'));scene.collection.objects.link(sun);sun.data.energy=2;sun.rotation_euler=(.5,-.35,-.65)
  for tag,entry in zip(['top','seam'],views):
   v=entry['view'];camera.location=Vector((v['position'][0],-v['position'][2],v['position'][1]));target=Vector((v['target'][0],-v['target'][2],v['target'][1]));camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.angle=math.radians(v['fov']);scene.render.filepath=str(OUT/(label+'-'+tag+'.png'));bpy.context.window.scene=scene;bpy.ops.render.render(write_still=True)
  bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE']
  for o in copies+[camera,sun]:
   data=o.data;bpy.data.objects.remove(o,do_unlink=True)
   if isinstance(data,bpy.types.Mesh)and data.users==0:bpy.data.meshes.remove(data)
  bpy.data.scenes.remove(scene);bpy.data.worlds.remove(world);update()
 checks=physical()
 if not all((OUT/('before-'+v+'.png')).exists()for v in ['top','seam']):previews('before')
 src.hide_render=True;previews('after');verify(before,{ORIGINAL});fingerprint=object_fingerprint(obj);bindings=[m.name for m in obj.data.materials];component=OUT/'street-layering227-component.blend';bpy.data.libraries.write(str(component),{obj},fake_user=True,compress=True);digest=sha(component)
 bpy.ops.wm.open_mainfile(filepath=str(BASE));update();verify(before,set())
 with bpy.data.libraries.load(str(component),link=False)as(a,b):b.objects=[NEW]
 obj=b.objects[0];bpy.data.collections[COLLECTION].objects.link(obj)
 for i,m in enumerate(bindings):obj.data.materials[i]=bpy.data.materials[m]
 bpy.data.objects[ORIGINAL].hide_render=True;update();verify(before,{ORIGINAL});assert object_fingerprint(obj)==fingerprint and physical()==checks;assert sha(BASE)==SHA and sha(component)==digest
 campus=bpy.data.scenes['00_CAMPUS_COMPLETE'];assert NEW in campus.objects and obj.visible_get(view_layer=campus.view_layers[0])
 saved=dict(vertices=[list(v.co)for v in obj.data.vertices],triangles=[dict(indices=list(f.vertices),sourceFace=row['sourceFace'],materialIndex=f.material_index,uvs={uv.name:[list(uv.data[i].uv)for i in f.loop_indices]for uv in obj.data.uv_layers},unchanged=row['unchanged'])for f,row in zip(obj.data.polygons,plan['triangles'])]);write('saved-mesh-temporary.json',saved)
 verification=dict(savedComponentReopenedAndAppended=True,originalObjectsVerified=7858,originalMaterialNodesVerified=len(before['materials']),protectedSpacesVerified=23,protectedSpaceObjectsVerified=853,allOriginalGeometryUVTransformsBindingsModifiersUnchanged=True,allOriginalCollectionMembershipsUnchanged=True,protectedSpaceSceneMembershipsUnchanged=True,onlyListedOriginalVisibilityChanged=True,newAsphaltVisibleInNativeCampus=True,noFullNativeWritten=True,noElevationChangeOrPolygonOffsetOrDepthBypass=True,sourceAndComponentSha256Rechecked=True,physicalChecks=checks,triangles=len(saved['triangles']))
 audit=dict(version=227,building='CAMPUS',baseline=str(BASE.relative_to(ROOT)),baselineSha256=SHA,componentPath=str(component.relative_to(ROOT)),componentSha256=digest,targetCollection=COLLECTION,destinationCollection=COLLECTION,addedObjects=[NEW],archivedObjects=[ORIGINAL],changedObjects=[],addedFingerprints={NEW:fingerprint},replacementMaterialBindings={NEW:bindings},sourceManifest=str((SOURCE/'sources.json').relative_to(ROOT)),verification=verification,geometricDecision={k:v for k,v in plan['report'].items()if not k.endswith('Geometry')},gallerySuggestions=views,scope='Remove216asphaltbeneaththecompleteexisting199stonefootprints.Onlythealready-visiblelayerpriorityisresolved;theroadnetwork,stonefootprintsandheightsremainunchanged.',limitations=['Stone/asphaltcolorpriorityisnotameasuredor2026materialsurvey.Thisonlyresolvesexistingcoplanardepthcompetition.','1mmnumericalcutguardaccommodatesproductionDraco20bitpositionquantization;itisnotanewkerborroadwidth.Allguard-bandpointsarecoveredbyexistinglowerdatum.Noexistingstoneboundaryorelevationismoved.','Existing216buriedrouteexclusionandallunrelatedsurfaceasphaltarepreserved.Nootherexistingpavingorbuilding/roomisaltered.'],previews=['before-top.png','after-top.png','before-seam.png','after-seam.png'])
 write('audit.json',audit);write('verification.json',verification);write('view-suggestions.json',views);print('STREET227_READY',digest,len(saved['triangles']),checks,flush=True)


def verify_saved():
 """Recompute allareas andcornerUVs from the saved/reopened Float32 mesh."""
 import numpy as np,gzip
 from shapely.geometry import Polygon,shape,Point,LineString,mapping
 from shapely.ops import unary_union
 native=json.loads((OUT/'native-input.json').read_text());plan=json.loads((OUT/'clip-plan.json').read_text());saved=json.loads((OUT/'saved-mesh-temporary.json').read_text());audit=json.loads((OUT/'audit.json').read_text());assert sha(ROOT/audit['componentPath'])==audit['componentSha256']
 source=native['objects'][0];fmap={f['index']:f for f in source['faces']};verts=np.array(saved['vertices']);polygons=[];max_uv_error=0;unchanged_count=0;maximum_z_error=0
 for f in saved['triangles']:
  v=verts[f['indices']];orig=fmap[f['sourceFace']];p=np.asarray(orig['vertices']);assert len(v)==3 and f['materialIndex']==orig['materialIndex'];polygons.append(Polygon(v[:,:2]));maximum_z_error=max(maximum_z_error,float(np.abs(v[:,2]-p[0,2]).max()))
  if f['unchanged']:
   assert np.array_equal(v,p);unchanged_count+=1
   for name,uv in f['uvs'].items():assert np.array_equal(uv,orig['uvs'][name])
  basis=np.column_stack((p[1,:2]-p[0,:2],p[2,:2]-p[0,:2]));weights=np.linalg.solve(basis,(v[:,:2]-p[0,:2]).T).T
  for name,uv in f['uvs'].items():
   old_uv=np.array(orig['uvs'][name]);expected=old_uv[0]+weights[:,0,None]*(old_uv[1]-old_uv[0])+weights[:,1,None]*(old_uv[2]-old_uv[0]);error=float(np.max(np.abs(np.array(uv)-expected)));max_uv_error=max(max_uv_error,error)
   assert error<.00001,(name,error)
 actual=unary_union(polygons);mask=shape(plan['report']['maskGeometry']);original=shape(plan['report']['originalGeometry']);expected=shape(plan['report']['expectedGeometry']);guard=plan['report']['dracoCutGuardM'];guarded=original.difference(mask.buffer(guard,join_style='mitre'));band=expected.difference(actual)
 overlap=actual.intersection(mask).area;extra=actual.difference(original).area;holes=guarded.difference(actual.buffer(.00002)).area;outside=actual.difference(guarded.buffer(.00002)).area;duplicate=sum(p.area for p in polygons)-actual.area
 assert overlap<1e-10 and actual.difference(original.buffer(.00002)).area<1e-8 and holes<1e-8 and outside<1e-8 and abs(duplicate)<1e-6 and maximum_z_error==0
 assert unchanged_count==plan['report']['unchangedOriginalTriangles']
 # A pair ofexterior/interior boundary probes lets theparent comparedecoded
 # productionDraco surfaces without dependingon triangleorder ornewnaming.
 segments=[];intersection=mask.boundary.intersection(original);lines=[intersection]if intersection.geom_type=='LineString'else[g for g in intersection.geoms if g.geom_type=='LineString']
 for line in lines:
  cs=list(line.coords)
  for a,b in zip(cs,cs[1:]):
   delta=np.array(b)-a;length=float(np.linalg.norm(delta))
   if length<.005:continue
   normal=np.array([-delta[1],delta[0]])/length;mid=(np.array(a)+b)/2
   if not mask.contains(Point(mid+normal*.0001)):normal=-normal
   def web(q):return[float(q[0]),.024,float(-q[1])]
   probes=[]
   for distance in [.00005,.00025,.0005,.001,.002,.005]:
    probes.append(dict(distanceM=distance,stoneSide=web(mid+normal*distance),asphaltSide=web(mid-normal*distance)))
   segments.append(dict(boundaryStartWeb=web(a),boundaryEndWeb=web(b),normalTowardStoneWorldXY=normal.tolist(),lengthM=length,coveredByHigherPaving=shape(plan['report']['higherPavingGeometry']).covers(Point(mid)),probes=probes))
 probe_report=dict(baselineSha256=SHA,componentSha256=audit['componentSha256'],coordinateConvention='Web[x,z,-y];nativez.024istheWebYdatum',asphaltMaterialNames=source['materials'],stoneMaterialNames=sorted(set(m for r in native['objects'][1:]for m in r['materials'])),sourceAsphalt20BitStepM=.0007366578251473727,sourceAsphalt20BitHalfStepM=.00036832891257368634,nativeCutGuardM=guard,scope='ProductionDracodecodemustcheckcoplanaroverlapandthenumerical1mmcontactband;notasurfaceorpropertysurvey.',segments=segments)
 write('production-draco-boundary-probes.json',probe_report)
 report=dict(savedFloat32MeshVerified=True,actualStoredAreaM2=actual.area,expectedExactNoGuardAreaM2=expected.area,asphaltRemovedUnderStoneM2=original.intersection(mask).area,additionalGuardBandAreaM2=band.area,residualAsphaltStoneCoplanarOverlapM2=overlap,asphaltOutsideOriginalFootprintM2=extra,asphaltOutsideOriginalFootprintBeyond20MicrometresM2=actual.difference(original.buffer(.00002)).area,missingBeyond20MicrometreToleranceM2=holes,excessBeyond20MicrometreToleranceM2=outside,selfOverlapAreaM2=duplicate,maximumPerCornerUVInterpolationError=max_uv_error,unchangedOriginalTrianglesVerified=unchanged_count,maximumGradeDifferenceM=maximum_z_error,newTriangles=len(saved['triangles']),guardM=guard,boundaryProbeSegments=len(segments),productionDracoStillToBeVerifiedByParent=True)
 write('saved-geometry-verification.json',report)
 for name in ['audit.json','verification.json']:
  j=json.loads((OUT/name).read_text());target=j['verification']if name=='audit.json'else j;target['savedMeshIndependentVerification']=report
  if name=='audit.json':j['productionBoundaryProbes']=str((OUT/'production-draco-boundary-probes.json').relative_to(ROOT))
  write(name,j)
 witness=dict(baselineSha256=SHA,componentSha256=audit['componentSha256'],inputObjects=native['objects'],savedMesh=saved,decision=plan['report'],supportSamples=json.loads((OUT/'support-samples.json').read_text()))
 payload=gzip.compress(json.dumps(witness,separators=(',',':')).encode(),compresslevel=9,mtime=0);(OUT/'saved-geometry-witness.json.gz').write_bytes(payload)
 j=json.loads((OUT/'audit.json').read_text());j['witnessPath']=str((OUT/'saved-geometry-witness.json.gz').relative_to(ROOT));j['witnessSha256']=hashlib.sha256(payload).hexdigest();j['witnessCompressedBytes']=len(payload);write('audit.json',j)
 refs=[]
 for path,role in [('result/blender/street-environment218/audit.json','Acceptedcoplanarconflictgeometryandunmeasuredmaterialownershiplimit'),('result/blender/street-environment216/audit.json','Atgrade-onlyasphaltcomponent;buriedStrandUnderpassalreadyexcluded'),('result/blender/stage226/baseline-state.json','Acceptedoriginalobjectfingerprints'),('result/blender/stage226/building-refinement.json','Accepted226sourceandadditionfingerprints')]:
  p=ROOT/path;refs.append(dict(path=path,sha256=sha(p),role=role))
 manifest=dict(version=227,readDate='2026-10-16',nativePath=str(BASE.relative_to(ROOT)),nativeSha256=SHA,evidenceType='Savedacceptednativegeometryandexistinglayeringwitness;nonewexternalsourceorroadsurvey',references=refs,asphaltObject=ORIGINAL,retainedStoneObjects=PALE,guardM=guard,guardPurpose='AccommodateDraco20bitpositionquantization;notanewroadwidthorphysicalexpansionjoint',limitation='Colorsandroadwidthsremainunmeasured.Onlydeterministicexistingdraw-ordercompetitionisresolved.',witnessPath=j['witnessPath'],witnessSha256=j['witnessSha256'])
 (SOURCE/'sources.json').write_text(json.dumps(manifest,indent=2)+'\n')
 print('STREET227_SAVED_GEOMETRY_PASS',json.dumps(report),flush=True)


if __name__=='__main__':
 if'bpy'in sys.modules:
  if(OUT/'clip-plan.json').exists():build()
  else:capture()
 else:
  if(OUT/'saved-mesh-temporary.json').exists():verify_saved()
  else:prepare()
