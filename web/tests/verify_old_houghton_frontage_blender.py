"""Reopen OLD's saved facade and inspect placement, preservation and clear panes."""
from pathlib import Path
import array, hashlib, json, math
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'result/blender/stage112'
audit=json.loads((OUT/'old-houghton-frontage-audit.json').read_text())
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v112.blend'))
for scene in bpy.data.scenes:
    for layer in scene.view_layers:layer.update()
bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE']
def fingerprint(o):
    h=hashlib.sha256(str([list(r)for r in o.matrix_world]).encode())
    if o.type=='MESH':
        v=array.array('f',[0])*(3*len(o.data.vertices));i=array.array('i',[0])*len(o.data.loops)
        o.data.vertices.foreach_get('co',v);o.data.loops.foreach_get('vertex_index',i)
        h.update(v.tobytes());h.update(i.tobytes())
    h.update(str([m.name if m else None for m in getattr(o.data,'materials',[])]).encode());return h.hexdigest()
assert all(fingerprint(bpy.data.objects[n])==h for n,h in audit['originalFingerprints'].items())
for n,state in audit['originalVisibility'].items():
    assert bpy.data.objects[n].hide_render==(True if n in audit['archived']else state),n
assert -28<audit['entryCentre']<-24
assert 15<audit['entryWidth']<17
mansard=[o for o in audit['openings']if o['zone']=='mansard']
assert len(mansard)==12
assert len({o['low']for o in mansard})==2
assert audit['pedimentCount']==6
pediments=bpy.data.objects['OLD_D5_houghton112_pediments_stone']
assert len(pediments.data.polygons)==30
for name in audit['addedObjects']:
    o=bpy.data.objects[name]
    assert not o.hide_render and not o.modifiers
    assert all(math.isfinite(c)for v in o.data.vertices for c in v.co)
    assert all(p.area>1e-9 for p in o.data.polygons),name
origin,right,normal=[Vector(audit[k])for k in ['origin','right','outward']]
geometry=[]
for o in bpy.data.collections['OLD_EXTERIOR'].all_objects:
    if o.hide_render or o.type!='MESH':continue
    vertices=[o.matrix_world@v.co for v in o.data.vertices]
    geometry.append((o.name,BVHTree.FromPolygons(vertices,[list(p.vertices)for p in o.data.polygons])))
probes=0
for opening in audit['openings']:
    x=opening['x']-opening['width']/2+opening['width']/opening['columns']*.5
    z=opening['low']+(opening['high']-opening['low'])/opening['rows']*.5
    p=origin+right*x+normal*(opening['depth']+.7)+Vector((0,0,z))
    hits=[]
    for name,bvh in geometry:
        loc,n,index,d=bvh.ray_cast(p,-normal,1.2)
        if loc is not None:hits.append((d,name))
    assert hits,opening
    first=min(hits)
    assert 'houghton112_'in first[1] and 'glass'in first[1],(opening,first)
    assert not [(d,n)for d,n in hits if 'glass'not in n and first[0]+.04<d<first[0]+.45],(opening,hits)
    probes+=1
# Walk the entrance with downward ray probes: every riser must be exposed,
# rather than hidden inside an oversized landing slab.
steps=[]
for depth in [2.90,2.60,2.30,2.00,1.70,1.40,.80,-.65]:
    p=origin+right*audit['entryCentre']+normal*depth+Vector((0,0,3))
    hits=[]
    for name,bvh in geometry:
        loc,n,index,d=bvh.ray_cast(p,Vector((0,0,-1)),3.1)
        if loc is not None:hits.append((d,name,loc.z))
    hit=min(hits)
    assert 'houghton112_steps_stone' in hit[1],hit
    steps.append(hit[2])
assert all(b-a>.18 for a,b in zip(steps[:5],steps[1:6])),steps
assert abs(steps[-1]-steps[-2])<1e-4 and abs(steps[-2]-steps[-3])<1e-4,steps
base=bpy.data.objects['OLD_D5_houghton112_entry-base_stone']
assert abs(min(v.co.z for v in base.data.vertices))<1e-5
assert abs(max(v.co.z for v in base.data.vertices)-audit['baseOffset'])<1e-5
# Entry sculpture was relocated with exactly the same mesh topology and finish.
for family in ['figures','products']:
    source=bpy.data.objects['OLD_V111_lattice_'+family]
    copy=bpy.data.objects['OLD_V112_entry_V111_lattice_'+family]
    assert len(source.data.vertices)==len(copy.data.vertices)
    assert len(source.data.polygons)==len(copy.data.polygons)
    assert list(source.data.materials)==list(copy.data.materials)
    p=copy.matrix_world@copy.data.vertices[0].co-origin
    assert -30<p.dot(right)<-22
result={'version':112,'originalGeometryRetained':True,'unrelatedVisibilityRetained':True,
        'entranceAtConnaughtEnd':True,'entryCentre':audit['entryCentre'],
        'mansardWindows':12,'triangularPediments':6,'clearWindowProbes':probes,
        'artworkTopologyRetained':True,'exposedStepHeights':steps,'archivedSources':len(audit['archived'])}
(OUT/'saved-verification.json').write_text(json.dumps(result,indent=2)+'\n')
print('SAVED_OLD_HOUGHTON_FRONTAGE_VERIFIED',probes,flush=True)
