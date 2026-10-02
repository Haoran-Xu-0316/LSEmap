"""Reopen the saved survey cap and check geometry, void and archival retention."""
from pathlib import Path
import array, hashlib, json, math
import bpy
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'result/blender/stage108'
audit=json.loads((OUT/'library-dome-dimensions-audit.json').read_text())
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v108.blend'))
def fingerprint(obj):
    digest=hashlib.sha256(str([list(row)for row in obj.matrix_world]).encode())
    if obj.type=='MESH':
        digest.update(array.array('f',[c for v in obj.data.vertices for c in v.co]).tobytes())
        digest.update(array.array('i',[loop.vertex_index for loop in obj.data.loops]).tobytes())
    digest.update(str([m.name if m else None for m in getattr(obj.data,'materials',[])]).encode())
    return digest.hexdigest()
assert all(fingerprint(bpy.data.objects[n])==h for n,h in audit['originalFingerprints'].items())
assert {o.name for o in bpy.data.objects}-set(audit['originalFingerprints'])==set(audit['copies'].values())
for source,copy in audit['copies'].items():
    assert bpy.data.objects[source].hide_render
    obj=bpy.data.objects[copy]
    assert not obj.hide_render and obj['sharedInteriorRoof']
    assert all(math.isfinite(c)for v in obj.data.vertices for c in v.co)
shell=bpy.data.objects['LRB_V108_survey_dome_shell']
p=[shell.matrix_world@v.co for v in shell.data.vertices]
for axis in [0,1]:
    assert abs(min(v[axis]for v in p)-(audit['centre'][axis]-6.89))<.001
    assert abs(max(v[axis]for v in p)-(audit['centre'][axis]+6.89))<.001
assert abs(min(v.z for v in p)-27.71)<.001
assert abs(max(v.z for v in p)-34.6)<.001
# Probe the roof centre: triangles must leave the reduced circular void open.
deck=bpy.data.objects['LRB_V108_survey_deck_opening']
assert min(poly.area for poly in deck.data.polygons)>1e-6
from mathutils import Vector
from mathutils.bvhtree import BVHTree
bvh=BVHTree.FromPolygons([deck.matrix_world@v.co for v in deck.data.vertices],[tuple(p.vertices)for p in deck.data.polygons])
cx,cy=audit['centre']
for r in [0,3,6.7]:
    for i in range(24):
        point=Vector((cx+r*math.cos(i*math.pi/12),cy+r*math.sin(i*math.pi/12),40))
        assert bvh.ray_cast(point,Vector((0,0,-1)),20)[0] is None
hits=0
for i in range(24):
    point=Vector((cx+8*math.cos(i*math.pi/12),cy+8*math.sin(i*math.pi/12),40))
    hits+=bvh.ray_cast(point,Vector((0,0,-1)),20)[0]is not None
assert hits==24,hits
report={'version':108,'originalsRetained':True,'newObjects':6,'radius':6.89,'height':6.89,'collar':1.91,'openVoidProbes':72,'annulusRoofProbes':24}
(OUT/'saved-verification.json').write_text(json.dumps(report,indent=2)+'\n')
print('SAVED_LIBRARY_SURVEY_DOME_VERIFIED',report,flush=True)
