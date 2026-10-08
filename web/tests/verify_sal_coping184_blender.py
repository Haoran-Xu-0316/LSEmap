"""Reopen SAL's continuous coping and check solid topology and aperture clearance."""
from pathlib import Path
import hashlib,json,sys,math
import bpy,bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree
root=Path(__file__).resolve().parents[2];sys.path.insert(0,str(root/'web/tools'))
from refine_architectural_glass import shape_signature
from refine_rooms import geometry_signatures
from refine_sal_coping184 import apply_sal_coping184,registered_chains,SOURCE,TARGET,GLASS_SOURCE,GLASS_TARGET,GLASS_CLEARANCE,WALL_SOURCE,WALL_TARGET
from refine_exterior_glass181 import is_glazing
stage=root/'result/blender/stage184';model=root/'result/blender/LSE_campus_detailed_v184.blend'
proof=json.loads((stage/'building-refinement.json').read_text())
assert hashlib.sha256(model.read_bytes()).hexdigest()==proof['sourceModelSha256']
bpy.ops.wm.open_mainfile(filepath=str(model))
for scene in bpy.data.scenes:
 for layer in scene.view_layers:layer.update()
assert geometry_signatures()==proof['geometrySignatures']
for name,digest in proof['originalShapesAndUVs'].items():assert shape_signature(bpy.data.objects[name])==digest
source=bpy.data.objects[SOURCE];target=bpy.data.objects[TARGET]
assert source.hide_render and not target.hide_render
assert list(target.data.materials)==list(source.data.materials)
assert target.data.uv_layers and target.name in bpy.data.scenes['00_CAMPUS_COMPLETE'].objects
chains,_=registered_chains(source);record=proof['changes'][0]
assert [[list(p)for p in chain]for chain in chains]==record['centrelineAnchors']
assert [len(chain)for chain in chains]==[23]*7
mesh=bmesh.new();mesh.from_mesh(target.data);assert all(len(e.link_faces)==2 for e in mesh.edges)
pending=set(mesh.verts);volumes=[]
while pending:
 seed=pending.pop();stack=[seed];vertices={seed}
 while stack:
  vertex=stack.pop()
  for edge in vertex.link_edges:
   neighbour=edge.other_vert(vertex)
   if neighbour in pending:pending.remove(neighbour);vertices.add(neighbour);stack.append(neighbour)
 faces={face for v in vertices for face in v.link_faces};centre=sum((v.co for v in vertices),Vector())/len(vertices)
 volume=sum((f.verts[0].co-centre).dot((f.verts[i].co-centre).cross(f.verts[i+1].co-centre))/6 for f in faces for i in range(1,len(f.verts)-1))
 assert volume>0;volumes.append(volume)
mesh.free();assert len(volumes)==7
assert len(target.data.polygons)==938 and len(source.data.polygons)==1232
# Coping must leave actual current glass apertures clear, not merely keep their object names.
def tree(obj):return BVHTree.FromPolygons([obj.matrix_world@v.co for v in obj.data.vertices],[tuple(f.vertices)for f in obj.data.polygons])
new_tree=tree(target);overlaps=[]
for obj in bpy.data.collections['SAL_EXTERIOR'].all_objects:
 if obj.type!='MESH' or obj.hide_render or not any(mat and is_glazing(mat)for mat in obj.data.materials):continue
 pairs=new_tree.overlap(tree(obj))
 if pairs:overlaps.append({'object':obj.name,'trianglePairs':len(pairs)})
assert not overlaps,overlaps
glass_source=bpy.data.objects[GLASS_SOURCE];glass_target=bpy.data.objects[GLASS_TARGET]
assert glass_source.hide_render and not glass_target.hide_render
assert list(glass_source.data.materials)==list(glass_target.data.materials)
assert len(record['recessedGablePanes'])==7
moved={i for pane in record['recessedGablePanes']for i in pane['vertices']}
assert len(moved)==56
for old,new in zip(glass_source.data.vertices,glass_target.data.vertices):
 if old.index not in moved:assert old.co==new.co
 else:assert abs(old.co.z-new.co.z)<1e-5
for layer in glass_source.data.uv_layers:
 assert [tuple(uv.uv)for uv in layer.data]==[tuple(uv.uv)for uv in glass_target.data.uv_layers[layer.name].data]
for pane in record['recessedGablePanes']:
 assert abs(pane['copingRear']-pane['newFront']-GLASS_CLEARANCE)<1e-6
assert [tuple(face.vertices)for face in glass_source.data.polygons]==[tuple(face.vertices)for face in glass_target.data.polygons]
# Recessed panes must remain visible through the actual registered window holes.
angle=math.radians(24.35);normal=Vector((-math.sin(angle),math.cos(angle),0));axis=Vector((-math.cos(angle),-math.sin(angle),0))
vertices=[];faces=[];owners=[]
for obj in bpy.data.collections['SAL_EXTERIOR'].all_objects:
 if obj.type!='MESH' or obj.hide_render:continue
 offset=len(vertices);vertices.extend(obj.matrix_world@v.co for v in obj.data.vertices)
 obj.data.calc_loop_triangles()
 faces.extend(tuple(offset+i for i in triangle.vertices)for triangle in obj.data.loop_triangles)
 owners.extend([obj.name]*len(obj.data.loop_triangles))
facade=BVHTree.FromPolygons(vertices,faces,all_triangles=True);visible_panes=0
for pane in record['recessedGablePanes']:
 points=[glass_target.matrix_world@glass_target.data.vertices[i].co for i in pane['vertices']]
 centre=sum(points,Vector())/len(points);width=max(p.dot(axis)for p in points)-min(p.dot(axis)for p in points);height=max(p.z for p in points)-min(p.z for p in points)
 # One-tenth-width lies within clear glazing in both the two-light
 # gables and three-light central window, away from stone and sash bars.
 point=centre+axis*(width*.1)+Vector((0,0,height*.13))
 hit=facade.ray_cast(point+normal*.8,-normal,2)
 assert hit[2] is not None and owners[hit[2]]==GLASS_TARGET,{'pane':pane,'firstObject':owners[hit[2]]if hit[2]is not None else None}
 visible_panes+=1
assert visible_panes==7
assert bpy.data.objects[WALL_SOURCE].hide_render and not bpy.data.objects[WALL_TARGET].hide_render
assert list(bpy.data.objects[WALL_SOURCE].data.materials)==list(bpy.data.objects[WALL_TARGET].data.materials)
# Earlier registered finishes and OLD bench contacts stay valid in this complete source.
for name in ['SAL183_SAL_Pilaster_brick_cores','SAL183_SAL_Chimney_stacks']:
 assert abs(bpy.data.objects[name].data.materials[0].diffuse_color[1]-.285)<1e-6
base=bpy.data.objects['OLD182_foyer_stone_bench_plinth'];bench=bpy.data.objects['OLD174_foyer_waiting_bench'];floor=bpy.data.objects['OLD174_foyer_lower_limestone_floor']
assert abs(min(v.co.z for v in base.data.vertices)-max(v.co.z for v in floor.data.vertices))<1e-6
assert abs(max(v.co.z for v in base.data.vertices)-min(v.co.z for v in bench.data.vertices))<1e-6
assert apply_sal_coping184()['alreadyApplied'];assert geometry_signatures()==proof['geometrySignatures']
(stage/'reopened-verification.json').write_text(json.dumps({'savedSceneReopened':True,'idempotent':True,'allOriginalShapesAndUVsPreserved':True,'closedPositiveCopingChains':len(volumes),'windowGlassOverlaps':overlaps,'recessedGablePanes':7,'visibleThroughWindowApertures':7,'paneSilhouettesAndFinishesRetained':True,'registeredAnchorsRetained':True,'internalEndCapsRemoved':294,'sourceModelSha256':proof['sourceModelSha256']},indent=2)+'\n')
print('SAL184_REOPENED_VERIFIED')
