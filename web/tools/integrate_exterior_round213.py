"""Integrate street finish corrections and the completed library guard repair."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'web/tools'))
from integrate_exterior_round194 import integrate
if __name__=='__main__':
 integrate(base=ROOT/'result/blender/LSE_campus_detailed_v212.blend',destination=ROOT/'result/blender/LSE_campus_detailed_v213.blend',proof=ROOT/'result/blender/stage213',version=213,
  reports=[('STREETS','result/blender/streets213/audit.json','00_SITE'),('LRB_CIRCULATION','result/blender/library-circulation213/audit.json','LRB_PUBLIC_INTERIOR168_study')],
  scope='Correct explicit asphalt on previously omitted named footways, align slab courses with mapped routes, retain flush pedestrian edges and remove crossing/high-paving duplicates. Open six existing library ramp/gallery guard connections. Preserve every building exterior and independent room; OLD historical registration remains unresolved rather than guessed.')
