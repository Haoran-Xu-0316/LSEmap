"""Assemble the reviewed curved CLM lettering into the complete campus."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "web/tools"))
sys.dont_write_bytecode = True
from integrate_exterior_round194 import integrate

if __name__ == "__main__":
    integrate(
        base=ROOT / "result/blender/LSE_campus_detailed_v239.blend",
        destination=ROOT / "result/blender/LSE_campus_detailed_v241.blend",
        proof=ROOT / "result/blender/stage241",
        version=241,
        baseline_proof=ROOT / "result/blender/stage239",
        reports=[
            ("CLM", "result/blender/clm-inscription241/audit.json", "CLM_EXTERIOR")
        ],
        scope="Conform the retained Clement House school-name glyphs to the existing curved frieze. Preserve every original object and material, room, glass surface and other building. Complete current building interiors remain unfinished.",
    )
    path = ROOT / "result/blender/stage241/building-refinement.json"
    record = json.loads(path.read_text())
    prior = json.loads(
        (ROOT / "result/blender/stage239/building-refinement.json").read_text()
    )
    for key in ["libraryNativeViewRouting", "librarySourceArchiveScene"]:
        record[key] = prior[key]
    path.write_text(json.dumps(record, indent=2) + "\n")
