"""SAW216 historical floor-outline registration from the2014 occupant guide.
Fixed configuration; source PDF and accepted complete native remain read-only.
"""
from pathlib import Path
import json,hashlib
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'result/blender/saw-floors216'
PDF=ROOT/'data/documents/saw_occupants_guide_2014.pdf'

def extract_vectors():
 import pdfplumber
 OUT.mkdir(parents=True,exist_ok=True)
 report={}
 with pdfplumber.open(PDF)as document:
  for page_number in range(26,33):
   page=document.pages[page_number-1]
   curves=[]
   for index,c in enumerate(page.curves):
    if c['top']<140 or c['bottom']>483:continue
    if c['width']<2 or c['height']<2:continue
    color=c.get('non_stroking_color')
    if color and isinstance(color,(list,tuple)) and len(color)>1 and max(color)-min(color)>.05:continue
    curves.append(dict(index=index,bbox=[c[k]for k in ['x0','top','x1','bottom']],width=c['width'],height=c['height'],fill=c['fill'],stroke=c['stroke'],color=color,strokeColor=c.get('stroking_color'),pts=c['pts'],path=c.get('path')))
   report[page_number]=dict(pageSize=[page.width,page.height],candidates=curves)
   print('EXTRACTED_PAGE',page_number,len(curves),flush=True)
 (OUT/'vectors.json').write_text(json.dumps(report,separators=(',',':'))+'\n')

# Manually reviewed outside faces of the grey enclosing wall lines. The sixth
# includes the published roof terrace as a floor surface; faint roof/context
# outlines and department colour boundaries are not floor contours.
OUTLINES_PIXELS={
31:[(145,395),(383,395),(515,509),(775,422),(1328,596),(1180,1196),(952,1196),(846,1144),(740,911),(685,763),(452,817),(226,628),(241,605),(283,555),(145,555)],
30:[(145,395),(383,395),(515,509),(775,422),(1328,596),(1254,894),(1328,1196),(1058,1196),(904,1170),(846,1144),(740,911),(685,763),(492,810),(465,828),(234,605),(283,555),(145,555)],
29:[(145,395),(383,395),(515,509),(775,422),(1328,596),(1254,879),(1328,1196),(1058,1196),(904,1170),(838,1135),(740,911),(685,763),(528,796),(492,834),(234,605),(283,555),(145,555)],
28:[(156,569),(382,410),(508,522),(779,426),(1345,601),(1271,899),(1345,1208),(1088,1208),(889,1175),(847,1152),(743,917),(693,765),(550,798),(513,846),(334,684)],
27:[(198,570),(351,468),(435,543),(655,474),(823,447),(976,514),(1188,562),(1188,1196),(1140,1196),(847,1144),(728,855),(696,769),(591,785),(540,847),(382,705)],
26:[(230,586),(310,535),(354,576),(899,478),(976,513),(990,558),(1176,606),(1176,1164),(993,1135),(979,1174),(851,1146),(733,863),(696,765),(630,779),(558,862),(379,699)]}

def prepare_registration():
 import numpy as np
 from shapely.geometry import Polygon
 vectors=json.loads((OUT/'vectors.json').read_text())
 cores={}
 for number,record in vectors.items():
  candidates=[]
  for curve in record['candidates']:
   x0,top,x1,bottom=curve['bbox']
   if (250<x0<320 and 210<top<240 and 12<curve['width']<18 and 20<curve['height']<26
       and len(curve['pts'])==7 and np.linalg.norm(np.array(curve['pts'][0])-curve['pts'][-1])<.01):candidates.append(curve)
  candidates.sort(key=lambda curve:curve['bbox'][0]);assert len(candidates)==2,(number,len(candidates));cores[number]=candidates
 ground=np.concatenate([curve['pts'][:-1]for curve in cores['32']])
 records={}
 for number,record in vectors.items():
  source=np.concatenate([curve['pts'][:-1]for curve in cores[number]])
  x=source-source.mean(0);y=ground-ground.mean(0)
  u,s,vh=np.linalg.svd(x.T@y);matrix=(s.sum()/(x*x).sum())*(u@vh)
  offset=ground.mean(0)-source.mean(0)@matrix
  residual=np.linalg.norm(source@matrix+offset-ground,axis=1)
  assert residual.max()<.061
  factor=1501/record['pageSize'][0]
  item=dict(page=int(number),level=32-int(number),matrix=matrix.tolist(),offset=offset.tolist(),maxResidualPdfPoints=float(residual.max()),fitControlCount=len(source),sourceControlCurveIndices=[c['index']for c in cores[number]],fitScope='Common dual-lift interior corners; similarity, not a flexible warp')
  if int(number)in OUTLINES_PIXELS:
   outline=np.array(OUTLINES_PIXELS[int(number)])/factor
   assert Polygon(outline).is_valid
   item['tracedPdfOutline']=outline.tolist()
   item['groundPagePixelOutline']=((outline@matrix+offset)*factor).tolist()
   item['traceMethod']='Visual outside wall-line trace; vertices rounded to raster pixels from the vector PDF; wall detail and exact thickness unresolved'
  records[number]=item
 (OUT/'registration.json').write_text(json.dumps(records,indent=2)+'\n')
 # One compact proof sheet overlays the trace on the actual source, retaining
 # the original drawing. It is private audit material, never a public texture.
 from PIL import Image,ImageDraw
 contact=Image.new('RGB',(1800,1200),'white')
 for index,number in enumerate(range(31,25,-1)):
  picture=Image.open(ROOT/f'data/previews/saw_occupants_guide_2014_p{number}.png').convert('RGB')
  draw=ImageDraw.Draw(picture)
  points=OUTLINES_PIXELS[number]
  draw.line(points+[points[0]],fill=(200,20,20),width=4)
  for p in points:draw.ellipse((p[0]-4,p[1]-4,p[0]+4,p[1]+4),fill=(200,20,20))
  crop=picture.crop((115,365,1380,1220));crop.thumbnail((600,560))
  x=(index%3)*600;y=(index//3)*600
  contact.paste(crop,(x,y+30));ImageDraw.Draw(contact).text((x+10,y+10),f'Level {32-number}; PDF page {number}',fill=(0,0,0))
 contact.save(OUT/'source-contours.png')


def inspect_native():
 import bpy
 from mathutils import Vector
 base=ROOT/'result/blender/LSE_campus_detailed_v215.blend'
 baseline='b6c726056d7e98dc229e1ac2dc1d01e7be35eb1835a28cd7a6bb88155a9c1a11'
 assert hashlib.sha256(base.read_bytes()).hexdigest()==baseline
 bpy.ops.wm.open_mainfile(filepath=str(base))
 bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE']
 names=['SAW_SAW_floor_0','SAW173_shared_floor_landings','SAW173_registered_main_treads']+['SAW173_registered_floor_'+str(z)for z in [3.45,8.1,11.1,14.1,18.0,21.9]]
 records=[]
 for name in names:
  obj=bpy.data.objects[name];assert not obj.hide_render
  obj.data.calc_loop_triangles()
  records.append(dict(name=name,vertices=[list(obj.matrix_world@v.co)for v in obj.data.vertices],triangles=[list(t.vertices)for t in obj.data.loop_triangles],materials=[m.name for m in obj.data.materials]))
 (OUT/'native-surfaces.json').write_text(json.dumps(records,separators=(',',':'))+'\n')
 print('SAWFLOOR216_NATIVE_READ',len(records),flush=True)


def prepare_surfaces():
 """Coordinate historical contours with retained stair geometry and headroom."""
 import numpy as np
 import shapely
 from shapely.geometry import Polygon
 from shapely.ops import unary_union
 from shapely.geometry.polygon import orient
 native={r['name']:r for r in json.loads((OUT/'native-surfaces.json').read_text())}
 registered=json.loads((OUT/'registration.json').read_text())
 anchors=np.array([[-65.223399,-15.905616],[-84.252182,28.425],[-55.301,36.609104]])
 factor=1501/595.276
 def world(points):
  p=np.array(points);a,b,c=anchors
  return a+(p[:,0:1]-145)/1200*(b-a)+(p[:,1:2]-400)/785*(c-b)
 def horizontal_surfaces(record):
  vertices=np.array(record['vertices']);surfaces=[]
  for triangle in record['triangles']:
   p=vertices[triangle]
   if np.ptp(p[:,2])<1e-5 and np.cross(p[1]-p[0],p[2]-p[0])[2]>0:
    polygon=Polygon(p[:,:2])
    if polygon.area>1e-9:surfaces.append((float(p[:,2].mean()),polygon))
  return surfaces
 treads=horizontal_surfaces(native['SAW173_registered_main_treads'])
 landings=horizontal_surfaces(native['SAW173_shared_floor_landings'])
 vectors=json.loads((OUT/'vectors.json').read_text())
 controls=registered['32']['sourceControlCurveIndices']
 cabins=[next(c for c in vectors['32']['candidates']if c['index']==index)['pts'][:-1]for index in controls]
 lifts=shapely.set_precision(unary_union([Polygon(world(np.array(points)*factor))for points in cabins]),.0001)
 records=[]
 for level,datum in enumerate([3.45,8.1,11.1,14.1,18.0,21.9],1):
  source='SAW173_registered_floor_'+str(datum)
  contour=shapely.set_precision(Polygon(world(registered[str(32-level)]['groundPagePixelOutline'])),.0001)
  assert contour.is_valid
  clearance=shapely.set_precision(unary_union([p for height,p in treads if datum-2.25<height<datum-.001]).buffer(.04,join_style=2),.0001)
  landing_clearance=shapely.set_precision(unary_union([p for height,p in treads if datum-2.43<height<datum-.001]).buffer(.04,join_style=2),.0001)
  arrival=unary_union([p for height,p in treads if abs(height-datum)<1e-4])
  old_landing=unary_union([p for height,p in landings if abs(height-datum)<1e-4])
  landing=shapely.set_precision(old_landing,.0001).intersection(contour).difference(landing_clearance).difference(lifts)
  assert landing.is_valid and landing.area>1
  floor=contour.difference(clearance).difference(lifts).difference(landing.buffer(.003,join_style=2)).difference(arrival.buffer(.003,join_style=2))
  assert floor.is_valid and floor.geom_type=='Polygon',floor.geom_type
  assert floor.intersection(clearance).area<1e-8
  assert floor.intersection(lifts).area<1e-8
  assert floor.intersection(landing).area<1e-8
  assert landing.difference(contour).area<1e-8
  assert arrival.distance(floor.union(landing))<.004,(level,arrival.distance(floor.union(landing)))
  assert landing.distance(floor)<.004
  contact_area=landing.buffer(.013,join_style=2).intersection(floor).area
  assert contact_area>.01,contact_area
  support=floor.union(landing).union(arrival)
  assert support.buffer(.005,join_style=2).geom_type=='Polygon'
  def encode_surface(geometry):
   triangles=[]
   for piece in shapely.constrained_delaunay_triangles(geometry).geoms:
    p=orient(piece,sign=1)
    assert geometry.covers(p.representative_point())
    points=list(p.exterior.coords)[:-1];assert len(points)==3
    triangles.append(points)
   assert abs(sum(Polygon(p).area for p in triangles)-geometry.area)<1e-7
   return triangles
  def polygons(geometry):
   return [dict(outer=list(orient(p,sign=1).exterior.coords)[:-1],holes=[list(r.coords)[:-1]for r in orient(p,sign=1).interiors])for p in (geometry.geoms if hasattr(geometry,'geoms')else[geometry])]
  records.append(dict(level=level,datum=datum,sourceObject=source,floorObject='SAWFLOOR216_registered_floor_'+str(datum),floorTriangles=encode_surface(floor),landingTriangles=encode_surface(landing),landingPolygons=polygons(landing),outlineWorld=list(contour.exterior.coords),floorArea=floor.area,landingArea=landing.area,oldLandingArea=old_landing.area,landingTrimmedArea=old_landing.difference(landing).area,clearanceArea=clearance.intersection(contour).area,liftVoidArea=lifts.intersection(contour).area,arrivalToSurfaceDistance=arrival.distance(floor.union(landing)),landingToFloorDistance=landing.distance(floor),landingFloorContactBandArea=contact_area,connectedWithFiveMillimetreSeamTolerance=True))
 plan=dict(version=216,baselineSha256='b6c726056d7e98dc229e1ac2dc1d01e7be35eb1835a28cd7a6bb88155a9c1a11',sourcePdfSha256=hashlib.sha256(PDF.read_bytes()).hexdigest(),clearanceHeight=2.25,headroomLateralEstimate=.04,floorLandingSeam=.003,liftVoidMethod='Two published cabin inner outlines kept clear; full shaft walls and door clearances are not reconstructed',floors=records)
 (OUT/'surface-plan.json').write_text(json.dumps(plan,indent=2)+'\n')
 print('SAWFLOOR216_PREPARED',[(r['level'],round(r['floorArea'],2),round(r['landingArea'],2))for r in records],flush=True)


def build_component():
 import sys
 import bpy
 import bmesh
 from mathutils import Vector
 from mathutils.bvhtree import BVHTree
 sys.path.insert(0,str(ROOT/'web/tools'))
 from integrate_exterior_round194 import object_fingerprint
 from refine_portsmouth_exterior207 import material_fingerprint
 base=ROOT/'result/blender/LSE_campus_detailed_v215.blend'
 plan=json.loads((OUT/'surface-plan.json').read_text());baseline=plan['baselineSha256']
 assert hashlib.sha256(base.read_bytes()).hexdigest()==baseline
 bpy.ops.wm.open_mainfile(filepath=str(base));bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE']
 for scene in bpy.data.scenes:
  for layer in scene.view_layers:layer.update()
 originals={o.name:object_fingerprint(o)for o in bpy.data.objects}
 material_states={m.name:material_fingerprint(m)for m in bpy.data.materials}
 visibility={o.name:o.hide_render for o in bpy.data.objects}
 collection=bpy.data.collections['SAW_STRUCTURE173_registered_main_circulation']
 added=[];archived=[];bindings={}
 def mesh_object(name,vertices,faces,source):
  mesh=bpy.data.meshes.new(name);mesh.from_pydata(vertices,[],faces);mesh.update()
  uv=mesh.uv_layers.new(name='MetricUV')
  for loop in mesh.loops:
   p=mesh.vertices[loop.vertex_index].co;uv.data[loop.index].uv=(p.x,p.y)
  material=bpy.data.objects[source].data.materials[0];mesh.materials.append(material)
  obj=bpy.data.objects.new(name,mesh);collection.objects.link(obj)
  obj['originalObject']=source;obj['destinationCollection']=collection.name;obj['historicalSourceYear']=2014
  obj['scope']='Registered historical floor outline and retained actual stair clearance; dimensions inherited estimates, not surveyed current conditions'
  obj.hide_render=False;obj.hide_set(False);added.append(obj);bindings[name]=[material.name]
  return obj
 for item in plan['floors']:
  vertices=[];faces=[];z=item['datum']
  for triangle in item['floorTriangles']:
   offset=len(vertices);vertices.extend((x,y,z)for x,y in triangle);faces.append((offset,offset+1,offset+2))
  obj=mesh_object(item['floorObject'],vertices,faces,item['sourceObject'])
  assert all(p.normal.z>.99 for p in obj.data.polygons)
  source=bpy.data.objects[item['sourceObject']];source.hide_render=True;source.hide_set(True);archived.append(source.name)
 # Keep each landing as one closed constant-thickness assembly per level. Hole
 # sidewalls are explicit; individual triangles do not create overlapping prisms.
 vertices=[];faces=[]
 for item in plan['floors']:
  z=item['datum'];bottom=z-.18
  for triangle in item['landingTriangles']:
   start=len(vertices)
   vertices.extend((x,y,height)for height in [bottom,z]for x,y in triangle)
   faces.extend([(start+2,start+1,start),(start+3,start+4,start+5)])
  for polygon in item['landingPolygons']:
   for ring in [polygon['outer']]+polygon['holes']:
    for a,b in zip(ring,ring[1:]+ring[:1]):
     start=len(vertices);vertices.extend([(a[0],a[1],bottom),(b[0],b[1],bottom),(b[0],b[1],z),(a[0],a[1],z)])
     faces.append(tuple(start+i for i in range(4)))
 landing=mesh_object('SAWFLOOR216_coordinated_shared_floor_landings',vertices,faces,'SAW173_shared_floor_landings')
 bm=bmesh.new();bm.from_mesh(landing.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.000001);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
 assert all(edge.is_manifold for edge in bm.edges),[(tuple(v.co),len(e.link_faces))for e in bm.edges if not e.is_manifold for v in e.verts][:20]
 assert bm.calc_volume(signed=True)>0
 bm.to_mesh(landing.data);bm.free();landing.data.update()
 old=bpy.data.objects['SAW173_shared_floor_landings'];old.hide_render=True;old.hide_set(True);archived.append(old.name)
 for s in bpy.data.scenes:
  for layer in s.view_layers:layer.update()
 changed_originals=[k for k,v in originals.items()if object_fingerprint(bpy.data.objects[k])!=v]
 assert not changed_originals,changed_originals[:20]
 assert all(material_fingerprint(bpy.data.materials[k])==v for k,v in material_states.items())
 fingerprints={o.name:object_fingerprint(o)for o in added}
 component=OUT/'saw-floors216-component.blend'
 bpy.data.libraries.write(str(component),set(added),fake_user=True,compress=True)
 # Reopen and validate actual saved float32 surfaces and measured connectivity.
 bpy.ops.wm.open_mainfile(filepath=str(base));bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE']
 for scene in bpy.data.scenes:
  for layer in scene.view_layers:layer.update()
 with bpy.data.libraries.load(str(component),link=False)as(available,loaded):loaded.objects=list(fingerprints)
 for obj in loaded.objects:
  for i,name in enumerate(bindings[obj.name]):obj.data.materials[i]=bpy.data.materials[name]
  collection=bpy.data.collections['SAW_STRUCTURE173_registered_main_circulation'];collection.objects.link(obj);obj.hide_render=False;obj.hide_set(False)
 for name in archived:bpy.data.objects[name].hide_render=True;bpy.data.objects[name].hide_set(True)
 changed_originals=[k for k,v in originals.items()if object_fingerprint(bpy.data.objects[k])!=v]
 assert not changed_originals,changed_originals[:20]
 assert all(object_fingerprint(bpy.data.objects[k])==v for k,v in fingerprints.items())
 assert all(material_fingerprint(bpy.data.materials[k])==v for k,v in material_states.items())
 assert all(bpy.data.objects[k].hide_render==v for k,v in visibility.items()if k not in archived)
 # Probe every actual retained tread centroid/corner beneath the next floor.
 surfaces=[bpy.data.objects[n]for n in fingerprints];vertices=[];faces=[]
 for obj in surfaces:
  start=len(vertices);vertices.extend(obj.matrix_world@v.co for v in obj.data.vertices);faces.extend(tuple(start+i for i in p.vertices)for p in obj.data.polygons)
 tree=BVHTree.FromPolygons(vertices,faces)
 tread=bpy.data.objects['SAW173_registered_main_treads'];tread.data.calc_loop_triangles();probes=[]
 for face in tread.data.polygons:
  if face.normal.z<.99:continue
  pts=[tread.matrix_world@tread.data.vertices[i].co for i in face.vertices];centre=sum(pts,Vector())/len(pts)
  for target in [centre]+[centre.lerp(p,.85)for p in pts]:
   hit=tree.ray_cast(target+Vector((0,0,.002)),Vector((0,0,1)),2.246)
   probes.append(hit[0]is not None)
 assert not any(probes),sum(probes)
 restored_surfaces=[]
 for obj in surfaces:
  obj.data.calc_loop_triangles()
  restored_surfaces.append(dict(name=obj.name,vertices=[list(obj.matrix_world@v.co)for v in obj.data.vertices],triangles=[list(t.vertices)for t in obj.data.loop_triangles]))
 (OUT/'reopened-surfaces.json').write_text(json.dumps(restored_surfaces,separators=(',',':'))+'\n')
 verification=dict(savedComponentReopened=True,originalObjectsVerified=len(originals),originalMaterialsVerified=len(material_states),originalGeometryUVsBindingsAndNodesPreserved=True,unrelatedVisibilityPreserved=True,retainedTreadHeadroomProbes=len(probes),headroomHits=0,landingClosedManifoldAndPositiveVolume=True,sourceModelUnchanged=hashlib.sha256(base.read_bytes()).hexdigest()==baseline)
 (OUT/'verification.json').write_text(json.dumps(verification,indent=2)+'\n')
 report=dict(version=216,baseline=str(base.relative_to(ROOT)),baselineSha256=baseline,componentPath=str(component.relative_to(ROOT)),componentSha256=hashlib.sha256(component.read_bytes()).hexdigest(),targetCollection='SAW_STRUCTURE173_registered_main_circulation',destinationCollection='SAW_STRUCTURE173_registered_main_circulation',addedObjects=list(fingerprints),archivedObjects=archived,changedObjects=[],addedFingerprints=fingerprints,replacementMaterialBindings=bindings,source=dict(path=str(PDF.relative_to(ROOT)),sha256=plan['sourcePdfSha256'],publicationYear=2014,pages=list(range(26,33)),url='https://info.lse.ac.uk/staff/divisions/estates-division/Assets/Documents/SAW/Final-Web-version-of-Occupants-Guide.pdf'),registration='12 common dual-lift vector controls per level; similarity to ground plan, then inherited173 estimated world anchors',floors=[{k:v for k,v in item.items()if k not in ['floorTriangles','landingTriangles','landingPolygons']}for item in plan['floors']],verification=verification,scope='Six distinct source-guided historical upper-floor perimeters, retained main stair clearance and coordinated clipped landings; room partitions remain unmodeled',limitations=['2014 historical guide does not establish current2026 conditions.','Outside wall-line contours are manually traced from vector-PDF renders; exact slab edge, survey dimensions and wall thickness are unresolved.','World registration and vertical datums inherit173 estimates; repeated common controls validate relative floor registration only.','Lift holes follow the two published inner cabin outlines, not a complete surveyed shaft/wall assembly.','Forty-millimetre lateral headroom margin,3mm seams,180mm landing thickness and2.25m clearance are authoring estimates, not safety certification.','Sixth-floor roof terrace is retained as part of the floor outline; no new exterior wall, room or fabricated current fitout is added.'])
 (OUT/'audit.json').write_text(json.dumps(report,indent=2)+'\n')
 print('SAWFLOOR216_COMPONENT_REOPENED',len(fingerprints),len(probes),flush=True)

def verify_reopened_surfaces():
 """Independently inspect actual reopened float32 meshes with Shapely."""
 import numpy as np
 from shapely.geometry import Polygon
 from shapely.ops import unary_union
 native={r['name']:r for r in json.loads((OUT/'native-surfaces.json').read_text())}
 restored={r['name']:r for r in json.loads((OUT/'reopened-surfaces.json').read_text())}
 plan=json.loads((OUT/'surface-plan.json').read_text())
 def top_surface(record,datum):
  vertices=np.array(record['vertices']);polygons=[]
  for triangle in record['triangles']:
   p=vertices[triangle]
   if max(abs(p[:,2]-datum))<1e-4 and np.cross(p[1]-p[0],p[2]-p[0])[2]>0:
    polygon=Polygon(p[:,:2])
    if polygon.area>1e-10:polygons.append(polygon)
  return unary_union(polygons)
 rows=[]
 for item in plan['floors']:
  z=item['datum'];floor=top_surface(restored[item['floorObject']],z)
  landing=top_surface(restored['SAWFLOOR216_coordinated_shared_floor_landings'],z)
  arrival=top_surface(native['SAW173_registered_main_treads'],z)
  intended_floor=unary_union([Polygon(p)for p in item['floorTriangles']])
  intended_landing=unary_union([Polygon(p)for p in item['landingTriangles']])
  floor_error=floor.symmetric_difference(intended_floor).area
  landing_error=landing.symmetric_difference(intended_landing).area
  assert floor_error<.002 and landing_error<.0002,(floor_error,landing_error)
  assert landing.distance(floor)<.004
  assert arrival.distance(floor.union(landing))<.004
  assert floor.union(landing).union(arrival).buffer(.005,join_style=2).geom_type=='Polygon'
  assert floor.intersection(landing).area<1e-7
  rows.append(dict(level=item['level'],actualFloorArea=floor.area,actualLandingArea=landing.area,floorSymmetricDifferenceSquareMetres=floor_error,landingSymmetricDifferenceSquareMetres=landing_error,actualLandingFloorDistance=landing.distance(floor),actualArrivalSurfaceDistance=arrival.distance(floor.union(landing)),actualFiveMillimetreConnectivity=True,actualFloorLandingOverlap=floor.intersection(landing).area))
 report=dict(savedReopenedGeometryVerified=True,precisionScope='Actual saved Blender float32 vertex and triangle data, no modifier or inferred bounds',floorCount=6,floors=rows)
 (OUT/'reopened-surface-verification.json').write_text(json.dumps(report,indent=2)+'\n')
 audit=json.loads((OUT/'audit.json').read_text());audit['reopenedSurfaceVerification']=report
 (OUT/'audit.json').write_text(json.dumps(audit,indent=2)+'\n')
 print('SAWFLOOR216_ACTUAL_CONNECTIVITY_VERIFIED',len(rows),flush=True)

if __name__=='__main__':
 try:import bpy
 except ImportError:
  if not(OUT/'vectors.json').exists():extract_vectors()
  prepare_registration()
  if(OUT/'native-surfaces.json').exists():prepare_surfaces()
  if(OUT/'audit.json').exists()and(OUT/'reopened-surfaces.json').exists():verify_reopened_surfaces()
 else:
  if(OUT/'surface-plan.json').exists():build_component()
  else:inspect_native()
