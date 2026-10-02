"""Reject any roof array crossing the skylight, building edge or plant platform."""
from pathlib import Path
import json,math
from shapely.geometry import Polygon,Point
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'result/blender/stage109'
p=json.loads((OUT/'roof-survey-geometry.json').read_text())
roof=Polygon(p['raisedBoundary']).difference(Point(p['centre']).buffer(7.3,quad_segs=32))
plant=Polygon(p['plant']['room']).buffer(.3)
# Unit enclosure clearance protects the new platform from obsolete PV arrays.
for centre in p['plant']['heatPumpCentres']:plant=plant.union(Point(centre).buffer(4))
a=p['rotationRadians'];u=(math.cos(a),math.sin(a));v=(math.sin(a),-math.cos(a))
valid=[]
for item in json.loads((OUT/'pv-candidates.json').read_text()):
 cx,cy=item['centre'];w,d=item['dimensions']
 polygon=Polygon([(cx+u[0]*x+v[0]*y,cy+u[1]*x+v[1]*y)for x,y in [(-w/2,-d/2),(w/2,-d/2),(w/2,d/2),(-w/2,d/2)]])
 if roof.contains(polygon)and not plant.intersects(polygon):valid.append(item)
(OUT/'pv-validated.json').write_text(json.dumps(valid,indent=2)+'\n')
print('LIBRARY_PV_ARRAYS_VALIDATED',len(valid))
