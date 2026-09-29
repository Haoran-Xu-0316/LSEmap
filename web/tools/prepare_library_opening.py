"""Prepare a registered circular opening with the GIS perimeter held fixed.

Only the core position is calibrated here; the 9.8m opening radius remains an
estimate. Floor-specific non-circular guide outlines are still unresolved.
"""
from pathlib import Path
import json
from shapely.geometry import Point,Polygon
from shapely.ops import triangulate,unary_union
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'result/blender/stage38'
registration=json.loads((OUT/'library-plan-registration.json').read_text())
lrb=next(b for b in json.loads((ROOT/'result/blender/site_geometry.json').read_text())['buildings'] if b['code']=='LRB')
centre=registration['meanGuideCentre']
outline=Polygon(lrb['rings'][0],lrb['rings'][1:])
hole=Point(*centre).buffer(9.8,quad_segs=32)
assert outline.contains(hole)
domain=outline.difference(hole)
triangles=[t for t in triangulate(domain) if domain.covers(t)]
assert domain.symmetric_difference(unary_union(triangles)).area<1e-7
(OUT/'registered-opening.json').write_text(json.dumps({'centre':centre,'radius':9.8,'triangles':[list(t.exterior.coords)[:3] for t in triangles],'surfaceArea':domain.area,'perimeterUnchanged':True,'scope':'Core registration only; existing circular opening approximation retained'},indent=2)+'\n')
print('REGISTERED_OPENING',len(triangles),'triangles; complete coverage; GIS perimeter unchanged')
