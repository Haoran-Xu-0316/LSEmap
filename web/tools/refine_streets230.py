"""Remove one proven conflicting complete bench from the accepted229batch.

Fixed Blender authoring configuration. The native229file is read-only. The
component contains all six other benches, with original geometry and bindings.
"""
from pathlib import Path
import hashlib,json,sys,collections,math
sys.dont_write_bytecode=True
import bpy,bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'result/blender/streets230'
DATA=ROOT/'data/collections/streets230'
BASE=ROOT/'result/blender/LSE_campus_detailed_v229.blend'
SHA='2ec7b3a42776f870e99b2a63f83f0736b70a0f2400a145b477f3d80bf54baa18'
ORIGINAL='SITE_V47_Slatted_benches'
REPLACEMENT='SITE230_Slatted_benches_retained_six'
COLLECTION='03_PUBLIC_REALM'
SOIL='SITE222_Square_six_tree_pool_soil'
STONE='SITE229_Square_six_jointed_stone_tree_pool_enclosures'
sys.path.insert(0,str(ROOT/'web/tools'))
from integrate_exterior_round194 import object_fingerprint,update_scene
from refine_portsmouth_exterior207 import material_fingerprint
from refine_ksw_exterior219 import modifier_state

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def write(path,value):path.write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n')
def components(obj):
 adjacency=[set()for v in obj.data.vertices]
 for e in obj.data.edges:
  a,b=e.vertices;adjacency[a].add(b);adjacency[b].add(a)
 pending=set(range(len(adjacency)));parts=[]
 while pending:
  first=min(pending);pending.remove(first);seen={first};queue=[first]
  while queue:
   for n in adjacency[queue.pop()]:
    if n in pending:pending.remove(n);seen.add(n);queue.append(n)
  parts.append(sorted(seen))
 return parts

def triangles(obj,selection=None):
 obj.data.calc_loop_triangles();result=[]
 for t in obj.data.loop_triangles:
  if selection is not None and not set(t.vertices)<=selection:continue
  result.append(dict(sourceTriangle=t.index,sourcePolygon=t.polygon_index,points=[list(obj.matrix_world@obj.data.vertices[i].co)for i in t.vertices],material=obj.data.materials[t.material_index].name))
 return result

def triangle_signatures(obj,selection=None):
 return collections.Counter(json.dumps((t['points'],t['material']))for t in triangles(obj,selection))
def tree(rows):
 return BVHTree.FromPolygons([Vector(p)for t in rows for p in t['points']],[(i*3,i*3+1,i*3+2)for i in range(len(rows))],all_triangles=True,epsilon=0)
def protected():
 meta=json.loads((ROOT/'web/tools/building-metadata.json').read_text())
 rooms={r['collection']:sorted(o.name for o in bpy.data.collections[r['collection']].all_objects)for r in meta['spaces']}
 assert len(rooms)==29 and len(set().union(*(set(v)for v in rooms.values())))==1170
 return dict(objects={o.name:object_fingerprint(o)for o in bpy.data.objects},materials={m.name:material_fingerprint(m)for m in bpy.data.materials},owners={o.name:sorted(c.name for c in o.users_collection)for o in bpy.data.objects},modifiers={o.name:modifier_state(o)for o in bpy.data.objects},props={o.name:repr(sorted(o.items()))for o in bpy.data.objects},visibility={o.name:o.hide_render for o in bpy.data.objects},rooms=rooms,scenes={s.name:sorted(s.objects.keys())for s in bpy.data.scenes})
def verify_protected(state):
 assert all(object_fingerprint(bpy.data.objects[n])==v for n,v in state['objects'].items())
 assert all(material_fingerprint(bpy.data.materials[n])==v for n,v in state['materials'].items())
 assert all(sorted(c.name for c in bpy.data.objects[n].users_collection)==v for n,v in state['owners'].items())
 assert all(modifier_state(bpy.data.objects[n])==v for n,v in state['modifiers'].items())
 assert all(repr(sorted(bpy.data.objects[n].items()))==v for n,v in state['props'].items())
 assert all(bpy.data.objects[n].hide_render==v for n,v in state['visibility'].items())
 assert all(sorted(o.name for o in bpy.data.collections[n].all_objects)==v for n,v in state['rooms'].items())
 assert all(sorted(n for n in bpy.data.scenes[s].objects.keys()if n!=REPLACEMENT)==v for s,v in state['scenes'].items())
 assert sha(BASE)==SHA

def collision(source,parts):
 assert len(parts)==245
 # The accepted47authoring loop contributes exactly35closed pieces per bench:
 # five slats, three brackets, three crossbars, six stems, six plates, twelve bolts.
 groups=[parts[i:i+35]for i in range(0,len(parts),35)]
 assert len(groups)==7 and all(sum(len(p)for p in g)==568 for g in groups)
 for group in groups:
  assert [len(p)for p in group]==[len(p)for p in groups[0]]
 group=groups[1];selected=set(v for p in group for v in p)
 bench=triangles(source,selected);bt=tree(bench);intersections=[]
 for name in [STONE,SOIL]:
  rows=triangles(bpy.data.objects[name]);hits=bt.overlap(tree(rows));assert hits
  intersections.append(dict(object=name,intersectingTrianglePairs=len(hits),witnessPairs=[dict(bench=bench[a],pool=rows[b])for a,b in hits[:6]]))
 feet=[]
 for local in [8,12,18,22,28,32]:
  points=[source.matrix_world@source.data.vertices[i].co for i in group[local]]
  low=Vector([min(p[i]for p in points)for i in range(3)]);high=Vector([max(p[i]for p in points)for i in range(3)]);centre=(low+high)/2
  probe=dict(benchPart=35+local,xy=list(centre)[:2],baseZ=low.z,topZ=high.z,hits=[])
  for name in [SOIL,STONE,'SITE206_CBG_square_stone_courses']:
   rows=triangles(bpy.data.objects[name]);btree=tree(rows);hit=btree.ray_cast(Vector((centre.x,centre.y,1)),Vector((0,0,-1)),2)
   if hit[0]is not None:probe['hits'].append(dict(object=name,surfaceZ=hit[0].z,penetrationM=max(0,hit[0].z-low.z),triangle=rows[hit[2]]))
  feet.append(probe)
 assert sum(any(h['object']==SOIL and h['penetrationM']>.31 for h in p['hits'])for p in feet)>=3
 assert sum(any(h['object']==STONE and h['penetrationM']>.41 for h in p['hits'])for p in feet)>=1
 solid=json.loads((OUT/'positive-volume-overlap.json').read_text());assert solid['baselineSha256']==SHA and solid['witness']['positiveOverlapVolumeLowerBoundM3']>0
 proof=dict(positiveVolumeProof='result/blender/streets230/positive-volume-overlap.json',positiveVolumeProofSha256=sha(OUT/'positive-volume-overlap.json'),baselineSha256=SHA,originalObject=ORIGINAL,originalCollection=COLLECTION,assemblyIndex=1,connectedParts=list(range(35,70)),verticesRemoved=len(selected),facesRemoved=sum(set(p.vertices)<=selected for p in source.data.polygons),trianglesRemoved=len(bench),assemblyComposition=dict(seatSlats=5,supportBrackets=3,crossbars=3,legStems=6,footPlates=6,fasteners=12),surfaceIntersections=intersections,footProbes=feet,decision='Remove the complete legacy bench because its wooden seat physically occupies strictly positive solid volume inside the accepted stone enclosure. Buried anchor depth and photographic absence are not removal criteria.',allOtherAssembliesRetained=6,noNewBenchOrRelocation=True)
 write(OUT/'collision-proof.json',proof);return selected,proof

def render_comparison(source,replacement):
 scene=bpy.data.scenes['00_CAMPUS_COMPLETE'];bpy.context.window.scene=scene
 camera=bpy.data.objects.new('STREETS230_REVIEW_CAMERA',bpy.data.cameras.new('STREETS230_REVIEW_CAMERA'));scene.collection.objects.link(camera);scene.camera=camera;camera.data.clip_end=600;camera.data.sensor_fit='VERTICAL'
 scene.render.engine='BLENDER_EEVEE';scene.render.resolution_x=1100;scene.render.resolution_y=825;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG'
 if hasattr(scene,'eevee'):scene.eevee.taa_render_samples=8
 # All native objects keep their accepted rendering visibility, including crowns.
 for o in scene.objects:
  if o.hide_render:o.hide_set(True)
 replacement.hide_set(False)
 active=sorted(o.name for o in scene.objects if not o.hide_render and o not in [source,replacement,camera])
 views=[dict(name='square-bench-conflict',position=[25,2.1,33],target=[30,.32,29],fov=55)]
 records=[]
 for view in views:
  eye=Vector((view['position'][0],-view['position'][2],view['position'][1]));target=Vector((view['target'][0],-view['target'][2],view['target'][1]));camera.location=eye;camera.rotation_euler=(target-eye).to_track_quat('-Z','Y').to_euler();camera.data.lens=camera.data.sensor_height/(2*math.tan(math.radians(view['fov'])/2));update_scene()
  graph=bpy.context.evaluated_depsgraph_get();probes=[]
  for direction in [(1,0,0),(-1,0,0),(0,1,0),(0,-1,0),(0,0,1),(0,0,-1)]:
   hit=scene.ray_cast(graph,eye,Vector(direction),distance=.25);probes.append(dict(direction=direction,nearHit=hit[4].name if hit[0]else None))
  assert all(p['nearHit']is None for p in probes),(view,probes)
  for phase in ['before','after']:
   source.hide_render=phase=='after';source.hide_set(phase=='after');replacement.hide_render=phase=='before';replacement.hide_set(phase=='before');update_scene();scene.render.filepath=str(OUT/(phase+'-'+view['name']+'.png'));bpy.ops.render.render(write_still=True)
  records.append(dict(view=view,cameraEyeProbes=probes,allNativeBuildingsAndCrownsRetained=True))
 source.hide_render=False;source.hide_set(False);replacement.hide_render=False;replacement.hide_set(False)
 bpy.data.objects.remove(camera,do_unlink=True);bpy.data.cameras.remove(bpy.data.cameras['STREETS230_REVIEW_CAMERA'])
 return records,hashlib.sha256('\n'.join(active).encode()).hexdigest(),len(active)

def build():
 assert sha(BASE)==SHA
 bpy.ops.wm.open_mainfile(filepath=str(BASE));update_scene();before=protected();assert len(before['objects'])==8179
 source=bpy.data.objects[ORIGINAL];assert not source.hide_render and [c.name for c in source.users_collection]==[COLLECTION]
 parts=components(source);removed,proof=collision(source,parts);retained=set(range(len(source.data.vertices)))-removed
 expected=triangle_signatures(source,retained)
 clone=source.copy();clone.data=source.data.copy();clone.name=REPLACEMENT;clone.data.name=REPLACEMENT;clone['originalObject']=ORIGINAL;clone['scope']='Remove only the complete existing bench physically penetrating unchanged229stone pool and222soil; retain six other complete benches exactly.'
 bm=bmesh.new();bm.from_mesh(clone.data);bm.verts.ensure_lookup_table();bmesh.ops.delete(bm,geom=[bm.verts[i]for i in sorted(removed)],context='VERTS');bm.to_mesh(clone.data);bm.free();clone.data.update();bpy.data.collections[COLLECTION].objects.link(clone);update_scene()
 assert triangle_signatures(clone)==expected
 assert len(components(clone))==210 and len(clone.data.vertices)==3408 and len(clone.data.polygons)==2124
 bindings=[m.name for m in source.data.materials];fingerprint=object_fingerprint(clone)
 verify_protected(before)
 component=OUT/'component.blend';bpy.data.libraries.write(str(component),{clone},fake_user=True,compress=True);component_sha=sha(component)
 # Reopen the standalone file before using it in the full-campus comparison.
 bpy.ops.wm.open_mainfile(filepath=str(component));loaded=bpy.data.objects[REPLACEMENT];assert object_fingerprint(loaded)==fingerprint and triangle_signatures(loaded)==expected
 bpy.ops.wm.open_mainfile(filepath=str(BASE));update_scene()
 with bpy.data.libraries.load(str(component),link=False)as(_,target):target.objects=[REPLACEMENT]
 clone=target.objects[0]
 for i,name in enumerate(bindings):clone.data.materials[i]=bpy.data.materials[name]
 bpy.data.collections[COLLECTION].objects.link(clone);update_scene();assert object_fingerprint(clone)==fingerprint and triangle_signatures(clone)==expected;verify_protected(before)
 views,visible_sha,visible_count=render_comparison(bpy.data.objects[ORIGINAL],clone);verify_protected(before)
 references=json.loads((ROOT/'data/collections/street-environment222/sources.json').read_text())[:2]
 for r in references:assert sha(ROOT/r['path'])==r['sha256']
 manifest=dict(version=230,baselineSha256=SHA,existingSourceManifest='data/collections/street-environment222/sources.json',sources=references,sourceInterpretation='Published built photographs establish stone tree-pool context. Removal is established by strictly positive native wood-seat/stone solid-volume overlap; anchor embedment is not the decision basis.',noSourcePhotoPixelsReused=True,collisionProof='result/blender/streets230/collision-proof.json',geometryPolicy='No paving, soil, stone, path, tree, stair, or building geometry is edited. No replacement bench placement is invented.')
 write(DATA/'sources.json',manifest)
 write(OUT/'audit.json',dict(version=230,baselineSha256=SHA,componentPath=str(component.relative_to(ROOT)),componentSha256=component_sha,targetCollection=COLLECTION,destinationCollection=COLLECTION,addedObjects=[REPLACEMENT],archivedObjects=[ORIGINAL],changedObjects=[],addedFingerprints={REPLACEMENT:fingerprint},replacementMaterialBindings={REPLACEMENT:bindings},originalObject=ORIGINAL,records=[dict(name=REPLACEMENT,vertices=3408,faces=2124,triangles=sum(expected.values()),retainedBenches=6,removedBenches=1)],positiveVolumeProof='result/blender/streets230/positive-volume-overlap.json',positiveVolumeProofSha256=sha(OUT/'positive-volume-overlap.json'),collisionProof=manifest['collisionProof'],sourceManifest=str((DATA/'sources.json').relative_to(ROOT)),verification=dict(componentReopened=True,appendedComponentReopened=True,retainedTrianglesExact=True,originalGeometryUVsTransformsBindingsNodesModifiersPropsOwnersAndVisibilityPreserved=True,originalObjectsVerified=8179,originalMaterialsVerified=len(before['materials']),protectedSpacesVerified=29,protectedRoomObjectsVerified=1170,noPathChange=True,noFullNativeSaved=True),previews=[phase+'-'+v['view']['name']+'.png'for v in views for phase in ['before','after']],cameras=views,productionVisibility=dict(allAcceptedBuildingsAndCrownsRetained=True,activeContextObjects=visible_count,activeContextNamesSha256=visible_sha),gallerySuggestions=[dict(code='CAMPUS',name=v['name'],label='LSE Square长椅碰撞修正',view={k:v[k]for k in ['position','target','fov']})for v in [r['view']for r in views]],limitations='One inherited7bench batch is replaced by an exact6bench subset. The accepted pool footprint is unchanged; this correction does not survey or relocate any bench.'))
 assert sha(BASE)==SHA and sha(component)==component_sha
 print('STREETS230_COMPONENT',dict(componentSha256=component_sha,retainedTriangles=sum(expected.values()),proof=proof['assemblyComposition']),flush=True)

if __name__=='__main__':build()
