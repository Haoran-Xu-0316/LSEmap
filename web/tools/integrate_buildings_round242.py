"""Assemble the reviewed source-constrained SAW upper circulation."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "web/tools"))
sys.dont_write_bytecode = True
from integrate_exterior_round194 import integrate

if __name__ == "__main__":
    audit = json.loads(
        (ROOT / "result/blender/saw-circulation242/audit.json").read_text()
    )
    assert audit["status"] == "candidate_verified_for_integration"
    integrate(
        base=ROOT / "result/blender/LSE_campus_detailed_v241.blend",
        destination=ROOT / "result/blender/LSE_campus_detailed_v242.blend",
        proof=ROOT / "result/blender/stage242",
        version=242,
        baseline_proof=ROOT / "result/blender/stage241",
        reports=[
            (
                "SAW",
                "result/blender/saw-circulation242/audit.json",
                "SAW_STRUCTURE173_registered_main_circulation",
            )
        ],
        scope="Replace only the estimated ST03 three-to-four and four-to-five circulation, retain lower original geometry/UVs and ST04, coordinate local thin floors inside vector-extracted historical circulation. Preserve every original object, material graph and room study. Full current building interiors remain incomplete.",
    )
    path = ROOT / "result/blender/stage242/building-refinement.json"
    record = json.loads(path.read_text())
    prior = json.loads(
        (ROOT / "result/blender/stage241/building-refinement.json").read_text()
    )
    for key in ["libraryNativeViewRouting", "librarySourceArchiveScene"]:
        record[key] = prior[key]
    path.write_text(json.dumps(record, indent=2) + "\n")
