"""Integrate coordinated SAW floors and corrected at-grade street context."""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'web/tools'))
from integrate_exterior_round194 import integrate

if __name__ == '__main__':
    integrate(
        base=ROOT / 'result/blender/LSE_campus_detailed_v215.blend',
        destination=ROOT / 'result/blender/LSE_campus_detailed_v216.blend',
        proof=ROOT / 'result/blender/stage216', version=216,
        baseline_proof=ROOT / 'result/blender/stage215',
        reports=[
            ('STREETS', 'result/blender/street-environment216/audit.json', '00_SITE'),
            ('CONTEXT', 'result/blender/context-datum216/audit.json', '00_SITE'),
            ('SAW', 'result/blender/saw-floors216/audit.json', 'SAW_PUBLIC_INTERIOR_study'),
        ],
        scope='Correct SAW upper-floor profiles and coordinate existing stair landings from the2014 guide. Remove only the wrongly surfaced Strand Underpass while retaining mapped at-grade roads and footways. Extend the unchanged flat presentation datum beneath existing surface footways. Preserve source geometry, materials and independent room studies.',
    )
