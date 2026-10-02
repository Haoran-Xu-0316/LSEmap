"""Prepare OLD roof zones from the 2024 roof plan and AA/BB/DD sections.
Run in the existing MachineLearning environment. Pixel outline reads and GIS
registration are estimates. Labelled AOD levels are retained explicitly.
"""
from pathlib import Path
import hashlib,json
from shapely.geometry import Polygon,box,Point
from shapely.geometry.polygon import orient
from shapely import constrained_delaunay_triangles
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'result/blender/stage113';OUT.mkdir(parents=True,exist_ok=True)
frame=json.loads((ROOT/'result/blender/stage52/old-houghton-audit.json').read_text())
ring=next(b for b in json.loads((ROOT/'result/blender/site_geometry.json').read_text())['buildings']if b['code']=='OLD')['rings'][0]
o,r,n=[frame[k]for k in ['origin','right','outward']]
def local(p):return [sum((p[i]-o[i])*axis[i]for i in range(2))for axis in [r,n]]
# Uniform 15px/m scale from the plan's 15m scale bar. The street-end anchor is
# approximate because a roof outline is set back from the street-level GIS.
def project(p):return [-34.50+(p[0]-371)/15,(p[1]-1055)/15]
def region(points):return Polygon([project(p)for p in points])
outer=Polygon([local(p)for p in ring]);assert outer.is_valid
west=region([[372,653],[511,653],[511,638],[674,638],[674,774],[623,774],[623,1004],[372,1004]])
central=region([[680,461],[851,461],[851,621],[861,621],[861,775],[735,775],[735,823],[623,823],[623,774],[674,774],[674,638],[620,638],[620,579],[680,579]])
court=region([[631,827],[1020,827],[1020,1004],[631,1004]])
skylight=region([[713,573],[827,573],[827,675],[713,675]])
barrel=region([[1020,603],[1145,603],[1145,802],[1020,802]])
# Keep the rebuilt street frontage and its continuous mansard free of a flat
# backing plane. The rest of the roof is partitioned, never layered on a slab.
entry_end=-18.295483589
mansard_void=box(-34.50,-3.49,entry_end,0.20)
front_east=box(2.53,-8,24.0,.20)
front_middle=box(entry_end,-1.1,2.53,.20)
regions=[];remaining=outer
for name,shape,height in [('mansard-void',mansard_void,None),('south-court',court,13.5),
                         ('front-east',front_east,20.1),('front-middle',front_middle,20.1),
                         ('west',west,27.14),('central',central,28.44)]:
    clipped=remaining.intersection(shape);remaining=remaining.difference(shape)
    if height is not None:regions.append((name,clipped,height))
regions.append(('perimeter',remaining,23.79))
assert central.contains(skylight)
roof_holes=skylight.union(barrel)
def triangles(shape):
    result=[]
    for t in constrained_delaunay_triangles(shape).geoms:
        pts=list(t.exterior.coords)[:3]
        if sum(a[0]*b[1]-b[0]*a[1]for a,b in zip(pts,pts[1:]+pts[:1]))<0:pts.reverse()
        result.append(pts)
    assert abs(sum(Polygon(t).area for t in result)-shape.area)<1e-6
    return result
def polys(shape):return list(shape.geoms)if hasattr(shape,'geoms')else[shape]
records=[]
for name,shape,height in regions:
    shaped=shape.difference(roof_holes)
    records.append({'name':name,'height':height,'area':shaped.area,'triangles':triangles(shaped),
                    'boundaries':[list(orient(p,sign=1).exterior.coords)[:-1]for p in polys(shape)if not p.is_empty]})
assert abs(sum(x['area']for x in records)+outer.intersection(mansard_void).area+outer.intersection(roof_holes).area-outer.area)<1e-5
risers=[]
for record,(_,shape,height) in zip(records,regions):
    for boundary in record['boundaries']:
        for a,b in zip(boundary,boundary[1:]+boundary[:1]):
            dx,dy=b[0]-a[0],b[1]-a[1];length=(dx*dx+dy*dy)**.5
            if length<.05:continue
            probe=Point((a[0]+b[0])/2+dy/length*.05,(a[1]+b[1])/2-dx/length*.05)
            if mansard_void.contains(probe):continue
            adjacent=next((h for _,p,h in regions if p.covers(probe)),24.30)
            if height>adjacent+.05:
                risers.append({'a':a,'b':b,'low':adjacent,'high':height,'zone':record['name']})
plant_centres=[project(p)for p in [[551,811],[629,689],[799,720]]]
# The first two units share one stepped acoustic enclosure. ASHP3 has its own.
screens=[{'name':'west','height':31.44,'base':27.14,'outline':[project(p)for p in [[513,861],[598,861],[598,772],[678,772],[678,637],[590,637],[590,740],[513,740]]]},
         {'name':'central','height':32.05,'base':28.44,'outline':[project(p)for p in [[734,772],[862,772],[862,683],[734,683]]]}]
source=ROOT/'data/collections/old-roof-2024/proposed-roof.pdf'
report={'version':113,'baseline':112,'origin':o,'right':r,'outward':n,'metresPerPixel':1/15,
        'sourcePixelAnchor':[371,1055],'localAnchor':[-34.5,0],
        'outerArea':outer.area,'mansardVoidArea':outer.intersection(mansard_void).area,
        'skylightArea':skylight.area,'barrelArea':barrel.area,'roofRegions':records,'risers':risers,
        'skylight':{'outline':list(skylight.exterior.coords)[:-1],'base':28.44,'ridge':31.44},
        'barrel':{'outline':list(barrel.exterior.coords)[:-1],'base':23.79,'rise':2.0},
        'plant':{'centres':plant_centres,'bases':[28.34,28.34,28.54],'directions':['longitudinal','longitudinal','transverse'],
                 'dimensions':[[2.2,4.4,2.0],[2.2,4.4,2.0],[4.4,2.2,2.0]],'screens':screens},
        'room':{'outline':[project(p)for p in [[704,486],[810,486],[810,565],[704,565]]],'base':28.44,'height':3.55},
        'source':'data/collections/old-roof-2024/proposed-roof.pdf','sourceSha256':hashlib.sha256(source.read_bytes()).hexdigest(),
        'sections':['section-aa.pdf','section-bb.pdf','section-dd.pdf'],
        'groundDatum':18.1,'labelledLevels':{'L-05':38.2,'L-06':41.89,'L-RF1':45.24,'L-RF2':49.54},
        'limits':['Planning proposal, not a 2026 as-built survey',
                  'Roof zones and their GIS registration are manually read estimates',
                  'Central roof spring, low courtyard roof, barrel curvature, room and plant sizes unlabelled and estimated',
                  'Equipment fan count follows plan symbols; mechanisms and installed model specifications not verified',
                  'North/west/east historic facade rows and complete interiors remain unresolved']}
(OUT/'old-roof-survey-geometry.json').write_text(json.dumps(report,indent=2)+'\n')
print('OLD_ROOF_REGIONS_PREPARED',len(records),round(outer.area,2),flush=True)
