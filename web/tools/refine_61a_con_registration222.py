"""Register the two historical61A floor plates without moving61A orCON.

Fixed authoring configuration.MachineLearning Python prepares the archived
PDF vectors;Blender builds and verifies the independent component library.
All vertical datums are inherited estimates,not a measured current survey.
"""
from pathlib import Path
import sys,json,hashlib,math
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'result/blender/aldwych-registration222'
ARCHIVE=ROOT/'data/collections/aldwych-registration222'
BASE=ROOT/'result/blender/LSE_campus_detailed_v221.blend'
SHA='62b61a56a402120ab5047096113b02e20f85f7957442e39b6262557c151c69cb'
PREFIX='ALD222_';COLLECTION='61A_EXTERIOR'
GLASS='61A208_61A_NEXT_retained_glazing_glass'
PDF=ROOT/'data/documents/61aldwych_brochure_2021.pdf'
PDF_SHA='edd2358acd6b36e4587b533a527bc1869393012fc8bc4849e3125f95a3821f10'
sys.path.insert(0,str(ROOT/'web/tools'))


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare_sources():
 import numpy as np,pdfplumber
 from shapely.geometry import Polygon,Point
 from shapely.ops import unary_union
 from shapely import constrained_delaunay_triangles
 from PIL import Image,ImageDraw
 from register_61a_envelope218 import transform,similarity,CONTROLS
 OUT.mkdir(exist_ok=True);ARCHIVE.mkdir(exist_ok=True);assert sha(PDF)==PDF_SHA
 hypothesis=json.loads((ROOT/'result/blender/61a-registration218/registration-hypothesis.json').read_text());fit=hypothesis['transform']
 site=json.loads((ROOT/'result/blender/site_geometry.json').read_text())
 mapped=unary_union([Polygon(r['rings'][0])for r in site['buildings']if r['id']in {'way/181939023','way/181939031'}])
 con=Polygon(next(r for r in site['buildings']if r['id']=='way/23613978')['rings'][0]);joint=unary_union([mapped,con])
 office=Polygon(hypothesis['sourceFloorFillBoundaryWorld']);tip=Point(hypothesis['diagnostic']['sourceFrontTipWorld'])
 diagnostic=dict(sourceFrontTip=list(tip.coords)[0],distanceTo61ABoundary=tip.distance(mapped.boundary),distanceToCONBoundary=tip.distance(con.boundary),distanceToCombinedStreetEnvelope=tip.distance(joint.boundary),tipWithinCON=con.contains(tip),sourceOutside61A=office.difference(mapped).area,sourceOverlapCON=office.intersection(con).area,sourceOutsideJointEnvelope=office.difference(joint).area,jointEnvelopeArea=joint.area,reason='The7.85m discrepancy mostly concerns an internal mapped ownership line;no independentCON/common-wall control supports a parcel transfer.')
 (OUT/'joint-registration-diagnostic.json').write_text(json.dumps(diagnostic,indent=2)+'\n')
 with pdfplumber.open(PDF)as doc:
  page=doc.pages[8]
  atria4=[page.rects[988]['pts'],page.curves[5073]['pts']]
  atria6=[page.curves[2432]['pts'],page.curves[91]['pts']]
  # Six-floor image uses a different scale on the printed spread.Register its
  # two atria to the fourth-floor voids before using the independent outline.
  controls4=[[134.636,236.806],[192.947,268.149],[325.7376,237.014],[415.6846,268.151]]
  controls6=[[712.1813,236.0165],[771.3973,267.4595],[906.0812,235.9721],[997.1332,267.5291]]
  targets=transform(controls4,fit)
  fit6=similarity(np.array(controls6)*[1,-1],targets)
  residual=np.linalg.norm(transform(controls6,fit6)-targets,axis=1)
  layouts=[]
  for label,index,voids,registration,z in [('4',5072,atria4,fit,15.),('6',31,atria6,fit6,22.2)]:
   outline=Polygon(transform(page.curves[index]['pts'],registration)).buffer(0)
   # Keep inside the accepted61A shell and outsideCON.No source outline is
   # stretched to match the disputed front.Clip is explicitly reported.
   shell=outline.intersection(mapped.buffer(-.12)).difference(con.buffer(.12)).simplify(.025,preserve_topology=True)
   holes=[Polygon(transform(p,registration)).buffer(0).simplify(.025,preserve_topology=True)for p in voids]
   plate=shell.difference(unary_union(holes)).buffer(0)
   assert plate.geom_type=='Polygon' and len(plate.interiors)==2
   triangles=[list(t.exterior.coords)[:-1]for t in constrained_delaunay_triangles(plate).geoms]
   assert abs(sum(Polygon(t).area for t in triangles)-plate.area)<1e-5
   columns=[]
   # Repeated approximately2.23pt column circles form the observed structural
   # grid.Exclude sanitary symbols in cores and non-circular small details.
   for curve_index,c in enumerate(page.curves):
    w,h=c['width'],c['height'];inside=(65<c['x0']<430)if label=='4'else(642<c['x0']<1015)
    is_circle=c['stroke']and not c['fill']and 2.00<w<(2.45 if label=='4'else 2.60) and .90<w/h<1.12 and len(c['pts'])in[5,6]
    if inside and 175<c['top']<280 and is_circle:
     centre=[(c['x0']+c['x1'])/2,(c['top']+c['bottom'])/2];point=transform([centre],registration)[0]
     if plate.contains(Point(point))and all(np.linalg.norm(point-np.array(q['world']))>.3 for q in columns):
      columns.append(dict(pdf=centre,world=point.tolist(),curveIndex=curve_index,diameter=w*registration['scale']))
   # Boundaries of the atria are drawn separately from the office underlay.
   # Their wall thickness and ceiling levels remain estimated construction.
   layouts.append(dict(floor=label,z=z,top=z+3.35,sourceCurve=index,registration=registration,sourceOutlineArea=outline.area,clippedAwayArea=outline.difference(shell).area,area=plate.area,outer=list(plate.exterior.coords),holes=[list(r.coords)for r in plate.interiors],holeProbes=[list(Polygon(r).representative_point().coords)[0]for r in plate.interiors],overlapCONArea=plate.intersection(con).area,triangles=triangles,columns=columns,atriumAreas=[h.area for h in holes]))
 data=dict(sourcePdf=str(PDF.relative_to(ROOT)),sourceSha256=PDF_SHA,sourcePage=9,publication='May2021',sourceCaptureDates='unknown',fourthControls=hypothesis['controls'],sixthInternalRegistrationResidualM=residual.tolist(),sixthControlsAreNotIndependentExternalSurvey=True,floors=layouts)
 (OUT/'plan-layout.json').write_text(json.dumps(data,indent=2)+'\n')
 im=Image.new('RGB',(1200,1100),'#f6f4ef');d=ImageDraw.Draw(im)
 def screen(ps):return[(80+(x+86)*10,1030-(y+150)*8.8)for x,y in ps]
 d.polygon(screen(joint.exterior.coords),fill='#d1d5d5',outline='#555b5d');d.line(screen(mapped.exterior.coords),fill='#30393d',width=2)
 d.line(screen(office.exterior.coords),fill='#b85e46',width=3)
 for l,color in zip(layouts,['#6d9d91','#477b98']):
  d.line(screen(l['outer']),fill=color,width=3)
  for h in l['holes']:d.polygon(screen(h),fill='#cfedf0',outline=color)
  for c in l['columns']:
   x,y=screen([c['world']])[0];d.ellipse((x-2,y-2,x+2,y+2),fill=color)
 d.text((35,20),'61A/CON joint boundary: red2021 outline / black accepted61A / grey combined envelope',fill='#26373e')
 d.text((35,40),'Two source floors and atria retained; disputed front clipped,not warped.Private model evidence.',fill='#4d5657')
 im.save(OUT/'joint-floor-registration.png')
 sources=dict(retrieved='2026-10-16',references=[dict(path=str(PDF.relative_to(ROOT)),sha256=PDF_SHA,url=hypothesis['sourceReference'],publication='May2021',photographDates='unknown',role='Indicative fourth/sixth floor plans and lower-right built street-corner photograph,p9 printed18'),dict(path='data/documents/property_handbook.pdf',sha256=sha(ROOT/'data/documents/property_handbook.pdf'),url='https://info.lse.ac.uk/staff/divisions/estates-division/Assets/Documents/Property-and-Space/LSE-Property-Handbook.pdf',page=15,role='Official building identity and built image;not a measured floor survey'),dict(path='data/collections/aldwych-registration222/manager-existing-corner.jpg',sha256=sha(ARCHIVE/'manager-existing-corner.jpg'),url='https://61aldwych.mybuildings.com/Core/SiteImages/537/b17582c33fe44129e3c4.jpg',parentUrl='https://61aldwych.mybuildings.com/Core/Content/61ALDWYCHBUILDINGHISTORY-TIMELINE/Content11557.aspx',photographDate='unknown',role='Original property-manager historical photograph corroborates pavilion;conflicts with stepped-gable image,so roof massing is retained')],decisions=['No61A/CON ownership transfer and no whole-building translation.','Do not replace pavilion from unresolved historical-photo conflict.','Use only two explicitly drawn floors;do not infer a complete current floor stack or2025competition scheme.','No source photographs embedded as textures.'])
 (ARCHIVE/'sources.json').write_text(json.dumps(sources,indent=2)+'\n')
 print('SOURCE_PLATES_READY',[(p['floor'],p['area'],len(p['columns']))for p in layouts],residual,flush=True)


def run():
 import bpy,bmesh
 from mathutils import Vector,Matrix
 from mathutils.bvhtree import BVHTree
 from integrate_exterior_round194 import accepted_fingerprints,object_fingerprint
 from refine_lrb_structure221 import original_state,verify_originals
 from build_room_samples167 import RoomGeometry
 def update():
  for s in bpy.data.scenes:
   for layer in s.view_layers:layer.update()
  bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE']
 def tree(objects):
  vs=[];fs=[]
  for o in objects:
   off=len(vs);vs.extend(o.matrix_world@v.co for v in o.data.vertices);fs.extend(tuple(off+i for i in f.vertices)for f in o.data.polygons)
  return BVHTree.FromPolygons(vs,fs)
 def plate_mesh(name,layout,z,depth,material):
  points={};vs=[];fs=[]
  def vertex(x,y,h):
   key=(round(x,7),round(y,7),round(h,7))
   if key not in points:points[key]=len(vs);vs.append((x,y,h))
   return points[key]
  for tri in layout['triangles']:
   ids=[vertex(x,y,z)for x,y in tri];top=[vertex(x,y,z+depth)for x,y in tri]
   fs.extend([tuple(reversed(ids)),tuple(top)])
  for ring in [layout['outer']]+layout['holes']:
   for a,b in zip(ring,ring[1:]):fs.append((vertex(*a,z),vertex(*b,z),vertex(*b,z+depth),vertex(*a,z+depth)))
  mesh=bpy.data.meshes.new(name);mesh.from_pydata(vs,[],fs);mesh.materials.append(material);mesh.update()
  bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));assert all(len(e.link_faces)==2 for e in bm.edges);volume=bm.calc_volume(signed=True);assert volume>0;bm.to_mesh(mesh);bm.free()
  uv=mesh.uv_layers.new(name='MetricSurfaceUV')
  for face in mesh.polygons:
   ps=[mesh.vertices[i].co for i in face.vertices];u=(ps[1]-ps[0]).normalized();v=face.normal.cross(u)
   for li,p in zip(face.loop_indices,ps):uv.data[li].uv=((p-ps[0]).dot(u),(p-ps[0]).dot(v))
  o=bpy.data.objects.new(name,mesh);bpy.data.collections[COLLECTION].objects.link(o);o['solidVolumeM3']=volume
  return o
 def previews(label,added):
  scene=bpy.data.scenes.new(PREFIX+'REVIEW');scene.render.engine='CYCLES';scene.cycles.samples=8;scene.cycles.use_denoising=True
  scene.render.resolution_x=1050;scene.render.resolution_y=800;scene.render.resolution_percentage=100;scene.view_settings.view_transform='AgX'
  world=bpy.data.worlds.new(PREFIX+'WORLD');world.use_nodes=True;world.node_tree.nodes['Background'].inputs[0].default_value=(.78,.82,.86,1);world.node_tree.nodes['Background'].inputs[1].default_value=.8;scene.world=world
  copies=[]
  for old in list(bpy.data.collections[COLLECTION].all_objects):
   if old.type!='MESH' or old.hide_render or not old.data.vertices:continue
   if label=='before'and old.name in [o.name for o in added]:continue
   if label=='after'and old.name==GLASS:continue
   o=old.copy();o.data=old.data.copy();o.data.transform(old.matrix_world);o.matrix_world=Matrix.Identity(4)
   # Only temporary preview copies are sectioned.No source datum is touched.
   bm=bmesh.new();bm.from_mesh(o.data)
   for height,outer in [(25.50,True),(14.70,False)]:
    bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=.000001,plane_co=(0,0,height),plane_no=(0,0,1),clear_outer=outer,clear_inner=not outer)
   bm.to_mesh(o.data);bm.free()
   if not o.data.polygons:bpy.data.objects.remove(o);continue
   scene.collection.objects.link(o);copies.append(o)
  camera=bpy.data.objects.new(PREFIX+'CAM',bpy.data.cameras.new(PREFIX+'CAM'));scene.collection.objects.link(camera);scene.camera=camera;camera.data.type='ORTHO';camera.data.clip_end=500
  sun=bpy.data.objects.new(PREFIX+'SUN',bpy.data.lights.new(PREFIX+'SUN','SUN'));scene.collection.objects.link(sun);sun.data.energy=2;sun.rotation_euler=(.5,-.4,-.5)
  for view,pos,target,scale in [('joint-cutaway',(-135,-165,115),(-49,-91,19),103),('atria',(-30,-69,76),(-48,-91,21),76)]:
   camera.location=pos;camera.rotation_euler=(Vector(target)-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.ortho_scale=scale
   scene.render.filepath=str(OUT/(label+'-'+view+'.png'));bpy.context.window.scene=scene;bpy.ops.render.render(write_still=True)
  bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE']
  for o in copies+[camera,sun]:
   mesh=o.data;bpy.data.objects.remove(o,do_unlink=True)
   if mesh.users==0 and isinstance(mesh,bpy.types.Mesh):bpy.data.meshes.remove(mesh)
  bpy.data.scenes.remove(scene);bpy.data.worlds.remove(world);update()
 assert sha(BASE)==SHA
 bpy.ops.wm.open_mainfile(filepath=str(BASE));update();before=original_state();expected=accepted_fingerprints(ROOT/'result/blender/stage221',SHA)
 assert before['objects']==expected and len(expected)==7651
 layouts=json.loads((OUT/'plan-layout.json').read_text())['floors']
 g=RoomGeometry(bpy.data.collections[COLLECTION],PREFIX)
 for key,color in [('structure',(.58,.59,.57)),('finish',(.71,.70,.66)),('soffit',(.81,.81,.77))]:
  mat=bpy.data.materials.new(PREFIX+key);mat.use_nodes=True;mat.diffuse_color=(*color,1);mat.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=mat.diffuse_color;mat.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value=.8;g.materials[key]=mat
 added=[];proof=[]
 for l in layouts:
  slab=plate_mesh(PREFIX+'floor'+l['floor']+'_slab',l,l['z']-.25,.25,g.materials['structure']);added.append(slab)
  finish=plate_mesh(PREFIX+'floor'+l['floor']+'_finish',l,l['z'],.016,g.materials['finish']);added.append(finish)
  ceiling=plate_mesh(PREFIX+'floor'+l['floor']+'_ceiling',l,l['top'],.20,g.materials['soffit']);added.append(ceiling)
  # Actual source column centres;height is confined to each demonstrated floor.
  for col in l['columns']:
   x,y=col['world'];g.tube('floor'+l['floor']+'_source_columns','soffit',(x,y,l['z']),(x,y,l['top']),col['diameter']/2)
  # Thin estimated inner faces bound the two atria at each demonstrated storey.
  # They are separate from the source exterior and do not imply unseen levels.
  for hole in l['holes']:
   for a,b in zip(hole,hole[1:]):
    a,b=Vector((*a,0)),Vector((*b,0));d=b-a
    if d.length<.05:continue
    c=(a+b)/2;c.z=(l['z']+l['top'])/2
    g.box('floor'+l['floor']+'_atrium_returns','soffit',c,(d.length,.14,l['top']-l['z']),math.atan2(d.y,d.x))
  proof.append(dict(floor=l['floor'],estimatedZ=l['z'],estimatedClearHeight=l['top']-l['z']-.016,slabThickness=.25,area=l['area'],atriumAreas=l['atriumAreas'],sourceColumns=len(l['columns'])))
 added+=g.finish()
 # Unambiguous two-floor street panes now have actual slabs/ceilings and a
 # source-derived finite volume behind them.All remaining glazing stays opaque.
 slab_trees={l['floor']:tree([bpy.data.objects[PREFIX+'floor'+l['floor']+'_slab']])for l in layouts}
 ceil_trees={l['floor']:tree([bpy.data.objects[PREFIX+'floor'+l['floor']+'_ceiling']])for l in layouts}
 src=bpy.data.objects[GLASS];glass=src.copy();glass.data=src.data.copy();glass.name=PREFIX+'backed_fourth_sixth_glazing';glass['originalObject']=GLASS;bpy.data.collections[COLLECTION].objects.link(glass)
 mat=bpy.data.materials['61A208_backed_ten_dormer_dielectric'].copy();mat.name=PREFIX+'physically_backed_two_floor_glass';glass.data.materials.append(mat);slot=len(glass.data.materials)-1
 samples=[]
 for i in range(0,len(src.data.vertices),8):
  ps=[src.matrix_world@v.co for v in src.data.vertices[i:i+8]];c=sum(ps,Vector())/8
  floor=next((l for l in layouts if l['z']+.3<c.z<l['top']-.3),None)
  if not floor:continue
  l=floor;edges=[ps[j]-ps[0]for j in [1,2,4]];horizontal=[v for v in edges if abs(v.z)<.01 and v.length>.001]
  n=min(horizontal,key=lambda p:p.length).normalized();valid=[]
  for sign in [-1,1]:
   p=c+n*(.65*sign);down=slab_trees[l['floor']].ray_cast(p,Vector((0,0,-1)),4);up=ceil_trees[l['floor']].ray_cast(p,Vector((0,0,1)),4)
   if down[0]is not None and up[0]is not None:valid.append((p,down[0],up[0]))
  if len(valid)!=1:continue
  p,down,up=valid[0]
  for f in glass.data.polygons:
   if all(i<=v<i+8 for v in f.vertices):f.material_index=slot
  samples.append(dict(pane=i//8,floor=l['floor'],point=list(c),inwardSupportPoint=list(p),floorTop=down.z,ceilingBottom=up.z,clearance=up.z-down.z))
 assert len(samples)>20,len(samples)
 glass.hide_render=False;glass.hide_set(False);added.append(glass)
 for o in added:o['destinationCollection']=COLLECTION;o['buildingCode']='61A';o['scope']='Historical indicative2021 fourth/sixth floor source geometry;native estimated heights;noCON ownership transfer'
 newnames=[o.name for o in added]
 previews('before',added);src.hide_render=True;previews('after',added);verify_originals(before,{GLASS})
 def physical_checks():
  checks=[]
  for l in layouts:
   floor=tree([bpy.data.objects[PREFIX+'floor'+l['floor']+'_slab']]);ceil=tree([bpy.data.objects[PREFIX+'floor'+l['floor']+'_ceiling']]);support=[];void=[]
   for col in l['columns']:
    p=Vector((*col['world'],l['z']+.1));hit=floor.ray_cast(p,Vector((0,0,-1)),.2);assert hit[0]is not None;support.append(abs(hit[0].z-l['z']))
   for point in l['holeProbes']:
    p=Vector((*point,l['z']+.1))
    hit=floor.ray_cast(p,Vector((0,0,-1)),.5);assert hit[0]is None;void.append(list(p))
   for s in [s for s in samples if s['floor']==l['floor']]:
    p=Vector(s['inwardSupportPoint']);down=floor.ray_cast(p,Vector((0,0,-1)),4);up=ceil.ray_cast(p,Vector((0,0,1)),4)
    assert down[0]is not None and up[0]is not None and abs(up[0].z-down[0].z-3.35)<1e-4
   checks.append(dict(floor=l['floor'],columnsOnSlab=len(support),maximumColumnSlabGap=max(support),openAtriumCentroids=len(void),twoFloorGlassSupportProbes=len([s for s in samples if s['floor']==l['floor']]),minimumFloorToSoffitM=3.35,overlapCONArea=l['overlapCONArea'],closedSlabVolumeM3=bpy.data.objects[PREFIX+'floor'+l['floor']+'_slab']['solidVolumeM3']))
  return checks
 checks=physical_checks();bindings={o.name:[m.name for m in o.data.materials]for o in added};fingerprints={o.name:object_fingerprint(o)for o in added}
 component=OUT/'aldwych-registration222-component.blend';bpy.data.libraries.write(str(component),set(added),fake_user=True,compress=True);component_sha=sha(component)
 newmaterials={m.name for o in added for m in o.data.materials if m.name not in before['materials']}
 bpy.ops.wm.open_mainfile(filepath=str(BASE));update();verify_originals(before,set())
 with bpy.data.libraries.load(str(component),link=False)as(available,loaded):loaded.objects=list(fingerprints)
 for o in loaded.objects:
  for i,name in enumerate(bindings[o.name]):o.data.materials[i]=bpy.data.materials[name]
  bpy.data.collections[COLLECTION].objects.link(o);o.hide_render=False;o.hide_set(False)
 bpy.data.objects[GLASS].hide_render=True;update();verify_originals(before,{GLASS});assert all(object_fingerprint(bpy.data.objects[n])==v for n,v in fingerprints.items());assert physical_checks()==checks
 triangles=sum(sum(len(p.vertices)-2 for p in bpy.data.objects[n].data.polygons)for n in fingerprints)
 verification=dict(savedComponentReopenedAndAppended=True,originalObjectsVerified=7651,originalMaterialNodesVerified=len(before['materials']),protectedSpacesVerified=19,protectedSpaceObjectsVerified=678,originalGeometryUVsTransformsBindingsAndModifiersUnchanged=True,allOriginalCollectionMembershipsUnchanged=True,protectedSpaceSceneMembershipsUnchanged=True,onlyListedOriginalVisibilityChanged=True,noFullNativeWritten=True,sourcePhotographsNotUsedAsTextures=True,sourceAndComponentSha256Rechecked=sha(BASE)==SHA and sha(component)==component_sha,addedObjects=len(fingerprints),triangles=triangles,physicalChecks=checks)
 shared=sorted(o.name for o in bpy.data.collections[COLLECTION].all_objects if o.name in before['objects']and not before['visibility'][o.name]and o.name!=GLASS)
 audit=dict(version=222,building='61A',reviewBuildings=['61A','CON'],baseline=str(BASE.relative_to(ROOT)),baselineSha256=SHA,componentPath=str(component.relative_to(ROOT)),componentSha256=component_sha,targetCollection='61A_PUBLIC_STRUCTURE222_study',destinationCollection='61A_PUBLIC_STRUCTURE222_study',collectionSpec=dict(kind='public-interior',name='61A_PUBLIC_STRUCTURE222_study',scene='REVIEW_61A_STRUCTURE222'),interiorCollection='61A_PUBLIC_STRUCTURE222_study',sharedObjects=shared,exteriorObjects=list(fingerprints),addedObjects=list(fingerprints),archivedObjects=[GLASS],changedObjects=[],addedFingerprints=fingerprints,replacementMaterialBindings=bindings,publicViewSuggestion=dict(interiorDisplayMaxZ=25.5,interiorView=dict(position=[-105,85,150],target=[-50,22.2,93],fov=48),interiorSections=[dict(id='4',label='4层：2021楼板与双中庭',minHeight=14.70,maxHeight=18.30),dict(id='6',label='6层：2021楼板与双中庭',minHeight=21.90,maxHeight=25.50)],coordinateSystem='Web coordinates are nativeX,nativeZ,-nativeY',label='61A fourth/sixth historical floor structure',scope='Two demonstrated historical source floors and atria;not complete current61A interior;interiorDisplayMaxZ omits upper ceiling/roof only from dedicated public export;campus/exterior retain physical tops',retainedReception=dict(collection='61A_PUBLIC_INTERIOR_study',scene='ROOM24_61A_RECEPTION',objects=55,unchanged=True)),physicalFloorRegistration=proof,backedGlazingSamples=samples,registrationDiagnostic=json.loads((OUT/'joint-registration-diagnostic.json').read_text()),verification=verification,sourceManifest=str((ARCHIVE/'sources.json').relative_to(ROOT)),changes=['Add the explicitly drawn fourth/sixth floor plates with the two actual source atrium holes,closed structural thickness,finish and soffit.','Add the observed source-plan column grid and estimated inner lightwell faces at these two demonstrated storeys only.','Enable dielectric glazing only on street panes with verified actual floor/soffit support;retain every other source pane and source optical binding.','Preserve both building footprints,CON envelope and unresolved pavilion;no7.85m shift or speculative parcel transfer.'],limitations=['The2021 plans explicitly state indicative purposes;three external controls do not survey the sharedCON wall.','Source floor ownership extending intoCON is clipped to the accepted61A shell,not presented as a complete measured floor.','Floor4z15m,floor6z22.2m,3.35m clear height,250mm slab,16mmfinish,200mmsoffit and140mm lightwell wall are inherited/model estimates.','Sixth-floor registration uses corresponding source atria,not independent external survey controls.','Only fourth and sixth floor plates are evidenced here;intermediate,lower and upper floor layouts remain unmodeled.','Physical ray/volume checks concern modeled connections and enclosure only,not structure,fire,accessibility or current fitout certification.','Historical property-manager and2021/LSE corner-roof photographs differ;capture dates and end views are unresolved,so the accepted roof is retained.'],previews=['before-joint-cutaway.png','after-joint-cutaway.png','before-atria.png','after-atria.png'])
 (OUT/'audit.json').write_text(json.dumps(audit,indent=2)+'\n');(OUT/'verification.json').write_text(json.dumps(verification,indent=2)+'\n');print('ALDWYCH222_READY',component_sha,len(added),triangles,len(samples),flush=True)


if __name__=='__main__':
 try:import bpy
 except ImportError:prepare_sources()
 else:run()
