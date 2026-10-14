"""Read-only verification of the private CBG position and eight-axis component.

Run in Blender's Text Editor. Does not save or replace any model.
"""
from pathlib import Path
import hashlib
import json
import math
import sys
import bpy
import bmesh
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'web/tools'))
from refine_ground_orientation199 import closed_islands, signed_volume
OUTPUT = ROOT / 'result/blender/cbg-envelope202'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify():
    report = json.loads((OUTPUT / 'audit.json').read_text())
    mapping = json.loads((ROOT / 'result/blender/cbg-georegistration202/rebuild-mapping.json').read_text())
    master = ROOT / report.get('baselinePath','result/blender/LSE_campus_detailed_v203.blend')
    assert digest(master) == report['baselineSha256']
    component = ROOT / report['componentPath']
    assert digest(component) == report['componentSha256']
    assert report['status'] == 'private-partial-reconstruction-not-for-release'
    assert len(report['remainingBeforeRelease']) == 5
    bpy.ops.wm.read_factory_settings(use_empty=True)
    with bpy.data.libraries.load(str(component), link=False) as (source, target):
        target.objects = list(report['addedObjects'])
    for obj in target.objects:
        bpy.context.scene.collection.objects.link(obj)
    for layer in bpy.context.scene.view_layers:
        layer.update()
    frame = mapping['legacy_frame_compatible_transform']
    ox, oy = frame['translation_world']
    c, s = math.cos(math.radians(frame['rotation_degrees'])), math.sin(math.radians(frame['rotation_degrees']))

    def local(point):
        return Vector((c * (point.x - ox) + s * (point.y - oy), -s * (point.x - ox) + c * (point.y - oy), point.z))

    webs = next(o for o in target.objects if o.name.endswith('tower_I_webs'))
    bm = bmesh.new()
    bm.from_mesh(webs.data)
    centres = []
    for faces, closed in closed_islands(bm):
        assert closed and signed_volume(faces) > 0
        vertices = {v for f in faces for v in f.verts}
        points = [local(webs.matrix_world @ vertex.co) for vertex in vertices]
        centre = sum(points, Vector()) / len(points)
        assert abs(max(p.z for p in points) - 52.2) < .001
        assert abs(min(p.z for p in points)) < .001
        centres.append(tuple(centre))
    bm.free()
    assert len(centres) == 16
    for expected in [-35, -29, -23, -17, -11, -5, 1, 7]:
        pair = [p for p in centres if abs(p[0] - expected) < .002]
        assert len(pair) == 2
        assert len([p for p in pair if abs(p[1] + 2.31) < .002]) == 1
    low = next(o for o in target.objects if o.get('originalObject') and 'external_I_columns' in o.get('originalObject') and not o.name.endswith(('tower_I_webs', 'tower_I_flanges', 'tower_column_caps')))
    assert max((low.matrix_world @ vertex.co).z for vertex in low.data.vertices) < 26
    assert sum(row['towerColumnPartsRemoved'] for row in report['records']) == 70
    front_centres = sorted([p for p in centres if abs(p[1] + 2.31) < .002])
    assert abs(front_centres[-1][0] - front_centres[0][0] - 42) < .003
    assert all(abs(b[0] - a[0] - 6) < .003 for a, b in zip(front_centres, front_centres[1:]))
    # Nominal grid endpoints are independently registered from outside CBG.
    for index, point in enumerate(mapping['tower']['nominal_axes_world']):
        expected = mapping['legacy_frame_compatible_transform']['tower_axis_x_G0_to_G7'][index]
        dx, dy = point[0] - ox, point[1] - oy
        assert abs(c * dx + s * dy - expected) < 1e-8
        assert abs(-s * dx + c * dy + 2) < 1e-8
    assert digest(master) == report['baselineSha256']
    result = {'componentSha256': report['componentSha256'], 'sourceUnchanged': True,
              'frontAxisCount': 8, 'totalTallColumnWebs': 16, 'gridSpanCount': 7,
              'axisPitchMetres': 6, 'axisLengthMetres': 42, 'heightMetres': 52.2,
              'noOldTallColumnsRemainInCopiedSystem': True,
              'everyNewColumnWebClosedAndOutward': True,
              'independentWorldEndpointRegistrationMatches': True,
              'notApprovedForRelease': True, 'remainingBeforeRelease': report['remainingBeforeRelease']}
    (OUTPUT / 'placement-verification.json').write_text(json.dumps(result, indent=2) + '\n')
    print('CBG202_PLACEMENT_VERIFIED', json.dumps(result), flush=True)


if __name__ == '__main__':
    verify()
