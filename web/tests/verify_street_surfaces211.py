"""Check serialized native paving coverage against the accepted mapped plan."""
from pathlib import Path
import json
from shapely.geometry import Polygon
from shapely.ops import unary_union
p=Path(__file__).resolve().parents[2]/'result/blender/street-surfaces211'
a=json.loads((p/'saved-ground-audit.json').read_text());plan=json.loads((p/'surface-plan.json').read_text());checks=[]
for area in plan['areas']:
 expected=unary_union([Polygon(t) for t in area['boundary']]);obj=next(o for o in a['objects'] if o['name']=='SITE211_'+area['name']+'_joint_bed')
 actual=unary_union([Polygon([obj['vertices'][i][:2] for i in face]) for face in obj['faces']])
 assert expected.difference(actual.buffer(.0002)).is_empty
 assert actual.difference(expected.buffer(.0002)).is_empty
 assert expected.symmetric_difference(actual).area<.05
 checks.append(dict(name=area['name'],actualPavingBoundaryAreaM2=actual.area,expectedAreaM2=expected.area,symmetricDifferenceAreaM2=expected.symmetric_difference(actual).area))
record=dict(savedModelSha256=a['sourceModelSha256'],nativeMeshCoverageVerified=True,coordinateToleranceMetres=.0002,regions=checks)
(p/'coverage-verification.json').write_text(json.dumps(record,indent=2)+'\n');print(record)
