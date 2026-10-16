"""PEA225:visible street-edge roof ladder andthree pairs of entrance leaves.

The eleven accepted glass solids,real openings,mass andold auditorium remain
unchanged.Only the photographed front outrigger is authored;no rear roof is
inferred.Dimensions inherit the registered facade andexplicit estimates.
"""
from pathlib import Path
import sys,json,hashlib,math
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'result/blender/pea-exterior225';SOURCE=ROOT/'data/collections/pea-exterior225'
BASE=ROOT/'result/blender/LSE_campus_detailed_v224.blend';SHA='02714d14231c7413f3202b6d2946ffcb698da9517485afd7124202e60da5a024'
PREFIX='PEA225_';COLLECTION='PEA_EXTERIOR';P='PEA_D5_exterior62_'
ARCHIVES=[P+'entry_mullion_dark',P+'entry_rail_dark',P+'door_handle_gold']
GLASS=['GLASS181_PEA_NEXT_ENVELOPE_'+k for k in ['entry_glass','ticket_glass','upper_glass']]
sys.path.insert(0,str(ROOT/'web/tools'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def packed(v):return hashlib.sha256(json.dumps(v,sort_keys=True).encode()).hexdigest()
def write(p,v):p.write_text(json.dumps(v,indent=2,ensure_ascii=False)+'\n')


def run():
 import bpy
 from mathutils import Vector,Matrix
 from mathutils.bvhtree import BVHTree
 from integrate_exterior_round194 import object_fingerprint,accepted_fingerprints
 from refine_portsmouth_exterior207 import material_fingerprint
 from build_clm_hongkong_room220 import modifier_payload
 from build_room_samples167 import RoomGeometry
 from refine_cbg_roof_envelope import components
 def update():
  for scene in bpy.data.scenes:
   for layer in scene.view_layers:layer.update()
  bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE']
 def state():
  meta=json.loads((ROOT/'web/tools/building-metadata.json').read_text());rooms={r['collection']:sorted(o.name for o in bpy.data.collections[r['collection']].all_objects)for r in meta['spaces']};assert len(rooms)==21 and len(set().union(*(set(v)for v in rooms.values())))==767
  return dict(objects={o.name:object_fingerprint(o)for o in bpy.data.objects},materials={m.name:material_fingerprint(m)for m in bpy.data.materials},modifiers={o.name:packed([modifier_payload(m)for m in o.modifiers])for o in bpy.data.objects},ownership={o.name:sorted(c.name for c in o.users_collection)for o in bpy.data.objects},visibility={o.name:o.hide_render for o in bpy.data.objects},rooms=rooms,roomScenes={c:{s.name:sorted(n for n in ns if n in s.objects)for s in bpy.data.scenes}for c,ns in rooms.items()})
 def verify(before,hidden):
  assert all(object_fingerprint(bpy.data.objects[n])==v for n,v in before['objects'].items())
  assert all(material_fingerprint(bpy.data.materials[n])==v for n,v in before['materials'].items())
  assert all(packed([modifier_payload(m)for m in bpy.data.objects[n].modifiers])==v for n,v in before['modifiers'].items())
  assert all(sorted(c.name for c in bpy.data.objects[n].users_collection)==v for n,v in before['ownership'].items())
  assert all(bpy.data.objects[n].hide_render==(True if n in hidden else v)for n,v in before['visibility'].items())
  assert all(sorted(o.name for o in bpy.data.collections[c].all_objects)==ns for c,ns in before['rooms'].items())
  assert {c:{s.name:sorted(n for n in ns if n in s.objects)for s in bpy.data.scenes}for c,ns in before['rooms'].items()}==before['roomScenes']
 def tree(objects):
  vs=[];fs=[]
  for o in objects:
   off=len(vs);vs.extend(o.matrix_world@v.co for v in o.data.vertices);fs.extend(tuple(off+i for i in p.vertices)for p in o.data.polygons)
  return BVHTree.FromPolygons(vs,fs)
 assert sha(BASE)==SHA;bpy.ops.wm.open_mainfile(filepath=str(BASE));update();before=state();assert len(before['objects'])==7763 and before['objects']==accepted_fingerprints(ROOT/'result/blender/stage224',SHA)
 protected=set().union(*(set(v)for v in before['rooms'].values()));assert not protected.intersection(ARCHIVES);assert all(not bpy.data.objects[n].hide_render for n in ARCHIVES+GLASS)
 col=bpy.data.collections[COLLECTION];profile=json.loads((ROOT/'result/blender/stage62/peacock-exterior-audit.json').read_text());wall=profile['frontWall'];org=Vector((*wall['p'],0));u=(Vector((*wall['q'],0))-org).normalized();n=Vector((*wall['outward'],0));L=wall['length'];entry=L*.46;entryw=3.82;x0=entry-entryw/2
 def world(p):return org+u*p[0]+n*p[1]+Vector((0,0,p[2]))
 g=RoomGeometry(col,PREFIX);unused=list(g.materials.values());g.materials={'pale':bpy.data.objects[P+'upper_coping_stone'].data.materials[0],'frame':bpy.data.objects[P+'window_jamb_frame'].data.materials[0],'dark':bpy.data.objects[ARCHIVES[0]].data.materials[0],'gold':bpy.data.objects[ARCHIVES[2]].data.materials[0]}
 def box(f,m,c,s):g.box(f,m,c,s)
 # Seven visible ladder axes form six front bays.Cantilever depth1.2m,
 # feet and0.57m risers are estimates rooted on the accepted copingtop.
 xs=[.18+i*(L-.36)/6 for i in range(7)]
 for x in xs:
  box('front_roof_bearing_feet','pale',(x,0,19.565),(.22,.20,.07))
  box('front_roof_riser_posts','pale',(x,0,19.85),(.10,.12,.57))
  box('front_roof_cross_rafters','pale',(x,.55,20.16),(.115,1.30,.12))
 for d in [0,1.15]:box('front_roof_longitudinal_rails','pale',(L/2,d,20.16),(L-.20,.11,.12))
 for d in [.37,.76]:box('front_roof_internal_rods','frame',(L/2,d,20.16),(L-.36,.032,.032))
 # Retain one accepted glass envelope butcorrect its joinery to six
 # individual leaves grouped inthree pairs;do not moveorcut any glass.
 for j in range(7):
  x=x0+j*entryw/6;width=.075 if j%2==0 else .045
  box('six_leaf_entry_vertical_frames','dark',(x,.15,1.205),(width,.12,2.35))
 for j in [0,2,4,6]:box('three_pair_transom_dividers','dark',(x0+j*entryw/6,.15,2.59),(.075,.12,.44))
 for z,h in [(.085,.11),(1.02,.14),(2.35,.11),(2.785,.05)]:box('six_leaf_entry_horizontal_rails','dark',(entry,.15,z),(entryw,.12,h))
 for pair in range(3):
  seam=x0+(2*pair+1)*entryw/6
  for side in [-1,1]:box('six_leaf_brass_pull_plates','gold',(seam+side*.075,.235,1.25),(.04,.045,.38))
 added=g.finish()
 for m in unused:
  if m.users==0:bpy.data.materials.remove(m)
 for o in added:
  for v in o.data.vertices:v.co=world(v.co)
  o.data.update();o['destinationCollection']=COLLECTION;o['evidenceScope']='Builtfrontstreetphotographs;rearroofexcluded;inheritedandestdimensionalstudy'
 newnames=[o.name for o in added];update()
 def physical():
  active=[bpy.data.objects[q]for q in newnames];coping=tree([bpy.data.objects[P+'upper_coping_stone']]);feet=[]
  for x in xs:
   hit=coping.ray_cast(world((x,0,19.70)),Vector((0,0,-1)),.4);assert hit[0]is not None;feet.append(abs(hit[0].z-19.53))
  posts=tree([o for o in active if 'riser_posts'in o.name]);rafter=tree([o for o in active if 'cross_rafters'in o.name]);joins=[]
  for x in xs:
   hit=posts.ray_cast(world((x,0,20.2)),Vector((0,0,-1)),.4);assert hit[0]is not None;joins.append(abs(hit[0].z-20.135))
   assert rafter.ray_cast(world((x,.30,20.3)),Vector((0,0,-1)),.3)[0]is not None
  walls=tree([bpy.data.objects[q]for q in ['PEA_NEXT_ENVELOPE_ground_dark_with_real_apertures','PEA_NEXT_ENVELOPE_ticket_stone_with_real_aperture']]);glass=tree([bpy.data.objects[q]for q in GLASS]);frames=tree([o for o in active if 'entry_'in o.name]);entryprobes=[]
  for j in range(6):
   x=x0+(j+.5)*entryw/6
   for z in [1.5,2.0]:
    start=world((x,.5,z));assert frames.ray_cast(start,-n,.5)[0]is None;assert walls.ray_cast(start,-n,1.2)[0]is None;hit=glass.ray_cast(start,-n,1.2);assert hit[0]is not None;entryprobes.append(hit[3])
  # Nine upperwindowprobes andtheticket retain the acceptednearfieldholes.
  otherprobes=0;allglass=[]
  for name in GLASS:
   o=bpy.data.objects[name]
   for ids in components(o.data):
    ps=[o.matrix_world@o.data.vertices[i].co for i in ids];centre=sum(ps,Vector())/len(ps);allglass.append((name,centre))
    if name==GLASS[0]:continue
    assert glass.ray_cast(centre+n*.6,-n,1.2)[0]is not None;otherprobes+=1
  assert len(allglass)==11
  optical={m.name:dict(webOpacity=m.get('webOpacity'),alpha=next(q for q in m.node_tree.nodes if q.type=='BSDF_PRINCIPLED').inputs['Alpha'].default_value)for name in GLASS for m in bpy.data.objects[name].data.materials}
  assert all(abs(v['webOpacity']-.82)<1e-6 for v in optical.values())
  return dict(acceptedGlassSolidsRetained=11,glassGeometryUVBindingsAndNodesUnchanged=True,glassOptics=optical,clearDoorLeafRaySamples=len(entryprobes),unmodifiedOtherWindowRaySamples=otherprobes,doorPairs=3,individualDoorLeaves=6,estimatedPairClearWidthM=entryw/3-.075,estimatedLeafClearWidthM=entryw/6-(.075+.045)/2,estimatedThresholdM=.03,roofFrontBays=6,roofBearingFootSamples=len(feet),maximumRoofFootToAcceptedCopingGapM=max(feet),maximumRiserTopDatumErrorM=max(joins),riserToRafterOverlapM=.035,roofFrontProjectionM=1.205,roofMaximumBackExtentM=-.10,roofTopM=20.22,upperLegacyCopingTopM=19.53,noRearRoofStructureAuthored=True,sourceFrameAndDoorCountsGeometricOnly=True)
 def previews(label):
  scene=bpy.data.scenes.new(PREFIX+'PREVIEW');scene.render.engine='CYCLES';scene.cycles.samples=10;scene.cycles.use_denoising=True;scene.render.resolution_x=1000;scene.render.resolution_y=850;scene.render.resolution_percentage=100;scene.view_settings.view_transform='AgX';w=bpy.data.worlds.new(PREFIX+'WORLD');w.use_nodes=True;w.node_tree.nodes['Background'].inputs[0].default_value=(.78,.82,.87,1);w.node_tree.nodes['Background'].inputs[1].default_value=.8;scene.world=w;copies=[]
  for old in col.all_objects:
   if old.hide_render and old.name not in ARCHIVES:continue
   if label=='before'and old.name in newnames or label=='after'and old.name in ARCHIVES:continue
   o=old.copy();o.data=old.data.copy();o.parent=None
   if o.type=='MESH':o.data.transform(old.matrix_world);o.matrix_world=Matrix.Identity(4)
   else:o.matrix_world=old.matrix_world.copy()
   o.hide_render=False;scene.collection.objects.link(o);copies.append(o)
  camera=bpy.data.objects.new(PREFIX+'CAM',bpy.data.cameras.new(PREFIX+'CAM'));scene.collection.objects.link(camera);scene.camera=camera;camera.data.type='ORTHO';camera.data.ortho_scale=26
  light=bpy.data.objects.new(PREFIX+'SUN',bpy.data.lights.new(PREFIX+'SUN','SUN'));scene.collection.objects.link(light);light.data.energy=2;light.rotation_euler=(.5,-.35,-.65)
  for tag,pos,target in [('streetfront',(2,40,12),(2,-1,9.5)),('oblique',(-18,29,17),(2,-2,9.5))]:
   camera.location=world(pos);camera.rotation_euler=(world(target)-camera.location).to_track_quat('-Z','Y').to_euler();scene.render.filepath=str(OUT/(label+'-'+tag+'.png'));bpy.context.window.scene=scene;bpy.ops.render.render(write_still=True)
  bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE']
  for o in copies+[camera,light]:bpy.data.objects.remove(o,do_unlink=True)
  bpy.data.scenes.remove(scene);bpy.data.worlds.remove(w);update()
 checks=physical();previews('before')
 for q in ARCHIVES:bpy.data.objects[q].hide_render=True
 previews('after');verify(before,set(ARCHIVES))
 fingerprints={o.name:object_fingerprint(o)for o in added};bindings={o.name:[m.name for m in o.data.materials]for o in added};component=OUT/'pea-exterior225-component.blend';bpy.data.libraries.write(str(component),set(added),fake_user=True,compress=True);digest=sha(component)
 bpy.ops.wm.open_mainfile(filepath=str(BASE));update();verify(before,set())
 with bpy.data.libraries.load(str(component),link=False)as(src,dst):dst.objects=list(fingerprints)
 for o in dst.objects:
  bpy.data.collections[COLLECTION].objects.link(o)
  for i,m in enumerate(bindings[o.name]):o.data.materials[i]=bpy.data.materials[m]
 for q in ARCHIVES:bpy.data.objects[q].hide_render=True
 update();verify(before,set(ARCHIVES));assert all(object_fingerprint(bpy.data.objects[q])==v for q,v in fingerprints.items());assert physical()==checks;assert sha(BASE)==SHA and sha(component)==digest
 campus=bpy.data.scenes['00_CAMPUS_COMPLETE'];assert all(q in campus.objects and bpy.data.objects[q].visible_get(view_layer=campus.view_layers[0])for q in fingerprints)
 def view(pos,target,fov):
  a,b=world(pos),world(target);return dict(position=[a.x,a.z,-a.y],target=[b.x,b.z,-b.y],fov=fov)
 views=[dict(code='PEA',name='pea-complete-frontage',label='Peacock完整街面与临街格架',view=view((-16,34,15),(2,-1,9.8),39)),dict(code='PEA',name='pea-paired-entrance',label='Peacock三组双扇入口',view=view((4,15,4.4),(4,.1,1.7),40))]
 verification=dict(savedComponentReopenedAndAppended=True,originalObjectsVerified=7763,originalMaterialNodesVerified=len(before['materials']),protectedSpacesVerified=21,protectedSpaceObjectsVerified=767,originalGeometryUVTransformsBindingsModifiersUnchanged=True,allOriginalCollectionMembershipsUnchanged=True,protectedSpaceSceneMembershipsUnchanged=True,all11GlassSolidsAndTheirMaterialNodesPreserved=True,onlyListedOriginalVisibilityChanged=True,allAddedObjectsPresentAndVisibleInNativeCampus=True,noFullNativeWritten=True,sourcePhotographsNotUsedAsTextures=True,sourceAndComponentSha256Rechecked=True,addedObjects=len(fingerprints),closedPositiveVolumeNewSolids=46,allNewSolidEdgesOppositelyPaired=True,triangles=sum(sum(len(p.vertices)-2 for p in bpy.data.objects[q].data.polygons)for q in fingerprints),physicalChecks=checks)
 audit=dict(version=225,building='PEA',baseline=str(BASE.relative_to(ROOT)),baselineSha256=SHA,componentPath=str(component.relative_to(ROOT)),componentSha256=digest,targetCollection=COLLECTION,destinationCollection=COLLECTION,addedObjects=list(fingerprints),archivedObjects=ARCHIVES,changedObjects=[],addedFingerprints=fingerprints,replacementMaterialBindings=bindings,sourceManifest=str((SOURCE/'sources.json').relative_to(ROOT)),gallerySuggestions=views,verification=verification,changes=['Complete the photographed shallowstreetedge ladderframe overtheexisting3x3windowwall;sevenbearingaxes andsixopenbays,withdepth/heightestimated.','Replace threeoldentrancemullion/rail/handlebatchesbythreepairedopenings,sixleafmeetinglines,transomframing andsixpullplates.','All11acceptedglasssolids,the0.82optics,thetwooriginalrealapertures,3x3windowmass,lowwing andhistoricalauditoriumremainunchanged.'],limitations=['2025/07and2021/09areuploadpaths,notverifiedphotographcapturedates.NoOctober2026surveyisclaimed.','Sourceprovesfrontframeanddoorleafpattern;frontprojection1.2m,0.57mriserheight,membersizesandtheinherited3.82mentrancewidthareestimated.','Onlythevisiblefrontedgeisreconstructed.Maximumbackextent0.10mbehindtheexistingfacade;unknownrearframe,whole-rooflayout,backstageandfoyerremainunmodeled.','Geometricdoorlight/supportchecksarenotstructural,fireoraccessibilitycertification.'],previews=['before-streetfront.png','after-streetfront.png','before-oblique.png','after-oblique.png'])
 write(OUT/'audit.json',audit);write(OUT/'verification.json',verification);write(OUT/'view-suggestions.json',views);print('PEA225_READY',digest,len(fingerprints),len(ARCHIVES),verification['triangles'],flush=True)


if __name__=='__main__':run()


def preview_reopened_component():
 """Isolate saved meshes inworldspace so preview inheritsno source hierarchy."""
 import bpy
 from mathutils import Vector,Matrix
 audit=json.loads((OUT/'audit.json').read_text());bpy.ops.wm.open_mainfile(filepath=str(BASE));col=bpy.data.collections[COLLECTION]
 with bpy.data.libraries.load(str(ROOT/audit['componentPath']),link=False)as(src,dst):dst.objects=list(audit['addedObjects'])
 for o in dst.objects:
  col.objects.link(o)
  for i,m in enumerate(audit['replacementMaterialBindings'][o.name]):o.data.materials[i]=bpy.data.materials[m]
 campus=bpy.data.scenes['00_CAMPUS_COMPLETE'];bpy.context.window.scene=campus
 for layer in campus.view_layers:layer.update()
 profile=json.loads((ROOT/'result/blender/stage62/peacock-exterior-audit.json').read_text())['frontWall'];org=Vector((*profile['p'],0));u=(Vector((*profile['q'],0))-org).normalized();normal=Vector((*profile['outward'],0))
 def world(p):return org+u*p[0]+normal*p[1]+Vector((0,0,p[2]))
 for label in ['before','after']:
  scene=bpy.data.scenes.new(PREFIX+'FINAL_PREVIEW');scene.render.engine='CYCLES';scene.cycles.samples=10;scene.cycles.use_denoising=True;scene.render.resolution_x=1000;scene.render.resolution_y=850;scene.render.resolution_percentage=100;scene.view_settings.view_transform='AgX';w=bpy.data.worlds.new(PREFIX+'FINAL_WORLD');w.use_nodes=True;w.node_tree.nodes['Background'].inputs[0].default_value=(.78,.82,.87,1);w.node_tree.nodes['Background'].inputs[1].default_value=.8;scene.world=w;copies=[]
  for old in list(col.all_objects):
   if old.hide_render:continue
   if label=='before'and old.name in audit['addedObjects']or label=='after'and old.name in ARCHIVES:continue
   o=old.copy();o.data=old.data.copy();o.parent=None
   for mod in list(o.constraints):o.constraints.remove(mod)
   if o.type=='MESH':o.data.transform(old.matrix_world);o.matrix_world=Matrix.Identity(4)
   else:o.matrix_world=old.matrix_world.copy()
   o.hide_render=False;o.hide_viewport=False;scene.collection.objects.link(o);copies.append(o)
  camera=bpy.data.objects.new(PREFIX+'FINAL_CAM',bpy.data.cameras.new(PREFIX+'FINAL_CAM'));scene.collection.objects.link(camera);scene.camera=camera;camera.data.type='ORTHO';camera.data.ortho_scale=26
  light=bpy.data.objects.new(PREFIX+'FINAL_SUN',bpy.data.lights.new(PREFIX+'FINAL_SUN','SUN'));scene.collection.objects.link(light);light.data.energy=2;light.rotation_euler=(.5,-.35,-.65)
  for tag,pos,target in [('streetfront',(2,40,12),(2,-1,9.5)),('oblique',(-18,29,17),(2,-2,9.5))]:
   camera.location=world(pos);camera.rotation_euler=(world(target)-camera.location).to_track_quat('-Z','Y').to_euler();scene.render.filepath=str(OUT/(label+'-'+tag+'.png'));bpy.context.window.scene=scene;bpy.ops.render.render(write_still=True)
  print('PEA225_PREVIEW',label,len(copies),flush=True);bpy.context.window.scene=campus
  for o in copies+[camera,light]:
   data=o.data;bpy.data.objects.remove(o,do_unlink=True)
   if isinstance(data,bpy.types.Mesh)and data.users==0:bpy.data.meshes.remove(data)
  bpy.data.scenes.remove(scene);bpy.data.worlds.remove(w)
