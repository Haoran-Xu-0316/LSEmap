"""Prepare a valid library roof inset, retaining the native circular lightwell.
Uses the user's MachineLearning environment; no arguments or interactive CLI.
"""
from pathlib import Path
import json
from shapely.geometry import Polygon,MultiPoint
from shapely import constrained_delaunay_triangles
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'result/blender/stage60'
ring=next(b for b in json.loads((ROOT/'result/blender/site_geometry.json').read_text())['buildings']if b['code']=='LRB')['rings'][0]
outer=Polygon(ring);hole=MultiPoint(json.loads((OUT/'roof-void.json').read_text())).convex_hull
inner=outer.buffer(-3.0,join_style='mitre');assert inner.geom_type=='Polygon' and inner.is_valid and inner.contains(hole)
def triangles(region,height):
 result=[]
 for triangle in constrained_delaunay_triangles(region).geoms:
  points=list(triangle.exterior.coords)[:3]
  if sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(points,points[1:]+points[:1]))<0:points.reverse()
  result.append([[x,y,height(x,y)]for x,y in points])
 assert abs(sum(Polygon([(p[0],p[1])for p in t]).area for t in result)-region.area)<.00001
 return result
from shapely.geometry import Point
band=outer.difference(inner);deck=inner.difference(hole)
result={'roofTriangles':triangles(band,lambda x,y:23+2.8*min(1,Point(x,y).distance(outer.boundary)/3)), 'deckTriangles':triangles(deck,lambda x,y:25.8),'holeArea':hole.area,'bandArea':band.area,'deckArea':deck.area,'outerArea':outer.area,'innerRing':list(inner.exterior.coords)[:-1]}
(OUT/'roof-geometry.json').write_text(json.dumps(result,indent=2)+'\n');print('LIBRARY_ROOF_REGIONS',len(result['roofTriangles']),len(result['deckTriangles']))
