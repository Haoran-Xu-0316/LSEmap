"""Integrate independently reviewed PEL canopy, OCS sash and LCH fanlight corrections."""

import hashlib
import json
import sys
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "web/tools"))
from integrate_exterior_round194 import integrate

COMPONENTS = [
    ("PEL", "pel257", "PEL_EXTERIOR"),
    ("OCS", "ocs257", "OCS_EXTERIOR"),
    ("LCH", "lch257", "LCH_EXTERIOR"),
]


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
        base=ROOT / "result/blender/LSE_campus_detailed_v256.blend",
        destination=ROOT / "result/blender/LSE_campus_detailed_v257.blend",
        proof=ROOT / "result/blender/stage257",
        version=257,
        baseline_proof=ROOT / "result/blender/stage256",
        reports=[
            (code, f"result/blender/{name}/audit.json", collection)
            for code, name, collection in COMPONENTS
        ],
        scope="Photo-guided exterior corrections only: PEL canopy physical underside reuses the existing yellow entry finish; OCS upper sashes use three photographed crossbars per window; LCH fanlight title and number follow the photographed vertical ordering and arched layout. Historic reference proportions remain estimates. All other original architecture, material graphs, glazing and35room studies are protected.",
    )
    path = ROOT / "result/blender/stage257/building-refinement.json"
    record = json.loads(path.read_text())
    prior = json.loads(
        (ROOT / "result/blender/stage256/building-refinement.json").read_text()
    )
    for key in ["libraryNativeViewRouting", "librarySourceArchiveScene"]:
        record[key] = prior[key]
    path.write_text(json.dumps(record, indent=2) + "\n")


if __name__ == "__main__":
    main()
