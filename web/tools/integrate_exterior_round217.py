"""Integrate registered Marshall ground structure and verified exterior finishes.

Run in Blender's Text Editor. The accepted216 native is immutable; independent
components replace only their named objects. Full save/reopen verification is
performed by the common integrator before browser export.
"""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'web/tools'))
from integrate_exterior_round194 import integrate

if __name__ == '__main__':
    integrate(
        base=ROOT / 'result/blender/LSE_campus_detailed_v216.blend',
        destination=ROOT / 'result/blender/LSE_campus_detailed_v217.blend',
        proof=ROOT / 'result/blender/stage217', version=217,
        baseline_proof=ROOT / 'result/blender/stage216',
        reports=[
            ('COW', 'result/blender/cow-exterior217/audit.json', 'COW_EXTERIOR'),
            ('OLD', 'result/blender/old-glazing217/audit.json', 'OLD_EXTERIOR'),
            ('MAR', 'result/blender/mar-registration217/audit.json', 'MAR_PUBLIC_INTERIOR_study'),
            ('STREETS', 'result/blender/street-environment217/audit.json', '00_SITE'),
        ],
        scope='Register Marshall ground entrances, nine supports and retained main stair against built2022 source plans; coordinate dependent slabs and guards. Refine Cowdray brick, stone, joinery and slate finishes without new geometry. Neutralize Old Building entrance glass while retaining blue frames. Remove only mapped underground footway remnants from the surface network. Preserve independent room studies and unrelated exteriors.',
    )
