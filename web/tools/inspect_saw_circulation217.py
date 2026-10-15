"""Locate published lift/stair conflicts before reconstructing SAW's cores.

Read-only Blender extraction followed by MachineLearning geometry analysis.
Historical guide outlines are exact source vectors; absolute registration and
stair heights remain inherited estimates. This is not an access certification.
"""
from pathlib import Path
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'result/blender/LSE_campus_detailed_v216.blend'
SHA = '12376d6365bbc57fa9eec97617453dbbfcf9235a8200bb90726f80c2147c1a60'
OUT = ROOT / 'result/blender/saw-circulation217'
OUT.mkdir(parents=True, exist_ok=True)
GUIDE_URL = 'https://info.lse.ac.uk/staff/divisions/estates-division/Assets/Documents/SAW/Final-Web-version-of-Occupants-Guide.pdf'
LEVELS = [0, 3.45, 8.1, 11.1, 14.1, 18, 21.9]


def extract_actual_geometry():
    import bpy
    sys.path.insert(0, str(ROOT / 'web/tools'))
    from integrate_exterior_round194 import accepted_fingerprints, object_fingerprint, update_scene
    assert hashlib.sha256(BASE.read_bytes()).hexdigest() == SHA
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    update_scene()
    expected = accepted_fingerprints(ROOT / 'result/blender/stage216', SHA)
    assert {obj.name: object_fingerprint(obj) for obj in bpy.data.objects} == expected
    rows = []
    for name in ['SAW173_registered_main_treads', 'SAW173_main_stair_rails']:
        obj = bpy.data.objects[name]
        obj.data.calc_loop_triangles()
        rows.append(dict(name=name,
                         vertices=[list(obj.matrix_world @ vertex.co) for vertex in obj.data.vertices],
                         triangles=[list(triangle.vertices) for triangle in obj.data.loop_triangles]))
    (OUT / 'actual-native-surfaces.json').write_text(json.dumps(rows, separators=(',', ':')) + '\n')
    assert hashlib.sha256(BASE.read_bytes()).hexdigest() == SHA
    (OUT / 'native-verification.json').write_text(json.dumps(dict(
        sourceModelSha256=SHA, acceptedObjectsVerified=len(expected), nativeFileUnchanged=True), indent=2) + '\n')
    print('SAW217_READ_ONLY', len(expected), flush=True)


def review_lift_conflicts():
    import numpy as np
    from shapely.geometry import Polygon
    from shapely.ops import unary_union
    from PIL import Image, ImageDraw
    source = ROOT / 'result/blender/saw-floors216'
    vectors = json.loads((source / 'vectors.json').read_text())
    registration = json.loads((source / 'registration.json').read_text())
    factor = 1501 / vectors['32']['pageSize'][0]
    anchors = np.array([[-65.223399, -15.905616], [-84.252182, 28.425], [-55.301, 36.609104]])

    def world(points):
        pixels = np.array(points) * factor
        a, b, c = anchors
        return a + (pixels[:, 0:1] - 145) / 1200 * (b - a) + (pixels[:, 1:2] - 400) / 785 * (c - b)

    cabins = []
    for index in registration['32']['sourceControlCurveIndices']:
        curve = next(curve for curve in vectors['32']['candidates'] if curve['index'] == index)
        polygon = Polygon(world(curve['pts'][:-1]))
        assert polygon.is_valid
        cabins.append(polygon)
    cabin_union = unary_union(cabins)
    native = json.loads((OUT / 'actual-native-surfaces.json').read_text())
    stair = next(item for item in native if item['name'] == 'SAW173_registered_main_treads')
    vertices = np.array(stair['vertices'])
    by_height = {}
    for indices in stair['triangles']:
        points = vertices[indices]
        if np.ptp(points[:, 2]) > 1e-5 or np.cross(points[1] - points[0], points[2] - points[0])[2] <= 0:
            continue
        by_height.setdefault(round(float(points[:, 2].mean()), 5), []).append(Polygon(points[:, :2]))
    treads = []
    for height, triangles in sorted(by_height.items()):
        polygon = unary_union(triangles)
        flight = next(i for i, datum in enumerate(LEVELS[1:]) if height <= datum + 1e-4)
        overlap = polygon.intersection(cabin_union).area
        treads.append(dict(height=height, flight=flight, polygon=polygon, cabinOverlapM2=overlap))
    assert len(treads) == 146
    conflicts = [item for item in treads if item['cabinOverlapM2'] > .0001]
    report = dict(version=217, sourceModelSha256=SHA, sourceGuide=GUIDE_URL,
                  sourcePublicationYear=2014, cabinCount=2, actualTreadCount=len(treads),
                  conflictingTreads=len(conflicts),
                  summedTreadCabinOverlapM2=sum(item['cabinOverlapM2'] for item in conflicts),
                  cabinOutlinesWorld=[list(polygon.exterior.coords) for polygon in cabins],
                  sourceVectorIndices=registration['32']['sourceControlCurveIndices'],
                  conflicts=[{key: value for key, value in item.items() if key != 'polygon'} for item in conflicts],
                  scope='Current stair top faces intersect the registered published cabin footprint. No invented wall thickness was added to this test.',
                  nextRequiredChange='Re-register the six connected main flights, floor apertures and landings against the actual core and source stair zone before adding continuous lift shafts.',
                  limitations='The guide is historical. Absolute world scale and inherited stair geometry are estimates. This detects modeling inconsistency, not surveyed clearance or safe access.')
    (OUT / 'lift-stair-conflicts.json').write_text(json.dumps(report, indent=2) + '\n')
    # Private schematic of actual native tread faces and source cabin outlines.
    bounds = unary_union([item['polygon'] for item in treads] + cabins).bounds
    image = Image.new('RGB', (1500, 1000), 'white')
    draw = ImageDraw.Draw(image)
    for flight in range(6):
        x, y = flight % 3 * 500, flight // 3 * 500
        scale = min(440 / (bounds[2] - bounds[0]), 410 / (bounds[3] - bounds[1]))
        def screen(polygon):
            return [(x + 30 + (px - bounds[0]) * scale, y + 60 + (bounds[3] - py) * scale)
                    for px, py in polygon.exterior.coords]
        draw.text((x + 20, y + 15), f'{flight}->{flight+1}: source cabins and actual estimated treads', fill='black')
        for polygon in cabins:
            draw.polygon(screen(polygon), fill='#d8dde1', outline='#334b5b', width=3)
        for item in treads:
            if item['flight'] != flight:
                continue
            draw.polygon(screen(item['polygon']), fill='#d58a83' if item['cabinOverlapM2'] > .0001 else '#a4bbc4', outline='white')
    image.save(OUT / 'lift-stair-conflicts.png')
    print('SAW217_SOURCE_CONFLICTS', report['conflictingTreads'], round(report['summedTreadCabinOverlapM2'], 4))


if __name__ == '__main__':
    try:
        import bpy
    except ModuleNotFoundError:
        review_lift_conflicts()
    else:
        extract_actual_geometry()
