"""Prepare clipped Parish Hall roof planes within the unchanged OSM footprint.

Dimensions are photo-based study estimates. No arguments or downloads required.
"""
from pathlib import Path
import json
import math
from shapely.geometry import Polygon, box
from shapely.ops import triangulate
ROOT=Path(__file__).resolve().parents[2]
profile=next(p for p in json.loads((ROOT/'result/blender/stage05/infill-geometry.json').read_text()) if p['code']=='PAR')
front=next(w for w in profile['walls'] if w['front'])
p,q=front['p'],front['q'];length=front['length']
u=[(q[i]-p[i])/length for i in range(2)];n=front['outward']
def local(point):
 d=[point[i]-p[i] for i in range(2)]
 return [sum(d[i]*u[i] for i in range(2)),sum(d[i]*n[i] for i in range(2))]
ring=[local(point) for point in profile['building']['rings'][0]]
polygon=Polygon(ring)
entry_start=length-4.7
entry=polygon.intersection(box(entry_start,-100,length+2,1))
main=polygon.difference(entry)
parts=[]
for shape,kind in [(main,'main'),(entry,'entry')]:
 ridge=-5.0
 for clip in [box(-100,ridge,100,100),box(-100,-100,100,ridge)]:
  piece=shape.intersection(clip)
  triangles=[list(t.exterior.coords)[:3] for t in triangulate(piece) if piece.covers(t)]
  parts.append({'kind':kind,'triangles':triangles})
assert abs(sum(Polygon(t).area for part in parts for t in part['triangles'])-polygon.area)<.001
out=ROOT/'result/blender/stage10/parish';out.mkdir(parents=True,exist_ok=True)
(out/'parish-geometry.json').write_text(json.dumps({'profile':profile,'front':front,'localRing':ring,'entryStart':entry_start,'roofParts':parts,'area':polygon.area},indent=2)+'\n')
print('PARISH_PLAN_PREPARED',polygon.area)
