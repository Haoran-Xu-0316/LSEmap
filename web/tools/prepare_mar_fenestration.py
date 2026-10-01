"""Prepare photo-proportioned MAR academic-wing apertures in the existing Python environment."""
from pathlib import Path
import json
from shapely.geometry import Polygon,box
from shapely import constrained_delaunay_triangles
r=Path(__file__).resolve().parents[2];D=json.loads((r/'result/blender/stage02/detail_geometry.json').read_text())
targets={'MAR_rear_way/1376078546_0','MAR_rear_way/1376078546_4','MAR_rear_way/1376078546_5','MAR_rear_way/1376078545_1','MAR_rear_way/1376078545_4'}
(r/'result/blender/stage75').mkdir(parents=True,exist_ok=True)
rows=[]
for s in D['surfaces']:
 if s['name'] not in targets:continue
 s=dict(s);s['oldOpenings']=s['openings'];domain=Polygon(s['outline']);new=[]
 for a,b,c,d in s['openings']:
  x,z=(a+c)/2,(b+d)/2;w=1.86;h=3.14;new.append([x-w/2,z-h/2,x+w/2,z+h/2])
 for rect in new:domain=domain.difference(box(*rect))
 geoms=[domain] if domain.geom_type=='Polygon' else list(domain.geoms)
 tris=constrained_delaunay_triangles(domain)
 assert abs(sum(t.area for t in tris.geoms)-domain.area)<1e-6
 s['openings']=new;s['triangles']=[list(t.exterior.coords)[:3] for t in tris.geoms];s['rings']=[list(g.exterior.coords)[:-1] for g in geoms]+[list(h.coords)[:-1] for g in geoms for h in g.interiors];rows.append(s)
assert len(rows)==5
(r/'result/blender/stage75/mar-fenestration.json').write_text(json.dumps({'surfaces':rows,'mar_center':D['mar_center']},indent=2))
print('PREPARED',sum(len(s['openings']) for s in rows),'window apertures')
