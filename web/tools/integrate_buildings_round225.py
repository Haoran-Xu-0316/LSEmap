"""Assemble the reviewed Peacock street frontage and isolated KSW.2.12 room.

The current224 campus remains read-only. All originals and earlier room studies
are retained; only declared Peacock framing replacements change visibility.
"""
from pathlib import Path
import sys,json
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'web/tools'))
from integrate_exterior_round194 import integrate

if __name__=='__main__':
    integrate(base=ROOT/'result/blender/LSE_campus_detailed_v224.blend',
        destination=ROOT/'result/blender/LSE_campus_detailed_v225.blend',
        proof=ROOT/'result/blender/stage225',version=225,
        baseline_proof=ROOT/'result/blender/stage224',
        reports=[
            ('PEA','result/blender/pea-exterior225/audit.json','PEA_EXTERIOR'),
            ('KSW','result/blender/ksw212-room225/audit.json','KSW212_ROOM225_study'),
        ],
        scope='Restore the photo-supported Peacock six-leaf entrance and shallow street roof frame. Add an independent KSW.2.12 collaborative-room sample from paired official plan and photo. Preserve all7763 source objects and21 prior spaces; dimensions and current complete interiors remain unverified.',
    )
    path=ROOT/'result/blender/stage225/building-refinement.json'
    record=json.loads(path.read_text())
    prior=json.loads((ROOT/'result/blender/stage224/building-refinement.json').read_text())
    for key in ['libraryNativeViewRouting','librarySourceArchiveScene']:record[key]=prior[key]
    path.write_text(json.dumps(record,indent=2)+'\n')
