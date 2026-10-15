"""Integrate photo-guided OLD doorway profiles and open-mesh entrance artwork.

The accepted217 campus remains immutable. SAW circulation, street boundaries
and61A registration hypotheses are review evidence only and are not integrated.
"""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'web/tools'))
from integrate_exterior_round194 import integrate

if __name__ == '__main__':
    integrate(
        base=ROOT / 'result/blender/LSE_campus_detailed_v217.blend',
        destination=ROOT / 'result/blender/LSE_campus_detailed_v218.blend',
        proof=ROOT / 'result/blender/stage218', version=218,
        baseline_proof=ROOT / 'result/blender/stage217',
        reports=[
            ('OLD', 'result/blender/old-portal218/audit.json', 'OLD_EXTERIOR'),
            ('OLD', 'result/blender/old-artwork218/audit.json', 'OLD_EXTERIOR'),
        ],
        scope='Differentiate fixed portal framing and fine paired-leaf seams while coordinating retained glass and handles. Replace four Final Sale artwork batches with six photo-guided shallow mesh figures, drapery, varied goods and baskets; preserve all other buildings, roads and independent rooms. SAW, streets and61A audits do not authorize geometry changes.',
    )
