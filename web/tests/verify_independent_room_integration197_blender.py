"""Verify room isolation and identity collision checks without opening campus data."""
from pathlib import Path
import sys
import bpy
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'web/tools'))
from integrate_exterior_round194 import component_destination
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.scene.name='00_CAMPUS_COMPLETE'
name='ROOM197_ISOLATION_PROOF'
report=dict(targetCollection=name,collectionSpec=dict(name=name,scene='ROOM197_PROOF_SCENE',kind='independent-room'),space=dict(label='Proof room'))
collection=component_destination(report,name)
assert collection.name in bpy.data.scenes['ROOM197_PROOF_SCENE'].collection.children
assert collection.name not in bpy.data.scenes['00_CAMPUS_COMPLETE'].collection.children
for bad in [report,dict(report,collectionSpec=dict(name='WRONG',scene='ROOM_OTHER',kind='independent-room')),dict(report,collectionSpec=dict(name=name,scene='ROOM_OTHER',kind='campus'))]:
    try:component_destination(bad,name)
    except AssertionError:pass
    else:raise AssertionError('Invalid or colliding room identity accepted')
ordinary=bpy.data.collections.new('EXTERIOR_PROOF')
assert component_destination({},ordinary.name)==ordinary
print('INDEPENDENT_ROOM_ISOLATION_AND_COLLISION_CHECKS_PASSED',flush=True)
