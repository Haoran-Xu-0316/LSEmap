"""Integrate verified footway and building components into the complete campus.

Fixed Blender Text Editor configuration. Keep all source objects and independent
room ownership, archiving only the explicitly superseded ground and facade batches.
"""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'web/tools'))
from integrate_exterior_round194 import integrate

if __name__ == '__main__':
    integrate(base=ROOT/'result/blender/LSE_campus_detailed_v208.blend',
              destination=ROOT/'result/blender/LSE_campus_detailed_v209.blend',
              proof=ROOT/'result/blender/stage209', version=209,
              reports=[('MAR', 'result/blender/mar-exterior209/audit.json', 'MAR_EXTERIOR'),
                       ('OLD', 'result/blender/old-exterior209/audit.json', 'OLD_EXTERIOR'),
                       ('CKK_INTERIOR', 'result/blender/ckk-interior209/audit.json', 'CKK_PUBLIC_INTERIOR_study'),
                       ('PEDESTRIAN_SURFACES', 'result/blender/pedestrian-surfaces209/audit.json', '00_SITE')],
              scope='Recover mapped park footways and their archived asphalt finishes without changing routes or approximate widths. Retain original geometry while neutralizing seven MAR glass batches and restoring continuous metric OLD mansard brick UVs. Add the missing CKK atrium oak return wall and two galleries in its independent public-interior study. Other buildings and every independent room remain unchanged; complete current interiors and a campus survey remain unfinished.')
