"""Prepare roof regions from the 2025 plan with one metric rigid registration.

The CAD drawing remains private. Published geometry uses manually read outline
coordinates; the GIS exterior and registered atrium centre remain fixed.
"""
from pathlib import Path
import hashlib,json,math
import numpy as np
from shapely.geometry import Polygon,Point
from shapely.geometry.polygon import orient
from shapely import constrained_delaunay_triangles
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'result/blender/stage109';OUT.mkdir(parents=True,exist_ok=True)
site=json.loads((ROOT/'result/blender/site_geometry.json').read_text())
ring=next(b for b in site['buildings']if b['code']=='LRB')['rings'][0]
cap=json.loads((ROOT/'result/blender/stage108/library-dome-dimensions-audit.json').read_text())
centre=np.array(cap['centre']);pixel_centre=np.array([993.0,629.0])
# 1888px-wide rendering: proposed drawing's 10m scale bar spans about 225px.
# Align the long Carey Street direction while retaining metric scale and centre.
direction=np.array(ring[7])-ring[4]
angle=math.atan2(direction[1],direction[0])-math.atan2(52,926)
rotation=np.array([[math.cos(angle),math.sin(angle)],[math.sin(angle),-math.cos(angle)]])
def project(p):return ((np.array(p)-pixel_centre)@rotation/22.5+centre).tolist()
# Raised main roof boundary, read from the existing survey. Its lower perimeter
# terrace, steps and local jogs are distinct from the GIS street facade outline.
outline=[[253,1180],[753,166],[1547,118],[1565,380],[1470,394],
         [1485,1055],[1339,1058],[1344,1132],[1293,1163],[1215,1157],
         [1199,1193],[731,1220],[725,1189],[567,1183],[565,1175]]
outer=Polygon(ring);survey=Polygon([project(p)for p in outline])
assert survey.is_valid
raised=survey.intersection(outer.buffer(-.18,join_style='mitre'))
assert raised.geom_type=='Polygon'
raised=orient(raised,sign=1.0)
hole=Point(centre).buffer(6.89,quad_segs=32)
assert raised.contains(hole.buffer(.5))
regions={'upper':raised.difference(hole),'lower':outer.difference(raised)}
def triangles(poly):
 result=[]
 for triangle in constrained_delaunay_triangles(poly).geoms:
  coords=list(triangle.exterior.coords)[:3]
  if sum(a[0]*b[1]-b[0]*a[1]for a,b in zip(coords,coords[1:]+coords[:1]))<0:coords.reverse()
  result.append(coords)
 assert abs(sum(Polygon(t).area for t in result)-poly.area)<1e-5
 return result
source=ROOT/'data/collections/library-roof-2025/existing-roof-plan.pdf'
report={'version':109,'centre':centre.tolist(),'metresPerPixel':1/22.5,'rotationRadians':angle,
        'sourcePixelCentre':pixel_centre.tolist(),'sourceRaisedOutlinePixels':outline,
        'raisedBoundary':list(raised.exterior.coords)[:-1],
        'upperTriangles':triangles(regions['upper']),'lowerTriangles':triangles(regions['lower']),
        'outerArea':outer.area,'holeArea':hole.area,'raisedArea':raised.area,
        'upperArea':regions['upper'].area,'lowerArea':regions['lower'].area,
        'sourceSha256':hashlib.sha256(source.read_bytes()).hexdigest(),
        'groundDatum':19.76,'lowerRoofHeight':40.0-19.76,'upperRoofHeight':43.75-19.76,
        'plant':{'room': [project(p)for p in [[1191,553],[1325,550],[1341,958],[1209,962]]],
                 'heatPumpCentres':[project([x,1067])for x in [779,909,1041]],
                 'unitDimensions':[2.2,5.2,2.5]},
        'registrationChecks':[{'pixel':p,'world':project(p),'gisIndex':i,'residualMetres':float(np.linalg.norm(np.array(project(p))-ring[i]))}for p,i in [([78,1255],0),([706,75],4),([1632,23],7)]],
        'limits':['Outline reads and source-to-GIS placement are approximate; perimeter is clipped to retained GIS','Existing centre retained; registration is not a survey of site coordinates','Plant room footprint simplified; other room and AHU shapes need subsequent review','Heat pump layout follows May 2025 approved proposal, not an as-built survey']}
assert abs(report['upperArea']+report['lowerArea']+report['holeArea']-outer.area)<1e-5
(OUT/'roof-survey-geometry.json').write_text(json.dumps(report,indent=2)+'\n')
print('LIBRARY_SURVEY_REGIONS',round(raised.area,2),round(regions['lower'].area,2),flush=True)
