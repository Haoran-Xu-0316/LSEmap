"""Integrate the accepted COL finish without moving any architecture."""

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
    reports = [
        ("COL", "col-finish252", "COL_EXTERIOR"),
    ]
    for _code, name, _collection in reports:
        folder = ROOT / "result/blender" / name
        audit = json.loads((folder / "audit.json").read_text())
        accepted = json.loads((folder / "acceptance.json").read_text())
        proof = json.loads((folder / "saved-verification.json").read_text())
        assert accepted["status"] == "accepted_for_bounded_integration", name
        assert accepted["componentSha256"] == audit["componentSha256"], name
        assert digest(ROOT / audit["componentPath"]) == audit["componentSha256"], name
        assert accepted["savedProofSha256"] == digest(folder / "saved-verification.json"), name
        assert proof["savedComponentReopened"], name
        assert accepted["protectedRooms"] == 35 and not audit.get("changedObjects"), name
        for view, expected in accepted["views"].items():
            assert digest(folder / view) == expected, view
    bpy.context.preferences.filepaths.save_version = 0
    integrate(
        base=ROOT / "result/blender/LSE_campus_detailed_v251.blend",
        destination=ROOT / "result/blender/LSE_campus_detailed_v252.blend",
        proof=ROOT / "result/blender/stage252",
        version=252,
        baseline_proof=ROOT / "result/blender/stage251",
        reports=[(code, f"result/blender/{name}/audit.json", collection)
                 for code, name, collection in reports],
        scope="COL Houghton stone and painted joinery follow the retained photo-guided finish family. Uniform stone albedo derives from the original tone-study linear mean without repeated macro-colour texture. Every original geometry coordinate and UV remains intact. Glass, roof, source apertures, global lighting, public structures and all35room studies remain unchanged. Photos and colour are not calibrated current surveys.",
    )
    path = ROOT / "result/blender/stage252/building-refinement.json"
    record = json.loads(path.read_text())
    prior = json.loads((ROOT / "result/blender/stage251/building-refinement.json").read_text())
    for key in ["libraryNativeViewRouting", "librarySourceArchiveScene"]:
        record[key] = prior[key]
    path.write_text(json.dumps(record, indent=2) + "\n")


if __name__ == "__main__":
    main()
