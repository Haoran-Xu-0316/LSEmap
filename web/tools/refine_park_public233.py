"""Fixed read-only diagnosis and bounded Lincoln's Inn Fields component authoring."""
from pathlib import Path
import sys,json,hashlib
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'result/blender/park-public233'
DATA=ROOT/'data/collections/park-public233'
BASE=ROOT/'result/blender/LSE_campus_detailed_v232.blend'
SHA='1f6ed3da66011e057233697fe8753374a55918d8c4278d56670cbd81192ae2a8'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
def diagnose():
 import bpy
 from mathutils import Vector
 sys.path.insert(0,str(ROOT/'web/tools'))
 from integrate_exterior_round194 import update_scene
 assert sha(BASE)==SHA
 bpy.ops.wm.open_mainfile(filepath=str(BASE));update_scene()
 rows=[]
 for o in bpy.data.objects:
  if o.type!='MESH' or o.hide_render:continue
  p=[o.matrix_world@Vector(v)for v in o.bound_box]
  lo=[min(v[i]for v in p)for i in range(3)];hi=[max(v[i]for v in p)for i in range(3)]
  if lo[0]>-110 and hi[0]<125 and lo[1]>85 and hi[1]<285:
   rows.append(dict(name=o.name,lo=lo,hi=hi,owners=[c.name for c in o.users_collection],materials=[m.name for m in o.data.materials],props=dict(o.items())))
 write(OUT/'native-inspection.json',dict(baselineSha256=SHA,objects=len(bpy.data.objects),rows=rows))
 print('PARK_DIAGNOSIS',[(r['name'],r['lo'],r['hi'])for r in rows if r['hi'][2]>2],flush=True)


# All rounds use one fixed baseline. Blender captures native UV-bearing faces;
# MachineLearning prepares bounded polygon cuts; Blender writes only a library.
GROUND='SITE209_GIS_green_way_30613392_path_openings'
OWNER='03_PUBLIC_REALM'
INPUT=OUT/'native-input.json'
PLAN=OUT/'plan.json'
def capture():
 import bpy
 from mathutils import Vector
 sys.path.insert(0,str(ROOT/'web/tools'))
 from integrate_exterior_round194 import update_scene
 assert sha(BASE)==SHA
 bpy.ops.wm.open_mainfile(filepath=str(BASE));update_scene()
 o=bpy.data.objects[GROUND];assert not o.hide_render
 rows=[]
 for f in o.data.polygons:
  rows.append(dict(index=f.index,vertices=[list(o.data.vertices[i].co)for i in f.vertices],material=f.material_index,smooth=f.use_smooth,uvs={uv.name:[list(uv.data[i].uv)for i in f.loop_indices]for uv in o.data.uv_layers}))
 write(INPUT,dict(baselineSha256=SHA,ground=GROUND,matrix=[list(r)for r in o.matrix_world],faces=rows,materials=[m.name for m in o.data.materials],uvNames=[uv.name for uv in o.data.uv_layers]))
 print('PARK233_CAPTURE',len(rows),flush=True)

def prepare():
 from shapely.geometry import Polygon,Point,LineString
 from shapely import constrained_delaunay_triangles,orient_polygons
 from shapely.ops import unary_union
 import math
 source=json.loads(INPUT.read_text());assert source['baselineSha256']==SHA
 site=json.loads((ROOT/'result/blender/site_geometry.json').read_text())
 circle=[]
 for identity in ['way/28531258','way/896810427']:
  coords=next(r['geometry']['coordinates']for r in site['roads']if r['id']==identity)
  circle.extend(coords if not circle else coords[1:])
 outer=Polygon(circle);assert outer.is_valid
 # Match the archived native 1.6m footway strips including 25mm caps.
 path_polys=[]
 for r in site['roads']:
  if r['properties'].get('highway')!='footway' or r['geometry']['type']!='LineString' or r['properties'].get('name'):continue
  for a,b in zip(r['geometry']['coordinates'],r['geometry']['coordinates'][1:]):
   length=math.dist(a,b)
   if length<=.1:continue
   u=[(b[i]-a[i])/length for i in range(2)];n=[-u[1],u[0]]
   path_polys.append(Polygon([[a[i]-.025*u[i]+.8*n[i]for i in range(2)],[b[i]+.025*u[i]+.8*n[i]for i in range(2)],[b[i]+.025*u[i]-.8*n[i]for i in range(2)],[a[i]-.025*u[i]-.8*n[i]for i in range(2)]]))
 paths=unary_union(path_polys)
 trees=json.loads((ROOT/'data/collections/street-environment232/selected-tree-envelope.json').read_text())['trunks']
 holes=[]
 for r in trees:
  p=Point(r['center'][:2])
  if outer.contains(p):holes.append(p.buffer(.55,quad_segs=12))
 # Photograph establishes compacted hardstanding around the pavilion. The
 # mapped circular path determines extent; existing paths and tree soil holes
 # are excluded exactly, never raised or repainted.
 available=outer.difference(paths).difference(unary_union(holes))
 ground=unary_union([Polygon([v[:2]for v in f['vertices']])for f in source['faces']])
 plaza=orient_polygons(available.intersection(ground))
 assert plaza.area>900 and plaza.intersection(paths).area<1e-8
 def tris(g):
  return [list(p.exterior.coords)[:-1]for p in constrained_delaunay_triangles(orient_polygons(g)).geoms if p.area>1e-9]
 retained=[];touched=[];removed=0
 for f in source['faces']:
  poly=Polygon([v[:2]for v in f['vertices']]);cut=poly.intersection(plaza)
  if cut.area<1e-9:continue
  assert len(f['vertices'])==3
  touched.append(f['index']);remaining=poly.difference(plaza);removed+=cut.area
  a,b,c=f['vertices'];det=(b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1])
  def weights(p):
   u=((b[1]-c[1])*(p[0]-c[0])+(c[0]-b[0])*(p[1]-c[1]))/det
   v=((c[1]-a[1])*(p[0]-c[0])+(a[0]-c[0])*(p[1]-c[1]))/det
   return [u,v,1-u-v]
  for triangle in tris(remaining):
   ws=[weights(p)for p in triangle]
   retained.append(dict(vertices=[[p[0],p[1],sum(w[i]*f['vertices'][i][2]for i in range(3))]for p,w in zip(triangle,ws)],material=f['material'],smooth=f['smooth'],uvs={n:[[sum(w[i]*uv[i][j]for i in range(3))for j in range(2)]for w in ws]for n,uv in f['uvs'].items()}))
 assert abs(removed-plaza.area)<1e-5
 buildings=[r for r in site['buildings']if r['id']in ['way/31694141','way/1367310699','way/301471946']]
 refs=['result/blender/site_geometry.json','data/collections/streets/raw/osm_map.osm','data/collections/street-environment232/selected-tree-envelope.json','data/collections/park-public233/bandstand-stephen-craven-20220601.jpg','data/collections/park-public233/cafe-letting-2023.pdf',str(INPUT.relative_to(ROOT))]
 write(PLAN,dict(baselineSha256=SHA,sourceHashes={p:sha(ROOT/p)for p in refs},touchedFaces=touched,retainedCutFaces=retained,plazaTriangles=tris(plaza),plazaAreaM2=plaza.area,plazaBoundedByOsmWays=['way/28531258','way/896810427'],plazaTreeHoles=len(holes),plazaPathIntersectionM2=plaza.intersection(paths).area,buildings=buildings))
 print('PARK233_PLAN',len(touched),len(retained),plaza.area,flush=True)

def build():
 import bpy,bmesh,math
 from mathutils import Vector
 sys.path.insert(0,str(ROOT/'web/tools'))
 from integrate_exterior_round194 import object_fingerprint,update_scene
 from refine_plaza_environment231 import state,preserve,solids
 from refine_streets230 import triangles,tree
 from refine_portsmouth_exterior207 import material_fingerprint
 plan=json.loads(PLAN.read_text());assert sha(BASE)==SHA and all(sha(ROOT/p)==h for p,h in plan['sourceHashes'].items())
 bpy.ops.wm.open_mainfile(filepath=str(BASE));update_scene();before=state();assert len(before['objects'])==8502 and len(before['rooms'])==34
 preserve.__globals__['BASE']=BASE;preserve.__globals__['SHA']=SHA
 archived=sorted(o.name for o in bpy.data.objects if o.name.startswith(('Context_way/31694141_','Context_way/1367310699_')))
 assert len(archived)==14 and all(not bpy.data.objects[n].hide_render for n in archived)
 archived.append(GROUND);source=bpy.data.objects[GROUND]
 mats={}
 for key,color in [('timber',(.115,.085,.050)),('roof_tiles',(.135,.123,.105)),('plinth',(.35,.35,.305)),('metal_roof',(.40,.43,.415)),('window',(.083,.123,.124)),('gravel',(.54,.49,.375)),('fascia',(.48,.46,.36))]:
  m=bpy.data.materials.new('PARK233_estimated_'+('glass' if key=='window' else key));m.use_nodes=True;m.diffuse_color=(*color,1);p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=m.diffuse_color;p.inputs['Roughness'].default_value=.92 if key!='window'else .28;p.inputs['Alpha'].default_value=1;p.inputs['Transmission Weight'].default_value=0;m['presentationEstimated']=True;mats[key]=m
 added=[]
 class Batch:
  def __init__(self,name,material,facility):self.name='PARK233_'+name;self.material=material;self.facility=facility;self.vertices=[];self.faces=[]
  def poly(self,points,z0,z1):
   n=len(points);start=len(self.vertices)
   self.vertices.extend((p[0],p[1],z)for z in [z0,z1]for p in points)
   self.faces.extend([tuple(start+i for i in range(n-1,-1,-1)),tuple(start+n+i for i in range(n))])
   self.faces.extend(tuple(start+i for i in [k,(k+1)%n,n+(k+1)%n,n+k])for k in range(n))
  def box(self,a,b,width,depth=None):
   a,b=Vector(a),Vector(b);axis=(b-a).normalized();ref=Vector((0,0,1))if abs(axis.z)<.9 else Vector((0,1,0));u=axis.cross(ref).normalized()*width/2;v=axis.cross(u).normalized()*(depth or width)/2;start=len(self.vertices)
   self.vertices.extend(p+u*x+v*y for p in [a,b]for x,y in [(-1,-1),(1,-1),(1,1),(-1,1)])
   self.faces.extend(tuple(start+i for i in f)for f in [(3,2,1,0),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)])
  def shell(self,rings):
   start=len(self.vertices);n=len(rings[0]);self.vertices.extend(p for ring in rings for p in ring)
   for j in range(len(rings)-1):
    for i in range(n):self.faces.append(tuple(start+k for k in [j*n+i,j*n+(i+1)%n,(j+1)*n+(i+1)%n,(j+1)*n+i]))
   self.faces.extend([tuple(start+i for i in range(n-1,-1,-1)),tuple(start+(len(rings)-1)*n+i for i in range(n))])
  def finish(self):
   m=bpy.data.meshes.new(self.name);m.from_pydata(self.vertices,[],self.faces);m.materials.append(self.material);m.update();bm=bmesh.new();bm.from_mesh(m);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(m);bm.free()
   uv=m.uv_layers.new(name='MetricUV')
   for f in m.polygons:
    for li in f.loop_indices:v=m.vertices[m.loops[li].vertex_index].co;uv.data[li].uv=(v.x,v.y)
   o=bpy.data.objects.new(self.name,m);bpy.data.collections[OWNER].objects.link(o);o['destinationCollection']=OWNER;o['sourceOsmFacility']=self.facility;o['dimensionsEstimated']=True;o['scope']='Source-registered park public structure; no source photo textures reused';added.append(o);return o
 def ring_xy(identity):return next(r['rings'][0]for r in plan['buildings']if r['id']==identity)
 br=ring_xy('way/1367310699');center=Vector((sum(p[0]for p in br)/8,sum(p[1]for p in br)/8,0))
 def bandring(scale,z):return [Vector((p[0],p[1],0))*scale+center*(1-scale)+Vector((0,0,z))for p in br]
 # The mapped outer roof extent is fixed. Photo ratios give the estimated
 # eave/peak height; all eight open bays retain real holes.
 plinth=Batch('bandstand_octagonal_ground_plinth',mats['plinth'],'way/1367310699');plinth.poly(br,.05,.14);plinth.poly([p[:2]for p in bandring(.94,0)],.14,.23);plinth.finish()
 roof=Batch('bandstand_closed_octagonal_pitched_roof',mats['roof_tiles'],'way/1367310699')
 roof.shell([bandring(1,3.46),bandring(.78,3.97),bandring(.30,5.47),bandring(.008,6.30),bandring(.008,6.13),bandring(.30,5.30),bandring(.78,3.80),bandring(1,3.29)])
 # Close the folded roof perimeter as one annular solid; capping the
 # outside rings would incorrectly add horizontal disks through the roof.
 roof.faces=roof.faces[:-2]
 for i in range(8):roof.faces.append((56+i,56+(i+1)%8,(i+1)%8,i))
 roof.finish()
 timber=Batch('bandstand_eight_posts_beams_and_knee_braces',mats['timber'],'way/1367310699');posts=bandring(.84,0)
 for i,p in enumerate(posts):
  timber.box(p+Vector((0,0,.23)),p+Vector((0,0,3.66)),.26,.30)
  q=posts[(i+1)%8];timber.box(p+Vector((0,0,3.46)),q+Vector((0,0,3.46)),.24,.27)
  for sign in [-1,1]:
   q=posts[(i+sign)%8];u=(q-p).normalized();timber.box(p+Vector((0,0,2.72)),p+u*.85+Vector((0,0,3.46)),.15)
   timber.box(p+u*.32+Vector((0,0,.23)),p+Vector((0,0,.72)),.12)
 timber.finish()
 fascia=Batch('bandstand_eave_fascia',mats['fascia'],'way/1367310699')
 for i,p in enumerate(br):fascia.box((*p,3.34),(*br[(i+1)%8],3.34),.13,.18)
 fascia.finish()
 finial=Batch('bandstand_roof_finial',mats['timber'],'way/1367310699');finial.box((*center[:2],6.25),(*center[:2],6.75),.11);finial.finish()
 # Cafe roof and glazed timber envelope occupy its archived rectangle. No
 # invented branded lettering, seating, or current operation is represented.
 cr=ring_xy('way/31694141');origin=Vector((*cr[0],0));u=(Vector((*cr[1],0))-origin);length=u.length;u.normalize();v=Vector((*cr[3],0))-origin;width=v.length;v.normalize()
 def cp(x,y,z):return origin+u*x+v*y+Vector((0,0,z))
 base=Batch('cafe_ground_plinth_and_sills',mats['plinth'],'way/31694141');base.poly(cr,.05,.28);base.finish()
 timber=Batch('cafe_timber_bays_and_gable_frames',mats['timber'],'way/31694141');glass=Batch('cafe_opaque_window_recesses',mats['window'],'way/31694141')
 bays=18
 for y in [.10,width-.10]:
  for i in range(bays+1):
   x=.10+(length-.20)*i/bays;timber.box(cp(x,y,.28),cp(x,y,3.12),.135)
  for z in [.40,2.93,3.10]:timber.box(cp(.1,y,z),cp(length-.1,y,z),.14)
  # Large recessed planes have opaque daylight tint; no alpha/transparent costs.
  for i in range(bays):
   a=.10+(length-.20)*i/bays+.07;b=.10+(length-.20)*(i+1)/bays-.07
   glass.box(cp(a,y,.0)+Vector((0,0,1.66)),cp(b,y,0)+Vector((0,0,1.66)),.035,2.45)
 for x in [.10,length-.10]:
  for y in [width*i/5 for i in range(6)]:timber.box(cp(x,y,.28),cp(x,y,3.12),.14)
  for y in [0,width]:timber.box(cp(x,y,3.1),cp(x,width/2,4.32),.16)
  timber.box(cp(x,0,3.05),cp(x,width,3.05),.17)
  glass.box(cp(x,.08,1.65),cp(x,width-.08,1.65),.04,2.45)
 timber.finish();glass.finish()
 # A closed folded metal roof stays within the mapped footprint.
 metal=Batch('cafe_closed_low_pitched_metal_roof',mats['metal_roof'],'way/31694141')
 section=[(0,3.10),(width/2,4.36),(width,3.10),(width,3.00),(width/2,4.26),(0,3.00)]
 metal.shell([[cp(x,y,z)for y,z in section]for x in [0,length]]);metal.finish()
 ribs=Batch('cafe_metal_roof_standing_seams',mats['metal_roof'],'way/31694141')
 for i in range(1,27):
  x=length*i/27
  for y0,y1,z0,z1 in [(0,width/2,3.12,4.38),(width/2,width,4.38,3.12)]:ribs.box(cp(x,y0,z0),cp(x,y1,z1),.023,.032)
 ribs.finish()
 # Preserve all untouched grass triangles and their original UVs exactly. Cut
 # faces alone receive barycentric UV interpolation at the same native datum.
 inp=json.loads(INPUT.read_text());rows=[f for f in inp['faces']if f['index']not in set(plan['touchedFaces'])]+plan['retainedCutFaces'];vertices=[];faces=[]
 for f in rows:
  start=len(vertices);vertices.extend(f['vertices']);faces.append(tuple(start+i for i in range(len(f['vertices']))))
 retained=source.copy();retained.data=bpy.data.meshes.new('PARK233_retained_park_grass_mesh');retained.name='PARK233_Park_grass_outside_mapped_bandstand_hardstanding';retained.data.from_pydata(vertices,[],faces);retained.data.update()
 for m in source.data.materials:retained.data.materials.append(m)
 for uvname in inp['uvNames']:
  uv=retained.data.uv_layers.new(name=uvname)
  for f,row in zip(retained.data.polygons,rows):
   for li,xy in zip(f.loop_indices,row['uvs'][uvname]):uv.data[li].uv=xy
 for f,row in zip(retained.data.polygons,rows):f.material_index=row['material'];f.use_smooth=row['smooth']
 bpy.data.collections[OWNER].objects.link(retained);retained['destinationCollection']=OWNER;retained['originalObject']=GROUND;retained['sourceOsmFacility']='way/28531258+way/896810427';added.append(retained)
 plaza=Batch('bandstand_mapped_circular_hardstanding',mats['gravel'],'way/28531258+way/896810427')
 for t in plan['plazaTriangles']:
  start=len(plaza.vertices);plaza.vertices.extend((*p,.05)for p in t);plaza.faces.append(tuple(start+i for i in range(3)))
 plaza_obj=plaza.finish();update_scene()
 # Check actual saved meshes against fixed native sources, not photographs.
 bounds=lambda o:([min((o.matrix_world@Vector(c))[i]for c in o.bound_box)for i in range(3)],[max((o.matrix_world@Vector(c))[i]for c in o.bound_box)for i in range(3)])
 groundtree=tree(triangles(source));supports=[]
 for identity,ring in [('way/1367310699',br),('way/31694141',cr)]:
  for xy in ring:
   hit=groundtree.ray_cast(Vector((*xy,.20)),Vector((0,0,-1)),.3)
   assert hit[0] is not None and abs(hit[0].z-.05)<1e-5,(identity,xy,hit)
   supports.append(dict(facility=identity,xy=xy,nativeSupportObject=GROUND,supportZ=hit[0].z,newBaseZ=.05,verticalGapM=abs(hit[0].z-.05)))
 collision_checks=[]
 protected_tree_names=['03_PUBLIC_REALM_Plane_tree_trunk','SITE232_LIF_fifty_continuous_organic_crowns']
 for o in added:
  if o in [retained,plaza_obj]:continue
  lo,hi=bounds(o);ot=tree(triangles(o))
  for name in protected_tree_names:
   other=bpy.data.objects[name];hits=ot.overlap(tree(triangles(other)));assert not hits,(o.name,name,len(hits));collision_checks.append(dict(addedObject=o.name,protectedTreeObject=name,actualTriangleIntersections=0))
 # Finite volume and closedness for every structure component. Ground remains
 # the original model's planar surface convention, with no depth offset.
 closed=[]
 for o in added:
  if o not in [retained,plaza_obj]:closed.extend(dict(object=o.name,**r)for r in solids(o))
 fingerprints={o.name:object_fingerprint(o)for o in added};bindings={o.name:[m.name for m in o.data.materials]for o in added};materials={m.name:material_fingerprint(m)for o in added for m in o.data.materials}
 preserve(before)
 component=OUT/'component.blend';bpy.data.libraries.write(str(component),set(added),fake_user=True,compress=True);component_sha=sha(component)
 # Independent reopen validates serialization before any review visibility.
 bpy.ops.wm.open_mainfile(filepath=str(component))
 assert all(object_fingerprint(bpy.data.objects[n])==v for n,v in fingerprints.items())
 assert all(material_fingerprint(bpy.data.materials[n])==v for n,v in materials.items())
 write(OUT/'reopened-verification.json',dict(componentSha256=component_sha,addedObjectsVerified=len(fingerprints),allGeometryUVsBindingsNodesVerified=True,sourceSha256=SHA))
 bpy.ops.wm.open_mainfile(filepath=str(BASE));update_scene()
 with bpy.data.libraries.load(str(component),link=False)as(_,dst):dst.objects=list(fingerprints)
 added=dst.objects
 for o in added:
  for i,n in enumerate(bindings[o.name]):
   if n in before['materials']:o.data.materials[i]=bpy.data.materials[n]
  # Library imports do not carry collection ownership. Explicit destination is
  # stored on every object and applies in the standard194integrator.
  bpy.data.collections[OWNER].objects.link(o)
 update_scene();assert all(object_fingerprint(bpy.data.objects[n])==v for n,v in fingerprints.items());preserve(before)
 write(OUT/'independent-verification.json',dict(componentSha256=component_sha,baselineSha256=SHA,baselineObjectsVerified=len(before['objects']),baselineMaterialsVerified=len(before['materials']),protectedSpacesVerified=len(before['rooms']),protectedSpaceObjectsVerified=len(set().union(*(set(v)for v in before['rooms'].values()))),baselineGeometryUVTransformsModifiersPropertiesOwnersAndVisibilityUnchanged=True,appendedComponentFingerprintsVerified=True))
 views=render_reviews(archived,added);preserve(before)
 refs=[dict(path=p,sha256=h)for p,h in plan['sourceHashes'].items()]
 write(DATA/'sources.json',dict(version=233,baselineSha256=SHA,sources=refs,photographs=[dict(url='https://www.geograph.org.uk/photo/7222768',local='bandstand-stephen-craven-20220601.jpg',author='Stephen Craven',captureDate='2022-06-01',license='CC-BY-SA-2.0',role='Primary photograph: open eight-post dark timber shelter, knee braces, steep octagonal tiled roof, low octagonal ground plinth and surrounding hardstanding',pixelsReused=False),dict(url='https://www.blb.uk.com/wp-content/uploads/2023/07/Details-Cafe-Lincolns-Inn-Fields-WC2A.pdf',local='cafe-letting-2023.pdf',publisher='Blanchflower Lloyd Baxter, sole letting agents for Camden landlord',publicationDateEvidence='URL directory2023/07; rateable-value2023/24 text',photoCaptureDate='unspecified',role='Single floor cafe next to courts; timber/glazed exterior, low metal pitched roof; archival tenant FIELDSpictured, not current operator appearance survey',pixelsReused=False)],currentOperator=dict(url='https://www.peartreecafe.co.uk/lincolnsinn',checkedDate='2026-10-17',local='operator-lincolnsinn.html',role='Identity and location only; no dimensions inferred'),osmDate='Archive retrieved2026-09-12; bandstand mapped2025-03-14; cafe tags updated2026-01-10; path surface checks2025-09-25',dimensionPolicy='OSM footprints and native ground datum fixed. Heights, material colours, bay count, brace sizes, roof pitches and detailing are source-based estimates, not measured drawings.',privateResearchOnly=True,noSourcePhotoTextures=True))
 write(OUT/'support-and-solid-proof.json',dict(nativeGroundSupports=supports,groundDatumM=.05,existingPathDatumM=.024,noPathMoved=True,noOffsetGroundLayer=True,plazaReplacesGrassAtSameDatum=True,plazaAreaM2=plan['plazaAreaM2'],plazaPathIntersectionM2=plan['plazaPathIntersectionM2'],treeSoilHoles=plan['plazaTreeHoles'],closedPositiveVolumeSolids=closed,treeCollisionChecks=collision_checks,bandstandConnections=dict(postBottomZ=.23,plinthTopZ=.23,postTopZ=3.66,approximateRoofUndersideAtPostZ=3.66,beamCentreZ=3.46,kneeBraceTopZ=3.46),untouchedSourceGrassFacesRetained=len(inp['faces'])-len(plan['touchedFaces']),sourceGrassCutFaceCount=len(plan['touchedFaces']),cutFaceUVs='Barycentric interpolation; untouched source coordinates and UVs copied exactly'))
 write(OUT/'audit.json',dict(version=233,authoringScript='web/tools/refine_park_public233.py',authoringScriptSha256=sha(Path(__file__)),baseline=str(BASE.relative_to(ROOT)),baselineSha256=SHA,componentPath=str(component.relative_to(ROOT)),componentSha256=component_sha,targetCollection=OWNER,destinationCollection=OWNER,addedObjects=list(fingerprints),archivedObjects=archived,changedObjects=[],addedFingerprints=fingerprints,replacementMaterialBindings=bindings,addedMaterialFingerprints=materials,sourceHashes=plan['sourceHashes'],sourceManifest='data/collections/park-public233/sources.json',supportProof='result/blender/park-public233/support-and-solid-proof.json',objectOwners={n:OWNER for n in fingerprints},archiveOwners={n:before['owners'][n]for n in archived},originalProxyIdentities=[dict(osm=r['id'],properties=r['properties'],areaM2=r['area'],scope='Preserved unnamed1storey proxy'if r['id']=='way/301471946'else'Replaced exact footprint')for r in plan['buildings']],verification=dict(componentReopened=True,componentAppendedToExactBaseline=True,all8502OriginalObjectsPreserved=True,all34SpacesPreserved=True,originalGeometryUVsTransformsBindingsNodesModifiersPropsOwnershipAndVisibilityPreserved=True,all50AcceptedParkCrownsAndTrunksPreserved=True,noAcceptedPathChanges=True,noFullNativeSaved=True),budget=dict(objects=len(added),vertices=sum(len(o.data.vertices)for o in added),triangles=sum(len(triangles(o))for o in added),newMaterials=len(mats),noTextureImagesAdded=True,noAlphaMaterials=True),cameras=views,previews=[p+'-'+v['name']+'.png'for v in views for p in ['before','after']],gallerySuggestions=[dict(code='CAMPUS',name='LIF-park-public',label='Lincoln’s Inn Fields公共建筑',view=dict(position=[-84,24,-88],target=[-4,2.8,-174],fov=58))],scope='Recover source-identified open bandstand and one-storey cafe envelope; mapped bandstand hardstanding replaces only bounded grass area at original datum. All accepted footways, fifty crowns, trunks and unnamed small structure remain untouched.',limitations=['Bandstand2022photograph and cafe2023letting brochure are historical evidence; no claim of2026as-built survey.','Cafe photograph capture date is unknown. Its prior tenant signage is not reproduced.','Building footprints follow archived OSM; cafe bay counts, unseen rear/end glazing layout, roof structure and heights are estimated envelope presentation.','Bandstand hardstanding boundary follows mapped surrounding circle, not a photographed measured paving survey; three original tree positions retain0.55msoil holes.','Nearby unidentified36.25m²one-storey service proxy retains its original estimated5.25mheight and geometry.']))
 assert sha(BASE)==SHA and sha(component)==component_sha
 print('PARK233_COMPLETE',component_sha,len(added),flush=True)

def render_reviews(archived,owned):
 import bpy,math
 from mathutils import Vector
 from integrate_exterior_round194 import update_scene
 s=bpy.data.scenes['00_CAMPUS_COMPLETE'];bpy.context.window.scene=s
 c=bpy.data.objects.new('PARK233_REVIEW_CAMERA',bpy.data.cameras.new('PARK233_REVIEW_CAMERA'));s.collection.objects.link(c);s.camera=c;c.data.clip_end=1800;c.data.sensor_fit='VERTICAL'
 s.render.engine='BLENDER_EEVEE';s.render.resolution_x=1100;s.render.resolution_y=825;s.render.resolution_percentage=100;s.render.image_settings.file_format='PNG'
 for o in s.objects:
  if o.hide_render:o.hide_set(True)
 views=[dict(name='LIF-park-public',eye=[-84,88,24],target=[-4,174,2.8],fov=58),dict(name='bandstand',eye=[-12,164,7.2],target=[10.45,184.37,3.0],fov=54)]
 for v in views:
  eye=Vector(v['eye']);target=Vector(v['target']);c.location=eye;c.rotation_euler=(target-eye).to_track_quat('-Z','Y').to_euler();c.data.lens=c.data.sensor_height/(2*math.tan(math.radians(v['fov'])/2))
  for phase in ['before','after']:
   for n in archived:bpy.data.objects[n].hide_render=phase=='after';bpy.data.objects[n].hide_set(phase=='after')
   for o in owned:o.hide_render=phase=='before';o.hide_set(phase=='before')
   update_scene();s.render.filepath=str(OUT/(phase+'-'+v['name']+'.png'));bpy.ops.render.render(write_still=True)
 for n in archived:bpy.data.objects[n].hide_render=False;bpy.data.objects[n].hide_set(False)
 for o in owned:o.hide_render=False;o.hide_set(False)
 bpy.data.objects.remove(c,do_unlink=True);bpy.data.cameras.remove(bpy.data.cameras['PARK233_REVIEW_CAMERA'])
 return views

if __name__=='__main__':
 try:import bpy
 except ModuleNotFoundError:prepare()
 else:
  if PLAN.exists():build()
  else:capture()
