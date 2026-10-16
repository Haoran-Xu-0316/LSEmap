"""Integrate three independently verified street and classroom components."""
from pathlib import Path
import json
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'web/tools'))
from integrate_exterior_round194 import integrate

if __name__=='__main__':
    integrate(base=ROOT/'result/blender/LSE_campus_detailed_v229.blend',
        destination=ROOT/'result/blender/LSE_campus_detailed_v230.blend',
        proof=ROOT/'result/blender/stage230',version=230,
        baseline_proof=ROOT/'result/blender/stage229',
        reports=[
            ('STREETS','result/blender/streets230/audit.json','03_PUBLIC_REALM'),
            ('CLM','result/blender/clm102-room230/audit.json','CLM102_ROOM230_study'),
            ('KSW','result/blender/ksw102-room230/audit.json','KSW102_ROOM230_study'),
        ],
        scope='Remove one complete obsolete bench assembly with verified positive-volume stone-surround interference; preserve all six unaffected benches and existing paving. Add independent historical CLM.1.02 and KSW.1.02 classrooms. Preserve8179 accepted objects,2184 material nodes and29 prior spaces. Room dimensions and current full interiors remain unresolved.',
    )
    path=ROOT/'result/blender/stage230/building-refinement.json'
    record=json.loads(path.read_text())
    prior=json.loads((ROOT/'result/blender/stage229/building-refinement.json').read_text())
    for key in ['libraryNativeViewRouting','librarySourceArchiveScene']:
        record[key]=prior[key]
    path.write_text(json.dumps(record,indent=2)+'\n')
