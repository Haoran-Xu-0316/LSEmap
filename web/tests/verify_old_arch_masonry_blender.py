"""Independently inspect saved radial arch faces and retained OLD joinery."""
from pathlib import Path
import json
import bpy
from mathutils import Vector
ROOT = Path(__file__).resolve().parents[2]
bpy.ops.wm.open_mainfile(filepath=str(ROOT / 'result/blender/LSE_campus_detailed_v69.blend'))
path = ROOT / 'result/blender/stage69/old-arch-masonry-audit.json'
audit = json.loads(path.read_text())
origin, right, outward = [Vector(audit['frame'][key]) for key in ['origin', 'right', 'outward']]
obj = bpy.data.objects['OLD_D5_arch69_stone']
fan = []
for polygon in obj.data.polygons:
    assert polygon.area > .000001, polygon.index
    assert (obj.matrix_world.to_3x3() @ polygon.normal).dot(outward) > .05, polygon.index
    points = [obj.matrix_world @ obj.data.vertices[i].co for i in polygon.vertices]
    if all(abs((p - origin).dot(outward) - .239) < .0001 for p in points):
        assert (obj.matrix_world.to_3x3() @ polygon.normal).dot(outward) > .99
        assert all(abs((p - origin).dot(right)) <= 4.751 and p.z <= 10.321 for p in points)
        fan.append(polygon.index)
assert len(fan) == 20, len(fan)
assert bpy.data.objects['OLD_V69_scroll_motto'].data.body == 'RERUM COGNOSCERE CAUSAS'
for name in audit['hiddenPreviousObjects']:
    assert bpy.data.objects[name].hide_render
for name in ['OLD_V56_Entry_stone', 'OLD_D5_entry65_glass', 'OLD_D5_entry65_steel', 'OLD_V53_Clare_blue']:
    assert not bpy.data.objects[name].hide_render
assert audit['changedExistingGeometry'] == []
audit['savedMeasurements'] = {'frontFacingFanStones': len(fan), 'mottoVerified': True,
                              'joineryAndEarlierReliefRetained': True}
path.write_text(json.dumps(audit, indent=2) + '\n')
print('SAVED_OLD_ARCH_MASONRY_VERIFIED', len(fan))
