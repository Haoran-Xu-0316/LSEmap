"""Assemble accepted public circulation and six tree enclosures from221.

Original geometry and detached room ownership remain intact. Each public study
shares only explicitly listed original objects with the geographic campus.
"""
from pathlib import Path
import sys
import json
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'web/tools'))
from integrate_exterior_round194 import integrate

if __name__ == '__main__':
    integrate(
        base=ROOT / 'result/blender/LSE_campus_detailed_v221.blend',
        destination=ROOT / 'result/blender/LSE_campus_detailed_v222.blend',
        proof=ROOT / 'result/blender/stage222', version=222,
        baseline_proof=ROOT / 'result/blender/stage221',
        reports=[
            ('61A', 'result/blender/aldwych-registration222/audit.json', '61A_EXTERIOR'),
            ('SAL', 'result/blender/sal-public222/audit.json', 'SAL_EXTERIOR'),
            ('STREETS', 'result/blender/street-environment222/audit.json', '00_SITE'),
        ],
        scope='Add indicative2021 fourth/sixth61A floor structure and atria, connected historical SAL public circulation and six photo-supported campus tree enclosures. Preserve original objects, materials and19 existing selectable rooms. Heights, fitout and landscape construction remain estimates.',
    )
    # Routing is unchanged from221; carry its acceptance record forward so
    # later source verification does not depend on an obsolete stage number.
    proof = ROOT / 'result/blender/stage222/building-refinement.json'
    record = json.loads(proof.read_text())
    prior = json.loads((ROOT / 'result/blender/stage221/building-refinement.json').read_text())
    for key in ['libraryNativeViewRouting', 'librarySourceArchiveScene']:
        record[key] = prior[key]
    proof.write_text(json.dumps(record, indent=2) + '\n')
