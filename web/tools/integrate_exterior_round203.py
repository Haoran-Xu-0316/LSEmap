"""Integrate the verified LCH street-window correction into the complete campus.

CBG teaching-wing and roof reconstructions remain private components until the
whole envelope, facade modules, circulation and camera registration agree.
"""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'web/tools'))
from integrate_exterior_round194 import integrate


if __name__ == '__main__':
    integrate(base=ROOT/'result/blender/LSE_campus_detailed_v201.blend',
              destination=ROOT/'result/blender/LSE_campus_detailed_v203.blend',
              proof=ROOT/'result/blender/stage203', version=203,
              reports=[('LCH','result/blender/lch-exterior203/audit.json','LCH_EXTERIOR')],
              scope='Restore two narrow sash columns in each LCH brick field and visible downpipes. Preserve May2025 white shopfront panels, central and projecting window bays, all other buildings, rooms and environment. CBG envelope candidates excluded.')
