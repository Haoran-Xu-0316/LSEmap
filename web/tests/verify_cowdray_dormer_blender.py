"""Inspect reopened attic rail geometry and untouched neighboring sash vertices."""
from pathlib import Path
from collections import Counter
import array, hashlib, json
import bpy, bmesh
from mathutils import Vector
ROOT = Path(__file__).resolve().parents[2]; OUT = ROOT / 'result/blender/stage98'
audit = json.loads((OUT / 'cowdray-dormer-audit.json').read_text())
bpy.ops.wm.open_mainfile(filepath=str(ROOT / 'result/blender/LSE_campus_detailed_v98.blend'))
bpy.context.window.scene = bpy.data.scenes['00_CAMPUS_COMPLETE']
def fingerprint(obj):
    h = hashlib.sha256(str([list(row) for row in obj.matrix_world]).encode())
    if obj.type == 'MESH':
        h.update(array.array('f', [c for v in obj.data.vertices for c in v.co]).tobytes())
        h.update(array.array('i', [l.vertex_index for l in obj.data.loops]).tobytes())
    h.update(str([m.name if m else None for m in getattr(obj.data, 'materials', [])]).encode())
    return h.hexdigest()
for name, digest in audit['originalFingerprints'].items():
    assert fingerprint(bpy.data.objects[name]) == digest, name
assert set(bpy.data.objects) - {bpy.data.objects[n] for n in audit['originalFingerprints']} == {bpy.data.objects[n] for n in audit['addedObjects']}
retained = bpy.data.objects['COW_V98_retained_sash_bars']
key = lambda p: tuple(round(c, 5) for c in p)
assert Counter(key(retained.matrix_world @ v.co) for v in retained.data.vertices) == Counter(key(p) for p in audit['retainedVertices'])
source = bpy.data.objects[audit['replacedObject']]
assert source.hide_render and not retained.hide_render
assert [m.name for m in retained.data.materials] == [m.name for m in source.data.materials]
rails = bpy.data.objects['COW_V98_dormer_six_row_rails']
bm = bmesh.new(); bm.from_mesh(rails.data)
assert all(e.is_manifold for e in bm.edges) and bm.calc_volume() > 0
seen = set(); centres = []
for seed in bm.verts:
    if seed in seen: continue
    component = []; pending = [seed]; seen.add(seed)
    while pending:
        v = pending.pop(); component.append(v)
        for e in v.link_edges:
            o = e.other_vert(v)
            if o not in seen: seen.add(o); pending.append(o)
    assert len(component) == 8
    centres.append(sum((rails.matrix_world @ v.co for v in component), Vector()) / len(component))
assert len(centres) == 44
windows = []
for w in audit['windows']:
    center, right, normal = [Vector(w[k]) for k in ['center', 'right', 'normal']]
    heights = sorted(p.z for p in centres if abs((p-center).dot(right)) < .01 and abs((p-center).dot(normal)-.005) < .01)
    assert len(heights) == 4
    fractions = [(z-w['bottom'])/(w['top']-w['bottom']) for z in heights]
    assert all(abs(a-b) < 1e-5 for a,b in zip(fractions,[1/6,2/6,4/6,5/6]))
    windows.append({'wall':w['wall'],'measuredHeights':heights})
bm.free()
audit['savedMeasurements'] = {'originalObjectsUnchanged':True,'retainedSashVerticesUnchanged':True,
                             'closedNewRails':True,'railCount':len(centres),'dormerWindows':windows}
(OUT / 'cowdray-dormer-audit.json').write_text(json.dumps(audit,indent=2)+'\n')
print('SAVED_COWDRAY_DORMERS_VERIFIED',len(windows),len(centres))
