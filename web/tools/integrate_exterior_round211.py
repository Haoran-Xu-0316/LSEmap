"""Integrate bounded pedestrian repairs and the source-mapped public park fence."""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'web/tools'))
from integrate_exterior_round194 import integrate

if __name__ == '__main__':
    integrate(base=ROOT/'result/blender/LSE_campus_detailed_v210.blend',
              destination=ROOT/'result/blender/LSE_campus_detailed_v211.blend',
              proof=ROOT/'result/blender/stage211', version=211,
              reports=[('STREETS', 'result/blender/street-surfaces211/audit.json', '00_SITE'),
                       ('PARK', 'result/blender/park-boundary211/audit.json', '03_PUBLIC_REALM')],
              scope='Restore mapped Strand and Sheffield pedestrian-area gaps, remove asphalt intrusion and retain existing detailed paving. Add the explicitly mapped public Lincoln Inn Fields metal fence with eight source-width gate openings. Preserve all buildings and eighteen independent rooms. Tile courses, stone colours and fence sections remain estimates.')
