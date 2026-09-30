"""Prepare clipped paving courses from the campus's existing road footprints.
Run in the MachineLearning environment. No dimensions here are a survey.
"""
from pathlib import Path
import json
import math
from shapely import affinity, constrained_delaunay_triangles
from shapely.geometry import Polygon, box
from shapely.ops import unary_union

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'result/blender/stage44'
site = json.loads((ROOT / 'result/blender/site_geometry.json').read_text())
surfaces = json.loads((OUT / 'road-surfaces.json').read_text())
footprints = unary_union([Polygon(b['rings'][0], b['rings'][1:]).buffer(0) for b in site['buildings'] if b['rings']]).buffer(.025)
streets = ['Portsmouth Street', 'Sheffield Street', 'Houghton Street', 'Clare Market', 'John Watkins Plaza']
used = Polygon()
records = []

def polygons(shape):
    if shape.is_empty:
        return []
    if shape.geom_type == 'Polygon':
        return [shape]
    return [p for geometry in getattr(shape, 'geoms', []) for p in polygons(geometry)]

def triangles(shape):
    result = []
    for polygon in polygons(shape):
        for tri in constrained_delaunay_triangles(polygon).geoms:
            if tri.area > 1e-12:
                result.append([list(p) for p in list(tri.exterior.coords)[:3]])
    area = sum(Polygon(tri).area for tri in result)
    assert abs(area-shape.area) < 1e-6, 'Triangulation must cover the complete surface'
    return result

for street in streets:
    region = unary_union([Polygon(poly).buffer(0) for entry in surfaces if entry['street'] == street for poly in entry['polygons']])
    # The plaza's mapped pedestrian polygon records the open area, not just a route.
    if street == 'John Watkins Plaza':
        areas = [Polygon(r['geometry']['coordinates'][0]) for r in site['roads'] if r['properties'].get('name') == street and r['geometry']['type'] == 'Polygon']
        region = unary_union([region, *areas])
    region = region.difference(footprints).difference(used).buffer(0)
    used = unary_union([used, region])
    line = max([r for r in site['roads'] if r['properties'].get('name') == street and r['geometry']['type'] == 'LineString'], key=lambda r:sum(math.dist(a,b) for a,b in zip(r['geometry']['coordinates'],r['geometry']['coordinates'][1:])))
    points = line['geometry']['coordinates']; dx,dy=points[-1][0]-points[0][0],points[-1][1]-points[0][1]
    angle = math.degrees(math.atan2(dy,dx))
    local = affinity.rotate(region, -angle, origin=(0,0))
    interior = local.buffer(-.18)
    xmin,ymin,xmax,ymax = local.bounds
    length,width = (.60,.30) if street == 'Portsmouth Street' else (.90,.60)
    tiles = []
    for row in range(math.floor(ymin/width), math.ceil(ymax/width)):
        shift = length*.5*(row%2)
        for column in range(math.floor((xmin-shift)/length),math.ceil((xmax-shift)/length)):
            x,y = column*length+shift,row*width
            tile = box(x+.003,y+.003,x+length-.003,y+width-.003).intersection(interior)
            if tile.area < .003:
                continue
            tile = affinity.rotate(tile,angle,origin=(0,0))
            shade = (row*73856093 ^ column*19349663) % 5
            tiles.append({'shade':shade,'triangles':triangles(tile)})
    edge = local.difference(interior)
    records.append({'street':street,'area':region.area,'angle':angle,'tileEstimate':[length,width],'base':triangles(region),'edge':triangles(affinity.rotate(edge,angle,origin=(0,0))),'tiles':tiles})
assert used.intersection(footprints).area < 1e-6
(OUT / 'paving-plan.json').write_text(json.dumps({'records':records,'sourceObjects':[e['object'] for e in surfaces],'footprintOverlapArea':used.intersection(footprints).area,'notes':['Paving course sizes, widths and colour values estimated','Existing route widths retained; mapped plaza area used','No future Portugal Street gardens added','No additional street furniture positioned without located photographs']},separators=(',',':')))
print('PAVING_PLAN',[(r['street'],round(r['area']),len(r['tiles'])) for r in records])
