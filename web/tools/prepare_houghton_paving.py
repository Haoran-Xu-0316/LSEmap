"""Prepare photo-guided Houghton Street setts with preserved tree openings.
Use the existing MachineLearning Python environment. Paver dimensions estimated.
"""
from pathlib import Path
import json,math
from shapely.geometry import Polygon,Point,box
from shapely.ops import unary_union
from shapely import affinity,constrained_delaunay_triangles
ROOT=Path(__file__).resolve().parents[2]
plan=json.loads((ROOT/'result/blender/stage47/street-plan.json').read_text())
record=next(r for r in plan['records']if r['street']=='Houghton Street')
angle=record['angle']
region=unary_union([Polygon(t)for t in record['base']])
local=affinity.rotate(region,-angle,origin=(0,0)).buffer(-.19)
openings=unary_union([affinity.rotate(Point(o['xy']).buffer(.70),-angle,origin=(0,0))for o in plan['objects']if o['kind']=='tree'])
local=local.difference(openings)
xmin,ymin,xmax,ymax=local.bounds
tiles=[]
for row in range(math.floor(ymin/.15),math.ceil(ymax/.15)):
    shift=.15*(row%2)
    for column in range(math.floor((xmin-shift)/.30),math.ceil((xmax-shift)/.30)):
        x=column*.30+shift;y=row*.15
        stone=box(x+.002,y+.002,x+.298,y+.148).intersection(local)
        if stone.area<.0005:continue
        stone=affinity.rotate(stone,angle,origin=(0,0))
        triangles=[list(t.exterior.coords)[:3]for t in constrained_delaunay_triangles(stone).geoms if t.area>.000001]
        tiles.append({'top':triangles,'shade':(row*73856093^column*19349663)%5})
record.update(tiles=tiles,stoneDimensions=[.30,.15],scope='Small rectangular grey pavers from user Houghton Street photograph; dimensions estimated, not surveyed')
(ROOT/'result/blender/stage48/houghton-plan.json').write_text(json.dumps(record,separators=(',',':')))
print('Houghton pavers',len(tiles))
