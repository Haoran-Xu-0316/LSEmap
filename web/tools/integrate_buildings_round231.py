"""Integrate source-backed plaza fixtures and independent historical room studies."""
from pathlib import Path
import json
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'web/tools'))
from integrate_exterior_round194 import integrate

if __name__=='__main__':
    integrate(base=ROOT/'result/blender/LSE_campus_detailed_v230.blend',
        destination=ROOT/'result/blender/LSE_campus_detailed_v231.blend',
        proof=ROOT/'result/blender/stage231',version=231,
        baseline_proof=ROOT/'result/blender/stage230',
        reports=[
            ('STREETS','result/blender/plaza-environment231/audit.json','03_PUBLIC_REALM'),
            ('OLD','result/blender/old126-room231/audit.json','OLD126_ROOM231_study'),
            ('CON','result/blender/con704-room231/audit.json','CON704_ROOM231_study'),
        ],
        scope='Restore four source-backed Watkins concrete tree containers at retained tree positions and within original grate footprints. Preserve other furniture,paving and planting. Add an independent OLD.1.26 classroom and rebuild the existing CON.7.04 default presentation without duplicate registration. Preserve8283 accepted objects,2220 material nodes and31 prior spaces. Dimensions,current layouts,unseen exteriors and comprehensive interiors remain unresolved.',
    )
    path=ROOT/'result/blender/stage231/building-refinement.json'
    record=json.loads(path.read_text())
    prior=json.loads((ROOT/'result/blender/stage230/building-refinement.json').read_text())
    for key in ['libraryNativeViewRouting','librarySourceArchiveScene']:
        record[key]=prior[key]
    path.write_text(json.dumps(record,indent=2)+'\n')
