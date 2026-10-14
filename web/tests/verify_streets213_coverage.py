"""Compare independently read saved street mesh coverage with the prepared plan."""
from pathlib import Path
import json
from shapely.geometry import Polygon
from shapely.ops import unary_union
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'result/blender/stage213'
plan=json.loads((ROOT/'result/blender/streets213/plan.json').read_text());saved=json.loads((OUT/'saved-streets.json').read_text())
expected=unary_union([Polygon(t) for r in plan['regions'] for t in r['body']+r['edge']])
actual=unary_union([Polygon([p[:2] for p in f['points']]) for o in saved['objects'] for f in o['faces']])
assert actual.difference(expected.buffer(.0001)).area<.00001
assert expected.difference(actual.buffer(.0001)).area<.00001
error=expected.symmetric_difference(actual).area
assert error<expected.length*.0001,error
area=sum(Polygon([p[:2] for p in f['points']]).area for o in saved['objects'] for f in o['faces'])
assert area-actual.area<expected.length*.00005,'Duplicated coplanar street faces'
record=dict(version=213,nativeMeshCoverageVerified=True,expectedAreaM2=expected.area,savedAreaM2=actual.area,symmetricDifferenceM2=error,duplicateAreaM2=area-actual.area,boundaryToleranceMetres=.0001,sourceWays=plan['sourceWays'],namedWays=plan['namedWays'])
(OUT/'street-coverage.json').write_text(json.dumps(record,indent=2)+'\n');print('STREETS213_COVERAGE',record)
