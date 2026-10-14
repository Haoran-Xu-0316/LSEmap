"""Integrate verified LRB/CLM exteriors and the registered OLD foyer finishes.

Run in Blender's Text Editor. One complete source is retained until the new
model is reopened and its original geometry, UVs and ownership are verified.
"""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'web/tools'))
from integrate_exterior_round194 import integrate

if __name__ == '__main__':
    integrate(
        base=ROOT / 'result/blender/LSE_campus_detailed_v195.blend',
        destination=ROOT / 'result/blender/LSE_campus_detailed_v196.blend',
        proof=ROOT / 'result/blender/stage196', version=196,
        reports=[('LRB','result/blender/lrb-exterior196/audit.json','LRB_EXTERIOR'),
                 ('CLM','result/blender/clm-exterior196/audit.json','CLM_EXTERIOR'),
                 ('OLD_FOYER','result/blender/old-foyer196/audit.json','OLD_MAIN_FOYER174')],
        scope='Photo-guided LRB/CLM whole-facade finishes and historical OLD foyer floor, entrance mat and disc lights; unrelated room layouts retained',
    )
