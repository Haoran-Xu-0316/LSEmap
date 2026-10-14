"""Integrate independent building corrections into the current complete campus.

Read-only source207. Retain all original objects and each room's scene ownership.
Run in Blender's Text Editor; no external command-line configuration is required.
"""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'web/tools'))
from integrate_exterior_round194 import integrate

if __name__=='__main__':
    integrate(base=ROOT/'result/blender/LSE_campus_detailed_v207.blend',
              destination=ROOT/'result/blender/LSE_campus_detailed_v208.blend',
              proof=ROOT/'result/blender/stage208',version=208,
              reports=[('61A','result/blender/61a-exterior208/audit.json','61A_EXTERIOR'),
                       ('CON','result/blender/con-exterior208/audit.json','CON_EXTERIOR'),
                       ('OCS','result/blender/ocs-exterior208/audit.json','OCS_EXTERIOR'),
                       ('LRB_INTERIOR','result/blender/lrb-interior208/audit.json','LRB_PUBLIC_INTERIOR168_study')],
              scope='Retain253 registered Aldwych window shells while reducing cyan tint and allowing finite transparency only on10 backed dormers; correct Connaught entrance granite and Old Curiosity Shop restoration colours; add four guide-supported library ground-floor public service counters. Preserve all other building geometry, every independent room and existing roads;61A footprint and full current interiors remain unverified.')
