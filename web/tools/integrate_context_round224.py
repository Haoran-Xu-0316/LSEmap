"""Assemble the reviewed RCS frontage inside the shared geographic city layer.

The accepted223 native is read-only. Original objects and all21 room studies
remain intact; only the eleven explicitly replaced proxy objects are hidden.
"""
from pathlib import Path
import sys,json
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'web/tools'))
from integrate_exterior_round194 import integrate

if __name__=='__main__':
    integrate(base=ROOT/'result/blender/LSE_campus_detailed_v223.blend',
        destination=ROOT/'result/blender/LSE_campus_detailed_v224.blend',
        proof=ROOT/'result/blender/stage224',version=224,
        baseline_proof=ROOT/'result/blender/stage223',
        reports=[('RCS_CONTEXT','result/blender/rcs-context224/audit.json','01_CITY_CONTEXT_estimated_heights')],
        scope='Replace the RCS Lincoln\'s Inn Fields gray street frontage and false high portico projection with photo-supported stone facade,70 window openings and six-column portico. Preserve all LSE exterior/interior assets and estimated unseen RCS rear volumes; source photographs remain private.',
    )
    path=ROOT/'result/blender/stage224/building-refinement.json'
    record=json.loads(path.read_text())
    prior=json.loads((ROOT/'result/blender/stage223/building-refinement.json').read_text())
    for key in ['libraryNativeViewRouting','librarySourceArchiveScene']:record[key]=prior[key]
    path.write_text(json.dumps(record,indent=2)+'\n')
