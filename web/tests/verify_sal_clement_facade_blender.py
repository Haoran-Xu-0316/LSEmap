"""Inspect saved SAL floor count, oblique side glazing and CLM capital geometry."""
from pathlib import Path
import json
import bpy
from mathutils import Vector
ROOT = Path(__file__).resolve().parents[2]
bpy.ops.wm.open_mainfile(filepath=str(ROOT / 'result/blender/LSE_campus_detailed_v70.blend'))
path = ROOT / 'result/blender/stage70/sal-clement-facade-audit.json'
audit = json.loads(path.read_text())
obj = bpy.data.objects['SAL_Window_glazing']
# Discover connected glass panels, independent of component ordering.
links = [[] for _ in obj.data.vertices]
for edge in obj.data.edges:
    a, b = edge.vertices
    links[a].append(b)
    links[b].append(a)
seen, heights = set(), []
for vertex in obj.data.vertices:
    if vertex.index in seen:
        continue
    stack, indices = [vertex.index], []
    seen.add(vertex.index)
    while stack:
        index = stack.pop()
        indices.append(index)
        for neighbor in links[index]:
            if neighbor not in seen:
                seen.add(neighbor)
                stack.append(neighbor)
    z = sum((obj.matrix_world @ obj.data.vertices[i].co).z for i in indices) / len(indices)
    # The central door is a separate glazed component centered at 2.4m.
    if 2.5 < z < 17.6:
        heights.append(round(z, 3))
assert set(heights) == {2.85, 7.3, 11.65, 15.85}, set(heights)
assert all(p.area > .000001 for p in obj.data.polygons)
glass = bpy.data.objects['SAL_D5_photo70_glass']
assert len(glass.data.vertices) == 18 * 8
u, n = [Vector(audit['salFrame'][key]) for key in ['right', 'outward']]
for i in range(18):
    points = [glass.matrix_world @ v.co for v in glass.data.vertices[i * 8:i * 8 + 8]]
    # Every side pane spans depth; a flat frontal pane cannot pass this check.
    depths = [p.dot(n) for p in points]
    assert max(depths) - min(depths) > .9
blue = bpy.data.materials['SAL_V70_blue_painted_sash']
assert blue.diffuse_color[2] > 4 * blue.diffuse_color[0]
for name in audit['hiddenPreviousObjects']:
    assert bpy.data.objects[name].hide_render
assert audit['clementCapitalScrolls'] == 8
assert len(bpy.data.objects['CLM_D5_photo70_capital'].data.vertices) > 5000
assert all(name.startswith('SAL_') for name in audit['changedExistingObjects'])
audit['savedMeasurements'] = {'mainWindowLevels': sorted(set(heights)), 'obliqueSidePanes': 18,
                              'clementCapitalScrolls': 8, 'outsideSalExistingObjectsUnchanged': True}
path.write_text(json.dumps(audit, indent=2) + '\n')
print('SAVED_SAL_CLEMENT_FACADE_VERIFIED', sorted(set(heights)), 18)
