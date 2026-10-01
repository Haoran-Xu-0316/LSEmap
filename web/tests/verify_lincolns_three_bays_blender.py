"""Independently reopen the corrected 51L frontage and inspect geometry."""
from pathlib import Path
from collections import Counter
import array, hashlib, json
import bpy, bmesh
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'result/blender/stage92'
audit=json.loads((OUT/'lincolns-three-bay-audit.json').read_text())
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v92.blend'))
def fingerprint(o):
    h=hashlib.sha256(str([list(r)for r in o.matrix_world]).encode())
    if o.type=='MESH':
        h.update(array.array('f',[c for v in o.data.vertices for c in v.co]).tobytes())
        h.update(array.array('i',[loop.vertex_index for loop in o.data.loops]).tobytes())
    h.update(str([m.name if m else None for m in getattr(o.data,'materials',[])]).encode())
    return h.hexdigest()
assert all(fingerprint(bpy.data.objects[n])==value for n,value in audit['baselineFingerprint'].items())
assert set(bpy.data.objects.keys())-set(audit['baselineFingerprint'])==set(audit['addedObjects'])
retained=[]
for record in audit['copies']:
    source,copy=[bpy.data.objects[record[k]]for k in ['source','copy']]
    removed=set(record['removedVertices'])
    expected=Counter(tuple(v.co)for v in source.data.vertices if v.index not in removed)
    assert Counter(tuple(v.co)for v in copy.data.vertices)==expected
    assert source.hide_render and not copy.hide_render
    retained.append({'name':copy.name,'retainedVertices':len(copy.data.vertices)})
# All newly authored construction components must be closed and positive-volume.
for name in audit['addedObjects']:
    if '_retained_'in name:continue
    obj=bpy.data.objects[name];bm=bmesh.new();bm.from_mesh(obj.data)
    assert all(e.is_manifold for e in bm.edges),name
    assert bm.calc_volume(signed=True)>0,name
    bm.free()
origin,right,normal=[Vector(audit['frame'][k])for k in ['origin','right','normal']]
glass=bpy.data.objects['51L_D5_threebay92_glass']
bm=bmesh.new();bm.from_mesh(glass.data)
seen=set();openings=[]
for seed in bm.verts:
    if seed in seen:continue
    group=[];pending=[seed];seen.add(seed)
    while pending:
        v=pending.pop();group.append(v)
        for e in v.link_edges:
            other=e.other_vert(v)
            if other not in seen:seen.add(other);pending.append(other)
    pts=[glass.matrix_world@v.co for v in group]
    lo,hi=min(p.z for p in pts),max(p.z for p in pts)
    x=[(p-origin).dot(right)for p in pts]
    floor=0 if lo<1 else round((lo-.82)/(20.8/6))
    openings.append({'floor':floor,'centerX':(min(x)+max(x))/2,'width':max(x)-min(x),'lower':lo,'upper':hi})
bm.free()
assert Counter(o['floor']for o in openings)==Counter({i:3 for i in range(6)})
length=audit['frame']['length']
for floor in range(6):
    row=sorted((o for o in openings if o['floor']==floor),key=lambda o:o['centerX'])
    for bay,o in enumerate(row):
        assert abs(o['centerX']-(bay+.5)*length/3)<2e-5
        assert abs(o['width']-length/3*.58)<2e-5
# The outdoor view's screen-right axis is opposite this footprint edge.
wood=bpy.data.objects['51L_D5_threebay92_wood']
assert all(-.1<(wood.matrix_world@v.co-origin).dot(right)<length/3 for v in wood.data.vertices)
frame=bpy.data.objects['51L_D5_threebay92_frame']
bm=bmesh.new();bm.from_mesh(frame.data)
seen=set();fine_verticals=0;horizontal_rails=0
for seed in bm.verts:
    if seed in seen:continue
    group=[];pending=[seed];seen.add(seed)
    while pending:
        v=pending.pop();group.append(v)
        for e in v.link_edges:
            other=e.other_vert(v)
            if other not in seen:seen.add(other);pending.append(other)
    pts=[frame.matrix_world@v.co for v in group]
    xs=[(p-origin).dot(right)for p in pts]
    w=max(xs)-min(xs);h=max(p.z for p in pts)-min(p.z for p in pts)
    fine_verticals+=int(w<.04 and h>1)
    horizontal_rails+=int(w>1 and h<.04)
bm.free()
assert fine_verticals==30 and horizontal_rails==72,(fine_verticals,horizontal_rails)
audit['savedMeasurements']={'originalObjectsUnchanged':True,'retainedOtherComponents':retained,
                            'closedNewComponents':True,'openings':openings,'rightEntryVerified':True,'fineVerticalBars':fine_verticals,'horizontalRails':horizontal_rails}
(OUT/'lincolns-three-bay-audit.json').write_text(json.dumps(audit,indent=2)+'\n')
print('SAVED_LINCOLNS_THREE_BAY_VERIFIED',len(retained),len(openings),flush=True)
