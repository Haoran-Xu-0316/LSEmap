"""MAR second-floor structure from built2022 drawings, preserving accepted222native.

Run directly in the approved Python runtime to prepare source geometry, then
in Blender's Text Editor to author/verify the small owned component.
"""
from pathlib import Path
import json,hashlib,math,sys
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'result/blender/mar-structure223'
DATA=ROOT/'data/collections/mar-structure223'
BASE=ROOT/'result/blender/LSE_campus_detailed_v222.blend'
SHA='0d31c829778d88d643d9b4001f28116730862e8703d81cb6ad0429f8113fb50b'
PREFIX='MAR223_'
COLLECTION='MAR_PUBLIC_INTERIOR_study'
LOWER=7.239999771118164
UPPER=12.8
SLAB_BOTTOM=12.48
SOURCE='data/collections/mar-built-registration-2026/grafton-marshall-built-plans-2022.pdf'

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def source_world(points):
 report=json.loads((ROOT/'result/blender/mar-registration217/audit.json').read_text())['geographicRegistration'];fit=report['secondPdfToNativeLocalCandidate']
 points=np.asarray(points);local=fit['scale']*points[:,::-1]@np.array(fit['rotation'])+np.array(fit['translation']);a=math.radians(22);u=np.array([math.cos(a),math.sin(a)]);n=np.array([-u[1],u[0]])
 return np.array(report['nativeOrigin'])+np.outer(local[:,0],u)+np.outer(local[:,1],n)


def prepare():
 from shapely.geometry import Polygon,Point
 from shapely.ops import unary_union
 from shapely import constrained_delaunay_triangles
 rows=json.loads((DATA/'native-source-surfaces.json').read_text());old=[r for r in rows if r['collection']==COLLECTION and r['name'].startswith('MAR_MAR_floor_way/')and abs(r['bounds'][2][0]-UPPER)<.001]
 assert len(old)==6
 native=unary_union([Polygon([row['points'][i][:2]for i in f])for row in old for f in row['faces']]).buffer(0)
 source_outline=[[187.3694,122.1588],[247.0934,122.1653],[247.0944,191.65],[222.8,200.5],[247.0944,219.0],[247.0944,300.3960],[93.9680,300.2492],[93.6028,220.6442]]
 outline=Polygon(source_world(source_outline));outer=outline.intersection(native).buffer(0);assert outer.geom_type=='Polygon'
 # Published curved perimeter is taken from source vectors, closed at its chord.
 curve=json.loads((DATA/'source-mainstair-aperture.json').read_text())
 stair=Polygon(source_world(curve['pts'])).buffer(0).simplify(.025,preserve_topology=True)
 diamond_pdf=[[189.237,193.934],[200.589,205.289],[189.237,216.6978],[177.8816,205.289]]
 diamond=Polygon(source_world(diamond_pdf));holes=[dict(id='main-stair',sourcePdf=curve['pts'],polygon=stair),dict(id='diamond-tree',sourcePdf=diamond_pdf,polygon=diamond)]
 floor=outer.difference(unary_union([h['polygon']for h in holes]));assert floor.geom_type=='Polygon'and len(floor.interiors)==2
 def pack(poly):
  tris=[list(t.exterior.coords)[:3]for t in constrained_delaunay_triangles(poly).geoms]
  assert abs(sum(Polygon(t).area for t in tris)-poly.area)<.00001
  return dict(boundary=[list(poly.exterior.coords)]+[list(r.coords)for r in poly.interiors],triangles=tris,areaSquareMetres=poly.area)
 first=next(r for r in rows if r['name']=='MAR217_coordinated_mezzanine_slab');first_floor=unary_union([Polygon([first['points'][i][:2]for i in f])for f in first['faces']if all(abs(first['points'][i][2]-LOWER)<.001 for i in f)]).buffer(0)
 controls=json.loads((DATA/'second-filled-controls.json').read_text());profiles=[];omitted=[]
 for i,row in enumerate(controls):
  x=(row['x0']+row['x1'])/2;y=(row['top']+row['bottom'])/2
  # These four large black cuts are the diamond tree branches, built separately.
  if 176<x<202 and 192<y<218:continue
  if row['x1']-row['x0']>6:continue
  p=Polygon(source_world(row['pts'])).buffer(0)
  if p.area<.05:continue
  if first_floor.buffer(.02).covers(p)and outer.buffer(.02).covers(p):profiles.append(dict(id=i,sourcePdf=row['pts'],profile=list(p.exterior.coords),centre=list(p.centroid.coords)[0]))
  else:omitted.append(dict(id=i,reason='Published profile extends beyond inherited first slab;do not invent support or change217slab'))
 centre=source_world([[189.237,205.289]])[0];assert first_floor.covers(Point(centre))
 tips=[]
 for p in source_world(diamond_pdf):
  axis=(p-centre)/np.linalg.norm(p-centre);tip=p+.24*axis;assert floor.covers(Point(tip));tips.append(tip.tolist())
 plan=dict(source=SOURCE,sourceSha256=sha(ROOT/SOURCE),sourceYear=2022,sourcePage=1,sourceFloor='second',sourceOutlinePdf=source_outline,outlineAccuracy='Source corner controls inherited217;notch source raster estimate;native boundary clipping prevents exterior protrusion',floor=pack(floor),archivedObjects=[r['name']for r in old],holes=[dict(id=h['id'],sourcePdf=h['sourcePdf'],world=list(h['polygon'].exterior.coords),areaSquareMetres=h['polygon'].area)for h in holes],columns=profiles,omittedColumns=omitted,tree=dict(centre=centre.tolist(),branchTips=tips,sourceCutProfiles=[r['pts']for r in controls if 176<(r['x0']+r['x1'])/2<202 and 192<(r['top']+r['bottom'])/2<218]),sourceFit=json.loads((ROOT/'result/blender/mar-registration217/audit.json').read_text())['geographicRegistration'])
 # These source-plan route segments stay in the white public commons.
 routes=[[[142,270],[196,270]],[[196,270],[196,234]],[[196,234],[179,223]],[[179,223],[173,210]],[[173,210],[173,193]],[[173,193],[192,153]],[[192,153],[210,153]],[[174,219],[149,219]],[[149,219],[145,236]],[[145,236],[145,264]]]
 plan['publicRoutes']=[source_world(r).tolist()for r in routes]
 (DATA/'structural-plan.json').write_text(json.dumps(plan,indent=2)+'\n');print('MAR223_PLAN',len(profiles),len(omitted),floor.area,flush=True)


try:import bpy
except ModuleNotFoundError:
 if __name__=='__main__':prepare()
else:
 from mathutils import Vector
 sys.path.insert(0,str(ROOT/'web/tools'))
 from integrate_exterior_round194 import object_fingerprint,accepted_fingerprints,update_scene,set_layer_hidden
 from refine_portsmouth_exterior207 import material_fingerprint
 from refine_sal_structure221 import stable_modifiers,rooms_state
 PLAN=json.loads((DATA/'structural-plan.json').read_text())

 class Batch:
  def __init__(self,name,material):self.name=PREFIX+name;self.material=material;self.vertices=[];self.faces=[]
  def add(self,points,faces):
   offset=len(self.vertices);self.vertices+=list(points);self.faces.extend(tuple(offset+i for i in f)for f in faces)
  def prism(self,ring,low,high):
   ring=list(ring)
   if ring[0]==ring[-1]:ring=ring[:-1]
   n=len(ring);self.add([(*p,z)for z in [low,high]for p in ring],[tuple(reversed(range(n))),tuple(range(n,n*2))]+[(i,(i+1)%n,(i+1)%n+n,i+n)for i in range(n)])
  def beam(self,a,b,width,depth=None):
   a,b=Vector(a),Vector(b);axis=(b-a).normalized();u=axis.cross(Vector((0,0,1)))
   if u.length<.001:u=Vector((1,0,0))
   u.normalize();v=axis.cross(u).normalized();depth=depth or width
   self.add([tuple(p+u*x*width/2+v*y*depth/2)for p in [a,b]for x,y in [(-1,-1),(1,-1),(1,1),(-1,1)]],[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)])
  def finish(self):
   import bmesh
   mesh=bpy.data.meshes.new(self.name);mesh.from_pydata(self.vertices,[],self.faces);mesh.materials.append(self.material);mesh.update();bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.000001);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free();mesh.update();obj=bpy.data.objects.new(self.name,mesh);bpy.data.collections[COLLECTION].objects.link(obj);obj['destinationCollection']=COLLECTION;obj['publicInteriorComponent']=True;obj['evidence_status']='Built2022source-plan estimate;inherited vertical datums';return obj

 def slab(name,low,high,mat):
  b=Batch(name,mat)
  for tri in PLAN['floor']['triangles']:
   a,c,d=tri
   if (c[0]-a[0])*(d[1]-a[1])-(c[1]-a[1])*(d[0]-a[0])<0:tri=list(reversed(tri))
   b.add([(*p,low)for p in tri],[(2,1,0)]);b.add([(*p,high)for p in tri],[(0,1,2)])
  for ring in PLAN['floor']['boundary']:
   for a,c in zip(ring,ring[1:]):b.add([(*a,low),(*c,low),(*c,high),(*a,high)],[(0,1,2,3)])
  return b.finish()

 def build():
  concrete=bpy.data.materials['MAR_D3_concrete'];metal=bpy.data.materials['MAR_D3_metal'];glass=bpy.data.materials['MAR177_mezzanine_guard_glass_dielectric'];cream=bpy.data.materials['MAR_D3_cream']
  carpet=bpy.data.materials.new(PREFIX+'neutral_public_carpet');carpet.use_nodes=True;node=carpet.node_tree.nodes.get('Principled BSDF');node.inputs['Base Color'].default_value=(.20,.225,.22,1);node.inputs['Roughness'].default_value=.86;carpet.diffuse_color=(.20,.225,.22,1)
  owned=[slab('second_structural_slab',SLAB_BOTTOM,UPPER-.025,concrete),slab('second_floor_finish',UPPER-.025,UPPER,carpet),slab('second_soffit',SLAB_BOTTOM-.025,SLAB_BOTTOM,concrete)]
  columns=Batch('source_upper_column_grid',concrete)
  for row in PLAN['columns']:columns.prism(row['profile'],LOWER,SLAB_BOTTOM)
  owned.append(columns.finish());tree=Batch('diamond_transfer_tree',concrete);x,y=PLAN['tree']['centre'];tree.prism([(x-.55,y-.55),(x+.55,y-.55),(x+.55,y+.55),(x-.55,y+.55)],LOWER,9.45)
  for p in PLAN['tree']['branchTips']:tree.beam((x,y,9.15),(*p,SLAB_BOTTOM+.03),1.12,.58)
  owned.append(tree.finish());guard=Batch('second_void_glass_guards',glass);frame=Batch('second_void_guard_frames',metal);guard_probes=[]
  for hole in PLAN['holes']:
   ring=hole['world'];area=sum(a[0]*b[1]-b[0]*a[1]for a,b in zip(ring,ring[1:]))/2
   for a,b in zip(ring,ring[1:]):
    a,b=Vector(a),Vector(b);axis=b-a;length=axis.length
    if length<.001:continue
    normal=Vector((axis.y,-axis.x)).normalized()*(1 if area>0 else-1);a+=normal*.08;b+=normal*.08;count=max(1,math.ceil(length/1.2))
    for j in range(count):
     p=a.lerp(b,j/count);q=a.lerp(b,(j+1)/count);guard.add([(*p,UPPER+.08),(*q,UPPER+.08),(*q,UPPER+1.10),(*p,UPPER+1.10)],[(0,1,2,3)]);frame.beam((*p,UPPER+1.13),(*q,UPPER+1.13),.045);frame.beam((*p,UPPER),(*p,UPPER+1.13),.04);guard_probes.append([*p,UPPER])
  owned +=[guard.finish(),frame.finish()]
  for name in PLAN['archivedObjects']:bpy.data.objects[name].hide_render=True;set_layer_hidden(bpy.data.objects[name],True)
  return owned,guard_probes

 def tree_for(objects):
  from mathutils.bvhtree import BVHTree
  vertices=[];faces=[];owners=[]
  for o in objects:
   if o.type!='MESH'or o.hide_render:continue
   offset=len(vertices);vertices.extend(o.matrix_world@v.co for v in o.data.vertices);faces.extend(tuple(offset+i for i in p.vertices)for p in o.data.polygons);owners +=[o.name]*len(o.data.polygons)
  return BVHTree.FromPolygons(vertices,faces),owners

 def verify(owned,guard_probes):
  decks=[o for o in owned if o.name in [PREFIX+'second_structural_slab',PREFIX+'second_floor_finish']];floor_tree,owners=tree_for(decks);routes=[]
  for index,(a,b)in enumerate(PLAN['publicRoutes']):
   a,b=Vector(a),Vector(b);count=max(2,math.ceil((b-a).length/.5))
   for i in range(count+1):
    p=a.lerp(b,i/count);hit=floor_tree.ray_cast(Vector((*p,UPPER+.02)),Vector((0,0,-1)),.1);assert hit[0]is not None,('Missing public second floor',index,list(p));routes.append(dict(route=index,position=list(p),support=owners[hit[2]]))
  guards=[]
  for p in guard_probes:
   hit=floor_tree.ray_cast(Vector((p[0],p[1],p[2]+.02)),Vector((0,0,-1)),.1);assert hit[0]is not None,('Floating guard',p);guards.append(dict(position=p,support=owners[hit[2]]))
  all_source=[o for o in bpy.data.collections[COLLECTION].all_objects if not o.hide_render];all_tree,all_owners=tree_for(all_source);supports=[]
  olddeck=bpy.data.objects['MAR217_coordinated_mezzanine_slab'];old_tree,_=tree_for([olddeck]);centres=[r['centre']for r in PLAN['columns']]+[PLAN['tree']['centre']]
  for p in centres:
   foot=old_tree.ray_cast(Vector((*p,LOWER+.01)),Vector((0,0,-1)),.05);assert foot[0]is not None,('Unseated new column',p);supports.append(dict(position=p,base=foot[0].z))
  voids=[]
  for hole in PLAN['holes']:
   p=np.asarray(hole['world'])[:-1].mean(axis=0);hit=floor_tree.ray_cast(Vector((*p,UPPER+.03)),Vector((0,0,-1)),.45);assert hit[0]is None,('Closed source void',hole['id']);voids.append(dict(id=hole['id'],centre=p.tolist(),floorHit=False))
  clear=[];blocked_projection=[]
  # First-level public routes outside support profiles retain at least2.1m clear.
  low_tree,low_owners=tree_for(owned)
  for index,(a,b)in enumerate(PLAN['publicRoutes']):
   a,b=Vector(a),Vector(b);count=max(2,math.ceil((b-a).length/.7))
   for i in range(count+1):
    p=a.lerp(b,i/count);floorhit=old_tree.ray_cast(Vector((*p,LOWER+.03)),Vector((0,0,-1)),.08)
    if floorhit[0]is None:continue
    head=low_tree.ray_cast(Vector((*p,LOWER+.03)),Vector((0,0,1)),2.07)
    if head[0]is not None:blocked_projection.append(dict(position=list(p),hit=low_owners[head[2]],reason='Projection of second-floor route is not asserted as first-floor route'));continue
    clear.append(dict(position=list(p),headClearanceMetres=2.1))
  assert len(clear)>80
  # The217arrival and its immediate bearing remain exact and seated.
  landing=bpy.data.objects['MAR217_registered_MAR_D3_stair_arrival_landing'];landing_tree,_=tree_for([landing]);arrival=[]
  for f in landing.data.polygons:
   points=[landing.matrix_world@landing.data.vertices[i].co for i in f.vertices]
   if all(abs(p.z-LOWER)<.002 for p in points):
    p=sum(points,Vector())/len(points);hit=landing_tree.ray_cast(p+Vector((0,0,.02)),Vector((0,0,-1)),.05);assert hit[0]is not None;head=low_tree.ray_cast(p+Vector((0,0,.03)),Vector((0,0,1)),2.07);assert head[0]is None;arrival.append(list(p))
  glass_rows=[];glass_seen=set();soffit_tree,_=tree_for([o for o in owned if o.name==PREFIX+'second_soffit'])
  for obj in bpy.data.collections['MAR_EXTERIOR'].all_objects:
   if obj.type!='MESH'or obj.hide_render or not any(m and ('glass'in m.name.lower()or'glazing'in m.name.lower())for m in obj.data.materials):continue
   for face in obj.data.polygons:
    pts=[obj.matrix_world@obj.data.vertices[i].co for i in face.vertices];p=sum(pts,Vector())/len(pts)
    if not 7.7<p.z<12.4:continue
    key=(obj.name,round(p.x,2),round(p.y,2))
    if key in glass_seen:continue
    glass_seen.add(key);axis=Vector((-14.46-p.x,50.4-p.y,0))
    if axis.length<.01:continue
    axis.normalize();backed=False;offset=None
    for distance in [.65,1.25,2.0]:
     q=p+axis*distance;low=old_tree.ray_cast(Vector((q.x,q.y,LOWER+.02)),Vector((0,0,-1)),.07);high=soffit_tree.ray_cast(Vector((q.x,q.y,LOWER+.05)),Vector((0,0,1)),UPPER-LOWER)
     if low[0]is not None and high[0]is not None:backed=True;offset=distance;break
    glass_rows.append(dict(object=obj.name,paneCentre=list(p),floorAndSoffitBacked=backed,inwardProbeMetres=offset,originalOpticsUnchanged=True))
  branch_rows=[]
  for p in PLAN['tree']['branchTips']:
   hit=floor_tree.ray_cast(Vector((*p,UPPER+.02)),Vector((0,0,-1)),.1);assert hit[0]is not None;branch_rows.append(dict(tip=p,secondSlabBearing=True))
  return dict(visibleUpperGlazingBacking=glass_rows,diamondBranchSlabBearing=branch_rows,secondFloorRouteProbes=routes,landingGuardSupportProbes=guards,columnBaseSupportProbes=supports,sourceVoidProbes=voids,firstLevelClearanceProbes=clear,excludedFirstLevelRouteProjections=blocked_projection,retained217ArrivalProbes=arrival,sourceBoundaryClippedToNative=True,upperMainStairLink='Unresolved first-floor plan and angular landing mismatch;existing217main stair and approach unchanged,no invented upper flight')

 def render(label,owned):
  scene=bpy.data.scenes.new(PREFIX+'REVIEW');scene.collection.children.link(bpy.data.collections[COLLECTION]);bpy.context.window.scene=scene
  world=bpy.data.worlds.new(scene.name);world.use_nodes=True;world.node_tree.nodes['Background'].inputs[0].default_value=(.8,.83,.88,1);world.node_tree.nodes['Background'].inputs[1].default_value=.8;scene.world=world
  ld=bpy.data.lights.new(scene.name,'SUN');ld.energy=2;sun=bpy.data.objects.new(scene.name+'_sun',ld);scene.collection.objects.link(sun);sun.rotation_euler=(.4,-.5,-.1)
  cd=bpy.data.cameras.new(scene.name);camera=bpy.data.objects.new(scene.name+'_camera',cd);scene.collection.objects.link(camera);scene.camera=camera;cd.clip_end=300;cd.lens=24
  scene.render.engine='BLENDER_EEVEE';scene.eevee.taa_render_samples=24;scene.render.resolution_x=1200;scene.render.resolution_y=900;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='AgX'
  hidden=[]
  for o in list(bpy.data.collections[COLLECTION].all_objects):
   if o.type=='MESH'and not o.hide_render:
    p=[o.matrix_world@Vector(c)for c in o.bound_box]
    if min(v.z for v in p)>13.95:hidden.append(o);o.hide_render=True
  views=[]
  for name,p,t,ortho in [('second-cutaway',(-41,12,55),(-13,50,9),74),('first-transfer',(-14,42,8.9),(-14.46,50.4,10.2),None),('second-void',(-19.5,47,16.4),(-14.46,50.4,11.6),None)]:
   cd.type='ORTHO'if ortho else'PERSP'
   if ortho:cd.ortho_scale=ortho
   camera.location=p;camera.rotation_euler=(Vector(t)-camera.location).to_track_quat('-Z','Y').to_euler();scene.render.filepath=str(OUT/(label+'-'+name+'.png'));bpy.ops.render.render(write_still=True)
   view=dict(position=[p[0],p[2],-p[1]],target=[t[0],t[2],-t[1]],fov=58.72)
   views.append(dict(name=name,view=view))
  for o in hidden:o.hide_render=False
  for o in [camera,sun]:bpy.data.objects.remove(o,do_unlink=True)
  bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE'];bpy.data.scenes.remove(scene);bpy.data.worlds.remove(world);bpy.data.cameras.remove(cd);bpy.data.lights.remove(ld);update_scene();return views

 def run():
  assert sha(BASE)==SHA;bpy.ops.wm.open_mainfile(filepath=str(BASE));update_scene();expected=accepted_fingerprints(ROOT/'result/blender/stage222',SHA);original={o.name:object_fingerprint(o)for o in bpy.data.objects};assert original==expected;assert len(original)==7688
  materials={m.name:material_fingerprint(m)for m in bpy.data.materials};modifiers={o.name:stable_modifiers(o)for o in bpy.data.objects};rooms=rooms_state();assert len(rooms)==21;members={o.name:sorted(c.name for c in o.users_collection)for o in bpy.data.objects};visibility={o.name:o.hide_render for o in bpy.data.objects};assert not set(PLAN['archivedObjects'])&set(n for r in rooms for n in r['objects'])
  def contains_collection(parent,target):return parent==target or any(contains_collection(child,target)for child in parent.children)
  campus_linked=contains_collection(bpy.data.scenes['00_CAMPUS_COMPLETE'].collection,bpy.data.collections[COLLECTION])
  before=render('before',[]);owned,guard_probes=build();update_scene();checks=verify(owned,guard_probes);views=render('after',owned)
  assert all(object_fingerprint(bpy.data.objects[n])==v for n,v in original.items());assert all(material_fingerprint(bpy.data.materials[n])==v for n,v in materials.items());assert all(stable_modifiers(bpy.data.objects[n])==v for n,v in modifiers.items());assert rooms_state()==rooms
  fingerprints={o.name:object_fingerprint(o)for o in owned};bindings={o.name:[m.name if m else None for m in o.data.materials]for o in owned};component=OUT/'component.blend';bpy.data.libraries.write(str(component),set(owned),fake_user=True,compress=True)
  bpy.ops.wm.open_mainfile(filepath=str(BASE));update_scene();assert{o.name:object_fingerprint(o)for o in bpy.data.objects}==expected
  with bpy.data.libraries.load(str(component),link=False)as(src,dst):dst.objects=list(fingerprints)
  for o in dst.objects:
   for i,n in enumerate(bindings[o.name]):o.data.materials[i]=bpy.data.materials[n]if n else None
   bpy.data.collections[COLLECTION].objects.link(o)
  for n in PLAN['archivedObjects']:bpy.data.objects[n].hide_render=True;set_layer_hidden(bpy.data.objects[n],True)
  update_scene();assert verify(dst.objects,guard_probes)==checks;assert all(object_fingerprint(bpy.data.objects[n])==v for n,v in fingerprints.items());assert all(object_fingerprint(bpy.data.objects[n])==v for n,v in original.items());assert all(material_fingerprint(bpy.data.materials[n])==v for n,v in materials.items());assert all(stable_modifiers(bpy.data.objects[n])==v for n,v in modifiers.items());assert rooms_state()==rooms;assert all(sorted(c.name for c in bpy.data.objects[n].users_collection)==v for n,v in members.items());assert all(bpy.data.objects[n].hide_render==(True if n in PLAN['archivedObjects']else v)for n,v in visibility.items());assert sha(BASE)==SHA
  verification=dict(savedComponentReopened=True,independentAcceptedObjectsVerified=len(original),allOriginalMaterialNodesVerified=len(materials),allOriginalModifierStacksVerified=len(modifiers),roomCollectionsPreserved=len(rooms),roomUniqueObjectsPreserved=len(set(n for r in rooms for n in r['objects'])),allSourceMembershipsUnchanged=True,geometryUVTransformsBindingsUnchanged=True,sourceNativeShaUnchanged=True,addedTriangles=sum(len(f.vertices)-2 for o in dst.objects for f in o.data.polygons),archivedTriangles=sum(len(f.vertices)-2 for n in PLAN['archivedObjects']for f in bpy.data.objects[n].data.polygons))
  report=dict(version=223,building='MAR',baseline=str(BASE.relative_to(ROOT)),baselineSha256=SHA,componentPath=str(component.relative_to(ROOT)),componentSha256=sha(component),targetCollection=COLLECTION,destinationCollection=COLLECTION,addedObjects=list(fingerprints),archivedObjects=PLAN['archivedObjects'],changedObjects=[],addedFingerprints=fingerprints,replacementMaterialBindings=bindings,nativeCampusCollectionLinked=campus_linked,campusCollectionLinkRequired=not campus_linked,exteriorSharingStrategy='All owned objects retain publicInteriorComponent=True for existingMARpublic/exterior export sharing;link existing public collection into campus ifcampusCollectionLinkRequired',sourceManifest='data/collections/mar-structure223/sources.json',plan='data/collections/mar-structure223/structural-plan.json',checks=checks,verification=verification,dimensions=dict(firstFloor=LOWER,secondFloor=UPPER,slabBottom=SLAB_BOTTOM,structuralThickness=UPPER-.025-SLAB_BOTTOM,finishThickness=.025,secondFloorAreaSquareMetres=PLAN['floor']['areaSquareMetres']),publicViewSuggestion=dict(interiorDisplayMaxZ=13.95,interiorView=views[1]['view'],interiorSections=[dict(id='G',label='G大堂与保留主梯',minHeight=-.1,maxHeight=6.94,scope='217入口、九支点及主梯完整保留',view=dict(position=[-.211,2,-65.70],target=[-.381,3.1,-44.306],fov=65)),dict(id='1',label='一层公共环廊与二层支承',minHeight=6.94,maxHeight=12.47,scope='保留217楼板和主梯上平台，补二层图示柱网与菱形树状支承',view=views[1]['view']),dict(id='2',label='二层结构与图示挑空',minHeight=12.47,maxHeight=13.95,scope='2022建成图二层结构楼板，菱形结构挑空与半圆主梯口；上行梯段未重建',view=views[2]['view'])],gallerySuggestions=[dict(name=v['name']+'-interior',label={'second-cutaway':'二层结构总览','first-transfer':'一层至二层结构支承','second-void':'二层菱形挑空'}[v['name']],sectionId='1'if v['name']=='first-transfer'else'2',view=v['view'])for v in views if v['name']!='second-cutaway']),limitations=['Built2022published plans and undated built photographs are not a2026survey.','The217horizontal registration and existing7.24m/12.8mlevels are retained estimates;notch corners,slab thickness,tree branch sections and surface finish are estimates.','Second-floor slabs include the structural footprint only,not complete classroom interiors or furniture.','The exact first-to-second main stair angular landing relation lacks a published first-floor plan;no speculative upper flight or false accessible route is introduced.','Columns extending outside the inherited first slab are omitted rather than inventing supports;see source plan omittedColumns.','Existing ground glazing,glass optical parameters,three entrances,five revolving units,nine source supports and registered ground-to-first stair remain unchanged.','Source photographs remain private reference and are not published textures.'])
  (OUT/'audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');(OUT/'verification.json').write_text(json.dumps(verification,indent=2)+'\n');print('MAR223_COMPONENT_REOPENED',len(fingerprints),verification,flush=True)

 if __name__=='__main__':run()
