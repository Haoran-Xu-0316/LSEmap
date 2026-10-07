"""Reopen the saved campus and check the OLD bench's physical support."""
from pathlib import Path
import hashlib,json,sys
import bpy,bmesh
root=Path(__file__).resolve().parents[2];sys.path.insert(0,str(root/'web/tools'))
from refine_architectural_glass import shape_signature
from refine_rooms import geometry_signatures
from refine_old_bench182 import apply_old_bench182
stage=root/'result/blender/stage182';model=root/'result/blender/LSE_campus_detailed_v182.blend'
proof=json.loads((stage/'building-refinement.json').read_text())
assert hashlib.sha256(model.read_bytes()).hexdigest()==proof['sourceModelSha256']
bpy.ops.wm.open_mainfile(filepath=str(model))
for s in bpy.data.scenes:
 for l in s.view_layers:l.update()
assert geometry_signatures()==proof['geometrySignatures']
for name,digest in proof['originalShapesAndUVs'].items():assert shape_signature(bpy.data.objects[name])==digest
bench=bpy.data.objects['OLD174_foyer_waiting_bench'];floor=bpy.data.objects['OLD174_foyer_lower_limestone_floor'];base=bpy.data.objects['OLD182_foyer_stone_bench_plinth']
assert bpy.data.objects['OLD174_foyer_bench_supports'].hide_render
assert base.name in bpy.data.scenes['00_CAMPUS_COMPLETE'].objects
assert tuple(base.matrix_world)==tuple(bench.matrix_world)
assert abs(min(v.co.z for v in base.data.vertices)-max(v.co.z for v in floor.data.vertices))<1e-6
assert abs(max(v.co.z for v in base.data.vertices)-min(v.co.z for v in bench.data.vertices))<1e-6
bm=bmesh.new();bm.from_mesh(base.data);assert all(len(e.link_faces)==2 for e in bm.edges)
assert bm.calc_volume(signed=True)>0;bm.free()
assert base.data.uv_layers and base.data.materials[0]==floor.data.materials[0]
assert apply_old_bench182()['alreadyApplied'];assert geometry_signatures()==proof['geometrySignatures']
(stage/'reopened-verification.json').write_text(json.dumps({'savedSceneReopened':True,'idempotent':True,'allOriginalShapesAndUVsPreserved':True,'benchSeatAndFloorTouching':True,'closedPositiveVolume':True,'sourceModelSha256':proof['sourceModelSha256']},indent=2)+'\n')
print('OLD182_REOPENED_VERIFIED')
