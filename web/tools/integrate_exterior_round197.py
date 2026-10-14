"""Assemble the accepted STC facade and two isolated historical room studies.

Open in Blender's Text Editor. New rooms remain in separate review scenes,
so their local coordinates cannot intersect the public campus overview.
"""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'web/tools'))
from integrate_exterior_round194 import integrate

if __name__ == '__main__':
    integrate(
        base=ROOT / 'result/blender/LSE_campus_detailed_v196.blend',
        destination=ROOT / 'result/blender/LSE_campus_detailed_v197.blend',
        proof=ROOT / 'result/blender/stage197', version=197,
        reports=[('STC','result/blender/stc-exterior197/audit.json','STC_EXTERIOR'),
                 ('FAW401','result/blender/faw-room197/audit.json','FAW401_ROOM197_study'),
                 ('CLM502','result/blender/clm-room197/audit.json','CLM502_ROOM197_study')],
        scope='Photo-guided STC facade finishes and independently isolated FAW.4.01 / CLM.5.02 historical room studies; campus geometry retained',
    )
