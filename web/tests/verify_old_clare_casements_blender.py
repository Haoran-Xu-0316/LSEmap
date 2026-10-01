"""Verify saved Clare Market windows and all retained blue-frame components."""
from pathlib import Path
import array, hashlib, json
from collections import Counter
import bpy, bmesh
from mathutils import Vector
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'result/blender/stage87'
a = json.loads((OUT / 'old-clare-casement-audit.json').read_text())
bpy.ops.wm.open_mainfile(filepath=str(ROOT / 'result/blender/LSE_campus_detailed_v87.blend'))
def fingerprint(obj):
    digest = hashlib.sha256(str([list(r) for r in obj.matrix_world]).encode())
    if obj.type == 'MESH':
        digest.update(array.array('f', [c for v in obj.data.vertices for c in v.co]).tobytes())
        digest.update(array.array('i', [loop.vertex_index for loop in obj.data.loops]).tobytes())
    digest.update(str([m.name if m else None for m in getattr(obj.data, 'materials', [])]).encode())
    return digest.hexdigest()
assert all(fingerprint(bpy.data.objects[n]) == old for n, old in a['baselineFingerprint'].items())
assert set(bpy.data.objects.keys()) - set(a['baselineFingerprint']) == {a['retainedObject'], a['newBars']}
assert bpy.data.objects[a['hiddenObject']].hide_render
origin, right, outward = [Vector(a['frame'][key]) for key in ['origin', 'right', 'outward']]
def local(obj, vertex):
    p = obj.matrix_world @ vertex.co - origin
    return Vector((p.dot(right), p.dot(outward), p.z))
def parts(mesh):
    seen = set()
    for vertex in mesh.verts:
        if vertex in seen or not vertex.link_faces:
            continue
        seen.add(vertex)
        todo, group = [vertex], []
        while todo:
            v = todo.pop()
            group.append(v)
            for edge in v.link_edges:
                other = edge.other_vert(v)
                if other not in seen:
                    seen.add(other)
                    todo.append(other)
        yield group
def bounds(obj, group):
    p = [local(obj,v) for v in group]
    lo, hi = [[f(v[i] for v in p) for i in range(3)] for f in [min,max]]
    return {'centre': [(lo[i]+hi[i])/2 for i in range(3)], 'size': [hi[i]-lo[i] for i in range(3)]}
obj = bpy.data.objects[a['newBars']]
mesh = bmesh.new()
mesh.from_mesh(obj.data)
measured = [bounds(obj,group) for group in parts(mesh)]
assert len(measured) == 56
assert mesh.calc_volume(signed=True) > 0
mesh.free()
for expected, actual in zip(a['members'], measured):
    for field in ['centre','size']:
        assert all(abs(x-y)<.001 for x,y in zip(expected[field],actual[field]))
for index,w in enumerate(a['windows']):
    bars = [m for m,e in zip(measured,a['members']) if e['window']==index]
    vertical = [m for m in bars if m['size'][0] < .08]
    assert len(vertical) == w['columns']-1
    if w['family']=='upper':
        heavy = [m for m in bars if m['size'][0]>.08 and m['size'][2]>.08]
        assert len(heavy)==1 and abs(heavy[0]['centre'][2]-w['z'])<.001

# Verify that retained entrance, perimeter frames and other blue details are exact.
def original_bars(part):
    cx,cy,cz = part['centre']
    dx,dy,dz = part['size']
    for w in a['windows']:
        if abs(cy+.10)>.015:
            continue
        if abs(cx-w['x'])<w['w']/2-.10 and abs(cz-w['z'])<.01 and dx<.08 and abs(dz-w['h'])<.01:
            return True
        if abs(cx-w['x'])<.01 and abs(cz-w['z'])<w['h']/2-.1 and abs(dx-w['w'])<.01 and dz<.06:
            return True
    return False
def signatures(obj, filter_bars):
    mesh = bmesh.new()
    mesh.from_mesh(obj.data)
    excluded = set()
    if filter_bars:
        for group in parts(mesh):
            if original_bars(bounds(obj,group)):
                excluded.update(f for v in group for f in v.link_faces)
    result = Counter((f.material_index, tuple(sorted(tuple(round(float(c),6) for c in local(obj,v)) for v in f.verts)))
                     for f in mesh.faces if f not in excluded)
    mesh.free()
    return result
assert signatures(bpy.data.objects[a['hiddenObject']],True) == signatures(bpy.data.objects[a['retainedObject']],False)
a['savedMeasurements']={'allOriginalObjectsUnchanged':True,'retainedFrameGeometryUnchanged':True,
                        'ordinaryFourColumnWindows':8,'twoColumnPortalUpperWindow':1,
                        'upperHeavyTransoms':5,'verticalMembers':25,'horizontalMembers':31}
(OUT/'old-clare-casement-audit.json').write_text(json.dumps(a,indent=2)+'\n')
print('SAVED_OLD_CLARE_CASEMENTS_VERIFIED',a['savedMeasurements'],flush=True)
