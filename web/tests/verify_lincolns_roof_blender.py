"""Reopen saved 51L roof and independently verify windows and clear sightlines."""
from pathlib import Path
import array,hashlib,json
import bpy,bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'result/blender/stage93'
audit=json.loads((OUT/'lincolns-roof-audit.json').read_text())
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v93.blend'))
def fingerprint(o):
    h=hashlib.sha256(str([list(r)for r in o.matrix_world]).encode())
    if o.type=='MESH':
        h.update(array.array('f',[c for v in o.data.vertices for c in v.co]).tobytes())
        h.update(array.array('i',[l.vertex_index for l in o.data.loops]).tobytes())
    h.update(str([m.name if m else None for m in getattr(o.data,'materials',[])]).encode())
    return h.hexdigest()
assert all(fingerprint(bpy.data.objects[n])==value for n,value in audit['baselineFingerprint'].items())
assert set(bpy.data.objects.keys())-set(audit['baselineFingerprint'])==set(audit['addedObjects'])
for name in audit['addedObjects']:
    bm=bmesh.new();bm.from_mesh(bpy.data.objects[name].data)
    assert all(e.is_manifold for e in bm.edges),name
    assert bm.calc_volume(signed=True)>0,name
    bm.free()
origin,right,normal=[Vector(audit['frame'][k])for k in ['origin','right','normal']]
glass=bpy.data.objects['51L_D5_roof93_glass']
bm=bmesh.new();bm.from_mesh(glass.data)
seen=set();windows=[]
for seed in bm.verts:
    if seed in seen:continue
    group=[];pending=[seed];seen.add(seed)
    while pending:
        v=pending.pop();group.append(v)
        for edge in v.link_edges:
            other=edge.other_vert(v)
            if other not in seen:seen.add(other);pending.append(other)
    pts=[glass.matrix_world@v.co for v in group]
    xs=[(p-origin).dot(right)for p in pts]
    center=sum(pts,Vector())/len(pts)
    windows.append({'center':list(center),'centerX':(min(xs)+max(xs))/2,
                    'width':max(xs)-min(xs),'height':max(p.z for p in pts)-min(p.z for p in pts)})
bm.free()
assert len(windows)==3
for bay,window in enumerate(sorted(windows,key=lambda w:w['centerX'])):
    assert abs(window['centerX']-(bay+.5)*audit['frame']['length']/3)<2e-5
    assert abs(window['width']-.95)<2e-5 and abs(window['height']-.82)<2e-5
# Slots must keep opaque roof panels and dormer cheeks out of the window opening.
slate=bpy.data.objects['51L_D5_roof93_slate']
bm=bmesh.new();bm.from_mesh(slate.data)
for v in bm.verts:v.co=slate.matrix_world@v.co
tree=BVHTree.FromBMesh(bm);bm.free()
for window in windows:
    hit=tree.ray_cast(Vector(window['center'])+normal*.03,normal,5)
    assert hit[0]is None,window
zs=[(slate.matrix_world@v.co).z for v in slate.data.vertices]
assert max(zs)>22.70 and min(zs)>20.85
audit['savedMeasurements']={'originalObjectsUnchanged':True,'closedNewMeshes':True,
                            'dormerWindows':windows,'clearWindowSightlines':True,
                            'roofHeightRange':[min(zs),max(zs)]}
(OUT/'lincolns-roof-audit.json').write_text(json.dumps(audit,indent=2)+'\n')
print('SAVED_LINCOLNS_ROOF_VERIFIED',windows,flush=True)
