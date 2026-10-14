"""Compare saved native church coverage with its source-mapped ground boundary."""
from pathlib import Path
import json
import math
from shapely.geometry import Polygon
from shapely.ops import unary_union
ROOT=Path(__file__).resolve().parents[2]
path=ROOT/'result/blender/stage212/public-realm-verification.json'
record=json.loads(path.read_text())
plan=json.loads((ROOT/'result/blender/strand-church212/geometry-plan.json').read_text())
c,s=math.cos(plan['angle']),math.sin(plan['angle']);cx,cy=plan['centre']
source=Polygon([(cx+c*x-s*y,cy+s*x+c*y) for x,y in plan['footprint']])
actual=unary_union([Polygon(t) for t in record['churchGroundFaces']])
assert actual.symmetric_difference(source).area<.01
assert actual.difference(source.buffer(.0002)).is_empty
assert source.difference(actual.buffer(.0002)).is_empty
record['churchMappedFootprintSymmetricDifferenceM2']=actual.symmetric_difference(source).area
record['churchMappedFootprintVerified']=True
path.write_text(json.dumps(record,indent=2)+'\n')
print('CHURCH212_FOOTPRINT_VERIFIED',actual.area)
