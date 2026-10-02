"""Independently reopen OLD's roof and check coverage, openings and preservation."""
from pathlib import Path
import array,hashlib,json,math
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'result/blender/stage113'
audit=json.loads((OUT/'old-roof-survey-audit.json').read_text());plan=audit['plan']
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v113.blend'))
for s in bpy.data.scenes:
    for l in s.view_layers:l.update()
bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE']
def fingerprint(o):
    h=hashlib.sha256(str([list(r)for r in o.matrix_world]).encode())
    if o.type=='MESH':
        v=array.array('f',[0])*(3*len(o.data.vertices));i=array.array('i',[0])*len(o.data.loops)
        o.data.vertices.foreach_get('co',v);o.data.loops.foreach_get('vertex_index',i)
        h.update(v.tobytes());h.update(i.tobytes())
    h.update(str([m.name if m else None for m in getattr(o.data,'materials',[])]).encode());return h.hexdigest()
assert all(fingerprint(bpy.data.objects[n])==h for n,h in audit['originalFingerprints'].items())
for n,state in audit['originalVisibility'].items():assert bpy.data.objects[n].hide_render==(True if n in audit['archived']else state),n
assert len(audit['archived'])==2
origin,right,normal=[Vector(plan[k])for k in ['origin','right','outward']]
def point(x,y,z):return origin+right*x+normal*y+Vector((0,0,z))
geometry=[]
for o in bpy.data.collections['OLD_EXTERIOR'].all_objects:
    if o.hide_render or o.type!='MESH':continue
    geometry.append((o.name,BVHTree.FromPolygons([o.matrix_world@v.co for v in o.data.vertices],[list(p.vertices)for p in o.data.polygons])))
for name in audit['addedObjects']:
    o=bpy.data.objects[name];assert not o.hide_render and not o.modifiers
    assert all(p.area>1e-9 for p in o.data.polygons),name
    assert all(math.isfinite(c)for v in o.data.vertices for c in v.co)
roof=bpy.data.objects['OLD_D5_roof113_decks_roof']
assert all(p.normal.z>.999 for p in roof.data.polygons)
expected_area=sum(r['area']for r in plan['roofRegions'])
assert abs(sum(p.area for p in roof.data.polygons)-expected_area)<.005
# Actual downward rays at each roof triangle centroid establish the partition.
roof_bvh=next(bvh for n,bvh in geometry if n==roof.name);probes=0
for r in plan['roofRegions']:
    for t in r['triangles']:
        x=sum(p[0]for p in t)/3;y=sum(p[1]for p in t)/3
        location,n,index,d=roof_bvh.ray_cast(point(x,y,36),Vector((0,0,-1)),30)
        assert location is not None and abs(location.z-r['height'])<1e-4,(r['name'],location)
        probes+=1
# Upper riser windows must see glass first, not the archived roof or opaque wall.
clear=0
for sample in audit['glazingProbes']:
    n=Vector(sample['normal']);p=Vector(sample['point'])+n*.6;hits=[]
    for name,bvh in geometry:
        loc,normal_hit,index,d=bvh.ray_cast(p,-n,.9)
        if loc is not None:hits.append((d,name))
    assert hits,sample
    assert 'roof113_risers_glass' in min(hits)[1],(sample,min(hits))
    clear+=1
# The gabled glass is exposed and its base does not sit on an opaque slab.
shape=plan['skylight']['outline'];a=min(p[0]for p in shape);b=max(p[0]for p in shape)
c=min(p[1]for p in shape);d=max(p[1]for p in shape)
x=a+(b-a)*.29;y=c+(d-c)*.37;hits=[]
for name,bvh in geometry:
    loc,n,index,dist=bvh.ray_cast(point(x,y,36),Vector((0,0,-1)),12)
    if loc is not None:hits.append((dist,name,loc.z))
assert 'roof113_skylight_glass' in min(hits)[1],hits
assert not [h for h in hits if 'decks_roof' in h[1]],hits
assert abs(max(v.co.z for v in bpy.data.objects['OLD_D5_roof113_skylight_glass'].data.vertices)-31.44)<1e-4
fans=bpy.data.objects['OLD_D5_roof113_fans_grille']
assert len(fans.data.polygons)==24
assert len(plan['plant']['centres'])==3 and len(plan['plant']['screens'])==2
assert min(r['height']for r in plan['roofRegions'])==13.5
assert max(r['height']for r in plan['roofRegions'])==28.44
result={'version':113,'originalGeometryRetained':True,'entryAndOtherBuildingsRetained':True,
        'roofArea':expected_area,'roofRegions':len(plan['roofRegions']),'roofProbes':probes,
        'clearRiserWindows':clear,'skylightExposed':True,'skylightOpaqueBackingRemoved':True,
        'heatPumpGroups':3,'acousticEnclosures':2,'schematicFans':24,
        'sourceModelSha256':hashlib.sha256((ROOT/'result/blender/LSE_campus_detailed_v113.blend').read_bytes()).hexdigest()}
(OUT/'saved-verification.json').write_text(json.dumps(result,indent=2)+'\n')
print('SAVED_OLD_ROOF_SURVEY_VERIFIED',probes,clear,flush=True)
