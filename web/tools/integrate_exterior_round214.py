"""Integrate the photographed CLM transom while retaining the complete campus."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'web/tools'))
from integrate_exterior_round194 import integrate
if __name__=='__main__':
 integrate(base=ROOT/'result/blender/LSE_campus_detailed_v213.blend',destination=ROOT/'result/blender/LSE_campus_detailed_v214.blend',proof=ROOT/'result/blender/stage214',version=214,
  reports=[('CLM','result/blender/clm-exterior214/audit.json','CLM_EXTERIOR')],
  scope='Restore the photographed CLM left portal transom with coordinated window/stone and bounded dark backing. Keep the opposite portal and all other exterior, street and independent room geometry; MAR dedicated public-study export ownership is repaired separately, without removing geographic upper floors. SAL side massing remains unresolved.')
