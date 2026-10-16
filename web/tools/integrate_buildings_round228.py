"""Assemble two paired historical classroom studies without altering the accepted campus."""
from pathlib import Path
import json
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'web/tools'))
from integrate_exterior_round194 import integrate

if __name__=='__main__':
    integrate(base=ROOT/'result/blender/LSE_campus_detailed_v227.blend',
        destination=ROOT/'result/blender/LSE_campus_detailed_v228.blend',
        proof=ROOT/'result/blender/stage228',version=228,
        baseline_proof=ROOT/'result/blender/stage227',
        reports=[
            ('CLM','result/blender/clmg03-room228/audit.json','CLMG03_ROOM228_study'),
            ('MAR','result/blender/mar108-room228/audit.json','MAR108_ROOM228_study'),
        ],
        scope='Add independent CLM.G.03 and MAR.1.08 historical classroom studies from paired source diagrams and photographs. Preserve all7970 accepted objects,2106 material nodes and25 prior spaces. New samples remain outside the geographic campus; dimensions are estimates and current complete interiors remain unresolved.',
    )
    path=ROOT/'result/blender/stage228/building-refinement.json'
    record=json.loads(path.read_text())
    prior=json.loads((ROOT/'result/blender/stage227/building-refinement.json').read_text())
    for key in ['libraryNativeViewRouting','librarySourceArchiveScene']:
        record[key]=prior[key]
    path.write_text(json.dumps(record,indent=2)+'\n')
