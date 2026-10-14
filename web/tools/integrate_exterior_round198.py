"""Integrate the continuous road network while preserving all campus buildings.

Run in Blender's Text Editor. The new complete source is reopened and checked
before the previous complete model may be removed during release cleanup.
"""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'web/tools'))
from integrate_exterior_round194 import integrate

if __name__=='__main__':
    integrate(base=ROOT/'result/blender/LSE_campus_detailed_v197.blend',
              destination=ROOT/'result/blender/LSE_campus_detailed_v198.blend',
              proof=ROOT/'result/blender/stage198',version=198,
              reports=[('ROADS','result/blender/street-network198/audit.json','00_SITE')],
              scope='Remove duplicate coplanar asphalt surfaces across the existing street network; retain every building, room, estimated road boundary and23 existing holes')
