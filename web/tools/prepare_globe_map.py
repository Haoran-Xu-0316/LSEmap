"""Draw the globe's original cartographic texture from public-domain Natural Earth.
Use the MachineLearning environment; the sculpture palette and heading are estimated.
"""
from pathlib import Path
import json
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'data/collections/public-realm-2026/globe/countries.geojson'
OUT = ROOT / 'result/blender/stage48'
OUT.mkdir(parents=True, exist_ok=True)
size = (4096, 2048)
image = Image.new('RGB', size, (168, 203, 218))
draw = ImageDraw.Draw(image)
palette = [(213, 195, 111), (128, 190, 159), (218, 161, 146), (161, 151, 190), (221, 173, 105), (159, 188, 152)]
features = json.loads(SOURCE.read_text())['features']

def project(point):
    longitude, latitude = point
    return ((longitude+180)/360*size[0], (90-latitude)/180*size[1])

for index, feature in enumerate(features):
    geometry = feature['geometry']
    polygons = geometry['coordinates'] if geometry['type']=='MultiPolygon' else [geometry['coordinates']]
    for polygon in polygons:
        draw.polygon([project(point) for point in polygon[0]], fill=palette[index%len(palette)], outline=(105, 126, 128), width=2)
        for hole in polygon[1:]:
            draw.polygon([project(point) for point in hole], fill=(168, 203, 218))
for longitude in range(-180,181,15):
    x = project((longitude,0))[0]
    draw.line((x,0,x,size[1]), fill=(139,175,189), width=1)
for latitude in range(-75,76,15):
    y = project((0,latitude))[1]
    draw.line((0,y,size[0],y), fill=(139,175,189), width=1)
# Labels are part of this study's new map, not a facsimile of the artwork lettering.
font = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf', 18)
occupied=[];labels=[]
# Rotate each glyph block, leaving political geography untouched. The native
# globe is inverted, so its country names must compensate independently.
for feature in sorted(features,key=lambda f:f['properties'].get('LABELRANK',10)):
    props=feature['properties'];longitude,latitude=props.get('LABEL_X'),props.get('LABEL_Y')
    if longitude is None or latitude is None or props.get('LABELRANK',10)>6:continue
    name=props.get('NAME_EN',props.get('NAME','')).upper()
    bounds=font.getbbox(name);w,h=bounds[2]-bounds[0]+6,bounds[3]-bounds[1]+6
    x,y=project((longitude,latitude));rect=(x-w/2-4,y-h/2-3,x+w/2+4,y+h/2+3)
    if any(rect[0]<r[2] and rect[2]>r[0] and rect[1]<r[3] and rect[3]>r[1] for r in occupied):continue
    label=Image.new('RGBA',(w,h));ink=ImageDraw.Draw(label)
    ink.text((3-bounds[0],3-bounds[1]),name,font=font,fill=(44,67,79,255))
    label=label.transpose(Image.Transpose.ROTATE_180)
    image.paste(label,(round(x-w/2),round(y-h/2)),label)
    occupied.append(rect);labels.append({'country':name,'orientationDegrees':180,'xy':[x,y]})
(OUT/'globe-labels.json').write_text(json.dumps({'labels':labels,'textureSize':size,'nativeGlobeInverted':True,'overlapRejected':True},indent=2)+'\n')
image.save(OUT/'globe-map.png', optimize=True)
(OUT/'map-provenance.json').write_text(json.dumps({'source':'https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_110m_admin_0_countries.geojson','license':'Natural Earth public domain','licenseUrl':'https://www.naturalearthdata.com/about/terms-of-use/','limitations':['Country palette and lettering estimated, not an exact artwork facsimile','Natural Earth boundaries are cartographic data, not the artwork original UN map']},indent=2)+'\n')
print('Globe map prepared')
