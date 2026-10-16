"""Assemble source-guided exterior,street and classroom components without altering the accepted campus."""
from pathlib import Path
import json
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'web/tools'))
from integrate_exterior_round194 import integrate

if __name__=='__main__':
    integrate(base=ROOT/'result/blender/LSE_campus_detailed_v228.blend',
        destination=ROOT/'result/blender/LSE_campus_detailed_v229.blend',
        proof=ROOT/'result/blender/stage229',version=229,
        baseline_proof=ROOT/'result/blender/stage228',
        reports=[
            ('SAL','result/blender/facade-material229/audit.json','SAL_EXTERIOR'),
            ('STREETS','result/blender/street-fixtures229/audit.json','00_SITE'),
            ('FAW','result/blender/faw102-room229/audit.json','FAW102_ROOM229_study'),
            ('SAL','result/blender/salb01-room229/audit.json','SALB01_ROOM229_study'),
        ],
        scope='Reduce unsupported intrinsic cyan in two SAL historical window batches while preserving optics and geometry. Add real shallow joints and arrises to six retained LSE Square stone surrounds without changing paving or footprints. Add independent FAW.1.02 and SAL.B.01 historical room studies. Preserve8074 accepted objects,2141 material nodes and27 prior spaces. New rooms remain outside the geographic campus; dimensions and current complete interiors remain unresolved.',
    )
    path=ROOT/'result/blender/stage229/building-refinement.json'
    record=json.loads(path.read_text())
    prior=json.loads((ROOT/'result/blender/stage228/building-refinement.json').read_text())
    for key in ['libraryNativeViewRouting','librarySourceArchiveScene']:
        record[key]=prior[key]
    path.write_text(json.dumps(record,indent=2)+'\n')
