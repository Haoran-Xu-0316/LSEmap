"""Verify independent auditorium membership and actual saved stage clearances."""
from pathlib import Path
import json,hashlib,bpy
ROOT=Path(__file__).resolve().parents[2]
proof=ROOT/'result/blender/stage207'
record=json.loads((proof/'building-refinement.json').read_text())
path=ROOT/'result/blender/LSE_campus_detailed_v207.blend'
assert hashlib.sha256(path.read_bytes()).hexdigest()==record['sourceModelSha256']
bpy.ops.wm.open_mainfile(filepath=str(path))
for scene in bpy.data.scenes:
 for layer in scene.view_layers:layer.update()
collection=bpy.data.collections['PEA_PUBLIC_INTERIOR_study']
new=[o for o in collection.all_objects if o.name.startswith('PEA207_')]
assert len(new)==30
campus=set(bpy.data.scenes['00_CAMPUS_COMPLETE'].objects)
assert not set(new)&campus
owners=[(scene,layer)for scene in bpy.data.scenes for layer in scene.view_layers if all(o.name in layer.objects for o in new)]
assert owners
for obj in new:
 assert not obj.hide_render
 assert all(not obj.hide_get(view_layer=layer)for scene,layer in owners)
old=json.loads((ROOT/'result/blender/pea-interior207/audit.json').read_text())['archivedObjects']
for name in old:
 obj=bpy.data.objects[name];assert obj.hide_render
 assert all(obj.hide_get(view_layer=layer)for scene,layer in owners if obj.name in layer.objects)
header=bpy.data.objects['PEA207_proscenium_header'];stage=bpy.data.objects['PEA207_stage_deck']
header_low=min((header.matrix_world@v.co).z for v in header.data.vertices)
stage_top=max((stage.matrix_world@v.co).z for v in stage.data.vertices)
assert abs(stage_top-1.05)<1e-5 and abs(header_low-stage_top-5.9)<1e-5
result={'savedNativeReopened':True,'roomObjects':len(new),'independentSceneCount':len(owners),'newObjectsVisibleInOwningLayers':True,'archivedObjectsHiddenInOwningLayers':True,'noAuditoriumLeakIntoCampus':True,'actualStageTop':stage_top,'actualStageClearHeight':header_low-stage_top}
(proof/'independent-scene-verification.json').write_text(json.dumps(result,indent=2)+'\n')
print('PEACOCK207_SCENE_VERIFIED',result)
