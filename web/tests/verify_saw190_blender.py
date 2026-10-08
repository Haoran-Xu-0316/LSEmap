"""Reopen the full campus and verify the SAW-only integration boundary."""
from pathlib import Path
import hashlib,json,sys
import bpy
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'web/tools'))
from refine_architectural_glass import shape_signature
from refine_old_lettering185 import font_signature
from refine_rooms import geometry_signatures
from refine_saw_brick_screens import apply_saw_brick_screens
from refine_building_details import BASE,TARGET,REPORT
proof=json.loads((REPORT/'building-refinement.json').read_text())
assert hashlib.sha256(BASE.read_bytes()).hexdigest()==proof['baselineSha256']
assert hashlib.sha256(TARGET.read_bytes()).hexdigest()==proof['sourceModelSha256']
bpy.ops.wm.open_mainfile(filepath=str(BASE))
collections={c.name:sorted(o.name for o in c.objects) for c in bpy.data.collections}
bpy.ops.wm.open_mainfile(filepath=str(TARGET))
for scene in bpy.data.scenes:
 for layer in scene.view_layers:layer.update()
assert geometry_signatures()==proof['geometrySignatures']
assert all(shape_signature(bpy.data.objects[n])==v for n,v in proof['originalShapesAndUVs'].items())
assert all(font_signature(bpy.data.objects[n])==v for n,v in proof['originalFonts'].items())
assert all(bpy.data.objects[n].hide_render==v for n,v in proof['visibility'].items())
change=proof['changes'][0];added=set(change['addedObjects'])
for name,objects in collections.items():
 assert sorted(o.name for o in bpy.data.collections[name].objects if o.name not in added)==objects
assert all(n in bpy.data.scenes['00_CAMPUS_COMPLETE'].objects for n in added)
assert all(not bpy.data.objects[n].hide_render for n in added)
assert apply_saw_brick_screens()['alreadyApplied']
assert not bpy.data.libraries
assert not any(i.source=='FILE' and not i.packed_file for i in bpy.data.images)
result=dict(version=190,savedSceneReopened=True,sourceModelSha256=proof['sourceModelSha256'],
 originalGeometryUVFontsBindingsPreserved=True,collectionsPreserved=True,idempotent=True,
 addedObjects=sorted(added),objects=len(bpy.data.objects),externalDependencies=False)
(REPORT/'reopened-verification.json').write_text(json.dumps(result,indent=2)+'\n')
print('SAW190_FULL_MODEL_VERIFIED',len(added),flush=True)
