"""Assemble the three reviewed public structural corrections from222.

Only declared replacements change visibility. All source geometry, material
nodes, modifiers and the21 existing spaces remain available in the native.
"""
from pathlib import Path
import sys,json
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'web/tools'))
from integrate_exterior_round194 import integrate

if __name__=='__main__':
    integrate(base=ROOT/'result/blender/LSE_campus_detailed_v222.blend',
        destination=ROOT/'result/blender/LSE_campus_detailed_v223.blend',
        proof=ROOT/'result/blender/stage223',version=223,
        baseline_proof=ROOT/'result/blender/stage222',
        reports=[
            ('CBG','result/blender/cbg-structure223/audit.json','CBG_PUBLIC_INTERIOR_study'),
            ('MAR','result/blender/mar-structure223/audit.json','MAR_PUBLIC_INTERIOR_study'),
            ('SAW','result/blender/saw-circulation223/audit.json','SAW_PUBLIC_INTERIOR_study'),
        ],
        scope='Correct the source-supported CBG academic public stair and corridor structure, add the MAR second-floor plate with actual source voids and supports, and restore the SAW fifth/sixth-floor spiral route. Preserve every source object and21 prior room studies; unpublished upper routes and fitout remain incomplete.',
    )
    path=ROOT/'result/blender/stage223/building-refinement.json'
    record=json.loads(path.read_text())
    prior=json.loads((ROOT/'result/blender/stage222/building-refinement.json').read_text())
    for key in ['libraryNativeViewRouting','librarySourceArchiveScene']:record[key]=prior[key]
    path.write_text(json.dumps(record,indent=2)+'\n')
