"""Assemble two independently sourced room studies in separate native scenes.

Run in Blender's Text Editor. Preserve campus exterior, landscape and prior
rooms; unknown full-floor connectivity is deliberately not fabricated.
"""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'web/tools'))
from integrate_exterior_round194 import integrate

if __name__ == '__main__':
    integrate(base=ROOT / 'result/blender/LSE_campus_detailed_v199.blend',
              destination=ROOT / 'result/blender/LSE_campus_detailed_v200.blend',
              proof=ROOT / 'result/blender/stage200', version=200,
              reports=[('OLD321','result/blender/old-room200/audit.json','OLD321_ROOM200_study'),
                       ('MAR107','result/blender/mar-room200/audit.json','MAR107_ROOM200_study')],
              scope='Independent historical OLD.3.21 and MAR.1.07 room studies from paired official plans/photos. All campus exterior, earlier rooms and environment retained; no full-floor registration claimed.')
