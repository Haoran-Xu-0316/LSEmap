"""Verify independent SAL brick finishes and preserved source geometry."""
from pathlib import Path
import hashlib,json,sys
import bpy
root=Path(__file__).resolve().parents[2];sys.path.insert(0,str(root/'web/tools'))
from refine_architectural_glass import shape_signature
from refine_rooms import geometry_signatures
from refine_sal_palette183 import apply_sal_palette183,COLOUR
stage=root/'result/blender/stage183';model=root/'result/blender/LSE_campus_detailed_v183.blend'
proof=json.loads((stage/'building-refinement.json').read_text())
assert hashlib.sha256(model.read_bytes()).hexdigest()==proof['sourceModelSha256']
bpy.ops.wm.open_mainfile(filepath=str(model))
for s in bpy.data.scenes:
 for l in s.view_layers:l.update()
assert geometry_signatures()==proof['geometrySignatures']
for name,digest in proof['originalShapesAndUVs'].items():assert shape_signature(bpy.data.objects[name])==digest
for record in proof['changes'][0]['records']:
 source=bpy.data.objects[record['source']];target=bpy.data.objects[record['target']]
 assert source.hide_render and not target.hide_render
 assert shape_signature(source)==shape_signature(target)
 for binding in record['bindings']:
  old=bpy.data.materials[binding['source']];new=target.data.materials[binding['slot']]
  assert old!=new and new.name==binding['target']
  assert abs(old.diffuse_color[1]-.185)<1e-6
  assert all(abs(a-b)<1e-6 for a,b in zip(new.diffuse_color,COLOUR))
  for source_node in old.node_tree.nodes:
   target_node=new.node_tree.nodes[source_node.name]
   if source_node.type=='TEX_BRICK':
    for key in ['Scale','Mortar Size','Mortar Smooth','Bias','Brick Width','Row Height']:
     assert source_node.inputs[key].default_value==target_node.inputs[key].default_value
    assert tuple(source_node.inputs['Mortar'].default_value)==tuple(target_node.inputs['Mortar'].default_value)
    assert all(abs(a-b)<1e-6 for a,b in zip(target_node.inputs['Color1'].default_value,COLOUR))
# Unphotographed rear and side proxy batches keep their old independent bindings.
for name in ['SAL_Secondary_elevation_brick','SAL_Tower_upper_back_volume']:
 assert not bpy.data.objects[name].hide_render
 assert abs(bpy.data.objects[name].data.materials[0].diffuse_color[1]-.185)<1e-6
# Keep the previous bench contact check in the current native rather than reopen an obsolete file.
base=bpy.data.objects['OLD182_foyer_stone_bench_plinth'];bench=bpy.data.objects['OLD174_foyer_waiting_bench'];floor=bpy.data.objects['OLD174_foyer_lower_limestone_floor']
assert abs(min(v.co.z for v in base.data.vertices)-max(v.co.z for v in floor.data.vertices))<1e-6
assert abs(max(v.co.z for v in base.data.vertices)-min(v.co.z for v in bench.data.vertices))<1e-6
assert apply_sal_palette183()['alreadyApplied'];assert geometry_signatures()==proof['geometrySignatures']
(stage/'reopened-verification.json').write_text(json.dumps({'savedSceneReopened':True,'idempotent':True,'allOriginalShapesAndUVsPreserved':True,'independentSALBrickMaterials':True,'brickScaleAndMortarRetained':True,'benchSeatAndFloorTouching':True,'sourceModelSha256':proof['sourceModelSha256']},indent=2)+'\n')
print('SAL183_REOPENED_VERIFIED')
