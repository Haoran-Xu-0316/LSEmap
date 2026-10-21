"""Integrate independently reviewed SHF blind wall and COW belt corrections."""

import hashlib
import json
import sys
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "web/tools"))
from integrate_exterior_round194 import integrate

COMPONENTS = [("SHF", "shf255", "SHF_EXTERIOR"), ("COW", "cow255", "COW_EXTERIOR")]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    for code, name, _collection in COMPONENTS:
        folder = ROOT / "result/blender" / name
        audit = json.loads((folder / "audit.json").read_text())
        proof = json.loads((folder / "verification.json").read_text())
        accepted = json.loads((folder / "acceptance.json").read_text())
        assert (
            proof["passed"]
            and proof.get("roomStudiesProtected", proof.get("protectedRoomStudies"))
            == 35
        ), code
        assert accepted["status"] == "accepted_for_bounded_integration", code
        assert (
            accepted["componentSha256"]
            == audit["componentSha256"]
            == sha(ROOT / audit["componentPath"])
        ), code
        assert accepted["verificationSha256"] == sha(folder / "verification.json"), code
        for image, expected in accepted["views"].items():
            assert sha(folder / image) == expected, image
    bpy.context.preferences.filepaths.save_version = 0
    integrate(
        base=ROOT / "result/blender/LSE_campus_detailed_v254.blend",
        destination=ROOT / "result/blender/LSE_campus_detailed_v255.blend",
        proof=ROOT / "result/blender/stage255",
        version=255,
        baseline_proof=ROOT / "result/blender/stage254",
        reports=[
            (code, f"result/blender/{name}/audit.json", collection)
            for code, name, collection in COMPONENTS
        ],
        scope="SHF removes two unsupported lower windows and restores photographed blind white wall and decorative frame. COW removes the unsupported short-street ground-floor continuous belt and cancels bevels only at four internal short-side head joints to close exposed construction slots. Existing colors, glass optics, roofs, interiors, source archives and all35room studies remain intact. Unsurveyed dimensions and unseen elevations remain estimated.",
    )
    path = ROOT / "result/blender/stage255/building-refinement.json"
    record = json.loads(path.read_text())
    prior = json.loads(
        (ROOT / "result/blender/stage254/building-refinement.json").read_text()
    )
    for key in ["libraryNativeViewRouting", "librarySourceArchiveScene"]:
        record[key] = prior[key]
    path.write_text(json.dumps(record, indent=2) + "\n")


if __name__ == "__main__":
    main()
