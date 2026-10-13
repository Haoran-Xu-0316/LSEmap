"""Reopen the private CBG roof component and inspect physical access/optical paths.

This does not certify a measured roof layout or publish an architectural study.
"""
from pathlib import Path
import bpy,bmesh,json,hashlib,sys
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'result/blender/cbg-roof-candidate'
sys.path.insert(0,str(ROOT/'web/tools'))
from refine_cbg_roof_envelope import coordinates,PREFIX,REAR_ROOF,TERRACE
proof=json.loads((OUT/'candidate.json').read_text())
component=ROOT/proof['candidatePath']
assert hashlib.sha256(component.read_bytes()).hexdigest()==proof['candidateSha256']
assert hashlib.sha256((ROOT/'result/blender/LSE_campus_detailed_v193.blend').read_bytes()).hexdigest()==proof['sourceModelSha256']
bpy.ops.wm.read_factory_settings(use_empty=True)
with bpy.data.libraries.load(str(component)) as (source,target):
 target.collections=[name for name in source.collections if name in ['CBG_EXTERIOR','CBG_PUBLIC_INTERIOR_study']]
for collection in target.collections:bpy.context.scene.collection.children.link(collection)
for layer in bpy.context.scene.view_layers:layer.update()
local,world=coordinates()
objects=[o for o in bpy.context.scene.objects if o.type=='MESH' and not o.hide_render]
trees=[(o,BVHTree.FromPolygons([o.matrix_world@v.co for v in o.data.vertices],[tuple(p.vertices) for p in o.data.polygons])) for o in objects]
def ray(point,direction,distance):
 start=world(point);end=world(Vector(point)+Vector(direction));hits=[]
 for obj,tree in trees:
  hit=tree.ray_cast(start,(end-start).normalized(),distance)
  if hit[0] is not None:hits.append(dict(object=obj.name,distance=hit[3],point=list(local(hit[0]))))
 return sorted(hits,key=lambda hit:hit['distance'])
paths=[];failures=[]
for y in (-.8,.4,3.0):
 for z in (46.2,47.4,48.3):
  hits=ray((8.0,y,z),(-1,0,0),2.0)
  if hits:failures.append(dict(scope='open-end',y=y,z=z,hits=hits[:2]))
  paths.append(dict(scope='top-end',point=[8,y,z],clearDistance=2.0))
for x in (-31,-16,0):
 hits=ray((x,15,50),(0,-1,0),2.0)
 if hits:failures.append(dict(scope='rear-upper-row',x=x,hits=hits[:2]))
 paths.append(dict(scope='rear-roof',point=[x,15,50],clearDistance=2.0))
guard=bpy.data.objects[PREFIX+'end_guard']
assert len(guard.data.vertices)==8 and len(guard.data.polygons)==6
material=guard.data.materials[0]
assert abs(material['webOpacity']-.28)<1e-5
assert material['webClosedGlazing'] and material.node_tree.nodes['Principled BSDF'].inputs['Metallic'].default_value==0
# Unaffected lower-floor faces retain exact native vertices, material slots and
# corner UVs. This guards against a volume cutter re-partitioning the entire
# tower merely because its combined mesh reaches the roof.
def face_key(obj,face):
    rows=[]
    for loop in face.loop_indices:
        vertex=obj.data.vertices[obj.data.loops[loop].vertex_index]
        rows.append((tuple(vertex.co),tuple(tuple(layer.data[loop].uv) for layer in obj.data.uv_layers)))
    return (face.material_index,tuple(sorted(rows)))
preserved_lower_faces=0
for record in proof['replacements']:
    original=bpy.data.objects[record['source']];replacement=bpy.data.objects[record['target']]
    existing={face_key(replacement,face) for face in replacement.data.polygons}
    for face in original.data.polygons:
        if max((original.matrix_world@original.data.vertices[i].co).z for i in face.vertices)<44:
            assert face_key(original,face) in existing, ('altered lower floor',original.name,face.index)
            preserved_lower_faces+=1
assert preserved_lower_faces>1000
# Closed replacement solids must retain closed topology. A four-corner curtain
# pane is deliberately single-sided and is assessed by the optical paths above.
topology=[]
for obj in objects:
 if not obj.name.startswith(PREFIX+'trim_'):continue
 source_name=obj['originalObject'];source=bpy.data.objects[source_name]
 if source_name.startswith('GLASS181_CBG_NEXT_EXTERIOR166_'):continue
 bm=bmesh.new();bm.from_mesh(obj.data)
 boundary=sum(len(edge.link_faces)!=2 for edge in bm.edges)
 if boundary:failures.append(dict(scope='solid-topology',object=obj.name,nonManifoldEdges=boundary,examples=[dict(faces=len(edge.link_faces),points=[list(local(obj.matrix_world@v.co)) for v in edge.verts]) for edge in bm.edges if len(edge.link_faces)!=2][:8]))
 bm.free();topology.append(dict(object=obj.name,nonManifoldEdges=boundary,cornerUVLayers=len(obj.data.uv_layers)))
assert topology
(OUT/'physical-checks.json').write_text(json.dumps(dict(candidateSha256=proof['candidateSha256'],source193Unchanged=True,
 reopened=True,preservedLowerFaces=preserved_lower_faces,clearPaths=paths,closedReplacementSolids=topology,failures=failures,
 limitations=['Probes establish local absence of inherited top windows/plates; whole internal circulation and actual dimensions remain unverified.']),indent=2)+'\n')
assert not failures, failures
print('CBG_PRIVATE_ROOF_PHYSICAL_CHECKS_PASSED',len(paths),len(topology),flush=True)
