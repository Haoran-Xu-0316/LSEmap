"""Integrate the verified OLD Clare Market portal while retaining all campus work.

Run in Blender's Text Editor. The CBG structural audit is evidence only; its
unregistered roof candidate is excluded from this complete native revision.
"""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'web/tools'))
from integrate_exterior_round194 import integrate

if __name__ == '__main__':
    integrate(base=ROOT / 'result/blender/LSE_campus_detailed_v200.blend',
              destination=ROOT / 'result/blender/LSE_campus_detailed_v201.blend',
              proof=ROOT / 'result/blender/stage201', version=201,
              reports=[('OLD','result/blender/old-exterior201/audit.json','OLD_EXTERIOR')],
              scope='Photographed broad recessed blue OLD Clare Market portal, corresponding joinery/glass/signs/pulls; all ordinary bays, Houghton arch, other buildings, rooms and environment retained. CBG grid audit does not alter geometry.')
