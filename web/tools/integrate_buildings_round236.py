"""Assemble the reviewed Clare Market entrance continuity repair.

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
    integrate(base=ROOT/'result/blender/LSE_campus_detailed_v234.blend',
        destination=ROOT/'result/blender/LSE_campus_detailed_v236.blend',
        proof=ROOT/'result/blender/stage236',version=236,
        baseline_proof=ROOT/'result/blender/stage234',
        reports=[('OLD','result/blender/street-public236/audit.json','OLD_EXTERIOR')],
        scope='Restore a supported Clare Market entry landing and two handrail feet without changing door, street or stair levels. Retain all accepted source objects and35room studies. Full current interiors, every room and unseen elevations remain incomplete.',
    )
    path=ROOT/'result/blender/stage236/building-refinement.json'
    record=json.loads(path.read_text())
    prior=json.loads((ROOT/'result/blender/stage234/building-refinement.json').read_text())
    for key in ['libraryNativeViewRouting','librarySourceArchiveScene']:
        record[key]=prior[key]
    path.write_text(json.dumps(record,indent=2)+'\n')
