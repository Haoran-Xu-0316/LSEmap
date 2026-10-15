"""Independently compare61A's historical floor perimeter with mapped ownership.

The drawn office boundary and mapped roof boundary are different observations.
A three-corner fit remains a hypothesis until independent perimeter controls
agree. This fixed-config workflow never changes native geometry.
"""
from pathlib import Path
import json
import hashlib
import numpy as np
from shapely.geometry import Polygon, Point
from shapely.ops import unary_union
from PIL import Image, ImageDraw

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'result/blender/61a-registration218'
PDF=ROOT/'data/documents/61aldwych_brochure_2021.pdf'
SOURCE_SHA='edd2358acd6b36e4587b533a527bc1869393012fc8bc4849e3125f95a3821f10'
# Upper-floor source boundaries are indicative. These corresponding wall
# corners establish a hypothesis, not an assertion of surveyed dimensions.
CONTROLS=[
 {'id':'Kingsway-north-party-wall','pdf':[62.2363,342.951],'world':[-76.5901484669,-60.25681352]},
 {'id':'Kingsway-south-street-turn','pdf':[431.5763,342.694],'world':[-50.0310112466,-124.208298214]},
 {'id':'rear-north-party-wall','pdf':[59.7103,176.717],'world':[-47.052185064,-47.840768613]},
]


def similarity(source,target):
    a=np.asarray(source);b=np.asarray(target)
    ac=a.mean(0);bc=b.mean(0);left,singular,right=np.linalg.svd((a-ac).T@(b-bc))
    rotation=left@right
    assert np.linalg.det(rotation)>.9999
    scale=singular.sum()/np.square(a-ac).sum()
    return dict(scale=float(scale),rotation=rotation.tolist(),translation=(bc-scale*ac@rotation).tolist())


def transform(points,fit):
    p=np.asarray(points)*[1,-1]
    return fit['scale']*p@np.asarray(fit['rotation'])+np.asarray(fit['translation'])


def source_vectors():
    """Read the actual historic floor fills, without tracing a raster photo."""
    import pdfplumber
    rows=[]
    with pdfplumber.open(PDF) as document:
        page=document.pages[8]
        for index,curve in enumerate(page.curves):
            points=curve.get('pts',[])
            in_floor=(40<curve['x0']<560 and 150<curve['top']<355 and curve['bottom']<365)
            if len(points)<3 or not in_floor:
                continue
            area=Polygon(points).area
            if area<400:
                continue
            rows.append(dict(index=index,bbox=[curve['x0'],curve['top'],curve['x1'],curve['bottom']],
                             area=area,fill=curve['fill'],fillColor=curve['non_stroking_color'],
                             stroke=curve['stroke'],strokeColor=curve['stroking_color'],points=points))
    rows.sort(key=lambda row:row['area'],reverse=True)
    (OUT/'fourth-floor-vector-candidates.json').write_text(json.dumps(rows,indent=2)+'\n')
    return rows


def prepare():
    OUT.mkdir(exist_ok=True)
    assert hashlib.sha256(PDF.read_bytes()).hexdigest()==SOURCE_SHA
    rows=source_vectors()
    source=np.array([row['pdf'] for row in CONTROLS])*[1,-1]
    target=np.array([row['world'] for row in CONTROLS])
    fit=similarity(source,target)
    fitted=transform([row['pdf'] for row in CONTROLS],fit)
    site=json.loads((ROOT/'result/blender/site_geometry.json').read_text())
    parcels=[row for row in site['buildings'] if row['id'] in {'way/181939023','way/181939031'}]
    mapped=unary_union([Polygon(row['rings'][0]) for row in parcels])
    office=Polygon(transform(rows[0]['points'],fit))
    front=transform([[513.7233,230.657]],fit)[0]
    hypothesis=dict(sourcePdf=PDF.relative_to(ROOT).as_posix(),sourceSha256=SOURCE_SHA,
      sourcePublication='May2021',sourcePage=9,transform=fit,
      controls=[dict(row,residualMetres=float(np.linalg.norm(fitted[i]-target[i]))) for i,row in enumerate(CONTROLS)],
      sourceFloorFillBoundaryWorld=list(office.exterior.coords),mappedBoundaryWorld=list(mapped.exterior.coords),
      diagnostic=dict(sourceAreaM2=office.area,mappedAreaM2=mapped.area,
         sourceOutsideMappedM2=office.difference(mapped).area,mappedOutsideSourceM2=mapped.difference(office).area,
         sourceFrontTipWorld=front.tolist(),frontTipDistanceToMappedBoundaryM=Point(front).distance(mapped.boundary)),
      status='Hypothesis under independent perimeter review; no native changes',
      sourceReference='https://s3-eu-west-1.amazonaws.com/agents-society-assets-files/ae303325518c4f9634961cdca4a7cfdc-61%20Aldwych_A4%20Brochure_2021_.pdf',
      currentStatusCheck={'checked':'2026-10-16','url':'https://www.lse.ac.uk/news/feixmerlin-and-alison-brooks-architects-selected-to-redevelop-61-aldwych',
        'publicationDate':'2025-10-23','scope':'Announced competition-winning proposals; estimated2028 completion subject to planning, not a completed current interior.'},
      limits='The indicative floor fill underlays some core/common-space categories and is not the published net lettable area. Mapped roof ownership is not a measured upper-floor boundary. Do not warp either outline to force agreement.')
    (OUT/'registration-hypothesis.json').write_text(json.dumps(hypothesis,indent=2)+'\n')
    image=Image.new('RGB',(1200,1100),'#f7f5f0');draw=ImageDraw.Draw(image)
    def screen(points):return [(80+(x+86)*10,1030-(y+150)*8.8) for x,y in points]
    for row in site['roads']:
        coords=row.get('geometry',{}).get('coordinates',[])
        if row.get('geometry',{}).get('type')=='LineString' and coords:
            draw.line(screen(coords),fill='#d7d4cc',width=7)
    for row in site['buildings']:
        p=Polygon(row['rings'][0])
        if not p.intersects(Polygon([(-85,-150),(10,-150),(10,-35),(-85,-35)])):continue
        draw.polygon(screen(p.exterior.coords),fill='#d7d9d8',outline='#8b9294',width=1)
        if row.get('code'):
            c=p.centroid;draw.text(screen([(c.x,c.y)])[0],str(row['code']),fill='#3a454b')
    draw.polygon(screen(office.exterior.coords),fill='#c7e0cd',outline='#447c58',width=3)
    draw.line(screen(mapped.exterior.coords),fill='#282f34',width=3)
    for row in CONTROLS:
        x,y=screen([row['world']])[0];draw.ellipse((x-5,y-5,x+5,y+5),fill='#bc584b');draw.text((x+7,y-12),row['id'],fill='#853f36')
    draw.text((40,20),'61A independent registration hypothesis: green2021 floor fill / black archived roof map',fill='#26373e')
    draw.text((40,40),'Three source wall controls fitted; remaining contour is not forced to the map. Private modeling evidence.',fill='#4d5657')
    image.save(OUT/'registration-hypothesis.png')
    print('61A218_HYPOTHESIS',hypothesis['diagnostic'],flush=True)


if __name__=='__main__':prepare()
