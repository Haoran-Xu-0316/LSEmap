"""Independently reopen OLD silhouette refinement and verify saved geometry."""
from pathlib import Path
import bpy, json, hashlib, array, math
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'result/blender/stage106'
audit=json.loads((OUT/'old-figure-silhouettes-audit.json').read_text())
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v106.blend'))
def digest(obj):
    h=hashlib.sha256(str([list(row) for row in obj.matrix_world]).encode())
    if obj.type=='MESH':
        h.update(array.array('f',[c for v in obj.data.vertices for c in v.co]).tobytes())
        h.update(array.array('i',[l.vertex_index for l in obj.data.loops]).tobytes())
    h.update(str([m.name if m else None for m in getattr(obj.data,'materials',[])]).encode())
    return h.hexdigest()
assert all(digest(bpy.data.objects[n])==h for n,h in audit['originalFingerprints'].items())
old=bpy.data.objects[audit['source']];new=bpy.data.objects[audit['copy']]
assert old.hide_render and not new.hide_render
extra={o.name for o in bpy.data.objects}-set(audit['originalFingerprints'])
assert extra=={new.name}
assert len(new.data.polygons)==audit['finalFaces']
assert not new.data.materials[0].use_backface_culling
assert all(math.isfinite(c) for v in new.data.vertices for c in v.co)
# Each strand is an open quad, 3.8mm wide and nondegenerate.
assert all(len(p.vertices)==4 and p.area>1e-10 for p in new.data.polygons)
for polygon in list(new.data.polygons)[::101]:
    points=[new.data.vertices[i].co for i in polygon.vertices]
    assert abs((points[3]-points[0]).length-.0038)<.00002
    assert abs((points[2]-points[1]).length-.0038)<.00002
assert len(new.data.polygons)<450000
(OUT/'saved-verification.json').write_text(json.dumps({'version':106,'originalsRetained':True,'newObjects':1,'strandQuads':len(new.data.polygons),'strandWidth':.0038,'doubleSided':True},indent=2)+'\n')
print('SAVED_OLD_FIGURES_VERIFIED',len(new.data.polygons),flush=True)
