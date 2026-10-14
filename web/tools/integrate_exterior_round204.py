"""Integrate the verified51L glazing finish, retaining every campus structure.

CBG's registered whole-building assembly stays private while podium and upper
circulation interfaces are incomplete. Run in Blender's Text Editor.
"""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'web/tools'))
from integrate_exterior_round194 import integrate


if __name__=='__main__':
    integrate(base=ROOT/'result/blender/LSE_campus_detailed_v203.blend',
              destination=ROOT/'result/blender/LSE_campus_detailed_v204.blend',
              proof=ROOT/'result/blender/stage204',version=204,
              reports=[('51L','result/blender/51l-exterior204/audit.json','51L_EXTERIOR')],
              scope='Replace six opaque51L glazing proxies with restrained neutral dielectric glass; preserve existing101pane shapes, UVs, all other buildings, every room and environment. No unsupported full interior or CBG assembly publication.')
