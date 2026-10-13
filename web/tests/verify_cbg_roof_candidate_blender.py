"""Reopen the private CBG roof component and inspect physical access/optical paths.

This does not certify a measured roof layout or publish an architectural study.
"""
from pathlib import Path
import bpy,bmesh,json,hashlib,sys
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'result/blender/cbg-roof-candidate'
sys.path.insert(0,str(ROOT/'web/tools'))
from refine_cbg_roof_envelope import coordinates,PREFIX,REAR_ROOF,TERRACE,STAIR_PARTS
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
for x in (-37,-30,-24):
 hits=ray((x,15,50),(0,-1,0),2.0)
 if hits:failures.append(dict(scope='rear-upper-row',x=x,hits=hits[:2]))
 paths.append(dict(scope='rear-roof',point=[x,15,50],clearDistance=2.0))
# Source-backed roof profile: garden on one end, retained higher middle core,
# and the photographed lower setback at the open end. Inspect actual geometry
# rather than accepting the candidate's own declared dimensions.
roof_profiles=[]
for x,y,low,high in [(-38,8.5,48.20,48.5),(-31,8.5,48.20,48.5),(-25,8.5,48.20,48.5),
                       (-17,10,52.1,52.5),(-8,10,52.1,52.5),(2,9,48.15,48.5),(5,9,48.15,48.5)]:
    hits=ray((x,y,54),(0,0,-1),8)
    assert hits and low<=hits[0]['point'][2]<=high, ('roof profile',x,y,hits[:2])
    roof_profiles.append(dict(point=[x,y],height=hits[0]['point'][2],object=hits[0]['object']))
for x in (-39,-31,-24):
    hits=ray((x,8,50),(0,-1,0),3)
    assert hits and 'terrace_thermal_' in hits[0]['object'], ('exposed upper academic strip',x,hits[:2])
for x in (-17,-8,-2):
    hits=ray((x,15,50),(0,-1,0),2)
    assert hits, ('middle core unexpectedly removed',x)
for bed in range(3):
    soil=bpy.data.objects[PREFIX+f'bed_{bed}_soil']
    assert len(soil.data.vertices)==8 and len(soil.data.polygons)==6
assert bpy.data.objects[PREFIX+'roof_paving_tiles'].data.polygons
assert all(bpy.data.objects[PREFIX+f'core_terrace_door_{leaf}'].data.materials[0]['webOpacity']==.82 for leaf in range(2))
# Test the complete new walking width, both flights and the mid landing.
# This catches a slab over an outer tread even when the centre happens to clear.
stair=bpy.data.objects[PREFIX+'upper_stair_treads']
assert len(stair.data.vertices)==28*8
headroom=[]
for start in range(0,len(stair.data.vertices),8):
    points=[local(stair.matrix_world@vertex.co) for vertex in stair.data.vertices[start:start+8]]
    left=min(point.x for point in points);right=max(point.x for point in points)
    y=sum(point.y for point in points)/8;z=max(point.z for point in points)+.025
    for fraction in (.15,.5,.85):
        x=left+(right-left)*fraction
        hits=ray((x,y,z),(0,0,1),2.0)
        if hits:failures.append(dict(scope='upper-return-stair-headroom',tread=start//8,point=[x,y,z],hits=hits[:2]))
        headroom.append(dict(point=[x,y,z],clearHeight=2.0))
mid_landing=bpy.data.objects[PREFIX+'upper_stair_mid_landing']
landing_points=[local(mid_landing.matrix_world@vertex.co) for vertex in mid_landing.data.vertices]
landing_headroom=[]
for x in (-12.3,-11.1,-9.9):
    for y in (-.7,-.1,.15):
        z=max(point.z for point in landing_points)+.025
        hits=ray((x,y,z),(0,0,1),2)
        if hits:failures.append(dict(scope='upper-stair-mid-landing-headroom',point=[x,y,z],hits=hits[:2]))
        landing_headroom.append(dict(point=[x,y,z],clearHeight=2.0))
# The source's first eight flights, rails and landings are copied exactly.
retained_stair_vertices=0
for name,(count,last) in STAIR_PARTS.items():
    original=bpy.data.objects[name];retained=bpy.data.objects[PREFIX+'connected_'+name]
    assert len(retained.data.vertices)==(count-last)*8
    expected=[tuple(vertex.co) for vertex in original.data.vertices[:(count-last)*8]]
    actual=[tuple(vertex.co) for vertex in retained.data.vertices]
    assert actual==expected, ('older stair geometry changed',name)
    retained_stair_vertices+=len(actual)
# Registered dimensions come from the drawing's corners, not candidate metadata.
registration=json.loads((ROOT/'data/collections/cbg_roof_registration/registration.json').read_text())['registration']['landmarks']
left=sum(registration[key]['local'][0] for key in ['upperStairFrontLeft','upperStairRearLeft'])/2
right=sum(registration[key]['local'][0] for key in ['upperStairFrontRight','upperStairRearRight'])/2
all_points=[local(stair.matrix_world@vertex.co) for vertex in stair.data.vertices]
assert abs(min(point.x for point in all_points)-(left+.12))<.05
assert abs(max(point.x for point in all_points)-(right-.12))<.05
# The upper landing has a continuous floor connection into the academic strip.
connections=[]
for x,y,z in [(-12.2,4.45,REAR_ROOF),(-11.2,5.12,REAR_ROOF),(-11.2,5.25,REAR_ROOF),
              (-4.4,1.95,TERRACE),(-6.5,2.0,TERRACE),(-8.2,2.50,TERRACE),
              (-8.2,3.35,TERRACE),(-10.0,4.55,TERRACE)]:
    hits=ray((x,y,z+.20),(0,0,-1),.5)
    assert hits, ('stair landing connection unsupported',x,y,z)
    assert abs(hits[0]['point'][2]-z)<.045, ('landing floor level mismatch',x,y,hits[:2])
    overhead=ray((x,y,z+.03),(0,0,1),2)
    if overhead:failures.append(dict(scope='stair-floor-connection-headroom',point=[x,y,z],hits=overhead[:2]))
    connections.append(dict(point=[x,y,z],floor=hits[0]['object'],clearHeight=2.0))


# Closed rail tubes, caps, stringers and treads must remain valid solid meshes.
# This covers the new geometry rather than only the inherited trimmed boxes.
new_stair_solids=[]
for obj in objects:
    if not obj.name.startswith(PREFIX+'upper_stair_'):
        continue
    mesh=bmesh.new();mesh.from_mesh(obj.data)
    boundary=sum(1 for edge in mesh.edges if len(edge.link_faces)!=2)
    volume=mesh.calc_volume(signed=True)
    assert boundary==0 and volume>0, ('invalid stair solid',obj.name,boundary,volume)
    mesh.free()
    new_stair_solids.append(dict(object=obj.name,nonManifoldEdges=boundary,signedVolume=volume))
assert new_stair_solids

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
 reopened=True,preservedLowerFaces=preserved_lower_faces,roofProfiles=roof_profiles,upperStairHeadroom=headroom,midLandingHeadroom=landing_headroom,stairConnections=connections,retainedStairVertices=retained_stair_vertices,newStairSolids=new_stair_solids,clearPaths=paths,closedReplacementSolids=topology,failures=failures,
 limitations=['Probes establish local absence of inherited top windows/plates; whole internal circulation and actual dimensions remain unverified.']),indent=2)+'\n')
assert not failures, failures
print('CBG_PRIVATE_ROOF_PHYSICAL_CHECKS_PASSED',len(paths),len(topology),flush=True)
