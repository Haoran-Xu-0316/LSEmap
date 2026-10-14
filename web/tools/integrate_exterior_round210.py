"""Integrate the corrected library roof and independently sourced CON.7.05 room.

Fixed Blender Text Editor configuration. Retain all original objects and existing
room identities; the new committee room has no invented campus-floor connection.
"""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'web/tools'))
from integrate_exterior_round194 import integrate

if __name__=='__main__':
    integrate(base=ROOT/'result/blender/LSE_campus_detailed_v209.blend',
              destination=ROOT/'result/blender/LSE_campus_detailed_v210.blend',
              proof=ROOT/'result/blender/stage210',version=210,
              reports=[('LRB','result/blender/lrb-exterior210/audit.json','LRB_EXTERIOR'),
                       ('CON705','result/blender/con-room210/audit.json','CON705_ROOM210_study')],
              scope='Correct the library south setback roof and corresponding envelope against the2025 existing-plan boundary; add supported upper-roof safety handrails without guessing lower-roof rail heights. Add an independent18-seat historical CON.7.05 committee-room sample from paired official plan/photo. Retain every previous room, unrelated building and mapped ground surface; current complete fitouts remain unverified.')
