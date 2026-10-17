"""Assemble the reviewed five Clare Market reliefs into the full campus."""

from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "web/tools"))
from integrate_exterior_round194 import integrate

if __name__ == "__main__":
    integrate(
        base=ROOT / "result/blender/LSE_campus_detailed_v238.blend",
        destination=ROOT / "result/blender/LSE_campus_detailed_v239.blend",
        proof=ROOT / "result/blender/stage239",
        version=239,
        baseline_proof=ROOT / "result/blender/stage238",
        reports=[("OLD", "result/blender/old-clare239/audit.json", "OLD_EXTERIOR")],
        scope="Refine five photographed Clare Market relief poses with continuous shallow bodies, curved limbs and joined necks. Preserve every original mesh, material node, window, backing panel, entrance, room and other building. Whole-campus current interiors remain incomplete.",
    )
    path = ROOT / "result/blender/stage239/building-refinement.json"
    record = json.loads(path.read_text())
    prior = json.loads(
        (ROOT / "result/blender/stage238/building-refinement.json").read_text()
    )
    for key in ["libraryNativeViewRouting", "librarySourceArchiveScene"]:
        record[key] = prior[key]
    path.write_text(json.dumps(record, indent=2) + "\n")
