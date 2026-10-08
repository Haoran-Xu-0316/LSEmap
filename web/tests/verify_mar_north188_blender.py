"""Reopen the isolated MAR candidate and verify upper-recess clearance only.

This is not whole-building or release acceptance. The middle opening, roof
terraces and registration of higher wings remain outstanding.
"""
from pathlib import Path
import hashlib,json,math,sys
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'web/tools'))
from refine_mar_exterior174 import world,N,local
from refine_mar_north188 import NAMES,SOURCES
from refine_architectural_glass import shape_signature
OUT=ROOT/'result/blender/mar-north-candidate'
proof=json.loads((OUT/'candidate.json').read_text())
model=ROOT/'result/blender/LSE_campus_detailed_v187.blend'
assert hashlib.sha256(model.read_bytes()).hexdigest()==proof['sourceModelSha256']
bpy.ops.wm.open_mainfile(filepath=str(model));scene=bpy.data.scenes['00_CAMPUS_COMPLETE'];bpy.context.window.scene=scene
for layer in scene.view_layers:layer.update()
before={o.name:shape_signature(o)for o in bpy.data.objects if o.type=='MESH'}
with bpy.data.libraries.load(str(OUT/'north-envelope-candidate.blend'),link=False)as (available,loaded):
    assert set(proof['addedObjects'])<=set(available.objects)
    loaded.objects=list(proof['addedObjects'])
trim_owners={record['target']:list(bpy.data.objects[record['source']].users_collection)for record in proof['trimRecords']}
trim_owners.update({record['target']:list(bpy.data.objects[record['ownerSource']].users_collection)for record in proof['floorInfillRecords']})
for obj in loaded.objects:
    assert obj is not None
    owners=trim_owners.get(obj.name,[bpy.data.collections['MAR_EXTERIOR']])
    for owner in owners:owner.objects.link(obj)
    obj.hide_render=False;obj.hide_set(False)
for name in proof['archivedObjects']:
    bpy.data.objects[name].hide_render=True;bpy.data.objects[name].hide_set(True)
for layer in scene.view_layers:layer.update()
assert all(shape_signature(bpy.data.objects[name])==digest for name,digest in before.items())
for name in proof['addedObjects']:
    obj=bpy.data.objects[name]
    assert all(math.isfinite(c)for v in obj.data.vertices for c in v.co)
    for uv in obj.data.uv_layers:assert all(math.isfinite(c)for corner in uv.data for c in corner.uv)
for original,replacement in zip(SOURCES,NAMES):
    assert bpy.data.objects[original].hide_render and not bpy.data.objects[replacement].hide_render

visible=set()
def collect(group):
    if group.hide_render:return
    visible.update(o for o in group.objects if not o.hide_render)
    for child in group.children:collect(child)
collect(scene.collection)
building=next(c for c in bpy.data.collections['02_LSE_BUILDINGS'].children if c.name.startswith('MAR_'))
visible.intersection_update(building.all_objects)
trees=[]
for obj in visible:
    if obj.type!='MESH' or not obj.data.polygons:continue
    if any(token in obj.name for token in ['upper_screen_shafts','upper_screen_hammerheads','north115_fin','north_screen_horizontal_edges']):continue
    trees.append((obj.name,BVHTree.FromPolygons([obj.matrix_world@v.co for v in obj.data.vertices],[tuple(f.vertices)for f in obj.data.polygons])))
front_checks=0;depth_checks=[]
for z in [25.2,28.1,31.1]:
    for step in range(49):
        x=-4.5+step*.25
        hits=[]
        for name,tree in trees:
            p,n,index,d=tree.ray_cast(world(x,19,z),-N,.6)
            if p is not None:hits.append(name)
        assert not hits,(x,z,hits)
        front_checks+=1
    for x in [-3,0,3,6]:
        hits=[]
        for name,tree in trees:
            p,n,index,d=tree.ray_cast(world(x,23,z),-N,25)
            if p is not None:hits.append((d,name))
        hit=min(hits)
        assert hit[1]in NAMES[:3],(x,z,hit)
        depth_checks.append(dict(x=x,z=z,firstHit=hit))
# Compare restored floor coverage against the original floor footprint, excluding
# the relocated court. Quarter-metre samples are offset from all cut boundaries.
floor_checks=0;restored_samples=0
outline=[(-4.95,21.16),(-4.95,8.8),(1.75,3.5),(8.25,16),(8.25,21.16)]
def in_new_court(x,y):
    return all((a[1]-b[1])*(x-a[0])+(b[0]-a[0])*(y-a[1])+.06*math.hypot(a[1]-b[1],b[0]-a[0])>=0
               for a,b in zip(outline,outline[1:]+outline[:1]))
def tree_for(name):
    obj=bpy.data.objects[name]
    return BVHTree.FromPolygons([obj.matrix_world@v.co for v in obj.data.vertices],[tuple(f.vertices)for f in obj.data.polygons])
trim_targets={r['source']:r['target']for r in proof['trimRecords']}
for record in proof['floorInfillRecords']:
    original=tree_for(record['source']);infill=tree_for(record['target'])
    retained=tree_for(trim_targets[record['ownerSource']])
    height=float(record['source'].rsplit('_',1)[1])
    for ix in range(96):
        x=-15.3+ix*.25+.037
        for iy in range(57):
            y=3.7+iy*.25+.021
            origin=world(x,y,height+1)
            def hit(tree):return tree.ray_cast(origin,Vector((0,0,-1)),2)[0]is not None
            source_hit=hit(original);added_hit=hit(infill);retained_hit=hit(retained)
            expected=source_hit and not in_new_court(x,y)
            assert (added_hit or retained_hit)==expected,(record['source'],x,y,expected,added_hit,retained_hit)
            assert not(added_hit and retained_hit),(record['source'],'overlapping floor',x,y)
            floor_checks+=1;restored_samples+=int(added_hit)
assert restored_samples>0
result=dict(candidateReopened=True,originalMeshesAndUVsPreserved=True,finiteCandidateVerticesAndUVs=True,
            clearFrontSamples=front_checks,depthSightlines=depth_checks,sourceModelSha256=proof['sourceModelSha256'],
            candidateObjects=len(proof['addedObjects']),floorCoverageSamples=floor_checks,restoredFloorSamples=restored_samples,releaseReady=False,
            remaining=['Middle-storey opening remains in the earlier position.','Roof-terrace continuity and lower-storey floor alignment need verification.','Upper-wing full plan and facade photo alignment remain approximate.'])
(OUT/'verification.json').write_text(json.dumps(result,indent=2)+'\n')
assert hashlib.sha256(model.read_bytes()).hexdigest()==proof['sourceModelSha256']
print('MAR188_CANDIDATE_VERIFIED',front_checks,len(depth_checks),len(proof['addedObjects']),floor_checks,restored_samples)
