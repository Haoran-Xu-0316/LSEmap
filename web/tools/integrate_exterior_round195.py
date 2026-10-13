"""Integrate independently verified KSW and COL exterior components.

Run in Blender's Text Editor. One retained complete source feeds one new model;
shared integration verifies preserved objects and reopens the resulting file.
"""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'web/tools'))
from integrate_exterior_round194 import integrate

if __name__ == '__main__':
    integrate(
        base=ROOT / 'result/blender/LSE_campus_detailed_v194.blend',
        destination=ROOT / 'result/blender/LSE_campus_detailed_v195.blend',
        proof=ROOT / 'result/blender/stage195', version=195,
        reports=[('KSW','result/blender/ksw-exterior195/audit.json','KSW_EXTERIOR'),
                 ('COL','result/blender/col-exterior195/building-refinement.json','COL_EXTERIOR')],
        scope='Photo-guided KSW and COL exterior refinements; unrelated rooms and surroundings retained',
    )
