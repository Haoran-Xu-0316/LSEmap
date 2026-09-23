"""Register the 2022 Coopers block-plan outlines to the local campus.

The drawing's SVG coordinates were read from its red/blue vector boundaries.
Five matching Old Curiosity Shop corners provide an approximate affine fit.
This is an architectural-study registration, not a surveyed property boundary.
Run directly with the existing Python environment; no command-line parameters.
"""
from pathlib import Path
import json
import numpy as np
from shapely.geometry import Polygon
from shapely.ops import triangulate

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'result/blender/stage08'
OUT.mkdir(parents=True, exist_ok=True)
site = json.loads((ROOT / 'result/blender/site_geometry.json').read_text())
shop = next(building for building in site['buildings'] if building.get('code') == 'OCS')['rings'][0]
source = np.array([[477.387, 637.5], [577.406, 597.48], [607.828, 675.719],
                   [597.867, 706.199], [500.066, 681.422]])
target = np.array([shop[0], shop[1], shop[3], shop[4], shop[5]])
controls = np.c_[source, np.ones(5)]
transform = np.linalg.lstsq(controls, target, rcond=None)[0]
residuals = np.linalg.norm(controls @ transform - target, axis=1)
assert max(residuals) < .15, 'Control-point fit differs from the reviewed registration'
plan_outlines = {
    '49L': [[379.588, 364.62], [470.308, 332.04], [534.388, 490.86],
            [484.227, 504.48], [477.148, 518.64], [423.628, 533.46], [359.789, 409.32]],
    '50L': [[424.949, 535.98], [479.129, 521.039], [486.207, 506.879],
            [535.469, 493.5], [577.406, 597.48], [477.387, 637.5]],
}
profiles = []
for code, points in plan_outlines.items():
    coordinates = (np.c_[points, np.ones(len(points))] @ transform).tolist()
    polygon = Polygon(coordinates)
    profiles.append({
        'code': code, 'ring': coordinates, 'center': list(polygon.centroid.coords)[0],
        'triangles': [list(triangle.exterior.coords)[:3] for triangle in triangulate(polygon)
                      if polygon.covers(triangle.representative_point())],
        'height': 10.9 if code == '49L' else 12.3,
        'scope': 'Block-plan-derived exterior envelope. The 50/50A frontage is a shared physical building, not an assertion of exclusive 50L tenancy. Vertical dimensions and unseen details are estimates.',
        'area': polygon.area,
    })
restaurant, neighbour = [Polygon(profile['ring']) for profile in profiles]
marshall = Polygon(next(building for building in site['buildings'] if building.get('code') == 'MAR')['rings'][0])
assert restaurant.intersection(neighbour).area < .01
assert restaurant.intersection(marshall).area < .01
report = {
    'profiles': profiles,
    'sourceUrl': 'https://docs.planning.org.uk/20220826/115/RELXRTRPFZ800/nev73t6wc2rk72nq.pdf',
    'drawing': 'RT22055-RTA-XX-XX-DR-A-00002, PL01, 2022-06-22',
    'registration': 'Affine registration from five OCS block-plan corners to the existing OSM-derived OCS outline; not survey coordinates.',
    'controlPointsSvg': source.tolist(), 'controlPointsLocal': target.tolist(),
    'transform': transform.tolist(), 'controlResidualMetres': residuals.tolist(),
    'replacementContextIds': ['way/181939042'],
    'overlap49WithMAR': restaurant.intersection(marshall).area,
    'overlap49With50': restaurant.intersection(neighbour).area,
}
(OUT / 'coopers-geometry.json').write_text(json.dumps(report, indent=2) + '\n')
print('COOPERS_REGISTRATION_COMPLETE', residuals.tolist())
