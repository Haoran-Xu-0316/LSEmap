"""Integrate continuous footway borders while retaining every campus building."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'web/tools'))
from integrate_exterior_round194 import integrate
if __name__=='__main__':
 integrate(base=ROOT/'result/blender/LSE_campus_detailed_v214.blend',destination=ROOT/'result/blender/LSE_campus_detailed_v215.blend',proof=ROOT/'result/blender/stage215',version=215,
  reports=[('STREETS','result/blender/streets215/audit.json','00_SITE')],
  scope='Remove transverse flush bands at internal mapped footway segment joins. Retain the accepted walking footprint, route UVs, existing exterior/interior geometry, street heights and source materials. Web finishing uses lighter Houghton stone, filtered edge joints and smaller clean asphalt assets.')
