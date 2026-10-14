"""Assemble accepted canopy, context finishes and ground orientation in one source.

Run in Blender's Text Editor. No buildings or independent rooms are remodelled;
all old geometry and bindings remain archived and the saved source is reopened.
"""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'web/tools'))
from integrate_exterior_round194 import integrate

if __name__=='__main__':
    integrate(base=ROOT/'result/blender/LSE_campus_detailed_v198.blend',
              destination=ROOT/'result/blender/LSE_campus_detailed_v199.blend',
              proof=ROOT/'result/blender/stage199',version=199,
              reports=[('CONTEXT','result/blender/context-palette199/audit.json','01_CITY_CONTEXT_estimated_heights'),
                       ('CANOPY','result/blender/landscape199/audit.json','03_PUBLIC_REALM'),
                       ('GROUND','result/blender/ground-orientation199/audit.json','00_SITE')],
              scope='Mapped finishes on24 existing context buildings and510 of522 existing crown envelopes; outward ground shells and grass sheets; protected LSE buildings, rooms, routes and earlier refined crowns retained')
