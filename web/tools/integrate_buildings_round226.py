"""Assemble the source-paired PAN.2.01 independent classroom.

Protect all accepted225 geometry, materials, ownership and existing rooms.
"""
from pathlib import Path
import sys,json
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'web/tools'))
from integrate_exterior_round194 import integrate

if __name__=='__main__':
    integrate(base=ROOT/'result/blender/LSE_campus_detailed_v225.blend',
        destination=ROOT/'result/blender/LSE_campus_detailed_v226.blend',
        proof=ROOT/'result/blender/stage226',version=226,
        baseline_proof=ROOT/'result/blender/stage225',
        reports=[
            ('PAN','result/blender/pan201-room226/audit.json','PAN201_ROOM226_study'),
        ],
        scope='Add an independent PAN.2.01 collaborative classroom from a paired official plan and photograph. Preserve all7809 accepted source objects and22 prior room spaces. Local scale and concealed surfaces remain estimates; whole-building interiors are not claimed.',
    )
    path=ROOT/'result/blender/stage226/building-refinement.json'
    record=json.loads(path.read_text())
    prior=json.loads((ROOT/'result/blender/stage225/building-refinement.json').read_text())
    for key in ['libraryNativeViewRouting','librarySourceArchiveScene']:record[key]=prior[key]
    path.write_text(json.dumps(record,indent=2)+'\n')
