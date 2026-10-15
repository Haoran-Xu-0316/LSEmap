"""Remove two mapped underground pedestrian routes from ground-level paving.

The archived source explicitly marks tunnel=yes and negative layer. Current
native geometry and accepted216 fingerprints are verified before authoring.
Original surface routes and their overlaps remain; tunnel depth is not guessed.
"""
from pathlib import Path
import hashlib,json,sys
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'result/blender/LSE_campus_detailed_v216.blend'
SHA='12376d6365bbc57fa9eec97617453dbbfcf9235a8200bb90726f80c2147c1a60'
OUT=ROOT/'result/blender/street-environment217';OUT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(ROOT/'web/tools'))
SOURCES=['SITE215_mapped_footway_body','SITE215_mapped_footway_edge']
TUNNELS=['way/432479184','way/1478702312']
def save(name,value):(OUT/name).write_text(json.dumps(value,indent=2)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def open_verified():
 import bpy
 from integrate_exterior_round194 import object_fingerprint,update_scene
 assert sha(BASE)==SHA
 bpy.ops.wm.open_mainfile(filepath=str(BASE));update_scene()
 old=json.loads((ROOT/'result/blender/stage216/baseline-state.json').read_text())['fingerprints'];new=json.loads((ROOT/'result/blender/stage216/building-refinement.json').read_text())['addedFingerprints']
 mismatches=[dict(name=name,type=bpy.data.objects[name].type,expected=value,actual=object_fingerprint(bpy.data.objects[name]))for name,value in {**old,**new}.items()if object_fingerprint(bpy.data.objects[name])!=value]
 save('baseline-differences.json',dict(baselineSha256=SHA,mismatches=mismatches))
 assert not mismatches,mismatches
 save('baseline-verification.json',dict(baselineSha256=SHA,acceptedOriginalsVerified=len(old),acceptedAddedObjectsVerified=len(new),verified=True))
 return bpy.context.scene

def inspect():
 import bpy
 from mathutils import Vector
 scene=open_verified();rows=[]
 for name in SOURCES:
  obj=bpy.data.objects[name];assert not obj.hide_render and not obj.hide_get()
  points=[obj.matrix_world@v.co for v in obj.data.vertices]
  rows.append(dict(name=name,vertices=[list(p)for p in points],faces=[dict(indices=list(f.vertices),uvs=[list(obj.data.uv_layers[0].data[i].uv)for i in f.loop_indices],material=f.material_index)for f in obj.data.polygons],materials=[m.name for m in obj.data.materials]))
 save('native-footways.json',dict(baselineSha256=SHA,objects=rows));print('SITE217_INSPECT',[(r['name'],len(r['faces']))for r in rows],flush=True)

def prepare():
 import math,struct
 from shapely.geometry import Polygon,shape,mapping
 from shapely.ops import unary_union
 from shapely import constrained_delaunay_triangles,make_valid
 native=json.loads((OUT/'native-footways.json').read_text());assert native['baselineSha256']==SHA
 site=json.loads((ROOT/'result/blender/site_geometry.json').read_text());old=json.loads((ROOT/'result/blender/streets215/plan.json').read_text())
 refs=[r for r in site['roads']if r['id']in TUNNELS];assert len(refs)==2
 assert all(r['properties'].get('tunnel')=='yes'and float(r['properties'].get('layer','0'))<0 for r in refs)
 other=[]
 for r in site['roads']:
  if r['id']in TUNNELS or r['properties'].get('highway')!='footway'or r['geometry']['type']!='LineString':continue
  for a,b in zip(r['geometry']['coordinates'],r['geometry']['coordinates'][1:]):
   length=math.dist(a,b)
   if length<.1:continue
   u=[(b[i]-a[i])/length for i in range(2)];v=[-u[1],u[0]]
   other.append(Polygon([(p[0]+sign*.025*u[0]+side*.8*v[0],p[1]+sign*.025*u[1]+side*.8*v[1])for p,sign,side in [(a,-1,1),(b,1,1),(b,1,-1),(a,-1,-1)]]))
 other=unary_union(other);tunnel=unary_union([Polygon(t)for r in old['regions']if r['id']in TUNNELS for t in r['body']+r['edge']]);cut=tunnel.difference(other.buffer(.0002))
 owners={}
 for family in ['body','edge']:
  rows=[]
  for region in old['regions']:
   for triangle in region[family]:
    tt=[tuple(struct.unpack('f',struct.pack('f',v))[0]for v in p)for p in triangle]
    cross=(tt[1][0]-tt[0][0])*(tt[2][1]-tt[0][1])-(tt[1][1]-tt[0][1])*(tt[2][0]-tt[0][0])
    if abs(cross)<1e-8:continue
    if cross<0:tt.reverse()
    rows.append((region['id'],tt))
  owners['SITE215_mapped_footway_'+family]=rows
 replacements=[];original_polygons=[];retained_polygons=[];removed_polygons=[]
 for row in native['objects']:
  changes=[];before=[];after=[]
  assert len(owners[row['name']])==len(row['faces'])
  for index,face in enumerate(row['faces']):
   pp=[row['vertices'][i]for i in face['indices']];poly=Polygon([p[:2]for p in pp]);before.append(poly)
   owner,sourceTriangle=owners[row['name']][index]
   assert [tuple(p[:2])for p in pp]==sourceTriangle,(row['name'],index)
   if owner not in TUNNELS:after.append(poly);continue
   kept=make_valid(poly.intersection(other.buffer(.0002)));pieces=[list(t.exterior.coords)[:-1]for t in constrained_delaunay_triangles(kept).geoms if t.area>1e-9]
   # UV is affine over the existing triangle; preserve its metric axes when a
   # boundary triangle is split instead of restarting the slab grid.
   a,b,c=pp;den=(b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1]);assert abs(den)>1e-12
   def uv(p):
    wa=((b[1]-c[1])*(p[0]-c[0])+(c[0]-b[0])*(p[1]-c[1]))/den;wb=((c[1]-a[1])*(p[0]-c[0])+(a[0]-c[0])*(p[1]-c[1]))/den;wc=1-wa-wb
    return[wa*face['uvs'][0][j]+wb*face['uvs'][1][j]+wc*face['uvs'][2][j]for j in range(2)]
   changes.append(dict(sourceFace=index,triangles=[dict(points=t,uvs=[uv(p)for p in t])for t in pieces],material=face['material']))
   after.extend(Polygon(t)for t in pieces)
  a=unary_union(before);b=unary_union(after);original_polygons.append(a);retained_polygons.append(b);removed_polygons.append(a.difference(b))
  replacements.append(dict(source=row['name'],name=row['name'].replace('SITE215','SITE217'),materials=row['materials'],changes=changes,sourceFaces=len(row['faces']),unchangedFaces=len(row['faces'])-len(changes),removedAreaM2=a.difference(b).area))
 actual=unary_union(original_polygons);retained=unary_union(retained_polygons);removed=actual.difference(retained)
 assert retained.difference(actual.buffer(.0002)).area<1e-7
 assert actual.intersection(other).difference(retained.buffer(.0002)).area<1e-7
 assert removed.area>40
 plan=dict(baselineSha256=SHA,sourceWays=refs,replacements=replacements,originalAreaM2=actual.area,retainedAreaM2=retained.area,removedExclusiveUndergroundAreaM2=removed.area,protectedSurfaceOverlapAreaM2=tunnel.intersection(other.buffer(.0002)).area,sourceGeometry=mapping(actual),retainedGeometry=mapping(retained),removedGeometry=mapping(removed),protectedOtherWayGeometry=mapping(other),scope='Remove only ground paving uniquely attributed to two explicit negative-layer tunnel footways; retain every other surface route overlap, existing widths, heights, materials, slab UV axes and216car-road correction.',limitations='Archived OSM negative layer and tunnel tags classify these two routes. Retained1.6m widths and source positions are inherited schematic estimates. No underground depth or current2026as-built survey inferred. Existing terrain below the former erroneous paving stays unchanged.')
 save('plan.json',plan);print('SITE217_PLAN',removed.area,[(r['source'],len(r['changes']),r['removedAreaM2'])for r in replacements],flush=True)


def build():
 import bpy,struct
 from mathutils import Vector
 from mathutils.bvhtree import BVHTree
 from integrate_exterior_round194 import object_fingerprint
 from refine_portsmouth_exterior207 import material_fingerprint
 scene=open_verified();plan=json.loads((OUT/'plan.json').read_text());assert plan['baselineSha256']==SHA
 originals={o.name:object_fingerprint(o)for o in bpy.data.objects};materials={m.name:material_fingerprint(m)for m in bpy.data.materials};owned=[];actual=[];protected=0
 for replacement in plan['replacements']:
  source=bpy.data.objects[replacement['source']];assert len(source.data.uv_layers)==1
  changes={r['sourceFace']:r for r in replacement['changes']};vertices=[list(v.co)for v in source.data.vertices];faces=[];slots=[];uvs=[];unchanged=[]
  for polygon in source.data.polygons:
   if polygon.index in changes:continue
   faces.append(tuple(polygon.vertices));slots.append(polygon.material_index);uvs.append([tuple(source.data.uv_layers[0].data[i].uv)for i in polygon.loop_indices]);unchanged.append(polygon.index)
  for change in replacement['changes']:
   for row in change['triangles']:
    pp=row['points'];tt=row['uvs']
    pp=[tuple(struct.unpack('f',struct.pack('f',v))[0]for v in p)for p in pp]
    cross=(pp[1][0]-pp[0][0])*(pp[2][1]-pp[0][1])-(pp[1][1]-pp[0][1])*(pp[2][0]-pp[0][0])
    if abs(cross)<1e-8:continue
    if cross<0:pp=list(reversed(pp));tt=list(reversed(tt))
    first=len(vertices);vertices.extend((p[0],p[1],.024)for p in pp);faces.append((first,first+1,first+2));slots.append(change['material']);uvs.append(tt)
  mesh=bpy.data.meshes.new(replacement['name']);mesh.from_pydata(vertices,[],faces);mesh.update()
  for m in source.data.materials:mesh.materials.append(m)
  layer=mesh.uv_layers.new(name=source.data.uv_layers[0].name)
  for polygon,slot,coords in zip(mesh.polygons,slots,uvs):
   polygon.material_index=slot
   for loop,value in zip(polygon.loop_indices,coords):layer.data[loop].uv=value
  mesh.normals_split_custom_set_from_vertices([(0,0,1)]*len(vertices))
  # Unaffected source faces retain exact native corner coordinates and UVs.
  for new_index,old_index in enumerate(unchanged):
   a=source.data.polygons[old_index];b=mesh.polygons[new_index]
   assert tuple(a.vertices)==tuple(b.vertices)
   assert [tuple(source.data.uv_layers[0].data[i].uv)for i in a.loop_indices]==[tuple(layer.data[i].uv)for i in b.loop_indices]
   assert a.material_index==b.material_index
   protected+=1
  obj=source.copy();obj.data=mesh;obj.name=replacement['name'];obj['originalObject']=source.name;obj['scope']=plan['scope'];bpy.data.collections['00_SITE'].objects.link(obj);owned.append(obj)
  actual.append(dict(name=obj.name,vertices=[list(v.co)for v in mesh.vertices],faces=[list(f.vertices)for f in mesh.polygons]))
 save('native-result.json',dict(baselineSha256=SHA,objects=actual))
 # Check the real visible ground below all changed source-face centres. These
 # are independent of the newly authored polygons and the target source mesh.
 ground_vertices=[];ground_faces=[];owners=[]
 for obj in scene.objects:
  if obj.name in SOURCES or obj in owned or obj.type!='MESH'or obj.hide_render or obj.hide_get():continue
  corners=[obj.matrix_world@Vector(p)for p in obj.bound_box]
  if min(p.z for p in corners)>.1 or max(p.z for p in corners)<-.2:continue
  if max(p.x for p in corners)<-260 or min(p.x for p in corners)>-130 or max(p.y for p in corners)<195 or min(p.y for p in corners)>260:continue
  points=[obj.matrix_world@v.co for v in obj.data.vertices]
  for polygon in obj.data.polygons:
   pp=[points[i]for i in polygon.vertices]
   if min(p.z for p in pp)<-.2 or max(p.z for p in pp)>.1 or max(p.z for p in pp)-min(p.z for p in pp)>.0001:continue
   start=len(ground_vertices);ground_vertices.extend(pp);ground_faces.append(tuple(range(start,start+len(pp))));owners.append(obj.name)
 tree=BVHTree.FromPolygons(ground_vertices,ground_faces);probes=[]
 for row in plan['replacements']:
  source=bpy.data.objects[row['source']]
  for change in row['changes']:
   polygon=source.data.polygons[change['sourceFace']];p=sum((source.matrix_world@source.data.vertices[i].co for i in polygon.vertices),Vector())/len(polygon.vertices)
   hit=tree.ray_cast(Vector((p.x,p.y,.15)),Vector((0,0,-1)),.4)
   probes.append(dict(source=source.name,sourceFace=polygon.index,xy=list(p.xy),support=owners[hit[2]]if hit[2]is not None else None,height=hit[0].z if hit[0]is not None else None))
 assert all(p['support']is not None for p in probes)
 save('ground-support.json',dict(probes=probes,allSupported=True))
 assert all(object_fingerprint(bpy.data.objects[n])==f for n,f in originals.items())
 assert all(material_fingerprint(bpy.data.materials[n])==f for n,f in materials.items())
 fingerprints={o.name:object_fingerprint(o)for o in owned};component=OUT/'component.blend';bpy.data.libraries.write(str(component),set(owned),fake_user=True,compress=True)
 camera_data=bpy.data.cameras.new('SITE217_review_camera');camera=bpy.data.objects.new('SITE217_review_camera',camera_data);scene.collection.objects.link(camera);camera.location=(-198,228,260);camera.rotation_euler=(Vector((-198,228,0))-camera.location).to_track_quat('-Z','Y').to_euler();camera_data.type='ORTHO';camera_data.ortho_scale=145;camera_data.clip_end=1500;scene.camera=camera
 scene.render.engine='BLENDER_WORKBENCH';scene.display.shading.light='STUDIO';scene.display.shading.color_type='MATERIAL';scene.display.shading.show_shadows=True;scene.display.shading.show_cavity=False
 scene.render.resolution_x=1400;scene.render.resolution_y=850;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG'
 for obj in owned:obj.hide_render=True
 scene.render.filepath=str(OUT/'before.png');bpy.ops.render.render(write_still=True)
 for obj in owned:obj.hide_render=False
 for name in SOURCES:bpy.data.objects[name].hide_render=True
 scene.render.filepath=str(OUT/'after.png');bpy.ops.render.render(write_still=True)
 bpy.ops.wm.read_factory_settings(use_empty=True)
 with bpy.data.libraries.load(str(component),link=False)as(_,target):target.objects=list(fingerprints)
 for obj in target.objects:bpy.context.scene.collection.objects.link(obj);assert object_fingerprint(obj)==fingerprints[obj.name]
 report={k:plan[k]for k in ['baselineSha256','sourceWays','originalAreaM2','retainedAreaM2','removedExclusiveUndergroundAreaM2','protectedSurfaceOverlapAreaM2','scope','limitations']}
 report.update(version=217,componentPath=str(component.relative_to(ROOT)),componentSha256=sha(component),targetCollection='00_SITE',addedObjects=list(fingerprints),archivedObjects=SOURCES,replacementMaterialBindings={r['name']:r['materials']for r in plan['replacements']},componentReopened=True,sourceOriginalsVerified=len(originals),sourceMaterialNodesVerified=len(materials),unchangedSourceFacesWithExactCornerUVs=protected,groundSupportProbes=len(probes),allGroundSupportProbesPassed=True)
 save('audit.json',report);print('SITE217_COMPONENT',report['componentSha256'],protected,len(probes),flush=True)

def verify_stored():
 from shapely.geometry import Polygon,shape
 from shapely.ops import unary_union
 plan=json.loads((OUT/'plan.json').read_text());actual=json.loads((OUT/'native-result.json').read_text());polygons=[];degenerate=0
 for obj in actual['objects']:
  for face in obj['faces']:
   p=Polygon([obj['vertices'][i][:2]for i in face]);degenerate+=int(p.area<1e-12)
   if p.area>0:polygons.append(p)
 union=unary_union(polygons);expected=shape(plan['retainedGeometry']);source=shape(plan['sourceGeometry']);other=shape(plan['protectedOtherWayGeometry'])
 missing=expected.difference(union.buffer(.0002)).area;extra=union.difference(expected.buffer(.0002)).area;overlap=source.intersection(other).difference(union.buffer(.0002)).area
 assert missing<1e-6 and extra<1e-6 and overlap<1e-6,(missing,extra,overlap)
 assert degenerate==0,degenerate
 report=dict(verified=True,storedAreaM2=union.area,expectedAreaM2=expected.area,sourceVsStoredRemovedAreaM2=source.difference(union).area,nativeFloat32DifferenceM2=union.symmetric_difference(expected).area,missingBeyondPointTwoMillimetresM2=missing,excessBeyondPointTwoMillimetresM2=extra,otherSurfaceOverlapLossM2=overlap,zeroAreaFaces=degenerate)
 save('geometry-verification.json',report)
 if(OUT/'audit.json').exists():
  a=json.loads((OUT/'audit.json').read_text());a['storedGeometryVerification']=report;save('audit.json',a)
 print('SITE217_GEOMETRY',report,flush=True)

if __name__=='__main__':
 try:import bpy
 except ImportError:
  prepare()
  if(OUT/'native-result.json').exists():verify_stored()
 else:build()if(OUT/'plan.json').exists()else inspect()
