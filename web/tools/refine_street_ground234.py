"""Fixed diagnosis and bounded deduplication of233campus exterior ground.

Native positive-area coplanar duplication is the evidence for this component.
No perceptible flicker improvement is claimed.
Use existing Blender and MachineLearning Python; no command-line configuration.
"""
from pathlib import Path
import hashlib,json,sys,math
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'result/blender/street-ground234';DATA=ROOT/'data/collections/street-ground234'
BASE=ROOT/'result/blender/LSE_campus_detailed_v233.blend';SHA='b1d01b4b74a7f9e33d9bab25e73f51f39361659b9236ca98c34056137d8b6660'
ROI=(-95,-150,115,85)
sys.path.insert(0,str(ROOT/'web/tools'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
def capture():
 import bpy
 from mathutils import Vector
 from integrate_exterior_round194 import update_scene,object_fingerprint
 assert sha(BASE)==SHA
 OUT.mkdir(parents=True,exist_ok=True);DATA.mkdir(parents=True,exist_ok=True)
 bpy.ops.wm.open_mainfile(filepath=str(BASE));update_scene();s=bpy.data.scenes['00_CAMPUS_COMPLETE'];rows=[];entry=[]
 for o in s.objects:
  if o.type!='MESH' or o.hide_render:continue
  p=[o.matrix_world@Vector(v)for v in o.bound_box];lo=[min(v[i]for v in p)for i in range(3)];hi=[max(v[i]for v in p)for i in range(3)]
  if lo[0]>ROI[2]or hi[0]<ROI[0]or lo[1]>ROI[3]or hi[1]<ROI[1]or lo[2]>1.5 or hi[2]<-.1:continue
  names=[m.name if m else None for m in o.data.materials];faces=[]
  if not any(c.name in ['00_SITE','03_PUBLIC_REALM']for c in o.users_collection):
   if any(k in o.name.lower()for k in ['step','stair','landing','floor','threshold','entrance','approach','ramp']):entry.append(dict(name=o.name,lo=lo,hi=hi,materials=names,owners=[c.name for c in o.users_collection]))
   continue
  for f in o.data.polygons:
   pp=[o.matrix_world@o.data.vertices[i].co for i in f.vertices]
   if min(v.z for v in pp)<-.1 or max(v.z for v in pp)>1.5 or max(v.z for v in pp)-min(v.z for v in pp)>1e-5:continue
   if min(v.x for v in pp)>ROI[2]or max(v.x for v in pp)<ROI[0]or min(v.y for v in pp)>ROI[3]or max(v.y for v in pp)<ROI[1]:continue
   normal=o.matrix_world.to_3x3().inverted().transposed()@f.normal
   if normal.z<.5 or len(pp)>100:continue
   area=sum(a.x*b.y-b.x*a.y for a,b in zip(pp,pp[1:]+pp[:1]))/2
   if abs(area)<1e-8:continue
   faces.append(dict(index=f.index,points=[list(v)for v in pp],z=pp[0].z,material=names[f.material_index]if names else None,area=abs(area)))
  if faces:rows.append(dict(name=o.name,lo=lo,hi=hi,owners=[c.name for c in o.users_collection],fingerprint=object_fingerprint(o),materials=names,faces=faces))
 write(OUT/'native-surfaces.json',dict(baselineSha256=SHA,objects=rows,entries=entry,roi=ROI,originalObjects=len(bpy.data.objects)))
 print('GROUND234_CAPTURE',len(rows),sum(len(r['faces'])for r in rows),len(entry),flush=True)
 # Review full context, including the current buildings and every accepted tree.
 c=bpy.data.objects.new('GROUND234_DIAGNOSIS_CAMERA',bpy.data.cameras.new('GROUND234_DIAGNOSIS_CAMERA'));s.collection.objects.link(c);s.camera=c;c.data.clip_end=1400;c.data.sensor_fit='VERTICAL'
 s.render.engine='BLENDER_EEVEE';s.render.resolution_x=1000;s.render.resolution_y=750;s.render.resolution_percentage=100;s.render.image_settings.file_format='PNG'
 for o in s.objects:
  if o.hide_render:o.hide_set(True)
 views=[dict(name='sheffield-ground',eye=[-50,-32,10],target=[-53,8,.3],fov=56),dict(name='houghton-ground',eye=[-7,-101,5],target=[10,-62,.3],fov=56),dict(name='portugal-ground',eye=[-2,16,9],target=[49,37,.1],fov=62)]
 for v in views:
  eye=Vector(v['eye']);target=Vector(v['target']);c.location=eye;c.rotation_euler=(target-eye).to_track_quat('-Z','Y').to_euler();c.data.lens=c.data.sensor_height/(2*math.tan(math.radians(v['fov'])/2));s.render.filepath=str(OUT/('before-'+v['name']+'.png'));bpy.ops.render.render(write_still=True)
 write(OUT/'diagnosis-cameras.json',views);assert sha(BASE)==SHA

def review():
 from shapely.geometry import Polygon,box,mapping
 from shapely.ops import unary_union
 from collections import defaultdict
 n=json.loads((OUT/'native-surfaces.json').read_text());groups=[];roi=box(*ROI)
 for r in n['objects']:
  groups_by_z=defaultdict(list)
  for f in r['faces']:
   if not -.01<float(f['z'])<.15:continue
   if not f['material']or not any(k in f['material'].lower()for k in ['paving','asphalt','tarmac','slab','yorkstone','grout','edge','stone']):continue
   groups_by_z[round(f['z'],5)].append(Polygon([v[:2]for v in f['points']]))
  for z,ps in groups_by_z.items():groups.append(dict(name=r['name'],z=z,geometry=unary_union(ps).intersection(roi)))
 # Compute each higher surface union once, not once per pair.
 above_by_z={z:unary_union([r['geometry']for r in groups if r['z']>z+.00001])for z in sorted(set(r['z']for r in groups))}
 pairs=[]
 for i,a in enumerate(groups):
  for b in groups[i+1:]:
   if abs(a['z']-b['z'])>.00001:continue
   g=a['geometry'].intersection(b['geometry'])
   if g.area<.05:continue
   visible=g.difference(above_by_z[a['z']])
   if visible.area>.05:pairs.append(dict(first=a['name'],second=b['name'],z=a['z'],exposedAreaM2=visible.area,geometry=mapping(visible)))
 pairs.sort(key=lambda r:r['exposedAreaM2'],reverse=True)
 write(OUT/'coplanar-diagnosis.json',dict(baselineSha256=SHA,groups=len(groups),pairs=pairs))
 print('GROUND234_REVIEW',[(r['first'],r['second'],r['exposedAreaM2'])for r in pairs[:20]],flush=True)

def route_support_diagnosis():
 """Read actual stored horizontal faces at mapped centre-line sample positions."""
 from shapely.geometry import Polygon,Point,LineString,box
 from shapely.strtree import STRtree
 native=json.loads((OUT/'native-surfaces.json').read_text());polys=[];owners=[];heights=[]
 for r in native['objects']:
  for f in r['faces']:
   if not .015<f['z']<.15 or not f['material']or not any(k in f['material'].lower()for k in ['paving','asphalt','tarmac','slab','yorkstone','grout','edge']):continue
   p=Polygon([v[:2]for v in f['points']])
   if p.is_valid and p.area>1e-9:polys.append(p);owners.append(r['name']);heights.append(f['z'])
 spatial=STRtree(polys);site=json.loads((ROOT/'result/blender/site_geometry.json').read_text());roi=box(*ROI);rows=[]
 for r in site['roads']:
  if r['properties'].get('name')not in ['Portugal Street','Sheffield Street','Houghton Street']or r['geometry']['type']!='LineString':continue
  line=LineString(r['geometry']['coordinates']);count=max(1,math.ceil(line.length/2))
  for i in range(count+1):
   p=line.interpolate(i/count,normalized=True)
   if not roi.contains(p):continue
   hits=[int(k)for k in spatial.query(p,predicate='intersects')];best=max(hits,key=lambda k:heights[k])if hits else None
   rows.append(dict(way=r['id'],name=r['properties']['name'],fraction=i/count,xy=list(p.coords)[0],support=owners[best]if best is not None else None,supportZ=heights[best]if best is not None else None))
 write(OUT/'route-support-diagnosis.json',dict(baselineSha256=SHA,source='result/blender/site_geometry.json',maximumNominalSpacingM=2,samples=len(rows),supported=sum(r['support']is not None for r in rows),unsupported=[r for r in rows if r['support']is None],rows=rows,limitations='Archived schematic centre lines sampled against actual saved native horizontal walking faces. This is continuity evidence, not an accessibility or measured crossfall survey.'))
 print('GROUND234_ROUTE_SUPPORT',len(rows),'unsupported',sum(r['support']is None for r in rows),flush=True)

def verify_entry_contact():
 """Fresh native readback of the retained street-facing step and ramp toes."""
 import bpy
 from mathutils import Vector
 from mathutils.bvhtree import BVHTree
 from integrate_exterior_round194 import object_fingerprint,update_scene
 assert sha(BASE)==SHA;bpy.ops.wm.open_mainfile(filepath=str(BASE));update_scene()
 native=json.loads((OUT/'native-surfaces.json').read_text());assert all(object_fingerprint(bpy.data.objects[r['name']])==r['fingerprint']for r in native['objects'])
 metadata=json.loads((ROOT/'result/blender/stage234/metadata-before.json').read_text());spaces={r['collection']:sorted(o.name for o in bpy.data.collections[r['collection']].all_objects)for r in metadata['spaces']};assert len(spaces)==34 and len(set().union(*(set(v)for v in spaces.values())))==1433
 points=[];faces=[];owners=[]
 for r in native['objects']:
  for f in r['faces']:
   if not .015<f['z']<.15 or not f['material']or not any(k in f['material'].lower()for k in ['paving','asphalt','tarmac','slab','yorkstone','grout','edge']):continue
   p=f['points']
   if not((min(v[0]for v in p)<7 and max(v[0]for v in p)>-8 and min(v[1]for v in p)<-75 and max(v[1]for v in p)>-100)or(min(v[0]for v in p)<36 and max(v[0]for v in p)>30 and min(v[1]for v in p)<11 and max(v[1]for v in p)>6)):continue
   start=len(points);points.extend(p);faces.append(tuple(start+i for i in range(len(p))));owners.append(r['name'])
 ground=BVHTree.FromPolygons(points,faces);records=[]
 for name in ['OLD_NEXT_ACCESS_external_four_steps','OLD_NEXT_APPROACH_continuous_ramp_surface','SITE232_EST_LRB_three_low_steps_and_entry_landing']:
  o=bpy.data.objects[name];assert not o.hide_render;ps=[o.matrix_world@v.co for v in o.data.vertices];low=min(p.z for p in ps);toes=[]
  for p in ps:
   if abs(p.z-low)<1e-5 and all((p-q).length>.0001 for q in toes):toes.append(p)
  for p in toes:
   hit=ground.ray_cast(Vector((p.x,p.y,.2)),Vector((0,0,-1)),.3)
   records.append(dict(approach=name,point=list(p),support=owners[hit[2]]if hit[2]is not None else None,supportZ=hit[0].z if hit[0]is not None else None,baseMinusPavingM=p.z-hit[0].z if hit[0]is not None else None))
 write(OUT/'entry-contact-verification.json',dict(baselineSha256=SHA,freshBlenderProcess=True,originalGroundFingerprintsVerified=len(native['objects']),objects=len(bpy.data.objects),protectedSpaces=34,protectedSpaceObjects=1433,samples=records,unsupported=[r for r in records if r['support']is None],positiveGroundGaps=[r for r in records if r['baseMinusPavingM']is not None and r['baseMinusPavingM']>.001],sourceAndAllStoredGroundGeometryUnchanged=True))
 print('GROUND234_ENTRY_CONTACT',len(records),'unsupported',sum(r['support']is None for r in records),'gaps',sum(r['baseMinusPavingM']is not None and r['baseMinusPavingM']>.001 for r in records),flush=True)


def capture_asphalt_overlap():
 import bpy
 from mathutils import Vector
 from integrate_exterior_round194 import object_fingerprint,update_scene
 from refine_portsmouth_exterior207 import material_fingerprint
 assert sha(BASE)==SHA;bpy.ops.wm.open_mainfile(filepath=str(BASE));update_scene();rows=[]
 for name in ['SITE211_209_Mapped_asphalt_footways','STREET227_Asphalt_clipped_beneath_retained_stone']:
  o=bpy.data.objects[name];assert not o.hide_render;m=o.data;m.calc_loop_triangles();normal_matrix=o.matrix_world.to_3x3().inverted().transposed();tris=[]
  for t in m.loop_triangles:
   points=[o.matrix_world@m.vertices[i].co for i in t.vertices]
   if not all(abs(p.z-.024)<1e-6 for p in points):continue
   tris.append(dict(face=t.polygon_index,loops=list(t.loops),points=[list(p)for p in points],uvs={u.name:[list(u.data[i].uv)for i in t.loops]for u in m.uv_layers},normals=[list((normal_matrix@m.corner_normals[i].vector).normalized())for i in t.loops],materialIndex=m.polygons[t.polygon_index].material_index))
  rows.append(dict(name=name,fingerprint=object_fingerprint(o),matrix=[list(r)for r in o.matrix_world],materials=[m.name if m else None for m in o.data.materials],materialFingerprints={m.name:material_fingerprint(m)for m in o.data.materials if m},owners=[c.name for c in o.users_collection],triangles=tris,vertices=len(m.vertices),polygons=len(m.polygons),uvNames=[u.name for u in m.uv_layers],hasCustomNormals=m.has_custom_normals))
 write(OUT/'asphalt-overlap-native.json',dict(baselineSha256=SHA,objects=rows));print('GROUND234_OVERLAP_CAPTURE',[(r['name'],len(r['triangles']))for r in rows],flush=True)


def prepare_dedup_plan():
 """Prepare the bounded exact-overlap candidate without mutating any native file."""
 from shapely.geometry import Polygon,shape,mapping
 from shapely.ops import unary_union
 from shapely import constrained_delaunay_triangles,orient_polygons
 raw=json.loads((OUT/'asphalt-overlap-native.json').read_text());comparison=json.loads((OUT/'asphalt-overlap-comparison.json').read_text());source=raw['objects'][0];proven=shape(comparison['scopedOverlapGeometry']);cover=unary_union([Polygon([p[:2]for p in t['points']])for t in raw['objects'][1]['triangles']]);cut=proven.buffer(-.001,join_style=2);rows=[];unchanged=[];changed=[]
 def weights(q,p):
  det=(q[1][1]-q[2][1])*(q[0][0]-q[2][0])+(q[2][0]-q[1][0])*(q[0][1]-q[2][1]);u=((q[1][1]-q[2][1])*(p[0]-q[2][0])+(q[2][0]-q[1][0])*(p[1]-q[2][1]))/det;v=((q[2][1]-q[0][1])*(p[0]-q[2][0])+(q[0][0]-q[2][0])*(p[1]-q[2][1]))/det;return [u,v,1-u-v]
 for index,t in enumerate(source['triangles']):
  poly=Polygon([p[:2]for p in t['points']]);intersection=poly.intersection(cut)
  if intersection.area<1e-9:rows.append(dict(**t,sourceTriangle=index,unchanged=True));unchanged.append(index);continue
  changed.append(index);remainder=orient_polygons(poly.difference(cut))
  for tri in constrained_delaunay_triangles(remainder).geoms:
   if tri.area<1e-10:continue
   tri=orient_polygons(tri);p=list(tri.exterior.coords)[:-1];ws=[weights(t['points'],xy)for xy in p]
   interp=lambda values:[[sum(w[i]*values[i][j]for i in range(3))for j in range(len(values[0]))]for w in ws]
   rows.append(dict(points=[[*xy,.024]for xy in p],uvs={n:interp(v)for n,v in t['uvs'].items()},normals=interp(t['normals']),materialIndex=t['materialIndex'],sourceTriangle=index,unchanged=False))
 refs=['result/blender/site_geometry.json','data/collections/streets/raw/osm_map.osm','data/collections/streets/raw/public_realm_strategy_2022.pdf','result/blender/street-ground234/asphalt-overlap-native.json','result/blender/street-ground234/asphalt-overlap-comparison.json','result/blender/stage234/metadata-before.json']
 write(OUT/'dedup-plan.json',dict(baselineSha256=SHA,source=source['name'],sourceFingerprint=source['fingerprint'],sourceHashes={p:sha(ROOT/p)for p in refs},provenOverlapAreaM2=proven.area,removedAreaM2=cut.area,retainedContactGuardAreaM2=proven.area-cut.area,retainedContactGuardMetres=.001,subtractionGeometry=mapping(cut),originalTriangleCount=len(source['triangles']),retainedTriangles=rows,untouchedSourceTriangles=unchanged,changedSourceTriangles=changed,scopeGeometry=comparison['scopedOverlapGeometry'],boundaryAndHeightsPolicy='Subtract only the scoped intersection covered by the retained227asphalt. Preserve all road/footway unions and0.024mZ; a bounded1mm retained contact guard along every proven intersection boundary, preserving original footway outer edges, no broad priority swap, kerb guess, new path or new material.'))
 print('GROUND234_CANDIDATE_PREPARED',len(rows),len(unchanged),len(changed),flush=True)

NEW='STREET234_Mapped_asphalt_footways_deduplicated_with_contact_guard'
SOURCE='SITE211_209_Mapped_asphalt_footways'
OTHER='STREET227_Asphalt_clipped_beneath_retained_stone'
OWNER='00_SITE'

def build_dedup_component():
 import bpy,struct
 from mathutils import Vector
 from integrate_exterior_round194 import object_fingerprint,update_scene
 from refine_plaza_environment231 import state,preserve
 from refine_portsmouth_exterior207 import material_fingerprint
 plan=json.loads((OUT/'dedup-plan.json').read_text());assert sha(BASE)==SHA and all(sha(ROOT/p)==h for p,h in plan['sourceHashes'].items())
 bpy.ops.wm.open_mainfile(filepath=str(BASE));update_scene();before=frozen_native_state();assert len(before['objects'])==8529 and len(before['rooms'])==34 and len(set().union(*(set(v)for v in before['rooms'].values())))==1433
 preserve.__globals__['BASE']=BASE;preserve.__globals__['SHA']=SHA
 source=bpy.data.objects[SOURCE];assert object_fingerprint(source)==plan['sourceFingerprint']and not source.hide_render;assert [c.name for c in source.users_collection]==[OWNER]
 vertices=[];faces=[];kept=[];collapsed=[]
 for index,row in enumerate(plan['retainedTriangles']):
  points=[[struct.unpack('f',struct.pack('f',v))[0]for v in p]for p in row['points']];a,b,c=points;area=((b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0]))/2
  if abs(area)<1e-12:
   assert not row['unchanged'];collapsed.append(index);continue
  assert area>0,(index,area)
  start=len(vertices);vertices.extend(points);faces.append((start,start+1,start+2));kept.append(row)
 mesh=bpy.data.meshes.new(NEW);mesh.from_pydata(vertices,[],faces);mesh.update()
 for material in source.data.materials:mesh.materials.append(material)
 for name in source.data.uv_layers.keys():
  uv=mesh.uv_layers.new(name=name)
  for f,row in zip(mesh.polygons,kept):
   for li,xy in zip(f.loop_indices,row['uvs'][name]):uv.data[li].uv=xy
 for f,row in zip(mesh.polygons,kept):f.material_index=row['materialIndex'];f.use_smooth=False
 normals=[Vector(n).normalized()for row in kept for n in row['normals']];mesh.normals_split_custom_set(normals)
 new=source.copy();new.data=mesh;new.name=NEW;bpy.data.collections[OWNER].objects.link(new);new['originalObject']=SOURCE;new['destinationCollection']=OWNER;new['scope']='Subtract only native proven coplanar asphalt duplicates. All road/footway unions and datums retained; no visible shimmer improvement claimed.'
 fingerprint=object_fingerprint(new);bindings=[m.name for m in new.data.materials];material_fingerprints={m.name:material_fingerprint(m)for m in new.data.materials};preserve(before)
 component=OUT/'component.blend';bpy.data.libraries.write(str(component),{new},fake_user=True,compress=True);component_sha=sha(component)
 bpy.ops.wm.open_mainfile(filepath=str(component));assert object_fingerprint(bpy.data.objects[NEW])==fingerprint;assert all(material_fingerprint(bpy.data.materials[n])==v for n,v in material_fingerprints.items())
 write(OUT/'serialized-mesh.json',dict(componentSha256=component_sha,vertices=[list(v.co)for v in bpy.data.objects[NEW].data.vertices],triangles=[list(f.vertices)for f in bpy.data.objects[NEW].data.polygons],uvs={u.name:[list(v.uv)for v in u.data]for u in bpy.data.objects[NEW].data.uv_layers},sourceTriangleIndices=[r['sourceTriangle']for r in kept],unchanged=[r['unchanged']for r in kept],normals=[list(n.vector)for n in bpy.data.objects[NEW].data.corner_normals]))
 bpy.ops.wm.open_mainfile(filepath=str(BASE));update_scene()
 with bpy.data.libraries.load(str(component),link=False)as(_,dst):dst.objects=[NEW]
 new=dst.objects[0]
 for i,n in enumerate(bindings):new.data.materials[i]=bpy.data.materials[n]
 bpy.data.collections[OWNER].objects.link(new);update_scene();assert object_fingerprint(new)==fingerprint;preserve(before)
 source=bpy.data.objects[SOURCE];views=render_dedup_review(source,new);preserve(before)
 write(OUT/'audit.json',dict(version=234,baseline=str(BASE.relative_to(ROOT)),baselineSha256=SHA,componentPath=str(component.relative_to(ROOT)),componentSha256=component_sha,targetCollection=OWNER,destinationCollection=OWNER,addedObjects=[NEW],archivedObjects=[SOURCE],changedObjects=[],addedFingerprints={NEW:fingerprint},replacementMaterialBindings={NEW:bindings},addedMaterialFingerprints=material_fingerprints,sourceHashes=plan['sourceHashes'],sourceManifest='data/collections/street-ground234/sources.json',objectOwners={NEW:OWNER},archiveOwners={SOURCE:before['owners'][SOURCE]},retainedDuplicateCoverageOwner=OTHER,verification=dict(componentReopened=True,componentAppendedToBaseline=True,originalGeometryUVsTransformsBindingsNodesModifiersPropsOwnersAndVisibilityPreserved=True,originalObjectsVerified=8529,protectedSpacesVerified=34,protectedSpaceMembersVerified=1433,noFullNativeSaved=True,noNewMaterialsOrTextures=True),budget=dict(originalSourceTriangles=425,nominalExactDifferenceTriangles=440,nominalTriangleDelta=15,guardedPlanTriangleDelta=len(plan['retainedTriangles'])-425,provenOverlapAreaM2=plan['provenOverlapAreaM2'],plannedRemovedAreaM2=plan['removedAreaM2'],plannedRetainedContactGuardAreaM2=plan['retainedContactGuardAreaM2'],retainedContactGuardMetres=.001,positiveAreaPlanTriangles=len(plan['retainedTriangles']),savedNondegenerateTriangles=len(faces),savedTriangleDelta=len(faces)-425,float32CollapsedNewFragments=len(collapsed),untouchedOriginalTriangles=len(plan['untouchedSourceTriangles']),archivedObjects=1,addedObjects=1),visualClaim='Duplicate native geometry is proven. A perceptible flicker improvement is not established; same-camera full-context images are non-regression evidence.',scope='Remove only the interior of the proven49.52286742m²coplanar asphalt intersection. Retain a bounded1mm native contact strip along all proven intersection boundaries to preserve original outer road edges and cover measured20bit quantization error. Actual removed and residual areas are recorded in budget. Preserve STREET227and every Portugal stone boundary,tree,building,footway union,datum and space.',cameras=views,previews=[p+'-'+v['name']+'.png'for v in views for p in ['before','after']],limitations=['Archived GIS widths and native road datums remain schematic estimates; no new surveyed kerb or current2026street layout inferred.','Material nodes and MetricUVs agree; tiny native split-normal differences do not establish perceptible shimmer.','Nominal overlay produces440triangles,including numerical slivers. Record actual positive-area savedFloat32count separately,never force degenerate triangles to meet a nominal budget.','OLDandLRBsupport probes include hidden foundation vertices at facade boundaries. Preserve their pre-existing unsupported-edge set; do not classify every such vertex as a walking-route defect.']))
 assert sha(BASE)==SHA and sha(component)==component_sha
 print('GROUND234_COMPONENT',component_sha,'savedTriangles',len(faces),'delta',len(faces)-425,'collapsed',len(collapsed),flush=True)

def render_dedup_review(source,new):
 import bpy
 from mathutils import Vector
 from integrate_exterior_round194 import update_scene
 s=bpy.data.scenes['00_CAMPUS_COMPLETE'];bpy.context.window.scene=s;c=bpy.data.objects.new('GROUND234_REVIEW_CAMERA',bpy.data.cameras.new('GROUND234_REVIEW_CAMERA'));s.collection.objects.link(c);s.camera=c;c.data.clip_end=1400;c.data.sensor_fit='VERTICAL'
 s.render.engine='BLENDER_EEVEE';s.render.resolution_x=1000;s.render.resolution_y=750;s.render.resolution_percentage=100;s.render.image_settings.file_format='PNG'
 for o in s.objects:
  if o.hide_render:o.hide_set(True)
 views=[dict(name='portugal-duplicate-nonregression',eye=[-2,16,9],target=[49,37,.1],fov=62)]
 for v in views:
  eye=Vector(v['eye']);target=Vector(v['target']);c.location=eye;c.rotation_euler=(target-eye).to_track_quat('-Z','Y').to_euler();c.data.lens=c.data.sensor_height/(2*math.tan(math.radians(v['fov'])/2))
  for phase in ['before','after']:
   source.hide_render=phase=='after';source.hide_set(phase=='after');new.hide_render=phase=='before';new.hide_set(phase=='before');update_scene();s.render.filepath=str(OUT/(phase+'-'+v['name']+'.png'));bpy.ops.render.render(write_still=True)
 source.hide_render=False;source.hide_set(False);new.hide_render=False;new.hide_set(False);bpy.data.objects.remove(c,do_unlink=True);bpy.data.cameras.remove(bpy.data.cameras['GROUND234_REVIEW_CAMERA']);return views

def frozen_native_state():
 """Protect the fixed233space roster even after234metadata is registered."""
 import bpy
 from integrate_exterior_round194 import object_fingerprint
 from refine_portsmouth_exterior207 import material_fingerprint
 from refine_ksw_exterior219 import modifier_state
 meta=json.loads((ROOT/'result/blender/stage234/metadata-before.json').read_text())
 rooms={r['collection']:sorted(o.name for o in bpy.data.collections[r['collection']].all_objects)for r in meta['spaces']}
 return dict(objects={o.name:object_fingerprint(o)for o in bpy.data.objects},materials={m.name:material_fingerprint(m)for m in bpy.data.materials},owners={o.name:sorted(c.name for c in o.users_collection)for o in bpy.data.objects},modifiers={o.name:modifier_state(o)for o in bpy.data.objects},props={o.name:repr(sorted(o.items()))for o in bpy.data.objects},visibility={o.name:o.hide_render for o in bpy.data.objects},rooms=rooms)

if __name__=='__main__':
 try:import bpy
 except ImportError:
  if (OUT/'asphalt-overlap-native.json').exists():compare_asphalt_overlap();prepare_dedup_plan()
  else:review();route_support_diagnosis()
 else:
  if not (OUT/'native-surfaces.json').exists():capture()
  elif not (OUT/'asphalt-overlap-native.json').exists():capture_asphalt_overlap()
  elif (OUT/'dedup-plan.json').exists():build_dedup_component()
  else:verify_entry_contact()
