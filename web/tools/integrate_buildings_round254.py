"""Integrate the reviewed Three Tuns glass without changing its architecture."""

import hashlib
import json
import sys
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "web/tools"))
from integrate_exterior_round194 import integrate


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    folder = ROOT / "result/blender/saw254"
    audit = json.loads((folder / "audit.json").read_text())
    proof = json.loads((folder / "verification.json").read_text())
    accepted = json.loads((folder / "acceptance.json").read_text())
    assert proof["passed"] and proof["protectedRoomStudies"] == 35
    assert accepted["status"] == "accepted_for_bounded_integration"
    assert accepted["componentSha256"] == audit["componentSha256"] == digest(ROOT / audit["componentPath"])
    assert accepted["verificationSha256"] == digest(folder / "verification.json")
    assert accepted["productionReviewSha256"] == digest(folder / "production-review.webp")
    assert audit["archivedObjects"] == ["SAW_V48_TUNS_glass"]
    assert audit["addedObjects"] == ["SAW254_Three_Tuns_clear_glass"]
    bpy.context.preferences.filepaths.save_version = 0
    integrate(
        base=ROOT / "result/blender/LSE_campus_detailed_v252.blend",
        destination=ROOT / "result/blender/LSE_campus_detailed_v254.blend",
        proof=ROOT / "result/blender/stage254",
        version=254,
        baseline_proof=ROOT / "result/blender/stage252",
        reports=[("SAW", "result/blender/saw254/audit.json", "SAW_THREE_TUNS_study")],
        scope="Three Tuns historical entrance glass reuses the accepted SAW Denning optical family. Only glass material changes; original pane geometry, timber, lettering, existing plan and walls remain intact. No new furniture, geometry, global lighting or current refurbishment claim.",
    )
    path = ROOT / "result/blender/stage254/building-refinement.json"
    record = json.loads(path.read_text())
    prior = json.loads((ROOT / "result/blender/stage252/building-refinement.json").read_text())
    for key in ["libraryNativeViewRouting", "librarySourceArchiveScene"]:
        record[key] = prior[key]
    path.write_text(json.dumps(record, indent=2) + "\n")


if __name__ == "__main__":
    main()
