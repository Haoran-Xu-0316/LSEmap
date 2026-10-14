"""Check the saved mesh against original ground coverage and surface evidence."""
from pathlib import Path
import json
from shapely.geometry import Polygon
from shapely.ops import unary_union
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'result/blender/pedestrian-surfaces209'


def coverage(row, top=None):
    polygons = []
    for face in row['faces']:
        points = [row['vertices'][index] for index in face]
        if top is None or all(abs(point[2]-top) < 1e-6 for point in points):
            polygon = Polygon([point[:2] for point in points])
            if polygon.area > 1e-10:
                polygons.append(polygon)
    return unary_union(polygons), sum(p.area for p in polygons)


original = json.loads((OUT/'native-audit.json').read_text())
saved = json.loads((OUT/'saved-ground-audit.json').read_text())
plan = json.loads((OUT/'surface-plan.json').read_text())
source_paths, old_additive = coverage(next(row for row in original['objects'] if row['name'] == plan['sourceObject']), .024)
path_rows = [row for row in saved['objects'] if 'footways' in row['name']]
actual_paths = unary_union([coverage(row)[0] for row in path_rows])
tolerance = .00015
# Discrete boundary Hausdorff distance overstates tiny filled/created overlay
# holes. Check both complete covered sets against the same bounded buffer.
assert source_paths.difference(actual_paths.buffer(tolerance)).is_empty
assert actual_paths.difference(source_paths.buffer(tolerance)).is_empty
assert source_paths.symmetric_difference(actual_paths).area < .5
asphalt = coverage(next(row for row in path_rows if 'asphalt' in row['name']))[0]
paving = coverage(next(row for row in path_rows if 'paved' in row['name']))[0]
assert asphalt.intersection(paving).area < .02
assert sum(coverage(row)[1] for row in path_rows)-actual_paths.area < .02
assert plan['matchedSegments'] == 645 and plan['explicitAsphaltWays'] == 50
exposed = 0
for green in plan['grasses']:
    old = next(row for row in original['objects'] if row['name'] == green['source'])
    name = 'SITE209_'+green['source'].replace('GROUND199_', '').replace('/', '_')+'_path_openings'
    current = next(row for row in saved['objects'] if row['name'] == name)
    before, _ = coverage(old)
    after, _ = coverage(current)
    expected = before.difference(source_paths)
    assert expected.symmetric_difference(after).area < .2
    assert after.intersection(actual_paths).area < .02
    assert after.difference(before.buffer(.00015)).area < 1e-5
    exposed += before.intersection(source_paths).area
assert exposed > 2000
assert saved['oldGrassOccludedProbeCount'] == saved['recoveredPathProbeCount'] > 20
result = dict(verified=True, savedMeshCoverageToleranceMetres=tolerance,
              savedDuplicateAreaM2=sum(coverage(row)[1] for row in path_rows)-actual_paths.area,
              removedDuplicateAreaM2=old_additive-source_paths.area,
              recoveredMappedPathAreaM2=exposed, savedPathRays=saved['recoveredPathProbeCount'],
              matchedSourceSegments=645, explicitAsphaltWays=50, originalMaterialsVerified=saved['originalMaterialsVerified'])
(OUT/'coverage-verification.json').write_text(json.dumps(result, indent=2)+'\n')
print(json.dumps(result))
