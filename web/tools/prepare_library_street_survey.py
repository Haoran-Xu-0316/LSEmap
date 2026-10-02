"""Register the 2025 existing Carey Street drawing against the current LRB shell.
Run in the existing MachineLearning environment. No historical model is required.
Pixel coordinates refer to the 1800px full sheet, not a scaled display preview.
"""
from pathlib import Path
import json
import math
from shapely.geometry import Polygon, box
from shapely.ops import unary_union
from shapely import constrained_delaunay_triangles

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'result/blender/stage117'
OUT.mkdir(parents=True, exist_ok=True)
native = json.loads((OUT / 'library-native.json').read_text())
ring = native['ring']

def add(a, b): return [x + y for x, y in zip(a, b)]
def sub(a, b): return [x - y for x, y in zip(a, b)]
def scale(a, s): return [x * s for x in a]
def unit(a): return scale(a, 1 / math.hypot(*a))
def triangles(poly):
    result = [list(t.exterior.coords)[:3] for t in constrained_delaunay_triangles(poly).geoms]
    assert abs(sum(Polygon(t).area for t in result) - poly.area) < .001
    return result

nw_origin, nw_end = ring[1], ring[2]
nw_axis = unit(sub(nw_end, nw_origin))
nw_normal = [-nw_axis[1], nw_axis[0]]
nw_length = math.dist(nw_end, nw_origin)
# Roof-plan tangent offset and projected corner width are visual estimates.
corner_end = add(nw_end, add(scale(nw_axis, 130 / 1171 * nw_length), scale(nw_normal, -2.08)))
carey_end = ring[7]
carey_axis = unit(sub(carey_end, corner_end))
carey_normal = [-carey_axis[1], carey_axis[0]]
carey_length = math.dist(corner_end, carey_end)
controls = [nw_end, add(nw_end, scale(nw_axis, 2.3)), add(corner_end, scale(carey_axis, -2.3)), corner_end]
def curve(t):
    weights = [(1-t)**3, 3*(1-t)**2*t, 3*(1-t)*t*t, t**3]
    return [sum(controls[j][i]*weights[j] for j in range(4)) for i in range(2)]
corner = [curve(i/48) for i in range(49)]
corner_distances = [0.0]
for a, b in zip(corner, corner[1:]): corner_distances.append(corner_distances[-1] + math.dist(a, b))
outer = Polygon(ring[:2] + corner + ring[7:])
assert outer.is_valid
# Recover the raised roof footprint from the retained current native triangles.
# This replaces the dependency on a deleted edition109 intermediate file.
roof = next(o for o in native['objects'] if o['name'] == 'LRB_D5_roof109_roof')
low_faces = [Polygon([roof['points'][i][:2] for i in f]) for f in roof['faces']
             if all(abs(roof['points'][i][2]-20.24) < .001 for i in f)]
raised = Polygon(ring).difference(unary_union(low_faces)).buffer(0)
# Float32 export coordinates create tiny perimeter slivers. Keep the main island.
raised = max(raised.geoms, key=lambda p: p.area) if hasattr(raised, 'geoms') else raised
assert outer.buffer(.02).covers(raised)
px = lambda x: carey_length * (1238-x) / (1238-383)
width = lambda pixels: carey_length * pixels / 855
centres = [473, 622, 771, 919, 1068]
rows = [(5.40, 8.61), (9.89, 12.21), (13.09, 15.79)]
openings = []
def window(x, w, lo, hi, cols, panes, kind, depth=-.075, curved=False):
    openings.append(dict(x=x, width=w, low=lo, high=hi, columns=cols, rows=panes,
                         kind=kind, depth=depth, curved=curved))
for level, (lo, hi) in enumerate(rows):
    for centre in centres:
        for offset in [-32, 0, 32]: window(px(centre+offset), width(27), lo, hi, 3, 6 if level==0 else 4, 'oriel', .16)
    window(px(1187), width(30), lo, hi, 3, 6 if level==0 else 4, 'single')
window(px(490), width(64), -.10, 4.24, 2, 2, 'service-door')
window(px(437), width(28), -.10, 4.24, 1, 32, 'louvre')
for centre in [622, 771]: window(px(centre), width(104), .28, 4.43, 3, 3, 'ground-modern')
for centre in [919, 1068]: window(px(centre), width(104), .90, 4.43, 9, 6, 'ground-historic')
window(px(1187), width(30), .65, 4.43, 3, 6, 'ground-single')
corner_length = corner_distances[-1]
for lo, hi in rows:
    for ratio in [.22, .50, .78]: window(corner_length*ratio, corner_length*.185, lo, hi, 2, 6 if lo==5.40 else 4, 'corner', -.07, True)
window(corner_length*.5, corner_length*.72, .05, 4.15, 3, 2, 'corner-entry', -.26, True)
window(px(1187), width(30), 17.75, 20.04, 3, 4, 'loft-single')
for ratio in [.22, .50, .78]: window(corner_length*ratio, corner_length*.185, 17.75, 20.04, 2, 4, 'corner-loft', -.07, True)
arches = [dict(x=px(c), radius=width(50), spring=17.75) for c in centres]

def wall_triangles(length, curved):
    wall = Polygon([(0,-.26), (length,-.26), (length,20.59), (0,20.59)])
    for opening in openings:
        if opening['curved'] != curved: continue
        a, b = opening['x']-opening['width']/2, opening['x']+opening['width']/2
        wall = wall.difference(Polygon([(a,opening['low']), (b,opening['low']), (b,opening['high']), (a,opening['high'])]))
    if not curved:
        for arch in arches:
            x, r, z = arch['x'], arch['radius'], arch['spring']
            outline = [(x+r*math.cos(i*math.pi/48), z+r*math.sin(i*math.pi/48)) for i in range(49)]
            wall = wall.difference(Polygon(outline))
    if curved:
        result = []
        for a, b in zip(corner_distances, corner_distances[1:]):
            piece = wall.intersection(box(a, -.27, b, 20.60))
            if not piece.is_empty: result.extend(triangles(piece))
        return result
    return triangles(wall)

plan = dict(version=117, ring=ring, cornerControls=controls, cornerCurve=corner,
            cornerDistances=corner_distances, cornerLength=corner_length,
            careyOrigin=corner_end, careyEnd=carey_end, careyAxis=carey_axis,
            careyNormal=carey_normal, careyLength=carey_length, careyCentres=[px(c) for c in centres],
            orielWidth=width(104), openings=openings, arches=arches,
            bodyRows=rows, careyWallTriangles=wall_triangles(carey_length, False),
            cornerWallTriangles=wall_triangles(corner_length, True),
            lowerRoofTriangles=triangles(outer.difference(raised)),
            outerBoundary=list(outer.exterior.coords)[:-1], raisedBoundary=list(raised.exterior.coords)[:-1],
            source='data/collections/library-roof-2025/existing-w-ne-elevations.pdf',
            drawing='4556-FBR-LR-ZZ-DR-A-113 P01, 17 April 2025, As Existing',
            registration='AOD heights minus estimated 20m local datum; drawing proportions registered to retained GIS endpoints',
            limits=['Unlabelled dimensions, corner controls and global registration estimated',
                    '2025 existing drawing, not a 2026 site survey', 'Other elevations and full interior levels remain unverified'])
(OUT/'street-survey-geometry.json').write_text(json.dumps(plan, indent=2)+'\n')
print('LIBRARY_STREET_SURVEY_PREPARED', carey_length, corner_length, len(openings), len(plan['lowerRoofTriangles']))
