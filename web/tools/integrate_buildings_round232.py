"""Integrate the current library entry, continuous park crowns and independent classrooms."""
from pathlib import Path
import json
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'web/tools'))
from integrate_exterior_round194 import integrate

if __name__=='__main__':
    integrate(base=ROOT/'result/blender/LSE_campus_detailed_v231.blend',
        destination=ROOT/'result/blender/LSE_campus_detailed_v232.blend',
        proof=ROOT/'result/blender/stage232',version=232,
        baseline_proof=ROOT/'result/blender/stage231',
        reports=[
            ('STREETS','result/blender/street-environment232/audit.json','03_PUBLIC_REALM'),
            ('LRB','result/blender/street-environment232/audit-candidate.json','LRB_EXTERIOR'),
            ('OLD','result/blender/old127-room232/audit.json','OLD127_ROOM232_study'),
            ('FAW','result/blender/faw103-room232/audit.json','FAW103_ROOM232_study'),
        ],
        scope='Repair the library entrance as a real local opening and floor-connected landing with three low steps. Replace only fifty mapped park crowns with continuous closed forms. Add source-based independent OLD.1.27 and FAW.1.03 classrooms. Preserve8383 accepted objects,2256 material nodes and32 prior spaces. Dimensions and current layouts remain unverified; comprehensive interiors are incomplete.',
    )
    path=ROOT/'result/blender/stage232/building-refinement.json'
    record=json.loads(path.read_text())
    prior=json.loads((ROOT/'result/blender/stage231/building-refinement.json').read_text())
    for key in ['libraryNativeViewRouting','librarySourceArchiveScene']:
        record[key]=prior[key]
    path.write_text(json.dumps(record,indent=2)+'\n')
