"""Measure the real decoded asphalt/stone contact, before and after replacement."""
from pathlib import Path
import json
from shapely.geometry import Polygon,shape
from shapely.ops import unary_union
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'result/blender/stage227/browser'
version=json.loads((ROOT/'web/public/models/catalogue.json').read_text())['version']
phase='before'if version=='226'else'after'
assert version in ['226','227']
source=json.loads((ROOT/'result/blender/street-layering227/geometric-decision.json').read_text())
decoded=json.loads((OUT/f'street-decoded-{phase}.json').read_text())
assert decoded['version']==version and decoded['realViewerAndDracoAssets']and not decoded['errors']
def union(faces):
 polygons=[Polygon([(p[0],p[1])for p in face])for face in faces]
 return unary_union([p for p in polygons if p.is_valid and p.area>1e-12])
mask=shape(source['maskGeometry']).buffer(.002,join_style=2)
asphalt=union(decoded['triangles']['asphalt']).intersection(mask)
stone=union(decoded['triangles']['stone']).intersection(mask)
overlap=asphalt.intersection(stone)
result=dict(phase=phase,version=version,sourceModelSha256=decoded['sourceModelSha256'],realViewerAndDracoAssets=True,asphaltFaces=len(decoded['triangles']['asphalt']),stoneFaces=len(decoded['triangles']['stone']),decodedCoplanarOverlapM2=overlap.area,repairGuardMetres=source['quantizationClearanceM'])
(OUT/f'street-depth-{phase}.json').write_text(json.dumps(result,indent=2)+'\n')
if phase=='before':assert overlap.area>20,result
else:assert overlap.area<1e-7,result
print('STREET_DEPTH_VERIFIED',result)
