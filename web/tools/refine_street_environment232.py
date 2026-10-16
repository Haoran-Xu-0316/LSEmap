"""Replace intersecting triple crown masses at50mapped Lincoln's Inn Fields trees.

Fixed Blender authoring script. No command-line configuration. Existing trunk
positions and per-tree crown envelopes are retained. Crown forms are visual
estimates, not a species inventory or a current canopy survey.
"""
from pathlib import Path
import sys,json,hashlib,math,collections
sys.dont_write_bytecode=True
import bpy,bmesh
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'result/blender/street-environment232';DATA=ROOT/'data/collections/street-environment232'
BASE=ROOT/'result/blender/LSE_campus_detailed_v231.blend'
SHA='667c0d1a8763d1e0ad0d026316ce38186c29678fffecc6b880e29ba3663c88b7'
SOURCE='LANDSCAPE199_Campus_registered_crowns';OWNER='03_PUBLIC_REALM'
RETAINED='SITE232_Campus_crowns_outside_selected_LIF_trees'
CROWNS='SITE232_LIF_fifty_continuous_organic_crowns'
sys.path.insert(0,str(ROOT/'web/tools'))
from refine_plaza_environment231 import state,preserve,solids
from refine_streets230 import components,triangles,triangle_signatures,tree
from integrate_exterior_round194 import object_fingerprint,update_scene

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
def box(o):
 p=[o.matrix_world@Vector(v)for v in o.bound_box];return [Vector([min(v[i]for v in p)for i in range(3)]),Vector([max(v[i]for v in p)for i in range(3)])]
def bounds(points):return Vector([min(v[i]for v in points)for i in range(3)]),Vector([max(v[i]for v in points)for i in range(3)])
def foliage():
 mats=[]
 for i,color in enumerate([(.100,.180,.061),(.126,.216,.077),(.151,.244,.092),(.169,.261,.102)]):
  m=bpy.data.materials.new('SITE232_LIF_opaque_foliage_'+str(i));m.use_nodes=True;m.diffuse_color=(*color,1);p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=m.diffuse_color;p.inputs['Roughness'].default_value=.94;p.inputs['Alpha'].default_value=1;p.inputs['Transmission Weight'].default_value=0
  m['webBaseColor']=list(m.diffuse_color);m['webRoughness']=.94;m['webMetallic']=0.;m['presentationEstimated']=True;mats.append(m)
 return mats

def organic_crowns(source,groups,selected):
 points=[];faces=[];slots=[];checks=[];lon=40;lat=20
 trunk=bpy.data.objects['03_PUBLIC_REALM_Plane_tree_trunk'];trunks=components(trunk)
 for row in selected:
  idx=row['group'];cluster=[groups[3*idx+j]for j in range(3)]
  lobes=[];old=[]
  for g in cluster:
   p=[source.matrix_world@source.data.vertices[v].co for v in g];old.extend(p);low,high=bounds(p);lobes.append(((low+high)/2,(high-low)/2))
  lo,hi=bounds(old);origin=lobes[0][0];seed=idx*2.399963229728653
  vertices=[];directions=[Vector((0,0,-1))]
  for ring in range(1,lat):
   theta=math.pi*ring/lat
   for k in range(lon):
    angle=math.tau*k/lon;directions.append(Vector((math.sin(theta)*math.cos(angle),math.sin(theta)*math.sin(angle),-math.cos(theta))))
  directions.append(Vector((0,0,1)))
  for d in directions:
   roots=[]
   for center,radius in lobes:
    q=origin-center;a=sum((d[j]/radius[j])**2 for j in range(3));b=2*sum(q[j]*d[j]/radius[j]**2 for j in range(3));c=sum((q[j]/radius[j])**2 for j in range(3))-1;disc=b*b-4*a*c
    if disc>=0:roots.append((-b+math.sqrt(disc))/(2*a))
   r=max(roots);theta=math.atan2(d.y,d.x)
   # Coherent broad foliage lobes plus a restrained finer contour. No leaves,
   # intersecting shells, transparency, coincident surfaces or extra tree stems.
   factor=1+.105*math.sin(5*theta+seed)*(.35+.65*(1-d.z*d.z))+.065*math.sin(7*d.z+3*theta-seed)+.035*math.cos(13*theta-5*d.z+seed*.3)
   vertices.append(origin+d*r*factor)
  vlo,vhi=bounds(vertices)
  vertices=[Vector([lo[j]+(v[j]-vlo[j])/(vhi[j]-vlo[j])*(hi[j]-lo[j])for j in range(3)])for v in vertices]
  fs=[]
  for k in range(lon):fs.append((0,1+(k+1)%lon,1+k))
  for ring in range(lat-2):
   a=1+ring*lon;b=a+lon
   for k in range(lon):
    j=(k+1)%lon;fs.extend([(a+k,a+j,b+j),(a+k,b+j,b+k)])
  top=len(vertices)-1;start=1+(lat-2)*lon
  for k in range(lon):fs.append((start+k,start+(k+1)%lon,top))
  start=len(points);points.extend(vertices);faces.extend(tuple(start+v for v in f)for f in fs)
  for f in fs:
   center=sum((vertices[v]for v in f),Vector())/3;d=(center-origin).normalized();field=math.sin(d.x*5+d.y*3+seed)+.45*math.cos(d.z*6-d.y*4+seed)
   slots.append(max(0,min(3,int(1.6+field*.9))))
  current_lo,current_hi=bounds(vertices);assert max(abs(a-b)for aa,bb in [(lo,current_lo),(hi,current_hi)]for a,b in zip(aa,bb))<1e-5
  tp=[trunk.matrix_world@trunk.data.vertices[v].co for v in trunks[idx]];tl,th=bounds(tp);tx,ty=row['center'][:2]
  bt=tree([dict(points=[list(vertices[v])for v in f])for f in fs]);hit=bt.ray_cast(Vector((tx,ty,th.z)),Vector((0,0,-1)),th.z)
  assert hit[0]is not None,(idx,'crown does not meet retained trunk')
  checks.append(dict(trunkGroup=idx,treeXY=[tx,ty],sourceCrownGroups=[3*idx+j for j in range(3)],retainedEnvelope=[list(lo),list(hi)],retainedTrunkTop=th.z,trunkToCrownRayContactZ=hit[0].z,pathClearanceM=lo.z,vertices=len(vertices),triangles=len(fs),dimensionPolicy='Per-tree accepted envelope and mapping retained; organic contour estimated'))
 m=bpy.data.meshes.new(CROWNS);m.from_pydata(points,[],faces);m.update()
 for mat in foliage():m.materials.append(mat)
 for p,slot in zip(m.polygons,slots):p.material_index=slot;p.use_smooth=True
 uv=m.uv_layers.new(name='CrownMetricUV')
 for p in m.polygons:
  for li in p.loop_indices:
   v=m.vertices[m.loops[li].vertex_index].co;uv.data[li].uv=(v.x,v.y)
 o=bpy.data.objects.new(CROWNS,m);bpy.data.collections[OWNER].objects.link(o);o['scope']='50mapped Lincoln\'s Inn Fields trees; replace150intersecting crown lobes with50closed continuous crown forms';o['dimensionsEstimated']=True;o['originalObject']=SOURCE
 return o,checks

def render(source,owned):
 s=bpy.data.scenes['00_CAMPUS_COMPLETE'];bpy.context.window.scene=s
 c=bpy.data.objects.new('STREET232_REVIEW_CAMERA',bpy.data.cameras.new('STREET232_REVIEW_CAMERA'));s.collection.objects.link(c);s.camera=c;c.data.clip_end=1500;c.data.sensor_fit='VERTICAL'
 s.render.engine='BLENDER_EEVEE';s.render.resolution_x=1100;s.render.resolution_y=825;s.render.resolution_percentage=100;s.render.image_settings.file_format='PNG'
 for o in s.objects:
  if o.hide_render:o.hide_set(True)
 active=sorted(o.name for o in s.objects if not o.hide_render and o.name not in [SOURCE,c.name]+[o.name for o in owned])
 views=[dict(name='campus',nativeCamera='01_campus_aerial'),dict(name='LIF-tree-contour',eye=[-84,88,24],target=[-43,142,7],fov=58)]
 for v in views:
  if 'nativeCamera'in v:
   original=bpy.data.objects[v['nativeCamera']];c.matrix_world=original.matrix_world.copy();c.data.lens=original.data.lens;c.data.sensor_fit=original.data.sensor_fit;c.data.sensor_width=original.data.sensor_width;c.data.sensor_height=original.data.sensor_height
  else:
   c.data.sensor_fit='VERTICAL';eye=Vector(v['eye']);target=Vector(v['target']);c.location=eye;c.rotation_euler=(target-eye).to_track_quat('-Z','Y').to_euler();c.data.lens=c.data.sensor_height/(2*math.tan(math.radians(v['fov'])/2))
  for phase in ['before','after']:
   source.hide_render=phase=='after';source.hide_set(phase=='after')
   for o in owned:o.hide_render=phase=='before';o.hide_set(phase=='before')
   update_scene();s.render.filepath=str(OUT/(phase+'-'+v['name']+'.png'));bpy.ops.render.render(write_still=True)
 source.hide_render=False;source.hide_set(False)
 for o in owned:o.hide_render=False;o.hide_set(False)
 bpy.data.objects.remove(c,do_unlink=True);bpy.data.cameras.remove(bpy.data.cameras['STREET232_REVIEW_CAMERA'])
 return views,dict(allAcceptedBuildingsAndCrownsRetained=True,activeContextObjects=len(active),activeContextNamesSha256=hashlib.sha256('\n'.join(active).encode()).hexdigest())

def build():
 OUT.mkdir(parents=True,exist_ok=True);DATA.mkdir(parents=True,exist_ok=True);assert sha(BASE)==SHA
 bpy.ops.wm.open_mainfile(filepath=str(BASE));update_scene();before=state();assert len(before['objects'])==8383
 assert len(before['rooms'])==32 and len(set().union(*(set(v)for v in before['rooms'].values())))==1325
 source=bpy.data.objects[SOURCE];assert not source.hide_render and [c.name for c in source.users_collection]==[OWNER]
 groups=components(source);assert len(groups)==522
 selected=json.loads((DATA/'selected-tree-envelope.json').read_text())['trunks'];assert len(selected)==50
 removed=set(v for r in selected for i in range(3)for v in groups[3*r['group']+i]);retained=set(range(len(source.data.vertices)))-removed;expected=triangle_signatures(source,retained)
 clone=source.copy();clone.data=source.data.copy();clone.name=RETAINED;clone.data.name=RETAINED
 bm=bmesh.new();bm.from_mesh(clone.data);bm.verts.ensure_lookup_table();bmesh.ops.delete(bm,geom=[bm.verts[v]for v in sorted(removed)],context='VERTS');bm.to_mesh(clone.data);bm.free();clone.data.update();bpy.data.collections[OWNER].objects.link(clone);assert triangle_signatures(clone)==expected
 crown,checks=organic_crowns(source,groups,selected);owned=[clone,crown];update_scene();solid=solids(crown);assert len(solid)==50 and all(r['volumeM3']>0 for r in solid)
 # Real triangle collision probes against every active exterior with an overlapping
 # bounding box. Tree-to-tree crown overlap remains ordinary canopy intergrowth.
 cb=box(crown);ct=tree(triangles(crown));collisions=[]
 for o in bpy.data.objects:
  if o.type!='MESH' or o.hide_render or not any(c.name.endswith('_EXTERIOR')for c in o.users_collection):continue
  lo,hi=box(o)
  if any(hi[j]<cb[0][j]or lo[j]>cb[1][j]for j in range(3)):continue
  hits=ct.overlap(tree(triangles(o)));assert not hits,(o.name,len(hits));collisions.append(dict(object=o.name,actualTriangleIntersections=0))
 fingerprints={o.name:object_fingerprint(o)for o in owned};bindings={o.name:[m.name for m in o.data.materials]for o in owned}
 # Imported preserve function uses231's prior BASE; override globals for this fixed baseline.
 preserve.__globals__['BASE']=BASE;preserve.__globals__['SHA']=SHA;preserve(before)
 component=OUT/'component.blend';bpy.data.libraries.write(str(component),set(owned),fake_user=True,compress=True);component_sha=sha(component)
 bpy.ops.wm.open_mainfile(filepath=str(component));assert all(object_fingerprint(bpy.data.objects[n])==v for n,v in fingerprints.items());assert triangle_signatures(bpy.data.objects[RETAINED])==expected
 bpy.ops.wm.open_mainfile(filepath=str(BASE));update_scene()
 with bpy.data.libraries.load(str(component),link=False)as(_,dst):dst.objects=list(fingerprints)
 owned=dst.objects
 for o in owned:
  for i,n in enumerate(bindings[o.name]):
   if n in before['materials']:o.data.materials[i]=bpy.data.materials[n]
  bpy.data.collections[OWNER].objects.link(o)
 update_scene();assert all(object_fingerprint(bpy.data.objects[n])==v for n,v in fingerprints.items());preserve(before)
 views,visibility=render(bpy.data.objects[SOURCE],owned);preserve(before)
 write(OUT/'support-and-solid-proof.json',dict(treeCount=50,removedIntersectingLobes=150,replacementClosedCrowns=50,trees=checks,closedSolids=solid,exteriorCollisions=collisions,allTrunksRetainedExactly=True,walkingSurfacesUnchanged=True,noTransparentMaterials=True,noLooseLeafGeometry=True,retainedUnselectedTrianglesExact=True))
 refs=[dict(path=p,sha256=sha(ROOT/p))for p in ['data/collections/streets/raw/public_realm_strategy_2022.pdf','data/collections/plaza-environment231/official-strategy-existing-watkins.png','data/collections/streets/raw/lse_dtm_1m.tif','data/collections/streets/derived/lidar_metadata.json','data/collections/streets/derived/greenspace.geojson','web/tools/refine_landscape199.py']]
 write(DATA/'sources.json',dict(version=232,sources=refs,sourceDate='Public realm strategy published2022; photograph capture unknown. DTMcomposite2022,exact pixel survey date unresolved. OSMarchive retrieved2026-09-12,park boundary timestamp2026-05-04.',selectedProblem='50existing mapped LIFtrees represented by150intersecting smooth crown masses; replace each triple with one opaque closed organic surface.',registration='OSMway/30613392park polygon selects50native trunk centres. Native trunk group i matches crown groups3i..3i+2. Preserve all accepted per-tree crown envelopes.',watkinsDecision='Current facade planes constrain a12–13mwide plaza and an estimated0.60mdoor-frame landing candidate. Native entrance slab/carpet probes instead returnZ0.32/0.332,so that candidate would create a0.318mstep down into the library. A continuous library-side band would also bury two protected231tree-pool bases. No stairs authored pending coordinated entrance-height/extent resolution; absence of an absolute Newlyn offset alone is not an obstruction.',dtmEvidence='data/collections/street-environment232/dtm-probes.json',crownDimensions='All existing per-tree envelope dimensions retained. Organic contour and opaque foliage colours are presentation estimates; no2026canopy survey or species claim.',noSourcePhotoPixelsReused=True))
 write(OUT/'audit.json',dict(version=232,baselineSha256=SHA,componentPath=str(component.relative_to(ROOT)),componentSha256=component_sha,targetCollection=OWNER,destinationCollection=OWNER,addedObjects=list(fingerprints),archivedObjects=[SOURCE],changedObjects=[],addedFingerprints=fingerprints,replacementMaterialBindings=bindings,originalObject=SOURCE,sourceManifest='data/collections/street-environment232/sources.json',supportProof='result/blender/street-environment232/support-and-solid-proof.json',verification=dict(componentReopened=True,appendedComponentReopened=True,originalGeometryUVsTransformsBindingsNodesModifiersPropsOwnersAndVisibilityPreserved=True,originalObjectsVerified=len(before['objects']),originalMaterialsVerified=len(before['materials']),protectedSpacesVerified=32,protectedRoomObjectsVerified=1325,retainedUnselectedTrianglesExact=True,closedPositiveVolumeNewSolids=50,allOriginalTrunksRetained=True,noPathChange=True,noFullNativeSaved=True),budget=dict(originalSelectedTriangles=48000,replacementSelectedTriangles=76000,triangleDelta=28000,selectedTreeCount=50,drawcallUpperBoundDelta=4,newOpaqueMaterialSlots=4,noPerLeafObjects=True),gallerySuggestions=[dict(code='CAMPUS',name='LIF-tree-contour',label='Lincoln’s Inn Fields树冠',view=dict(position=[-84,24,-88],target=[-43,7,-142],fov=58),suggestedExistingBuildingEntrances=['MAR','SAL'])],records=[dict(name=o.name,vertices=len(o.data.vertices),faces=len(o.data.polygons),triangles=len(triangles(o)))for o in owned],cameras=views,previews=[phase+'-'+v['name']+'.png'for v in views for phase in ['before','after']],productionVisibility=visibility,scope='Replace150intersecting crown masses at50existing Lincoln\'s Inn Fields trees with50continuous opaque organic crowns; preserve per-tree envelope and all remaining geometry.',limitations=['Crown contours and colours are visual estimates,not a measured canopy inventory.','Neighbouring mature trees may naturally intergrow; all mapped positions and original aggregate crown envelopes are retained.','Watkins stair feasibility exposed an existing0.318mentrance-frame/finished-floor discrepancy and potential continuous-platform/two-tree-pool conflict; no stairs or entrance geometry changed.']))
 assert sha(BASE)==SHA and sha(component)==component_sha
 print('STREET_ENVIRONMENT232_COMPLETE',component_sha,flush=True)
if __name__=='__main__':build()
