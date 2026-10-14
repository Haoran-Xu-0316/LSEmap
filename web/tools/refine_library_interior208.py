"""Register the LRB ground-floor public service desks to the official guide.

Run in Blender's Text Editor. The v207 campus remains read-only. Four public
counter footprints follow the archived official G plan; obscured Enquiries,
Security and Support curves are interpolated from the visible contour. The
LSE LIFE reception outline is recovered from its PDF path. Counter heights,
finishes and the inherited plan-to-campus transform are estimates. This is
not a surveyed room plan or a reconstruction of restricted staff areas.
"""
from pathlib import Path
import hashlib,json,math,sys
import bpy,bmesh
from mathutils import Vector,Matrix
from mathutils.geometry import tessellate_polygon
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'result/blender/lrb-interior208'
BASE=ROOT/'result/blender/LSE_campus_detailed_v207.blend'
BASE_SHA='44a0b2f09a6a13bbb9532e3a75e415aea7798bef63798e62036bbceb89ded7b0'
COMPONENT=OUT/'library-interior208-component.blend'
COLLECTION='LRB_PUBLIC_INTERIOR168_study'
sys.path.insert(0,str(ROOT/'web/tools'))
from integrate_exterior_round194 import object_fingerprint,update_scene
COUNTERS=[
 ('Enquiries',[(584,289),(592,281),(600,285),(610,287),(620,286),(627,284),(631,297),(621,299),(611,299),(601,297),(592,294)]),
 ('Security',[(631,280),(640,277),(649,276.5),(658,278),(669,281),(679,281),(682,292),(671,293),(659,291),(650,289),(640,290),(635,292)]),
 ('Support',[(687,276),(693,263),(701,247),(714,241),(720,252),(711,259),(705,270),(696,282),(691,287)]),
]

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def point(p):
 x,y=p
 # Inherited affine used by the accepted plan-derived LSE LIFE workspaces.
 return(.0719063418*x-.0000220201874*y+15.6175472,-.00119674917*x-.0704995938*y+46.1506280)
def polygon_area(p):return sum(a[0]*b[1]-b[0]*a[1]for a,b in zip(p,p[1:]+p[:1]))/2

def material(source,name):
 m=bpy.data.materials[source].copy();m.name=name;return m

def prism(vertices,faces,polygon,bottom,top):
 p=list(polygon)
 if polygon_area(p)<0:p.reverse()
 n=len(p);start=len(vertices);vertices.extend((x,y,z)for z in [bottom,top]for x,y in p)
 points=[Vector((x,y,0))for x,y in p];lookup={tuple(q):i for i,q in enumerate(points)}
 for tri in tessellate_polygon([points]):
  ids=[q if isinstance(q,int) else lookup[tuple(q)]for q in tri]
  faces.extend([tuple(start+i for i in reversed(ids)),tuple(start+n+i for i in ids)])
 faces.extend((start+i,start+(i+1)%n,start+(i+1)%n+n,start+i+n)for i in range(n))

def create_batch(name,mat,parts):
 verts=[];faces=[]
 for polygon,lo,hi in parts:prism(verts,faces,polygon,lo,hi)
 mesh=bpy.data.meshes.new(name+'_mesh');mesh.from_pydata(verts,[],faces);mesh.update();mesh.materials.append(mat)
 uv=mesh.uv_layers.new(name='SurfaceUV')
 for f in mesh.polygons:
  for i in f.loop_indices:
   p=mesh.vertices[mesh.loops[i].vertex_index].co;uv.data[i].uv=(p.x,p.y)if abs(f.normal.z)>.5 else(p.x+p.y,p.z)
 obj=bpy.data.objects.new(name,mesh);bpy.data.collections[COLLECTION].objects.link(obj)
 obj['buildingCode']='LRB';obj['floorId']='G';obj['destinationCollection']=COLLECTION
 obj['scope']='Official guide public service desk locations; interpolated contours, heights and material finishes estimated'
 obj['sourcePlan']='data/documents/library_floor_plans.pdf page3';obj['dimensionsEstimated']=True
 obj['counterLabels']=json.dumps([x[0]for x in COUNTERS]+['LSE LIFE reception'])
 return obj

def render(label,added):
 # Temporary G-only cutaway copies, never written into the component or campus.
 scene=bpy.data.scenes.new('LRB208_SERVICE_REVIEW');scene.render.engine='CYCLES';scene.cycles.samples=24
 scene.render.resolution_x=1200;scene.render.resolution_y=760;scene.render.resolution_percentage=100
 scene.world=bpy.data.worlds.new('LRB208_REVIEW_WORLD');scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.8,.85,.9,1);scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.6
 clones=[]
 for old in list(bpy.data.collections[COLLECTION].all_objects):
  if old.hide_render or old.type!='MESH' or(old in added and label=='before'):continue
  assert old.parent is None
  source_matrix=old.matrix_basis.copy()
  clone=old.copy();clone.data=old.data.copy();clone.data.transform(source_matrix);clone.matrix_basis=Matrix.Identity(4);bm=bmesh.new();bm.from_mesh(clone.data)
  remove=[v for v in bm.verts if not .0-1e-4<=v.co.z<=3.92]
  bmesh.ops.delete(bm,geom=remove,context='VERTS');bm.to_mesh(clone.data);bm.free()
  if not len(clone.data.polygons):bpy.data.objects.remove(clone);continue
  scene.collection.objects.link(clone);clones.append(clone)
 camera=bpy.data.objects.new('LRB208_REVIEW_CAMERA',bpy.data.cameras.new('LRB208_REVIEW_CAMERA'));scene.collection.objects.link(camera);scene.camera=camera
 camera.data.type='ORTHO';camera.data.ortho_scale=39;camera.location=(72,-2,35);target=Vector((72,27,.8));camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler()
 lamp=bpy.data.objects.new('LRB208_REVIEW_SUN',bpy.data.lights.new('LRB208_REVIEW_SUN','SUN'));scene.collection.objects.link(lamp);lamp.rotation_euler=(.45,-.35,-.3);lamp.data.energy=2
 scene.render.filepath=str(OUT/(label+'-public-service-zone.png'));scene.render.image_settings.file_format='PNG';bpy.context.window.scene=scene;bpy.ops.render.render(write_still=True)
 bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE']
 for o in clones+[camera,lamp]:bpy.data.objects.remove(o,do_unlink=True)
 bpy.data.scenes.remove(scene)

def run():
 OUT.mkdir(parents=True,exist_ok=True);assert sha(BASE)==BASE_SHA
 bpy.ops.wm.open_mainfile(filepath=str(BASE));update_scene()
 originals={o.name:object_fingerprint(o)for o in bpy.data.objects};visibility={o.name:o.hide_render for o in bpy.data.objects}
 sourcecheck=json.loads((OUT/'source-review.json').read_text());assert sourcecheck['sameBytes']
 life=next(c for c in json.loads((OUT/'counter-footprints.json').read_text())if c['label']=='LSE LIFE reception')
 footprints=[dict(label=label,pixels=p,world=[point(q)for q in p],height=.86)for label,p in COUNTERS]
 footprints.append(dict(label='LSE LIFE reception',pixels=life['planPixels'],world=[point(q)for q in life['planPixels']],height=.80))
 floor=bpy.data.objects['LRB168__LRB_library_floor_slabs'];verts=[floor.matrix_basis@v.co for v in floor.data.vertices];tree=BVHTree.FromPolygons(verts,[list(p.vertices)for p in floor.data.polygons],all_triangles=False)
 rays=[]
 for item in footprints:
  pts=item['world'];centre=tuple(sum(p[k]for p in pts)/len(pts)for k in range(2))
  for x,y in pts+[centre]:
   hit=tree.ray_cast(Vector((x,y,3.5)),Vector((0,0,-1)),4)
   assert hit[0]and abs(hit[0].z-.32)<1e-4,(item['label'],hit)
   rays.append(dict(label=item['label'],xy=[x,y],supportZ=hit[0].z))
  assert all(math.hypot(x-75.593385,y-13.262314)>10.4 for x,y in pts)
  item['areaSquareMetres']=abs(polygon_area(pts));item['baseZ']=.332;item['topZ']=.332+item['height']
 # Existing G furniture box components stay outside every new counter envelope.
 body_parts=[(x['world'],.332,x['topZ']-.045)for x in footprints]
 top_parts=[(x['world'],x['topZ']-.045,x['topZ'])for x in footprints]
 body=create_batch('LRB208_G_public_service_counter_bodies',material('ATRIA_white','LRB208_counter_white'),body_parts)
 top=create_batch('LRB208_G_public_service_counter_tops',material('LRB_V21_desk','LRB208_counter_neutral_tops'),top_parts)
 added=[body,top];update_scene()
 collisions=[]
 for old in list(bpy.data.collections[COLLECTION].all_objects):
  if old in added or old.type!='MESH' or old.get('floorId')!='G':continue
  tree_old=BVHTree.FromPolygons([old.matrix_basis@v.co for v in old.data.vertices],[list(p.vertices)for p in old.data.polygons])
  for new in added:
   tree_new=BVHTree.FromPolygons([v.co for v in new.data.vertices],[list(p.vertices)for p in new.data.polygons])
   if tree_new.overlap(tree_old):collisions.append([new.name,old.name])
 assert not collisions,collisions
 assert all(object_fingerprint(bpy.data.objects[n])==v for n,v in originals.items())
 states={o.name:object_fingerprint(o)for o in added};bpy.data.libraries.write(str(COMPONENT),set(added),fake_user=True,compress=True)
 render('before',added);render('after',added)
 audit=dict(version=208,building='LRB',baseline=str(BASE.relative_to(ROOT)),baselineSha256=BASE_SHA,component=str(COMPONENT.relative_to(ROOT)),componentSha256=sha(COMPONENT),destinationCollection=COLLECTION,targetCollection=COLLECTION,addedObjects=[o.name for o in added],archivedObjects=[],originalObjectPolicy='New public counters without an original alias; all original objects retained unchanged',footprints=footprints,sourceReview='result/blender/lrb-interior208/source-review.json',sourceUrl=sourcecheck['url'],sourcePlanPage=3,registration='Inherited affine matching accepted G workspace placement; not an independent surveyed registration',inheritedRegistrationCheck='result/blender/lrb-interior208/inherited-registration-check.json',maxPerimeterControlResidualMetres=.7888271896420499,pixelToWorldAffine=[[.0719063418,-.0000220201874,15.6175472],[-.00119674917,-.0704995938,46.1506280]],supportRayCount=len(rays),supportRays=rays,furnitureCollisions=collisions,scope='Four guide-supported public service desk footprints at G, replacing no native object',limitations=['Three service desk contours interpolate parts obscured by diagram text; LSE LIFE contour recovered from PDF path79.','Counter heights, slab datum, neutral finish and inherited affine scale are estimates.','No exact2026 room survey, accessible-compliance claim, staff area, closed room, upper floor, atrium outline or exterior change.','Existing G furniture and all17 independent room studies remain unchanged.'])
 (OUT/'audit.json').write_text(json.dumps(audit,indent=2)+'\n')
 # Actually reopen the unchanged full native and reload only the saved component.
 bpy.ops.wm.open_mainfile(filepath=str(BASE));update_scene()
 with bpy.data.libraries.load(str(COMPONENT),link=False)as(src,dst):
  assert set(src.objects)==set(states);dst.objects=list(states)
 for o in dst.objects:
  bpy.data.collections[COLLECTION].objects.link(o);assert object_fingerprint(o)==states[o.name]
 update_scene()
 assert all(object_fingerprint(bpy.data.objects[n])==v for n,v in originals.items())
 assert all(bpy.data.objects[n].hide_render==v for n,v in visibility.items())
 verification=dict(savedComponentReopened=True,componentSha256=sha(COMPONENT),baselineSha256=sha(BASE),baselineUnchanged=sha(BASE)==BASE_SHA,originalObjectsVerified=len(originals),originalGeometryUVsMaterialBindingsUnchanged=True,allOriginalVisibilityUnchanged=True,newBatchesVerified=len(states),supportRaysVerified=len(rays),supportedFloorZ=.32,noGStudyFurnitureIntersections=True,noAtriumOpeningIntrusion=True,exteriorAndRoomSamplesUnchanged=True,renderedBeforeAfter=True)
 (OUT/'verification.json').write_text(json.dumps(verification,indent=2)+'\n');print('LRB208_VERIFIED',verification,flush=True)

if __name__=='__main__':
 run();bpy.ops.wm.quit_blender()
