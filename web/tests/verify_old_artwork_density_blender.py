"""Independently reopen OLD lattice refinement and measure retained open holes."""
from pathlib import Path
import array
import hashlib
import json
import math
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'result/blender/stage111-old'
audit = json.loads((OUT / 'old-artwork-density-audit.json').read_text())
bpy.ops.wm.open_mainfile(filepath=str(ROOT / 'result/blender/LSE_campus_detailed_v111.blend'))
for scene in bpy.data.scenes:
    for layer in scene.view_layers:
        layer.update()
def fingerprint(obj):
    digest = hashlib.sha256(str([list(row) for row in obj.matrix_world]).encode())
    if obj.type == 'MESH':
        digest.update(array.array('f', [c for v in obj.data.vertices for c in v.co]).tobytes())
        digest.update(array.array('i', [l.vertex_index for l in obj.data.loops]).tobytes())
    digest.update(str([m.name if m else None for m in getattr(obj.data, 'materials', [])]).encode())
    return digest.hexdigest()
assert all(fingerprint(bpy.data.objects[n]) == h for n, h in audit['originalFingerprints'].items())
frame = json.loads((ROOT / 'result/blender/stage52/old-houghton-audit.json').read_text())
origin, right, outward = [Vector(frame[k]) for k in ['origin', 'right', 'outward']]
def tree(obj):
    vertices = [obj.matrix_world @ v.co for v in obj.data.vertices]
    return BVHTree.FromPolygons(vertices, [list(p.vertices) for p in obj.data.polygons], all_triangles=False)
measured = []
for record in audit['copies']:
    original, copy = [bpy.data.objects[record[k]] for k in ['source', 'copy']]
    assert original.hide_render and not copy.hide_render
    assert len(copy.data.vertices) == record['vertices']
    assert len(copy.data.polygons) == record['faces']
    assert [l.vertex_index for l in original.data.loops] == [l.vertex_index for l in copy.data.loops]
    distances = [(copy.matrix_world @ v.co - original.matrix_world @ a.co).length for a,v in zip(original.data.vertices,copy.data.vertices)]
    assert all(math.isfinite(c) for v in copy.data.vertices for c in v.co)
    assert max(distances) <= record['offset'] + .00002
    assert sum(distances) / len(distances) >= record['offset'] * .98
    old_tree, new_tree = tree(original), tree(copy)
    hits = [0,0]
    samples = 0
    for ix in range(240):
        x = -2.7 + (ix+.5)*5.4/240
        for iz in range(144):
            z = 4.25 + (iz+.5)*3.4/144
            start = origin + right*x + outward*2 + Vector((0,0,z))
            samples += 1
            for index,bvh in enumerate([old_tree,new_tree]):
                hits[index] += bvh.ray_cast(start,-outward,5)[0] is not None
    assert hits[1] > hits[0]*1.10, hits
    # Large empty regions and small thread holes must survive the adjustment.
    assert hits[1] < samples*.75, hits
    measured.append({**record, 'samples':samples,'beforeHits':hits[0],'afterHits':hits[1],
                     'maxOffset':max(distances),'topologyUnchanged':True})
audit['savedMeasurements'] = {'allOriginalObjectsUnchanged':True,'openLatticeRetained':True,'families':measured}
(OUT/'old-artwork-density-audit.json').write_text(json.dumps(audit,indent=2)+'\n')
print('OLD_ARTWORK_DENSITY_VERIFIED', measured, flush=True)
