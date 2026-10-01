"""Reopen saved corner; inspect shape, glazing, planar doors and retained parts."""
from pathlib import Path
from collections import Counter
import array, hashlib, json, math
import bpy,bmesh
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'result/blender/stage96'
def fingerprint(obj):
    digest=hashlib.sha256(str([list(row) for row in obj.matrix_world]).encode())
    if obj.type=='MESH':
        digest.update(array.array('f',[c for v in obj.data.vertices for c in v.co]).tobytes())
        digest.update(array.array('i',[l.vertex_index for l in obj.data.loops]).tobytes())
    digest.update(str([m.name if m else None for m in getattr(obj.data,'materials',[])]).encode())
    return digest.hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v96.blend'))
a=json.loads((OUT/'lincolns-rounded-corner-audit.json').read_text())
assert all(fingerprint(bpy.data.objects[n])==v for n,v in a['baselineFingerprint'].items())
expected={r['copy'] for r in a['copies']}|{a['roofCap']}
assert set(bpy.data.objects.keys())-set(a['baselineFingerprint'])==expected
for row in a['copies']:
    old=bpy.data.objects[row['source']];new=bpy.data.objects[row['copy']]
    assert old.hide_render and not new.hide_render
    if row.get('planarLabel'):continue
    current=Counter(tuple(v.co) for v in new.data.vertices)
    required=Counter(tuple(p) for p in row['retainedVertices'])
    assert all(current[p]>=n for p,n in required.items()),row['source']
    assert [m.name for m in old.data.materials]==[m.name for m in new.data.materials]
    assert all(math.isfinite(c) for v in new.data.vertices for c in v.co)
    old_mesh=bmesh.new();old_mesh.from_mesh(old.data)
    new_mesh=bmesh.new();new_mesh.from_mesh(new.data)
    assert sum(e.is_boundary for e in old_mesh.edges)==sum(e.is_boundary for e in new_mesh.edges),row['source']
    old_mesh.free();new_mesh.free()
# Door leaves undergo rigid translation, with every vertex difference identical.
row=next(r for r in a['copies'] if 'oak_door_leaf' in r['source'])
old,new=[bpy.data.objects[row[k]] for k in ['source','copy']]
deltas=[new.matrix_world@v.co-old.matrix_world@u.co for u,v in zip(old.data.vertices,new.data.vertices)]
assert len(old.data.vertices)==len(new.data.vertices)
assert max((d-deltas[0]).length for d in deltas)<1e-5
normal=Vector(a['frame']['normal']);origin=Vector(a['frame']['start']);right=Vector(a['frame']['right'])
assert abs(deltas[0].dot(normal)-a['midpointBow'])<1e-5
# Independently measure a saved horizontal rail across the curved corner.
row=next(r for r in a['copies'] if 'retained_D5_sash_rails_frame' in r['source'])
obj=bpy.data.objects[row['copy']]
mesh=bmesh.new();mesh.from_mesh(obj.data);seen=set();profiles=[]
for seed in mesh.verts:
    if seed in seen:continue
    pending=[seed];seen.add(seed);vertices=[]
    while pending:
        v=pending.pop();vertices.append(obj.matrix_world@v.co)
        for edge in v.link_edges:
            q=edge.other_vert(v)
            if q not in seen:seen.add(q);pending.append(q)
    points=[((p-origin).dot(right),(p-origin).dot(normal),p.z) for p in vertices]
    if max(p[2] for p in points)-min(p[2] for p in points)>.2:continue
    width=max(p[0] for p in points)-min(p[0] for p in points)
    if 1.0<width<2.2 and min(p[1] for p in points)>.15:
        # A straight rail cannot have this mid-span sagitta and numerous stations.
        levels=sorted(set(round(p[0],4) for p in points))
        bow=max(p[1] for p in points)-min(p[1] for p in points)
        assert len(levels)>12 and bow>.09,(len(levels),bow)
        profiles.append({'width':width,'stations':len(levels),'depthRange':bow})
mesh.free();assert len(profiles)>=10,len(profiles)
cap=bpy.data.objects[a['roofCap']];mesh=bmesh.new();mesh.from_mesh(cap.data)
assert all(e.is_manifold for e in mesh.edges)
assert mesh.calc_volume(signed=True)>0;mesh.free()
a['savedMeasurements']={'originalGeometryAndBindingsUnchanged':True,'retainedNeighborVerticesUnchanged':True,
                       'cornerCopies':len(a['copies']),'planarDoorTranslation':list(deltas[0]),
                       'curvedRailProfiles':profiles,'roofCrescentClosed':True}
(OUT/'lincolns-rounded-corner-audit.json').write_text(json.dumps(a,indent=2)+'\n')
print('SAVED_LINCOLNS_ROUNDED_CORNER_VERIFIED',len(profiles),a['midpointBow'],flush=True)
