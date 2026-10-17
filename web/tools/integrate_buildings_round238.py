"""Assemble the reviewed PEL entrance and finish corrections into the campus."""

from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "web/tools"))
from integrate_exterior_round194 import integrate

if __name__ == "__main__":
    integrate(
        base=ROOT / "result/blender/LSE_campus_detailed_v237.blend",
        destination=ROOT / "result/blender/LSE_campus_detailed_v238.blend",
        proof=ROOT / "result/blender/stage238",
        version=238,
        baseline_proof=ROOT / "result/blender/stage237",
        reports=[("PEL", "result/blender/pel-exterior238/audit.json", "PEL_EXTERIOR")],
        scope="Move the existing PEL revolving-door assembly to the photographed left side, coordinate its central frame and side-door pull, and refine source-supported front finishes. Retain all source objects, all rooms and every other building. Whole-campus current interiors remain incomplete.",
    )
    path = ROOT / "result/blender/stage238/building-refinement.json"
    record = json.loads(path.read_text())
    prior = json.loads(
        (ROOT / "result/blender/stage237/building-refinement.json").read_text()
    )
    for key in ["libraryNativeViewRouting", "librarySourceArchiveScene"]:
        record[key] = prior[key]
    path.write_text(json.dumps(record, indent=2) + "\n")
