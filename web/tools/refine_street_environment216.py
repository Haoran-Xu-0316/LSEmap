"""Remove buried Strand Underpass from an erroneous at-grade asphalt network.

Fixed workflow: Blender first captures archived source/visible road footprints;
MachineLearning prepares the planar difference; Blender writes one component;
MachineLearning independently verifies its actual Float32 geometry. No new road
width, tunnel profile, marker or terrain beyond the original map is inferred.
"""
from pathlib import Path
import hashlib,json,sys
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'result/blender/LSE_campus_detailed_v215.blend'
SHA='b6c726056d7e98dc229e1ac2dc1d01e7be35eb1835a28cd7a6bb88155a9c1a11'
OUT=ROOT/'result/blender/street-environment216'
OUT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(ROOT/'web/tools'))
def save(name,value):(OUT/name).write_text(json.dumps(value,indent=2)+'\n')
def inspect_roads():
 import bpy
 from mathutils import Vector
 assert hashlib.sha256(BASE.read_bytes()).hexdigest()==SHA
 bpy.ops.wm.open_mainfile(filepath=str(BASE));bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE']
 old=json.loads((ROOT/'result/blender/street-network198/native-road-audit.json').read_text())
 names=[r['name']for r in old['roads']if r['materials']==['Road asphalt']]
 rows=[]
 for name in names:
  obj=bpy.data.objects[name];points=[obj.matrix_world@v.co for v in obj.data.vertices];faces=[]
  for f in obj.data.polygons:
   ps=[points[i]for i in f.vertices]
   if all(abs(p.z-.024)<1e-5 for p in ps):faces.append([list(p)for p in ps])
  rows.append(dict(name=name,faces=faces))
 save('original-road-tops.json',dict(baselineSha256=SHA,roads=rows))
 source=bpy.data.objects['SITE211_198_Continuous_asphalt_road_network']
 assert not source.hide_render and not source.hide_get()
 points=[source.matrix_world@v.co for v in source.data.vertices]
 visible=[dict(vertices=[list(points[i])for i in f.vertices],material=source.data.materials[f.material_index].name)for f in source.data.polygons if all(abs(points[i].z-.024)<1e-5 for i in f.vertices)]
 save('native-inventory.json',dict(baselineSha256=SHA,ground=[dict(name=source.name,faces=visible)]))
 print('SITE216_ORIGINAL_ROADS',len(rows),flush=True)


def prepare():
 from shapely.geometry import Polygon,shape,mapping
 from shapely.ops import unary_union
 from shapely import make_valid,constrained_delaunay_triangles,orient_polygons
 n=json.loads((OUT/'original-road-tops.json').read_text());v=json.loads((OUT/'native-inventory.json').read_text());site=json.loads((ROOT/'result/blender/site_geometry.json').read_text())
 poly=lambda faces:make_valid(unary_union([Polygon([p[:2]for p in f])for f in faces]))
 tunnels=[r for r in site['roads']if r['properties'].get('name')=='Strand Underpass'];assert len(tunnels)==1
 assert all(r['properties'].get('tunnel')=='yes'and float(r['properties']['layer'])<0 for r in tunnels)
 underground=[r for r in n['roads']if'Strand Underpass'in r['name']];surface=[r for r in n['roads']if r not in underground]
 tunnel=poly([f for r in underground for f in r['faces']]);others=poly([f for r in surface for f in r['faces']]);current=poly([f['vertices']for r in v['ground']if r['name']=='SITE211_198_Continuous_asphalt_road_network'for f in r['faces']])
 removed=make_valid(current.intersection(tunnel.difference(others.buffer(.0002))));retained=orient_polygons(make_valid(current.difference(removed)))
 def triangles(g):return[list(t.exterior.coords)[:-1]for t in constrained_delaunay_triangles(g).geoms if t.area>1e-8]
 print('areas',current.area,tunnel.area,removed.area,retained.area,'triangles',len(triangles(retained)))
 print('other-road-error',current.intersection(others).difference(retained.buffer(.0002)).area)
 plan=dict(baselineSha256=n['baselineSha256'],source='SITE211_198_Continuous_asphalt_road_network',sourceMaterial='Road asphalt.002',allUndergroundWays=tunnels,undergroundNativeSources=[r['name']for r in underground],surfaceNativeSourceCount=len(surface),originalAreaM2=current.area,undergroundOriginalStripAreaM2=tunnel.area,removedExclusiveUndergroundAreaM2=removed.area,retainedAreaM2=retained.area,preservedSurfaceOverlapAreaM2=current.intersection(others).area,otherSurfaceLossM2=current.intersection(others).difference(retained.buffer(.0002)).area,triangles=triangles(retained),removedTriangles=triangles(removed),removedGeometry=mapping(removed),retainedGeometry=mapping(retained),sourceOtherGeometry=mapping(others),top=.024,boundaryToleranceMetres=.0002,limitations='OSM2026-09-12archive identifies entire Strand Underpass way25803161 as tunnel=yes/layer=-1. Only its exclusive mistakenly at-grade asphalt is removed; all other archived surface-road overlap retained. Original13m schematic width is not replaced by a new guessed width. Existing ground/pedestrian surfaces remain; no underground depth/profile, new traffic marking, kerb or current2026site survey inferred.')
 (OUT/'plan.json').write_text(json.dumps(plan,indent=2)+'\n')

def build():
 import bpy,math,struct
 from mathutils import Vector
 from mathutils.bvhtree import BVHTree
 from integrate_exterior_round194 import object_fingerprint
 from refine_portsmouth_exterior207 import material_fingerprint
 assert hashlib.sha256(BASE.read_bytes()).hexdigest()==SHA
 plan=json.loads((OUT/'plan.json').read_text());assert plan['baselineSha256']==SHA
 bpy.ops.wm.open_mainfile(filepath=str(BASE));scene=bpy.data.scenes['00_CAMPUS_COMPLETE'];bpy.context.window.scene=scene
 originals={o.name:object_fingerprint(o)for o in bpy.data.objects};materials={m.name:material_fingerprint(m)for m in bpy.data.materials}
 source=bpy.data.objects[plan['source']];assert not source.hide_render and not source.hide_get()
 vertices=[];faces=[]
 for triangle in plan['triangles']:
  t=[tuple(struct.unpack('f',struct.pack('f',c))[0]for c in p)for p in triangle]
  signed=(t[1][0]-t[0][0])*(t[2][1]-t[0][1])-(t[1][1]-t[0][1])*(t[2][0]-t[0][0])
  if abs(signed)<1e-8:continue
  if signed<0:t.reverse()
  first=len(vertices);vertices.extend((p[0],p[1],plan['top'])for p in t);faces.append((first,first+1,first+2))
 name='SITE216_At_grade_asphalt_underground_route_removed';mesh=bpy.data.meshes.new(name);mesh.from_pydata(vertices,[],faces);mesh.update();mesh.materials.append(source.data.materials[0])
 uv=mesh.uv_layers.new(name='MetricUV')
 for loop in mesh.loops:uv.data[loop.index].uv=mesh.vertices[loop.vertex_index].co.xy
 mesh.normals_split_custom_set_from_vertices([(0,0,1)]*len(vertices))
 obj=bpy.data.objects.new(name,mesh);bpy.data.collections['00_SITE'].objects.link(obj);obj['originalObject']=source.name;obj['scope']=plan['limitations']
 # Independent native Float32 footprint check is performed by MachineLearning
 # from the actual stored vertices, rather than the triangulation input.
 save('native-result.json',dict(vertices=[list(v.co)for v in mesh.vertices],triangles=[list(f.vertices)for f in mesh.polygons]))
 # Probe retained current ground independently of the incorrect asphalt. The
 # source buried strip extends beyond the original map datum; such orphan road
 # portions are removed too and are reported separately rather than infilled.
 ground_vertices=[];ground_faces=[];owners=[]
 for candidate in scene.objects:
  if candidate in (source,obj)or candidate.type!='MESH'or candidate.hide_render or candidate.hide_get():continue
  corners=[candidate.matrix_world@Vector(c)for c in candidate.bound_box]
  if min(c.z for c in corners)>.15 or max(c.z for c in corners)<-.2:continue
  ps=[candidate.matrix_world@v.co for v in candidate.data.vertices]
  for polygon in candidate.data.polygons:
   points=[ps[i]for i in polygon.vertices]
   if min(p.z for p in points)<-.2 or max(p.z for p in points)>.15 or max(p.z for p in points)-min(p.z for p in points)>.0001:continue
   start=len(ground_vertices);ground_vertices.extend(points);ground_faces.append(tuple(range(start,start+len(points))));owners.append(candidate.name)
 ground=BVHTree.FromPolygons(ground_vertices,ground_faces)
 probes=[]
 for t in plan['removedTriangles']:
  x=sum(p[0]for p in t)/3;y=sum(p[1]for p in t)/3
  hit=ground.ray_cast(Vector((x,y,.18)),Vector((0,0,-1)),.4)
  probes.append(dict(xy=[x,y],support=owners[hit[2]]if hit[2]is not None else None,height=hit[0].z if hit[0]is not None else None))
 save('ground-support.json',dict(samples=probes,supported=sum(p['support']is not None for p in probes),unsupported=sum(p['support']is None for p in probes)))
 assert all(object_fingerprint(bpy.data.objects[n])==f for n,f in originals.items())
 assert all(material_fingerprint(bpy.data.materials[n])==f for n,f in materials.items())
 fingerprint=object_fingerprint(obj);component=OUT/'component.blend';bpy.data.libraries.write(str(component),{obj},fake_user=True,compress=True)
 # Two identical native viewpoints make the false above-ground route visible.
 camera_data=bpy.data.cameras.new('SITE216_review_camera');camera=bpy.data.objects.new('SITE216_review_camera',camera_data);scene.collection.objects.link(camera)
 camera.location=(-115,-230,650);camera.rotation_euler=(Vector((-115,-230,0))-camera.location).to_track_quat('-Z','Y').to_euler();camera_data.type='ORTHO';camera_data.ortho_scale=470;camera_data.clip_end=1500;scene.camera=camera
 scene.render.engine='BLENDER_WORKBENCH';scene.display.shading.light='STUDIO';scene.display.shading.color_type='MATERIAL';scene.display.shading.show_shadows=True;scene.display.shading.show_cavity=False
 scene.render.resolution_x=1200;scene.render.resolution_y=1000;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG'
 obj.hide_render=True;scene.render.filepath=str(OUT/'before.png');bpy.ops.render.render(write_still=True)
 obj.hide_render=False;source.hide_render=True;scene.render.filepath=str(OUT/'after.png');bpy.ops.render.render(write_still=True)
 bpy.ops.wm.read_factory_settings(use_empty=True)
 with bpy.data.libraries.load(str(component),link=False)as(_,target):target.objects=[name]
 loaded=target.objects[0];bpy.context.scene.collection.objects.link(loaded);assert object_fingerprint(loaded)==fingerprint
 report={k:plan[k]for k in ['baselineSha256','allUndergroundWays','undergroundNativeSources','surfaceNativeSourceCount','originalAreaM2','undergroundOriginalStripAreaM2','removedExclusiveUndergroundAreaM2','retainedAreaM2','preservedSurfaceOverlapAreaM2','otherSurfaceLossM2','boundaryToleranceMetres','limitations']}
 report.update(version=216,componentPath=str(component.relative_to(ROOT)),componentSha256=hashlib.sha256(component.read_bytes()).hexdigest(),targetCollection='00_SITE',addedObjects=[name],archivedObjects=[plan['source']],replacementMaterialBindings={name:[plan['sourceMaterial']]},originalsVerified=len(originals),originalMaterialsVerified=len(materials),componentReopened=True,sourceGeometryUVMaterialsPreserved=True,triangles=len(faces),nativeSupportProbes=len(probes),nativeSupportHits=sum(p['support']is not None for p in probes),nativeSupportMisses=sum(p['support']is None for p in probes),scope='Remove the entire mapped buried Strand Underpass from its erroneous at-grade-only asphalt footprint. Retain all overlapping original surface roads,211mapped plazas,215footways and all trees.')
 assert all(p['support'] is not None or p['xy'][1]<-335 for p in probes), 'Unsupported removal within map datum'
 report['outsideDatumPolicy']='All unsupported probe centres lie south of original y=-335map datum; remove former orphan buried road without inventing terrain beyond map.'
 save('audit.json',report);print('SITE216_COMPONENT',report,flush=True)

def verify_stored_geometry():
 from shapely.geometry import Polygon,shape,box
 from shapely.ops import unary_union
 plan=json.loads((OUT/'plan.json').read_text());stored=json.loads((OUT/'native-result.json').read_text())
 actual=unary_union([Polygon([stored['vertices'][i][:2]for i in t])for t in stored['triangles']])
 expected=shape(plan['retainedGeometry']);others=shape(plan['sourceOtherGeometry']);removed=shape(plan['removedGeometry'])
 assert actual.is_valid
 missing=expected.difference(actual.buffer(.0002)).area;excess=actual.difference(expected.buffer(.0002)).area
 assert missing<1e-6 and excess<1e-6,(missing,excess)
 assert actual.intersection(removed.buffer(-.0002)).area<.00001
 overlapError=expected.intersection(others).difference(actual.buffer(.0002)).area
 assert overlapError<1e-6,overlapError
 validDatum=box(-350,-335,350,415)
 report=dict(actualStoredFootprintAreaM2=actual.area,expectedAreaM2=expected.area,areaDifferenceM2=actual.symmetric_difference(expected).area,missingBeyondPointTwoMillimetresM2=missing,excessBeyondPointTwoMillimetresM2=excess,otherSurfaceLossBeyondToleranceM2=overlapError,removedInsideExistingDatumM2=removed.intersection(validDatum).area,removedOrphanOutsideExistingDatumM2=removed.difference(validDatum).area,verified=True,triangleCount=len(stored['triangles']))
 save('geometry-verification.json',report)
 if(OUT/'audit.json').exists():
  audit=json.loads((OUT/'audit.json').read_text());audit['storedGeometryVerification']=report;save('audit.json',audit)
 print('SITE216_GEOMETRY',report)

if __name__=='__main__':
 try:import bpy
 except ImportError:
  prepare()
  if(OUT/'native-result.json').exists():verify_stored_geometry()
 else:build()if(OUT/'plan.json').exists()else inspect_roads()
