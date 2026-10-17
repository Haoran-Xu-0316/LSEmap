"""Assemble reviewed street geometry and an independently sourced classroom.

Run in Blender's editor. Exact source objects remain in the complete native;
only reviewed visibility replacements and the isolated new room are added.
"""
from pathlib import Path
import json
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'web/tools'))
from integrate_exterior_round194 import integrate

if __name__=='__main__':
    integrate(base=ROOT/'result/blender/LSE_campus_detailed_v233.blend',
        destination=ROOT/'result/blender/LSE_campus_detailed_v234.blend',
        proof=ROOT/'result/blender/stage234',version=234,
        baseline_proof=ROOT/'result/blender/stage233',
        reports=[
            ('STREETS','result/blender/street-ground234/audit.json','00_SITE'),
            ('CKK','result/blender/ckk110-room234/audit.json','CKK110_ROOM234_study'),
        ],
        scope='Remove proven duplicate coplanar asphalt without moving the supported road union; add an independent historical CKK.1.10 room with source seat positions. Preserve every accepted geographic building, source material and prior room. Unregistered public entry connections, floor datums, current interiors and unseen elevations remain incomplete.',
    )
    path=ROOT/'result/blender/stage234/building-refinement.json'
    record=json.loads(path.read_text())
    prior=json.loads((ROOT/'result/blender/stage233/building-refinement.json').read_text())
    for key in ['libraryNativeViewRouting','librarySourceArchiveScene']:
        record[key]=prior[key]
    path.write_text(json.dumps(record,indent=2)+'\n')
