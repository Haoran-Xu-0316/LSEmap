"""Append the paired-source Hong Kong Theatre as an isolated room scene.

The accepted219 exterior corrections and every prior room remain unchanged.
Historical seating symbols do not establish a current hire capacity or a fully
registered building floor. This fixed-config integration writes one new native.
"""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'web/tools'))
from integrate_exterior_round194 import integrate

if __name__ == '__main__':
    integrate(
        base=ROOT / 'result/blender/LSE_campus_detailed_v219.blend',
        destination=ROOT / 'result/blender/LSE_campus_detailed_v220.blend',
        proof=ROOT / 'result/blender/stage220', version=220,
        baseline_proof=ROOT / 'result/blender/stage219',
        reports=[('CLM', 'result/blender/clm-hongkong220/audit.json', 'CLMG02_ROOM220_study')],
        scope='Add an isolated historical Hong Kong Theatre room from the official paired plan and interior photograph, retaining source-guided seating banks, stage, wood-panelled teaching wall and visible equipment. Preserve all prior campus geometry, material nodes, room assets and roads; do not infer an unseen second level or current seating capacity.',
    )
