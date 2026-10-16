"""SAL public entrance structure from built project photographs. Fixed authoring."""
from pathlib import Path
import hashlib,json,sys
import bpy
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'result/blender/LSE_campus_detailed_v220.blend'
SHA='974c47b4af06a6caa5f474c1c75e05ffb4084285cb1ef8a4ceb11bd93738f6c0'
OUT=ROOT/'result/blender/sal-structure221'
PREFIX='SAL221_'
sys.path.insert(0,str(ROOT/'web/tools'))
from integrate_exterior_round194 import accepted_fingerprints,object_fingerprint
from refine_portsmouth_exterior207 import material_fingerprint


def update():
 for scene in bpy.data.scenes:
  for layer in scene.view_layers:layer.update()


def inspect():
 assert hashlib.sha256(BASE.read_bytes()).hexdigest()==SHA
 bpy.ops.wm.open_mainfile(filepath=str(BASE));bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE'];update()
 expected=accepted_fingerprints(ROOT/'result/blender/stage220',SHA)
 assert {o.name:object_fingerprint(o)for o in bpy.data.objects}==expected
 rows=[]
 for c in bpy.data.collections:
  if 'SAL'not in c.name:continue
  objects=[]
  for o in c.all_objects:
   if o.hide_render:continue
   points=[o.matrix_world@Vector(p)for p in o.bound_box]
   objects.append(dict(name=o.name,matrix=[list(row)for row in o.matrix_world],localBounds=[list(v)for v in o.bound_box],type=o.type,materials=[m.name if m else None for m in getattr(o.data,'materials',[])],bounds=[[min(p[i]for p in points),max(p[i]for p in points)]for i in range(3)]))
  rows.append(dict(collection=c.name,objects=objects))
 (OUT/'inspection.json').write_text(json.dumps(rows,indent=2)+'\n')
 print('SAL221_INSPECTED',len(expected),flush=True)



COLLECTION='SAL_EXTERIOR'
ROOF='GLASS181_SAL_Glass_pavilion_roof'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def registration():
 import math
 angle=math.radians(24.35)
 right=Vector((-math.cos(angle),-math.sin(angle),0));inward=Vector((math.sin(angle),-math.cos(angle),0))
 source=bpy.data.objects[ROOF]
 pts=[source.matrix_world@vertex.co for vertex in source.data.vertices]
 origin=sum(pts,Vector())/len(pts);origin.z=0
 xs=[(point-origin).dot(right)for point in pts];ys=[(point-origin).dot(inward)for point in pts]
 return origin,right,inward,(min(xs),max(xs),min(ys),max(ys))


def world(x,y,z):
 origin,right,inward,_=registration();return origin+right*x+inward*y+Vector((0,0,z))


class Batch:
 def __init__(self,name,material):self.name=PREFIX+name;self.material=material;self.vertices=[];self.faces=[]
 def solid(self,points,faces):
  start=len(self.vertices);self.vertices.extend(world(*point)for point in points);self.faces.extend(tuple(start+i for i in face)for face in faces)
 def box(self,low,high):
  x,y,z=low;X,Y,Z=high
  self.solid([(x,y,z),(X,y,z),(X,Y,z),(x,Y,z),(x,y,Z),(X,y,Z),(X,Y,Z),(x,Y,Z)],[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)])
 def beam(self,a,b,width):
  a,b=Vector(a),Vector(b);axis=(b-a).normalized();ref=Vector((0,0,1))
  if abs(axis.dot(ref))>.95:ref=Vector((1,0,0))
  side=axis.cross(ref).normalized()*width/2;other=axis.cross(side).normalized()*width/2
  points=[p+side*s+other*t for p in [a,b]for s,t in [(-1,-1),(1,-1),(1,1),(-1,1)]]
  self.solid(points,[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)])
 def column(self,x,y,low,high,radius,segments=12):
  import math
  pts=[(x+radius*math.cos(i*math.tau/segments),y+radius*math.sin(i*math.tau/segments),z)for z in [low,high]for i in range(segments)]
  faces=[tuple(reversed(range(segments))),tuple(range(segments,segments*2))]+[(i,(i+1)%segments,(i+1)%segments+segments,i+segments)for i in range(segments)]
  self.solid(pts,faces)
 def triangle(self,points,thickness):
  pts=[tuple(p)for p in points]+[(p[0],p[1],p[2]+thickness)for p in points]
  self.solid(pts,[(0,2,1),(3,4,5),(0,1,4,3),(1,2,5,4),(2,0,3,5)])
 def finish(self):
  import bmesh
  mesh=bpy.data.meshes.new(self.name);mesh.from_pydata(self.vertices,[],self.faces);mesh.materials.append(self.material);mesh.update()
  bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free()
  obj=bpy.data.objects.new(self.name,mesh);bpy.data.collections[COLLECTION].objects.link(obj)
  obj['destinationCollection']=COLLECTION;obj['scope']='Photographed2012built entrance pavilion features; footprint and datum inherited, dimensions estimated; no full interior claim'
  return obj


def material(name,color,roughness,metallic=0):
 m=bpy.data.materials.new(PREFIX+name);m.diffuse_color=(*color,1);m.use_nodes=True
 shader=m.node_tree.nodes.get('Principled BSDF');shader.inputs['Base Color'].default_value=m.diffuse_color;shader.inputs['Roughness'].default_value=roughness;shader.inputs['Metallic'].default_value=metallic
 m['webSurfaceRole']='opaque';return m


def build():
 white=material('white_painted_structure',(.79,.79,.75),.42)
 tile=material('warm_grey_limestone_floor',(.52,.50,.44),.67)
 oak=material('light_oak_reception',(.49,.31,.13),.5)
 steel=material('brushed_stainless_gates',(.43,.45,.45),.31,.78)
 dark=material('gate_reader_and_counter_worktop',(.035,.04,.045),.41)
 shade=material('white_sail_panels',(.82,.82,.79),.64)
 batches={name:Batch(name,mat)for name,mat in [('floor',tile),('white_supports',white),('roof_triangular_panels',shade),('reception_oak',oak),('reception_base',white),('access_gate_steel',steel),('counter_and_readers',dark)]}
 # Fit inherited glazed-shell boundary; do not extrapolate the actual full passage.
 batches['floor'].box((-2.31,-2.70,.00),(2.31,2.70,.10))
 b=batches['white_supports'];s=batches['roof_triangular_panels'];records=[]
 for start in [-2.64,-.87,.90]:
  low=start;tip=start+1.53;post=(0,tip,3.00)
  b.column(0,tip,.10,3.00,.075)
  left=(-2.27,low,3.235);right=(2.27,low,3.235)
  b.beam(left,post,.07);b.beam(post,right,.07);b.beam(left,right,.065)
  s.triangle([left,right,post],.022)
  # Each photo-supported inverted triangular panel has a real central support.
  records.append(dict(panelCorners=[left,right,post],postCentre=[0,tip],postBottom=.10,postTop=3.00,estimatedPostDiameter=.15))
 # Longitudinal white roof-edge liners, below the original roof glass and frame.
 b.box((-2.29,-2.70,3.19),(-2.20,2.70,3.25));b.box((2.20,-2.70,3.19),(2.29,2.70,3.25))
 # Reception remains behind the existing front doors and beside the clear bypass.
 batches['reception_base'].box((.15,1.20,.10),(1.99,1.94,.27))
 batches['reception_oak'].box((.10,1.15,.27),(2.04,1.99,1.04))
 batches['reception_oak'].box((.10,1.15,1.04),(2.04,1.34,1.16))
 batches['counter_and_readers'].box((.15,1.35,1.035),(1.99,1.94,1.065))
 # Three lanes indicated by four narrow rounded gate chassis in the photographs.
 gates=[]
 for x in [-.10,.61,1.32,2.03]:
  batches['access_gate_steel'].column(x,-.72,.10,1.07,.105,12)
  batches['access_gate_steel'].column(x,.02,.10,1.07,.105,12)
  batches['access_gate_steel'].box((x-.105,-.72,.10),(x+.105,.02,1.07))
  batches['counter_and_readers'].box((x-.065,-.76,1.07),(x+.065,-.58,1.095))
 for left,right in zip([-.10,.61,1.32],[.61,1.32,2.03]):
  mid=(left+right)/2
  batches['access_gate_steel'].box((left+.105,-.38,.34),(mid-.014,-.35,.99))
  batches['access_gate_steel'].box((mid+.014,-.38,.34),(right-.105,-.35,.99))
  gates.append(dict(leftChassis=left,rightChassis=right,clearWidth=right-left-.21,closedFlaps=True))
 owned=[batch.finish()for batch in batches.values()]
 return owned,dict(roofSupports=records,accessLanes=gates,uncontrolledBypassWidth=2.31-0.205,finishedFloorTop=.10,frontDoorOriginalBottom=.105,receptionCounterTop=1.16)


def stable_modifiers(obj):
 def stable(value):
  if isinstance(value,bpy.types.ID):return(value.bl_rna.identifier,value.name)
  if value is None or isinstance(value,(bool,int,float,str)):return value
  if hasattr(value,'to_list'):return value.to_list()
  try:return list(value)
  except TypeError:return str(value)
 return[(m.name,m.type,[(p.identifier,stable(getattr(m,p.identifier,None)))for p in m.bl_rna.properties if not p.is_readonly and p.identifier!='rna_type'])for m in obj.modifiers]


def rooms_state():
 metadata=json.loads((ROOT/'web/tools/building-metadata.json').read_text());rows=[]
 for room in metadata['spaces']:
  c=bpy.data.collections.get(room['collection'])
  if c:rows.append(dict(collection=c.name,objects=sorted(o.name for o in c.all_objects),memberships={o.name:sorted(v.name for v in o.users_collection)for o in c.all_objects},scenes=sorted(s.name for s in bpy.data.scenes if c.name in s.collection.children)))
 return rows


def render_views(label):
 scene=bpy.data.scenes.new(PREFIX+'REVIEW');scene.collection.children.link(bpy.data.collections[COLLECTION]);bpy.context.window.scene=scene
 w=bpy.data.worlds.new(scene.name);w.use_nodes=True;w.node_tree.nodes['Background'].inputs[0].default_value=(.78,.81,.85,1);w.node_tree.nodes['Background'].inputs[1].default_value=.65;scene.world=w
 ld=bpy.data.lights.new(scene.name,'SUN');ld.energy=2;ld.angle=.13;sun=bpy.data.objects.new(scene.name+'_sun',ld);scene.collection.objects.link(sun);sun.rotation_euler=(.4,-.5,-.1)
 cd=bpy.data.cameras.new(scene.name);camera=bpy.data.objects.new(scene.name+'_camera',cd);scene.collection.objects.link(camera);scene.camera=camera
 cd.lens=24;cd.clip_end=300
 scene.render.engine='CYCLES';scene.cycles.samples=24;scene.cycles.use_denoising=True
 scene.render.resolution_x=960;scene.render.resolution_y=880;scene.render.resolution_percentage=100;scene.view_settings.view_transform='AgX';scene.render.image_settings.file_format='PNG'
 views=[]
 for name,position,target in [('front',(0,-8,2.35),(0,.8,1.65)),('inside',(-1.7,-2.42,1.72),(.4,1.2,1.8))]:
  camera.location=world(*position);focus=world(*target);camera.rotation_euler=(focus-camera.location).to_track_quat('-Z','Y').to_euler();scene.render.filepath=str(OUT/(label+'-'+name+'.png'));bpy.ops.render.render(write_still=True);views.append(dict(name=name,position=list(camera.location),target=list(focus),lens=24))
 bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE']
 for obj in [camera,sun]:bpy.data.objects.remove(obj,do_unlink=True)
 bpy.data.scenes.remove(scene);bpy.data.worlds.remove(w);bpy.data.cameras.remove(cd);bpy.data.lights.remove(ld);update()
 return views


def verify_structure(owned,dimensions):
 from mathutils.bvhtree import BVHTree
 source=bpy.data.objects[ROOF];verts=[source.matrix_world@v.co for v in source.data.vertices];faces=[tuple(f.vertices)for f in source.data.polygons];roof=BVHTree.FromPolygons(verts,faces)
 slab=next(obj for obj in owned if obj.name==PREFIX+'floor');floor=BVHTree.FromPolygons([slab.matrix_world@v.co for v in slab.data.vertices],[tuple(f.vertices)for f in slab.data.polygons])
 rows=[]
 for record in dimensions['roofSupports']:
  x,y=record['postCentre'];hit=floor.ray_cast(world(x,y,.25),Vector((0,0,-1)),.3);assert hit[0]is not None and abs(hit[0].z-.10)<1e-4
  rows.append(dict(post=[x,y],floorHeight=hit[0].z))
  for corner in record['panelCorners']:
   hit=roof.ray_cast(world(corner[0],corner[1],corner[2]+.001),Vector((0,0,1)),.5);assert hit[0]is not None
   rows.append(dict(panelPoint=corner,roofHeight=hit[0].z,verticalGap=hit[3]))
 # All new floor-bearing members have actual surface support after saving.
 floor_contacts=[]
 points=[('column',(0,r['postCentre'][1]))for r in dimensions['roofSupports']]
 points += [('gate',(x,y))for x in [-.10,.61,1.32,2.03]for y in [-.72,.02]]
 points += [('reception',(x,y))for x in [.20,1.94]for y in [1.25,1.89]]
 for feature,(x,y)in points:
  hit=floor.ray_cast(world(x,y,.23),Vector((0,0,-1)),.20);assert hit[0]is not None and abs(hit[0].z-.10)<1e-4
  floor_contacts.append(dict(feature=feature,localPosition=[x,y],supportHeight=hit[0].z))
 vertices=[];polygons=[]
 for obj in owned:
  if obj==slab:continue
  offset=len(vertices);vertices.extend(obj.matrix_world@v.co for v in obj.data.vertices);polygons.extend(tuple(offset+i for i in face.vertices)for face in obj.data.polygons)
 tree=BVHTree.FromPolygons(vertices,polygons);origin,right,inward,bounds=registration();paths=[]
 for x in [-1.9,-1.2,-.4]:
  for z in [.40,1.20,2.20]:
   hit=tree.ray_cast(world(x,-2.55,z),inward,5.05);assert hit[0]is None,('Blocked left bypass',x,z,hit)
   paths.append(dict(kind='left bypass',x=x,height=z,lengthMetres=5.05,hit=False))
 for x in [-1.,-.5,0,.5,1.]:
  for z in [.4,1.2,2.2]:
   hit=tree.ray_cast(world(x,-2.67,z),inward,1.42);assert hit[0]is None,('New object blocks door vestibule',x,z,hit)
   paths.append(dict(kind='retained door vestibule',x=x,height=z,lengthMetres=1.42,hit=False))
 return dict(postFloorAndPanelRoofSupportProbes=rows,actualFloorContactProbes=floor_contacts,newGeometryClearanceRays=paths,postCount=3,continuousFloor=True,leftBypassClearWidth=2.105,doorSillToFloor=.005,scope='Actual saved mesh support and clearance, original closed doors excluded from open-aperture check; dimensions estimated, no egress or accessibility certification')


def run():
 inspect();originals={o.name:object_fingerprint(o)for o in bpy.data.objects};materials={m.name:material_fingerprint(m)for m in bpy.data.materials};modifiers={o.name:stable_modifiers(o)for o in bpy.data.objects};visibility={o.name:o.hide_render for o in bpy.data.objects};rooms=rooms_state();assert len(rooms)==19
 cameras=render_views('before');owned,dimensions=build();update();checks=verify_structure(owned,dimensions)
 assert render_views('after')==cameras
 assert all(object_fingerprint(bpy.data.objects[n])==v for n,v in originals.items());assert all(material_fingerprint(bpy.data.materials[n])==v for n,v in materials.items());assert rooms_state()==rooms
 fingerprints={o.name:object_fingerprint(o)for o in owned};bindings={o.name:[m.name for m in o.data.materials]for o in owned};component=OUT/'component.blend';bpy.data.libraries.write(str(component),set(owned),fake_user=True,compress=True)
 bpy.ops.wm.open_mainfile(filepath=str(BASE));bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE'];update();assert{obj.name:object_fingerprint(obj)for obj in bpy.data.objects}==accepted_fingerprints(ROOT/'result/blender/stage220',SHA)
 with bpy.data.libraries.load(str(component),link=False)as(src,dst):dst.objects=list(fingerprints)
 for obj in dst.objects:
  for i,name in enumerate(bindings[obj.name]):obj.data.materials[i]=bpy.data.materials[name]
  bpy.data.collections[COLLECTION].objects.link(obj)
 update();assert all(object_fingerprint(bpy.data.objects[n])==v for n,v in originals.items());assert all(object_fingerprint(bpy.data.objects[n])==v for n,v in fingerprints.items());assert all(material_fingerprint(bpy.data.materials[n])==v for n,v in materials.items());assert all(stable_modifiers(bpy.data.objects[n])==v for n,v in modifiers.items());assert all(bpy.data.objects[n].hide_render==v for n,v in visibility.items());assert rooms_state()==rooms
 assert verify_structure(dst.objects,dimensions)==checks
 references=[]
 for name in ['SAL_6fc777f9f01e.jpg','SAL_a4d4dae75d52.jpg','SAL_5b39324ea103.jpg']:
  p=ROOT/'data/collections/library_round5/photos'/name;references.append(dict(path=str(p.relative_to(ROOT)),sha256=sha(p),source='https://www.jesticowhiles.com/project/lincolns-inn-fields-london-school-of-economics/',stage='2012built project, photo capture date unspecified',distribution='Private reference only; no public texture'))
 p=ROOT/'data/collections/interiors/originals/2012-32LIF.pdf';references.append(dict(path=str(p.relative_to(ROOT)),sha256=sha(p),source='https://info.lse.ac.uk/staff/divisions/estates-division/Assets/Documents/Cap-Dev/2012-32LIF.pdf',stage='Official2012project record; March-December2012construction, side glass extension for level entry; not a current survey'))
 verification=dict(savedComponentReopened=True,acceptedSourceObjects=len(originals),sourceMaterialNodesVerified=len(materials),sourceModifierStacksVerified=len(modifiers),allOriginalGeometryUVTransformBindingsAndVisibilityPreserved=True,roomCollectionsPreserved=len(rooms),roomUniqueObjectsPreserved=len(set(n for r in rooms for n in r['objects'])),roomObjectCollectionAndSceneMembershipsPreserved=True,baselineUnchanged=sha(BASE)==SHA)
 report=dict(defaultInterior='ExistingSAL.G.01classroom sample remains unchanged; the new public pavilion belongs to whole-building exterior.',version=221,baseline=str(BASE.relative_to(ROOT)),baselineSha256=SHA,componentPath=str(component.relative_to(ROOT)),componentSha256=sha(component),targetCollection=COLLECTION,destinationCollection=COLLECTION,addedObjects=list(fingerprints),archivedObjects=[],changedObjects=[],addedFingerprints=fingerprints,replacementMaterialBindings=bindings,scope='Photo-supported public entrance pavilion insert: continuous slab, three white triangular roof shade/support assemblies, light oak reception and three stainless gate lanes within inherited envelope. Retain the historic facade, all original roof glass and frames, no replacement of room samples.',dimensions=dimensions,checks=checks,references=references,verification=verification,previews=['before-front.png','after-front.png','before-inside.png','after-inside.png'],cameras=cameras,galleryViewSuggestion=dict(code='SAL',name='sal-public-entrance',label='玻璃入口亭与公共接待',view=dict(position=[cameras[1]['position'][0],cameras[1]['position'][2],-cameras[1]['position'][1]],target=[cameras[1]['target'][0],cameras[1]['target'][2],-cameras[1]['target'][1]],fov=69.02)),limitations=['Existing pavilion footprint about4.75x5.5m and3.3mroof datum are inherited estimates, not independently surveyed; this is a bounded public-entry insert rather than complete registration of the real passage.','Triangle shade geometry, post diameters, counter dimensions and gate spacings are photograph proportions fitted within the retained shell; not engineering or accessibility certification.','2012built project and current website publication do not establish2026current interiors.','Upper floors, exact connections into the historic building, full foyer depth, lifts and unseen rooms remain unbuilt and unverified.','Source photographs are private visual references; no photography or artwork is redistributed as a texture.'])
 (OUT/'audit.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n');(OUT/'verification.json').write_text(json.dumps(verification,indent=2)+'\n');print('SAL221_COMPONENT_REOPENED',len(owned),len(originals),len(materials),flush=True)


def validate_saved_component():
 """Reopen the written component for additional literal floor and aperture rays."""
 report=json.loads((OUT/'audit.json').read_text());assert report['componentSha256']==sha(ROOT/report['componentPath'])
 inspect();expected=accepted_fingerprints(ROOT/'result/blender/stage220',SHA)
 material_states={m.name:material_fingerprint(m)for m in bpy.data.materials};rooms=rooms_state();modifiers={o.name:stable_modifiers(o)for o in bpy.data.objects};visibility={o.name:o.hide_render for o in bpy.data.objects}
 with bpy.data.libraries.load(str(ROOT/report['componentPath']),link=False)as(src,dst):dst.objects=list(report['addedObjects'])
 for obj in dst.objects:
  for i,name in enumerate(report['replacementMaterialBindings'][obj.name]):obj.data.materials[i]=bpy.data.materials[name]
  bpy.data.collections[COLLECTION].objects.link(obj)
 update();report['checks']=verify_structure(dst.objects,report['dimensions'])
 assert all(object_fingerprint(bpy.data.objects[n])==v for n,v in expected.items());assert all(object_fingerprint(bpy.data.objects[n])==v for n,v in report['addedFingerprints'].items());assert all(material_fingerprint(bpy.data.materials[n])==v for n,v in material_states.items());assert all(stable_modifiers(bpy.data.objects[n])==v for n,v in modifiers.items());assert all(bpy.data.objects[n].hide_render==v for n,v in visibility.items());assert rooms_state()==rooms
 report['defaultInterior']='ExistingSAL.G.01classroom sample remains unchanged; the new public pavilion belongs to whole-building exterior.'
 suggestions=[]
 for index,name,label in [(1,'sal-public-entrance','玻璃入口亭与公共接待'),(0,'sal-entrance-exterior','公共入口与历史立面')]:
  camera=report['cameras'][index];suggestions.append(dict(code='SAL',name=name,label=label,view=dict(position=[camera['position'][0],camera['position'][2],-camera['position'][1]],target=[camera['target'][0],camera['target'][2],-camera['target'][1]],fov=69.02)))
 report['galleryViewSuggestions']=suggestions
 report['verification']['addedTriangles']=sum(len(face.vertices)-2 for obj in dst.objects for face in obj.data.polygons);report['verification']['actualSavedFloorContactProbes']=len(report['checks']['actualFloorContactProbes']);report['verification']['actualSavedDoorAndBypassClearanceRays']=len(report['checks']['newGeometryClearanceRays']);report['verification']['allOriginalPavilionGlassParametersPreserved']=True
 assert sha(BASE)==SHA
 (OUT/'audit.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n');(OUT/'verification.json').write_text(json.dumps(report['verification'],indent=2)+'\n');(OUT/'gallery-views-suggestion.json').write_text(json.dumps(suggestions,indent=2,ensure_ascii=False)+'\n')
 print('SAL221_SAVED_GEOMETRY_PROBES_PASSED',report['verification']['actualSavedFloorContactProbes'],report['verification']['actualSavedDoorAndBypassClearanceRays'],flush=True)


if __name__=='__main__':run()
