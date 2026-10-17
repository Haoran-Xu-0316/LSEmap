"""Assemble reviewed library glazing, park facilities and public circulation.

Run in Blender's editor. Preserve accepted source objects and existing rooms;
only exact reviewed replacement sources change visibility in the new native.
"""
from pathlib import Path
import json
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'web/tools'))
from integrate_exterior_round194 import integrate

if __name__=='__main__':
    integrate(base=ROOT/'result/blender/LSE_campus_detailed_v232.blend',
        destination=ROOT/'result/blender/LSE_campus_detailed_v233.blend',
        proof=ROOT/'result/blender/stage233',version=233,
        baseline_proof=ROOT/'result/blender/stage232',
        reports=[
            ('LRB','result/blender/lrb-glazing233/audit.json','LRB_EXTERIOR'),
            ('PARK','result/blender/park-public233/audit.json','03_PUBLIC_REALM'),
            ('OLD','result/blender/old-exterior233/audit.json','OLD_EXTERIOR'),
            ('SAW','result/blender/saw-circulation233/audit.json','SAW_STRUCTURE173_registered_main_circulation'),
        ],
        scope='Replace opaque library window proxies with finite-transmission dielectric finishes; restore the photo-supported Old Building upper grille band while retaining mansard and lower facade; restore source-identified park bandstand and one-storey cafe at mapped footprints; coordinate source-constrained estimated SAW public stair runs and slab openings against fixed lifts. Preserve8502 source objects,2299 material nodes and34 independent spaces. Unseen elevations,current room layouts and full interiors remain incomplete.',
    )
    path=ROOT/'result/blender/stage233/building-refinement.json'
    record=json.loads(path.read_text())
    prior=json.loads((ROOT/'result/blender/stage232/building-refinement.json').read_text())
    for key in ['libraryNativeViewRouting','librarySourceArchiveScene']:
        record[key]=prior[key]
    path.write_text(json.dumps(record,indent=2)+'\n')
