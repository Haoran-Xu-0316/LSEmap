"""Prepare photo-guided SAW roof openings and fitted photovoltaic modules.
No arguments: run this file in the project's existing Python environment.
"""
from pathlib import Path
import json,math
from shapely.geometry import Polygon
from shapely.ops import triangulate
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'result/blender/stage83';OUT.mkdir(parents=True,exist_ok=True)
d=json.loads((ROOT/'result/blender/stage02/detail_geometry.json').read_text())
site=json.loads((ROOT/'result/blender/site_geometry.json').read_text())
r=next(b for b in site['buildings']if b['code']=='SAW')['rings'][0]
a,b=r[12],r[7];length=math.dist(a,b);u=[(b[i]-a[i])/length for i in range(2)]
# Toward the western roof field. Official terrace area guides the estimated strip.
west=[-u[1],u[0]];width=115/length
upper=[a,b,[b[i]+west[i]*width for i in range(2)],[a[i]+west[i]*width for i in range(2)]]
green=[r[12],r[7],r[10]]
holes=Polygon(upper).union(Polygon(green))
roof=[];candidates=[]
def cross(a,b):return [a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]
def dot(a,b):return sum(x*y for x,y in zip(a,b))
for index,tri in enumerate(d['saw_roof_triangles']):
 p,q,t=tri;normal=cross([q[i]-p[i]for i in range(3)],[t[i]-p[i]for i in range(3)])
 norm=math.sqrt(dot(normal,normal));normal=[v/norm for v in normal]
 if normal[2]<0:normal=[-v for v in normal]
 def height(x,y):return p[2]-(normal[0]*(x-p[0])+normal[1]*(y-p[1]))/normal[2]
 keep=Polygon([(v[0],v[1])for v in tri]).difference(holes)
 pieces=list(keep.geoms)if keep.geom_type=='MultiPolygon' else [keep]
 for piece in pieces:
  if piece.is_empty:continue
  for shape in triangulate(piece):
   if not piece.covers(shape):continue
   roof.append([[x,y,height(x,y)]for x,y in list(shape.exterior.coords)[:3]])
 # Work in the actual sloping plane, not its horizontal projection.
 edge=[q[i]-p[i]for i in range(3)];size=math.sqrt(dot(edge,edge));axis=[v/size for v in edge];side=cross(normal,axis)
 def local(v):
  delta=[v[i]-p[i]for i in range(3)]
  return (dot(delta,axis),dot(delta,side))
 poly=Polygon([local(v)for v in tri])
 def world(x,y):return [p[i]+axis[i]*x+side[i]*y+normal[i]*.075 for i in range(3)]
 # Subtract terrace footprints from candidates in the horizontal plane.
 minx,miny,maxx,maxy=poly.bounds
 for j in range(math.ceil((maxy-miny)/1.68)):
  for k in range(math.ceil((maxx-minx)/1.08)):
   x=minx+k*1.08+.04;y=miny+j*1.68+.04
   points=[world(xx,yy)for xx,yy in [(x,y),(x+1,y),(x+1,y+1.6),(x,y+1.6)]]
   module=Polygon([(v[0],v[1])for v in points])
   if poly.buffer(-.12).covers(Polygon([(x,y),(x+1,y),(x+1,y+1.6),(x,y+1.6)])) and keep.covers(module):
    centre=[sum(v[i]for v in points)/4 for i in range(3)]
    # Prioritise the west slope; count and layout are visual estimates.
    candidates.append({'corners':points,'normal':normal,'triangle':index,'priority':centre[0]})
assert len(candidates)>=159,len(candidates)
panels=sorted(candidates,key=lambda p:p['priority'])[:159]
plan={'upperTerrace':upper,'upperLevel':21.9,'upperArea':Polygon(upper).area,'greenRoof':green,'greenLevel':18.0,
 'roofTriangles':roof,'sourceRoofTriangles':d['saw_roof_triangles'],'panels':panels,'panelArea':len(panels)*1.6,
 'chimneys':[{'centre':[r[2][0]+1.2,r[2][1]+1.0],'angle':math.atan2(u[1],u[0]),'size':[2.4,1.1],'base':21.9,'top':28.9},
 {'centre':[r[4][0]+1.3,r[4][1]-.8],'angle':math.atan2(u[1],u[0]),'size':[2.4,1.1],'base':21.9,'top':28.9}],
 'limits':['Coordinates and terrace/chimney positions estimated from the archived footprint and LSE roof photograph','115m2 terrace and 254m2 PV are historical LSE published areas; new geometry does not prove 2026 measured dimensions','159 module count, spacing and cell subdivisions are modelling estimates, not an installed equipment inventory','Existing brick folds and facade outlines retained; roof outline and current interiors remain under review']}
(OUT/'roof-plan.json').write_text(json.dumps(plan,indent=2)+'\n')
print('SAW_ROOF_PLAN',len(roof),len(panels),plan['panelArea'],plan['upperArea'])
