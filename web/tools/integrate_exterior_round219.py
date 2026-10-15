"""Integrate supported CKK and Kingsway facade finish corrections.

The accepted218 campus is read-only. Component copies preserve source meshes,
UVs and optics; LRB's review does not authorize a geometry or finish change.
"""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'web/tools'))
from integrate_exterior_round194 import integrate

if __name__ == '__main__':
    integrate(
        base=ROOT / 'result/blender/LSE_campus_detailed_v218.blend',
        destination=ROOT / 'result/blender/LSE_campus_detailed_v219.blend',
        proof=ROOT / 'result/blender/stage219', version=219,
        baseline_proof=ROOT / 'result/blender/stage218',
        reports=[
            ('CKK', 'result/blender/ckk-exterior219/audit.json', 'CKK_EXTERIOR'),
            ('KSW', 'result/blender/ksw-exterior219/audit.json', 'KSW_EXTERIOR'),
        ],
        scope='Neutralize photograph-supported inherent glazing casts while retaining linear luminance and optical parameters. Differentiate CKK graphite painted frames. Preserve geometry, all interior studies and roads; no fabricated transparency or unobserved room enclosure.',
    )
