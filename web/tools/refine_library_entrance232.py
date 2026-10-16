"""Build the accepted estimated local Watkins/library entrance component.

The retained entrance finish, doorway centre and facade axis bound this local
three-riser proposal. Photograph stair location/width remain estimates. Original
231geometry stays untouched. No full-campus file or public export is written.
"""
from pathlib import Path
import sys,json,hashlib,math,collections
import bpy,bmesh
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'web/tools'))
import refine_street_environment232 as street
from refine_streets230 import components,triangles,tree,triangle_signatures
from integrate_exterior_round194 import object_fingerprint,update_scene
from refine_plaza_environment231 import state,preserve,solids
OUT=ROOT/'result/blender/street-environment232';DATA=ROOT/'data/collections/street-environment232'
BASE=street.BASE;SHA=street.SHA
FRAME='LRB196_FINISH_LRB_V109_facade_V35_entry_door_frames'
GLASS='LRB196_FINISH_GLASS181_LRB_NEXT_retained_glazing'
PLINTH='LRB_V109_facade_V35_plinth'
BRICK='LRB196_FINISH_LRB_V109_facade_V35_brick_spandrels'
WINDOW_FRAMES='LRB196_FINISH_LRB_NEXT_retained_window_frames'
SILLS='LRB_NEXT_retained_sills'
ORIGINALS=[FRAME,GLASS,PLINTH,BRICK,WINDOW_FRAMES,SILLS]
PREFIX='SITE232_EST_LRB_'
def write(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def owner(o):return [c.name for c in o.users_collection]

def clone(source,label):
 o=source.copy();o.data=source.data.copy();o.name=PREFIX+label;o.data.name=o.name;bpy.data.collections['LRB_EXTERIOR'].objects.link(o);o['estimatedCandidate']=True;o['originalObject']=source.name;o['sourceReference']='Official2022PublicRealmStrategyPDF51existing-conditionphotographs';return o

def make_mesh(name,vertices,faces,mat,collection):
 m=bpy.data.meshes.new(PREFIX+name);m.from_pydata(vertices,[],faces);m.materials.append(mat);m.update()
 bm=bmesh.new();bm.from_mesh(m);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(m);bm.free()
 uv=m.uv_layers.new(name='MetricUV')
 for p in m.polygons:
  for li in p.loop_indices:
   v=m.vertices[m.loops[li].vertex_index].co;uv.data[li].uv=(v.x,v.z if abs(p.normal.z)<.7 else v.y)
 o=bpy.data.objects.new(PREFIX+name,m);bpy.data.collections[collection].objects.link(o);o['estimatedCandidate']=True;o['scope']='Local source-constrained entry geometry; dimensions estimated, not a measured survey';return o

class Geometry:
 def __init__(self):self.vertices=[];self.faces=[]
 def box(self,center,size):
  start=len(self.vertices);x,y,z=center;a,b,c=[v/2 for v in size]
  self.vertices.extend(world(x+sx*a,y+sy*b,z+sz*c)for sz in [-1,1]for sy in [-1,1]for sx in [-1,1])
  self.faces.extend(tuple(start+v for v in f)for f in [(0,2,3,1),(4,5,7,6),(0,1,5,4),(2,6,7,3),(0,4,6,2),(1,3,7,5)])
 def side_extrusion(self,profile,width):
  start=len(self.vertices);n=len(profile)
  for across in [-width/2,width/2]:self.vertices.extend(world(across,depth,z)for depth,z in profile)
  self.faces.extend([tuple(start+i for i in range(n-1,-1,-1)),tuple(start+n+i for i in range(n))])
  for i in range(n):j=(i+1)%n;self.faces.append(tuple(start+v for v in [i,j,n+j,n+i]))
 def tube(self,a,b,r):
  a=world(*a);b=world(*b);axis=(b-a).normalized();ref=Vector((0,0,1))if abs(axis.z)<.9 else Vector((1,0,0));u=axis.cross(ref).normalized();v=axis.cross(u).normalized();n=12;start=len(self.vertices)
  for p in [a,b]:self.vertices.extend(p+r*(u*math.cos(k*math.tau/n)+v*math.sin(k*math.tau/n))for k in range(n))
  self.faces.extend([tuple(start+i for i in range(n-1,-1,-1)),tuple(start+n+i for i in range(n))])
  for i in range(n):j=(i+1)%n;self.faces.append(tuple(start+v for v in [i,j,n+j,n+i]))
 def finish(self,name,mat,col):return make_mesh(name,self.vertices,self.faces,mat,col)

def world(across,depth,z):return ORIGIN+U*across+N*depth+Vector((0,0,z))
def local(p):q=p-ORIGIN;return q.dot(U),q.dot(N),p.z

def render(sources,added):
 s=bpy.data.scenes['00_CAMPUS_COMPLETE'];bpy.context.window.scene=s
 cam=bpy.data.objects.new(PREFIX+'REVIEW_CAMERA',bpy.data.cameras.new(PREFIX+'REVIEW_CAMERA'));s.collection.objects.link(cam);s.camera=cam;cam.data.clip_end=600;cam.data.sensor_fit='VERTICAL';cam.data.lens=cam.data.sensor_height/(2*math.tan(math.radians(57)/2))
 eye=world(-3.4,6.2,2.3);target=world(0,.45,1.05);cam.location=eye;cam.rotation_euler=(target-eye).to_track_quat('-Z','Y').to_euler();s.render.engine='BLENDER_EEVEE';s.render.resolution_x=1100;s.render.resolution_y=825;s.render.resolution_percentage=100;s.render.image_settings.file_format='PNG'
 for o in s.objects:
  if o.hide_render:o.hide_set(True)
 context=sorted(o.name for o in s.objects if not o.hide_render and o not in sources+added+[cam])
 for phase in ['before','after']:
  for o in sources:o.hide_render=phase=='after';o.hide_set(phase=='after')
  for o in added:o.hide_render=phase=='before';o.hide_set(phase=='before')
  update_scene();s.render.filepath=str(OUT/(phase+'-estimated-library-entrance.png'));bpy.ops.render.render(write_still=True)
 for o in sources:o.hide_render=False;o.hide_set(False)
 for o in added:o.hide_render=False;o.hide_set(False)
 bpy.data.objects.remove(cam,do_unlink=True);bpy.data.cameras.remove(bpy.data.cameras[PREFIX+'REVIEW_CAMERA'])
 return dict(position=[eye.x,eye.z,-eye.y],target=[target.x,target.z,-target.y],fov=57,allAcceptedBuildingsAndCrownsRetained=True,activeContextObjects=len(context),activeContextNamesSha256=hashlib.sha256('\n'.join(context).encode()).hexdigest())

def polygon_signatures(obj,selection=None):
 result=collections.Counter();mesh=obj.data
 for polygon in mesh.polygons:
  if selection is not None and not set(polygon.vertices)<=selection:continue
  corners=[]
  for li in polygon.loop_indices:
   world_point=obj.matrix_world@mesh.vertices[mesh.loops[li].vertex_index].co
   corners.append((tuple(world_point),tuple((layer.name,tuple(layer.data[li].uv))for layer in mesh.uv_layers)))
  rotations=[corners[i:]+corners[:i]for i in range(len(corners))];canonical=min(rotations)
  result[repr((canonical,mesh.materials[polygon.material_index].name,polygon.use_smooth))]+=1
 return result

def cut_local_parts(obj,cutters,back,ffl):
 """Retain raw original faces/UVs; clip only intersecting closed source pieces."""
 original=obj.data;groups=components(obj);chosen=[]
 boxes=[(-.62,.62,-1.05,.55,ffl,2.91),(-.7401,.7401,back-.001,.601,-.01,ffl+.001)]
 for group in groups:
  points=[local(obj.matrix_world@original.vertices[v].co)for v in group]
  lo=[min(p[j]for p in points)for j in range(3)];hi=[max(p[j]for p in points)for j in range(3)]
  if any(all(hi[j]>box[j*2]+1e-7 and lo[j]<box[j*2+1]-1e-7 for j in range(3))for box in boxes):chosen.append(group)
 assert chosen,(obj.name,'no original solid at portal')
 selected=set(v for g in chosen for v in g);untouched=set(range(len(original.vertices)))-selected
 expected=triangle_signatures(obj,untouched);uv_expected=polygon_signatures(obj,untouched)
 keep=sorted(untouched);mapping={v:i for i,v in enumerate(keep)}
 vertices=[original.vertices[v].co.copy()for v in keep];faces=[];slots=[];smooth=[]
 layer_names=[layer.name for layer in original.uv_layers];uvs={name:[]for name in layer_names}
 for polygon in original.polygons:
  if polygon.vertices[0]in selected:continue
  assert all(v in untouched for v in polygon.vertices)
  faces.append(tuple(mapping[v]for v in polygon.vertices));slots.append(polygon.material_index);smooth.append(polygon.use_smooth)
  for name in layer_names:uvs[name].extend(tuple(original.uv_layers[name].data[li].uv)for li in polygon.loop_indices)
 materials=[m for m in original.materials];material_names=[m.name for m in materials];piece_volumes=[]
 for group in chosen:
  piece=obj.copy();piece.data=original.copy();piece.name=PREFIX+'PRIVATE_ORIGINAL_SOLID';bpy.data.collections['LRB_EXTERIOR'].objects.link(piece)
  bm=bmesh.new();bm.from_mesh(piece.data);bm.verts.ensure_lookup_table();part=set(group);bmesh.ops.delete(bm,geom=[v for v in bm.verts if v.index not in part],context='VERTS');bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(piece.data);bm.free()
  for cutter in cutters:
   bpy.context.view_layer.objects.active=piece;mod=piece.modifiers.new('Bounded estimated entrance cut','BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=cutter;bpy.ops.object.modifier_apply(modifier=mod.name)
  if piece.data.polygons:
   bm=bmesh.new();bm.from_mesh(piece.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));volume=bm.calc_volume(signed=True);assert all(e.is_manifold and e.is_contiguous for e in bm.edges)and volume>0,(obj.name,'cut piece not closed positive');piece_volumes.append(volume);bm.to_mesh(piece.data);bm.free()
   offset=len(vertices);vertices.extend(v.co.copy()for v in piece.data.vertices)
   for polygon in piece.data.polygons:
    faces.append(tuple(offset+v for v in polygon.vertices));name=piece.data.materials[polygon.material_index].name;slots.append(material_names.index(name)if name in material_names else 0);smooth.append(polygon.use_smooth)
    for label in layer_names:
     layer=piece.data.uv_layers.get(label);uvs[label].extend(tuple(layer.data[li].uv)if layer else(0.,0.)for li in polygon.loop_indices)
  mesh=piece.data;bpy.data.objects.remove(piece,do_unlink=True);bpy.data.meshes.remove(mesh)
 replacement=bpy.data.meshes.new(obj.name+'_bounded_mesh');replacement.from_pydata(vertices,[],faces);replacement.update()
 for material in materials:replacement.materials.append(material)
 for polygon,slot,shade in zip(replacement.polygons,slots,smooth):polygon.material_index=slot;polygon.use_smooth=shade
 for label in layer_names:
  layer=replacement.uv_layers.new(name=label)
  for target,value in zip(layer.data,uvs[label]):target.uv=value
 obj.data=replacement;bpy.data.meshes.remove(original)
 actual=triangle_signatures(obj);assert not(expected-actual),(obj.name,'untouched triangle changed')
 actual_uv=polygon_signatures(obj);assert not(uv_expected-actual_uv),(obj.name,'untouched UV/material face changed')
 return dict(originalClosedPartsClipped=len(chosen),originalClosedPartsRetainedExactly=len(groups)-len(chosen),retainedTriangles=sum(expected.values()),retainedTrianglesExact=True,retainedPolygonGeometryUVMaterialAndSmoothExact=True,clippedPiecePositiveVolumesM3=piece_volumes)

def build():
 global ORIGIN,U,N
 assert sha(BASE)==SHA;bpy.ops.wm.open_mainfile(filepath=str(BASE));update_scene();before=state();assert len(before['objects'])==8383
 sources=[bpy.data.objects[n]for n in ORIGINALS];assert all(not o.hide_render and owner(o)==['LRB_EXTERIOR']for o in sources)
 frame=sources[0];groups=components(frame);assert len(groups)==3
 centers=[]
 for g in groups:centers.append(sum((frame.matrix_world@frame.data.vertices[v].co for v in g),Vector())/len(g))
 centers.sort(key=lambda p:p.x);ORIGIN=(centers[0]+centers[-1])/2;ORIGIN.z=0;U=(centers[-1]-centers[0]).normalized();U.z=0;N=Vector((U.y,-U.x,0))
 # The original entry floor edge follows the retained facade footprint.
 carpet=bpy.data.objects['LRB168__LRB_gallery_carpet'];floor=tree(triangles(carpet));floor_probes=[];rear=[]
 for across in [-.65,0,.65]:
  lo,hi=-1.,0.
  for _ in range(30):
   mid=(lo+hi)/2;hit=floor.ray_cast(world(across,mid,1),Vector((0,0,-1)),1)
   if hit[0]is not None:lo=mid
   else:hi=mid
  p=world(across,lo-.01,1);hit=floor.ray_cast(p,Vector((0,0,-1)),1);assert hit[0]is not None
  floor_probes.append(dict(across=across,edgeDepth=(lo+hi)/2,finishZ=hit[0].z));rear.append((lo+hi)/2)
 ffl=sum(r['finishZ']for r in floor_probes)/3;assert abs(ffl-.332)<1e-5 and max(rear)-min(rear)<.003
 back=sum(rear)/3;outside=.05;riser=(ffl-outside)/3;assert .09<riser<.10
 # Clone the inherited three door stiles, extending their lower ends only.
 stile=clone(frame,'entry_stiles_to_retained_FFL');inv=stile.matrix_world.inverted();changed=0
 for v in stile.data.vertices:
  p=stile.matrix_world@v.co
  if abs(p.z-.65)<1e-4:p.z=ffl;v.co=inv@p;changed+=1
 assert changed==12;stile.data.update();bm=bmesh.new();bm.from_mesh(stile.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(stile.data);bm.free()
 # The old generic glazing,brick apron and plinth occupy the framed portal.
 # Subtract one bounded true doorway from copied batches,then add two door leaves.
 g=Geometry();g.box((0,-.25,(ffl+2.91)/2),(1.24,1.6,2.91-ffl));cutter=g.finish('PRIVATE_DOOR_CUTTER',sources[2].data.materials[0],'LRB_EXTERIOR')
 g=Geometry();g.box((0,(back+.6)/2,(-.01+ffl+.001)/2),(1.4802,.6-back+.002,ffl+.001+.01));footing=g.finish('PRIVATE_PLATFORM_FOOTING_CLEARANCE',sources[2].data.materials[0],'LRB_EXTERIOR')
 replacements=[stile];cuts=[]
 for original,label in zip(sources[1:],['glazing_with_entry_aperture','plinth_with_entry_aperture','brick_apron_with_entry_aperture','window_frames_without_portal_crossbar','sills_without_portal_obstruction']):
  o=clone(original,label);before_triangles=len(triangles(o));affected=cut_local_parts(o,[cutter,footing],back,ffl);replacements.append(o);cuts.append(dict(original=original.name,replacement=o.name,preservation=affected,beforeTriangles=before_triangles,afterTriangles=len(triangles(o))))
 for temp in [cutter,footing]:
  mesh=temp.data;bpy.data.objects.remove(temp,do_unlink=True);bpy.data.meshes.remove(mesh)
 # Use the same accepted glazing material. Two closed leaves are bound by the
 # existing centre and side stiles; lower edge meets a real low stone threshold.
 g=Geometry()
 for across in [-.31,.31]:g.box((across,-.15,(ffl+.025+2.90)/2),(.555,.045,2.90-(ffl+.025)))
 leaves=g.finish('paired_glazed_entry_leaves',sources[1].data.materials[0],'LRB_EXTERIOR');replacements.append(leaves)
 stone_mat=bpy.data.materials['SITE172_SITE_V47_slab_2_Watkins.001']
 # One contiguous solid cross section: foundation meets native joint bedZ0.04;
 # the rear reaches the measured native floor footprint edge with no floating cap.
 profile=[(back,.04),(back,ffl),(1.30,ffl),(1.30,ffl-riser),(1.70,ffl-riser),(1.70,ffl-2*riser),(2.10,ffl-2*riser),(2.10,.04)]
 g=Geometry();g.side_extrusion(profile,1.48);steps=g.finish('three_low_steps_and_entry_landing',stone_mat,'LRB_EXTERIOR');replacements.append(steps)
 # Short handrails follow photographed circulation edges. This local extent and
 #0.90mrail height are explicitly estimated; no continuous plaza platform implied.
 metal=bpy.data.materials.new(PREFIX+'estimated_rail_dark_metal');metal.use_nodes=True;metal.diffuse_color=(.065,.075,.075,1);p=metal.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=metal.diffuse_color;p.inputs['Roughness'].default_value=.63;p.inputs['Metallic'].default_value=.4
 metal['webBaseColor']=list(metal.diffuse_color);metal['webMetallic']=.4;metal['webRoughness']=.63
 g=Geometry()
 for x in [-.70,.70]:
  for d,z in [(.10,ffl),(1.15,ffl),(1.90,ffl-2*riser)]:g.tube((x,d,z),(x,d,z+.90),.024)
  g.tube((x,.10,ffl+.90),(x,1.15,ffl+.90),.025);g.tube((x,1.15,ffl+.90),(x,1.90,ffl-2*riser+.90),.025)
 rails=g.finish('short_local_landing_handrails',metal,'LRB_EXTERIOR');replacements.append(rails);update_scene()
 # Every landing foundation sample meets the active native paving,except the
 # rear threshold,which abuts the unchanged retained building floor edge.
 paving=tree(triangles(bpy.data.objects['SITE194_SITE_V47_John_Watkins_Plaza']));supports=[]
 for across in [-.72,0,.72]:
  for d in [.05,.65,1.25,1.50,1.90,2.08]:
   p=world(across,d,.6);hit=paving.ray_cast(p,Vector((0,0,-1)),.7);assert hit[0]is not None
   assert .039<hit[0].z<.051;supports.append(dict(across=across,depth=d,pavingZ=hit[0].z,foundationZ=.04))
 solid={o.name:solids(o)for o in [leaves,steps,rails,stile]}
 # Real triangle proof that this local estimate stays clear of231tree containers
 # and existing picnic seating; intentional handrail/base contacts are excluded.
 st=tree(triangles(steps));collision=[]
 for wall in replacements[1:6]:
  hits=st.overlap(tree(triangles(wall)));
  if hits:write(OUT/'candidate-collision-debug.json',dict(object=wall.name,pairs=[dict(step=triangles(steps)[a],wall=triangles(wall)[b])for a,b in hits[:8]]))
  assert not hits,(wall.name,'wall/landingintersections',len(hits));collision.append(dict(object=wall.name,stepTriangleIntersections=0))
 for name in ['SITE231_Watkins_four_concrete_tree_containers','SITE231_Watkins_four_container_soil','SITE174_John_Watkins_Plaza_picnic_seating','03_PUBLIC_REALM_Plane_tree_trunk']:
  hits=st.overlap(tree(triangles(bpy.data.objects[name])));assert not hits,(name,len(hits));collision.append(dict(object=name,stepTriangleIntersections=0))
 # A route through both panels is physically transparent glass only. Test below
 # the door leaves to show old masonry no longer seals the entrance floor zone.
 route=[]
 for o in replacements[1:6]:
  bt=tree(triangles(o))
  for across in [-.28,.28]:
   for height in [ffl+.035,.56,.69,1.2,1.9,2.5]:
    hit=bt.ray_cast(world(across,.5,height),-N,1.5);assert hit[0]is None,(o.name,across,height,hit[0]);route.append(dict(object=o.name,across=across,height=height,masonryOrOldGlassTriangleBlockingPortal=False))
 fingerprints={o.name:object_fingerprint(o)for o in replacements};bindings={o.name:[m.name for m in o.data.materials]for o in replacements};owners={o.name:owner(o)for o in replacements}
 preserve.__globals__['BASE']=BASE;preserve.__globals__['SHA']=SHA;preserve(before)
 comp=OUT/'component-candidate.blend';bpy.data.libraries.write(str(comp),set(replacements),fake_user=True,compress=True);digest=sha(comp)
 bpy.ops.wm.open_mainfile(filepath=str(comp));assert all(object_fingerprint(bpy.data.objects[n])==v for n,v in fingerprints.items())
 bpy.ops.wm.open_mainfile(filepath=str(BASE));update_scene()
 with bpy.data.libraries.load(str(comp),link=False)as(_,dst):dst.objects=list(fingerprints)
 added=dst.objects
 for o in added:
  for i,n in enumerate(bindings[o.name]):
   if n in before['materials']:o.data.materials[i]=bpy.data.materials[n]
  for col in owners[o.name]:bpy.data.collections[col].objects.link(o)
 update_scene();assert all(object_fingerprint(bpy.data.objects[n])==v for n,v in fingerprints.items());preserve(before)
 camera=render([bpy.data.objects[o]for o in ORIGINALS],added);preserve(before)
 proof=dict(origin=list(ORIGIN),acrossDoor=list(U),outwards=list(N),floorProbes=floor_probes,doorFrameOldBottom=.65,doorFrameNewBottom=ffl,doorHeightPolicy='Extend12lowerstilevertices to unchangedFFL; retain frameXY,top,transom,handles and canopy',doorwayClearWidth=1.24,landingWidth=1.48,landingRearDepth=back,landingFrontDepth=1.30,stairOuterDepth=2.10,riserHeightM=riser,visibleRisers=3,treadDepthM=.40,landingFinishZ=ffl,outsidePavingZ=outside,groundSupports=supports,closedPositiveSolids=solid,fixtureCollisions=collision,thresholdRoute=route,source='OfficialPublicRealmStrategy2022PDF51photograph,threevisiblelowsteps and sidehandrail; retained current native floor level and doorway frame axis',estimatedDimensions=['Along-facade stair station follows current framed entrance,not a surveyed photographed riser station','1.48mwidth from1.375mouterdoorframe plus marginal edge allowance','1.30mlanding depth,.40mtreads,.90mrail height are bounded design estimates','Photograph does not establish this local configuration as exact built geometry'],cuts=cuts,noTreeOrPoolMoved=True,noInteriorChanged=True,landingToInteriorFinishDifferenceM=abs(ffl-floor_probes[1]['finishZ']),defaultInteriorExportBoundary='MetadataLRBinteriorCollectionisLRB_PUBLIC_INTERIOR168_study. CandidateobjectsallbelongLRB_EXTERIOR,so standaloneLRBexteriorandcampusexportsinclude them,butisolateddefaultinteriorcollectiondoesnotautomaticallyincludeexternallanding/door. ExistinginteriorFFLandgeometryunchanged. RootmayrendercurrentLRBexteriorcontextwhenneeded.')
 write(OUT/'candidate-support-and-solid-proof.json',proof)
 write(OUT/'audit-candidate.json',dict(version=232,status='estimated_geometry_requires_independent_visual_review',baselineSha256=SHA,componentPath=str(comp.relative_to(ROOT)),componentSha256=digest,targetCollection='LRB_EXTERIOR',destinationCollection='LRB_EXTERIOR',objectOwners=owners,addedObjects=list(fingerprints),archivedObjects=ORIGINALS,changedObjects=[],addedFingerprints=fingerprints,replacementMaterialBindings=bindings,supportProof='result/blender/street-environment232/candidate-support-and-solid-proof.json',sourceManifest='data/collections/street-environment232/entrance-sources.json',verification=dict(componentReopened=True,appendedComponentReopened=True,originalGeometryUVsTransformsBindingsNodesModifiersPropsOwnersAndVisibilityPreserved=True,originalObjectsVerified=len(before['objects']),originalMaterialsVerified=len(before['materials']),protectedSpacesVerified=32,protectedRoomObjectsVerified=1325,noFullNativeSaved=True,originalTreePoolsAndFurniturePreserved=True),records=[dict(name=o.name,owner=owners[o.name],vertices=len(o.data.vertices),triangles=len(triangles(o)))for o in added],previews=['before-estimated-library-entrance.png','after-estimated-library-entrance.png'],camera=camera,limitations=proof['estimatedDimensions'],scope='Estimated local3low-riser entry landing to actual retained libraryFFL. Correct inherited framed-window/masonry doorway obstruction on copied batches. No continuous plaza platform or whole-building rise.',sourceDate='Officialpublication2022,photographcaptureunknown; no2026survey claim'))
 assert sha(BASE)==SHA and sha(comp)==digest
 print('ESTIMATED_ENTRANCE_CANDIDATE_COMPLETE',digest,flush=True)
if __name__=='__main__':build()
