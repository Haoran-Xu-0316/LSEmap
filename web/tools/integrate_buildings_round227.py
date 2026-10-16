"""Integrate two source-paired rooms and a coordinated street contact repair.

Read the accepted226 native without overwriting it. Keep every original as an
archival source and append only independently reopened, reviewed components.
"""
from pathlib import Path
import json
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'web/tools'))
from integrate_exterior_round194 import integrate

if __name__=='__main__':
    integrate(base=ROOT/'result/blender/LSE_campus_detailed_v226.blend',
        destination=ROOT/'result/blender/LSE_campus_detailed_v227.blend',
        proof=ROOT/'result/blender/stage227',version=227,
        baseline_proof=ROOT/'result/blender/stage226',
        reports=[
            ('CKK','result/blender/ckk115-room227/audit.json','CKK115_ROOM227_study'),
            ('OLD','result/blender/old606-room227/audit.json','OLD606_ROOM227_study'),
            ('STREETS','result/blender/street-layering227/audit.json','00_SITE'),
        ],
        scope='Add independent CKK.1.15 and OLD.6.06 classroom studies from paired historical room sources. Remove coplanar asphalt under retained stone without changing stone boundaries, heights or route layout. Protect all7858 accepted objects,2068 material nodes and23 prior spaces; source gaps and current complete interiors remain unresolved.',
    )
    path=ROOT/'result/blender/stage227/building-refinement.json'
    record=json.loads(path.read_text())
    prior=json.loads((ROOT/'result/blender/stage226/building-refinement.json').read_text())
    for key in ['libraryNativeViewRouting','librarySourceArchiveScene']:
        record[key]=prior[key]
    path.write_text(json.dumps(record,indent=2)+'\n')
