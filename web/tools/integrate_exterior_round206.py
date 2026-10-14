"""Integrate the mapped LSE Square ground and SAW glazing corrections.

The source205 campus remains read-only. Only the exact bounded replacement
lists are archived; unrelated building surfaces and every room remain intact.
Run in Blender's Text Editor after both components pass saved-file checks.
"""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'web/tools'))
from integrate_exterior_round194 import integrate

if __name__=='__main__':
    integrate(base=ROOT/'result/blender/LSE_campus_detailed_v205.blend',
              destination=ROOT/'result/blender/LSE_campus_detailed_v206.blend',
              proof=ROOT/'result/blender/stage206',version=206,
              reports=[('LSE_SQUARE','result/blender/cbg-ground206/audit.json','00_SITE'),
                       ('SAW','result/blender/saw-exterior206/audit.json','SAW_EXTERIOR')],
              scope='Replace unfinished LSE Square road-strip/datum presentation with mapped stone paving and registered entrance joins. Improve six retained SAW entrance/roof glass objects without changing their geometry, UVs, perforated screens or interiors. Preserve all unrelated buildings, rooms and streets; no future Portugal Street pedestrianisation modeled.')
