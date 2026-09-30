"""Read saved OLD joinery geometry and independently measure the stair approach."""
from pathlib import Path
import json
import bpy
from mathutils import Vector
ROOT = Path(__file__).resolve().parents[2]
bpy.ops.wm.open_mainfile(filepath=str(ROOT / 'result/blender/LSE_campus_detailed_v65.blend'))
path = ROOT / 'result/blender/stage65/old-entry-joinery-audit.json'
audit = json.loads(path.read_text())
origin, right, outward = [Vector(audit['frame'][key]) for key in ['origin', 'right', 'outward']]
def local(obj, vertex):
    p = obj.matrix_world @ vertex.co
    return ((p - origin).dot(right), (p - origin).dot(outward), p.z)
stone = bpy.data.objects['OLD_D5_entry65_stone']
assert len(stone.data.vertices) == 48
measured = []
for i in range(1, 5):
    points = [local(stone, v) for v in stone.data.vertices[i * 8:i * 8 + 8]]
    bound = [[min(p[axis] for p in points), max(p[axis] for p in points)] for axis in range(3)]
    assert abs(bound[0][0] + 4.4) < .0001 and abs(bound[0][1] - 3.2) < .0001
    assert abs(bound[1][1] - audit['steps'][i - 1]['front']) < .0001
    assert abs(bound[2][1] - audit['steps'][i - 1]['top']) < .0001
    measured.append(bound)
glass = bpy.data.objects['OLD_D5_entry65_glass']
assert len(glass.data.vertices) == 64
for i in range(0, 8, 2):
    points = [local(glass, v) for v in glass.data.vertices[i * 8:i * 8 + 8]]
    assert abs(max(p[2] for p in points) - 3.62) < .0001
    assert abs(min(p[2] for p in points) - .70) < .0001
for name in audit['hiddenPreviousObjects']:
    assert bpy.data.objects[name].hide_render
assert not bpy.data.objects['OLD_V56_Entry_stone'].hide_render
assert not bpy.data.objects['OLD_V53_Clare_blue'].hide_render
assert audit['changedExistingGeometry'] == ['OLD_V52_Houghton_iron']
audit['savedMeasurements'] = {'stairBounds': measured, 'glassLeaves': 4, 'transomLights': 4}
path.write_text(json.dumps(audit, indent=2) + '\n')
print('SAVED_OLD_ENTRY_JOINERY_VERIFIED')
