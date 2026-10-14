"""Integrate source-based Peacock auditorium and Portsmouth entrance corrections.

Read-only source206; preserve every original mesh and room. Changes are bounded
by each saved component's exact replacement list. Run in Blender's Text Editor.
"""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'web/tools'))
from integrate_exterior_round194 import integrate

if __name__=='__main__':
    integrate(base=ROOT/'result/blender/LSE_campus_detailed_v206.blend',
              destination=ROOT/'result/blender/LSE_campus_detailed_v207.blend',
              proof=ROOT/'result/blender/stage207',version=207,
              reports=[('PEA_INTERIOR','result/blender/pea-interior207/audit.json','PEA_PUBLIC_INTERIOR_study'),
                       ('POR','result/blender/por-exterior207/audit.json','POR_EXTERIOR')],
              scope='Reconstruct the historical Peacock auditorium from archived plan curves/section anchors, with estimated individual seating and Circle width; correct three photo-supported Portsmouth entrance components. Preserve unrelated buildings, every other room, all roads and original source objects.')
