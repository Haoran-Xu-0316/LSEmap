"""Compare CBG's inherited structural grid with a scaled architect drawing.

Read-only Blender audit. The 2016 drawing is design evidence, not an as-built
survey. Do not resize the campus or publish the private roof candidate here.
"""
from pathlib import Path
import hashlib
import json
import math
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
NATIVE = ROOT / 'result/blender/LSE_campus_detailed_v199.blend'
DRAWING = ROOT / 'data/collections/cbg_roof_registration/level12-plan-rshp-2016.jpg'
OUTPUT = ROOT / 'result/blender/cbg-grid200'
# The visible horizontal scale bar spans 0–20m in this exact archived bitmap.
SCALE_BAR = [(1220, 1159), (1505, 1159)]
# Eight structural column centres read from the top edge of the tower plan.
PLAN_COLUMNS = [(796, 634), (882, 639), (970, 644), (1056, 648),
                (1141, 652), (1227, 657), (1313, 662), (1399, 668)]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def connected_centres(obj, to_local):
    mesh = obj.data
    adjacency = [set() for _ in mesh.vertices]
    for edge in mesh.edges:
        a, b = edge.vertices
        adjacency[a].add(b)
        adjacency[b].add(a)
    unseen = set(range(len(mesh.vertices)))
    components = []
    while unseen:
        start = unseen.pop()
        pending, island = [start], [start]
        while pending:
            index = pending.pop()
            neighbours = adjacency[index] & unseen
            unseen.difference_update(neighbours)
            pending.extend(neighbours)
            island.extend(neighbours)
        points = [to_local(obj.matrix_world @ mesh.vertices[i].co) for i in island]
        low = [min(p[j] for p in points) for j in range(3)]
        high = [max(p[j] for p in points) for j in range(3)]
        components.append({'low': low, 'high': high,
                           'centre': [(a + b) / 2 for a, b in zip(low, high)]})
    return components


def audit():
    original_sha = digest(NATIVE)
    assert original_sha == '23a119c5b1235f780a8f17f29c8a02ff1d6a2036e269312bb7d5c459c4216877'
    assert digest(DRAWING) == '5dc5b500a66ebcd630031c999f8a347a0de21daab443d3f009908337c32c29cc'
    bpy.ops.wm.open_mainfile(filepath=str(NATIVE))
    site = json.loads((ROOT / 'result/blender/site_geometry.json').read_text())
    cx, cy = next(b['center'] for b in site['buildings'] if b['code'] == 'CBG')
    angle = math.radians(58)
    c, s = math.cos(angle), math.sin(angle)

    def to_local(p):
        return Vector((c * (p.x - cx) + s * (p.y - cy),
                       -s * (p.x - cx) + c * (p.y - cy), p.z))

    columns = [o for o in bpy.data.collections['CBG_EXTERIOR'].all_objects
               if o.type == 'MESH' and not o.hide_render and 'external_I_columns' in o.name]
    assert len(columns) == 1, [o.name for o in columns]
    pieces = connected_centres(columns[0], to_local)
    # Cross-section plates may be disconnected; collapse their bounding centres
    # into the existing structural x/y axes rather than counting plates as columns.
    axes = sorted(set((round(p['centre'][0], 2), round(p['centre'][1], 2)) for p in pieces))
    front = sorted(set(x for x, y in axes if abs(y + 2) < .35))
    if not front:
        front_y = min(y for x, y in axes)
        front = sorted(set(x for x, y in axes if abs(y - front_y) < .35))
    native_spans = [b - a for a, b in zip(front, front[1:])]
    metres_per_pixel = 20 / math.dist(*SCALE_BAR)
    plan_spans = [math.dist(a, b) * metres_per_pixel for a, b in zip(PLAN_COLUMNS, PLAN_COLUMNS[1:])]
    report = {'sourceModelSha256': original_sha,
              'drawing': {'path': str(DRAWING.relative_to(ROOT)), 'sha256': digest(DRAWING),
                          'date': 'Copyright2016; design-stage architect plan, not current survey',
                          'scaleBarPixels': SCALE_BAR, 'scaleBarMetres': 20,
                          'metresPerPixel': metres_per_pixel, 'columnCentrePixels': PLAN_COLUMNS,
                          'gridSpansMetres': plan_spans, 'gridSpanCount': len(plan_spans)},
              'native': {'object': columns[0].name, 'componentCount': len(pieces),
                         'axisPairs': axes, 'frontAxesMetres': front, 'gridSpansMetres': native_spans},
              'decision': 'Do not merge the roof candidate. Independently scaled2016 grid is about6m; resolve inherited structural-grid and floor registration before modifying envelope.',
              'limitations': ['Manual pixel centres have approximately2px reading uncertainty.',
                             'Design drawing dimensions cannot establish current built dimensions.',
                             'This audit does not authorize whole-building rescaling from one historical plan.'],
              'nativeFileUnchanged': digest(NATIVE) == original_sha}
    assert report['nativeFileUnchanged']
    assert all(5.8 < span < 6.3 for span in plan_spans), plan_spans
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / 'audit.json').write_text(json.dumps(report, indent=2) + '\n')
    print('CBG200_GRID', json.dumps({'planSpans': plan_spans, 'nativeFrontAxes': front, 'nativeSpans': native_spans}), flush=True)


if __name__ == '__main__':
    audit()
