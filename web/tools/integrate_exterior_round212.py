"""Integrate three independently verified public-realm and circulation components."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'web/tools'))
from integrate_exterior_round194 import integrate

if __name__=='__main__':
    integrate(base=ROOT/'result/blender/LSE_campus_detailed_v211.blend',
              destination=ROOT/'result/blender/LSE_campus_detailed_v212.blend',
              proof=ROOT/'result/blender/stage212',version=212,
              reports=[('COURTS','result/blender/park-courts212/audit.json','03_PUBLIC_REALM'),
                       ('OLD_PUBLIC','result/blender/old-public212/audit.json','OLD_MAIN_FOYER174'),
                       ('CHURCH','result/blender/strand-church212/audit.json','01_CITY_CONTEXT_estimated_heights')],
              scope='Restore the omitted full hardcourt facility with mapped sports layouts; connect the registered historical OLD foyer to its source-supported central/east public corridor; add the omitted mapped St Clement Danes landmark with registered west tower and bounded estimated silhouette. Preserve every original building, path, fence and independent classroom; no complete current interiors claim.')
