"""Assemble the reviewed KGS cupola shading and LSE Square understory.

Run in Blender's editor. Source meshes, materials, rooms and ownership remain
in the full native; only the two exact superseded batches change visibility.
"""
from pathlib import Path
import json
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'web/tools'))
from integrate_exterior_round194 import integrate

if __name__=='__main__':
    integrate(base=ROOT/'result/blender/LSE_campus_detailed_v236.blend',
        destination=ROOT/'result/blender/LSE_campus_detailed_v237.blend',
        proof=ROOT/'result/blender/stage237',version=237,
        baseline_proof=ROOT/'result/blender/stage236',
        reports=[('KGS','result/blender/kgs-surface237/audit.json','KGS_EXTERIOR'),
                 ('STREETS','result/blender/street-environment237/audit.json','00_SITE')],
        scope='Smooth only cupola shell normals and restore photo-supported low planting inside six existing LSE Square tree pools. Retain all accepted source objects and35room studies. Full current interiors, every room and unseen elevations remain incomplete.',
    )
    path=ROOT/'result/blender/stage237/building-refinement.json'
    record=json.loads(path.read_text())
    prior=json.loads((ROOT/'result/blender/stage236/building-refinement.json').read_text())
    for key in ['libraryNativeViewRouting','librarySourceArchiveScene']:
        record[key]=prior[key]
    path.write_text(json.dumps(record,indent=2)+'\n')
