"""Reopen the standalone OLD foyer component and verify retained source data."""
from pathlib import Path
import hashlib
import json
import sys
import bpy
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'web/tools'))
from integrate_exterior_round194 import object_fingerprint
from refine_col_exterior195 import state
proof=ROOT/'result/blender/old-foyer196'
report=json.loads((proof/'audit.json').read_text())
base=ROOT/'result/blender/LSE_campus_detailed_v195.blend'
expected_sha=report['baselineSha256']
if not base.exists():
    authoring=json.loads((ROOT/'web/tools/building-metadata.json').read_text())
    catalogue=json.loads((ROOT/'web/public/models/catalogue.json').read_text())
    base=ROOT/f"result/blender/LSE_campus_detailed_v{authoring['sourceVersion']}.blend"
    expected_sha=catalogue['sourceModelSha256']
component=ROOT/report['componentPath']
assert hashlib.sha256(base.read_bytes()).hexdigest()==expected_sha
assert hashlib.sha256(component.read_bytes()).hexdigest()==report['componentSha256']
bpy.ops.wm.open_mainfile(filepath=str(base))
for scene in bpy.data.scenes:
    for layer in scene.view_layers:layer.update()
original_states={item['originalObject']:state(bpy.data.objects[item['originalObject']]) for item in report['replacements']}
for item in report['replacements']:assert original_states[item['originalObject']]==item['originalState']
bpy.ops.wm.read_factory_settings(use_empty=True)
with bpy.data.libraries.load(str(component),link=False) as (available,target):target.objects=list(report['addedObjects'])
for obj in target.objects:bpy.context.scene.collection.objects.link(obj)
bpy.context.view_layer.update()
for obj in target.objects:
    actual=object_fingerprint(obj)
    assert actual==report['fingerprints'][obj.name],(obj.name,actual,report['fingerprints'][obj.name])
    if obj.get('originalObject'):
        original=original_states[obj['originalObject']]
        assert state(obj)['geometry']==original['geometry']
        assert state(obj)['uv']==original['uv']
assert len(report['floorCoverageSamples'])==9
assert hashlib.sha256(base.read_bytes()).hexdigest()==expected_sha
(proof/'verification.json').write_text(json.dumps(dict(componentReopened=True,addedObjectsVerified=len(target.objects),sourceGeometryAndUVPreserved=True,baselineUnchanged=True,floorCoverageSamples=9),indent=2)+'\n')
print('OLD_FOYER196_COMPONENT_VERIFIED',len(target.objects),flush=True)
