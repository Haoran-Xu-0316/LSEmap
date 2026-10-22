"""Integrate reviewed MAR fin finish, solid third-floor deck and LRB approach corrections."""

import hashlib
import json
import sys
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "web/tools"))
from integrate_exterior_round194 import integrate

COMPONENTS = [
    ("MAR", "mar-finish258", "MAR_EXTERIOR"),
    ("MAR", "mar258", "MAR_PUBLIC_INTERIOR_study"),
    ("LRB", "lrb258", "LRB_EXTERIOR"),
]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    baseline = ROOT / "result/blender/LSE_campus_detailed_v257.blend"
    assert (
        sha(baseline)
        == "5f73b29480de08425d4d8ab3c39aa1e2b9231656f81f1f763ee1ffa200568db9"
    )
    for code, name, _collection in COMPONENTS:
        folder = ROOT / "result/blender" / name
        audit = json.loads((folder / "audit.json").read_text())
        proof = json.loads((folder / "verification.json").read_text())
        accepted = json.loads((folder / "acceptance.json").read_text())
        protected_rooms = proof.get(
            "roomStudiesProtected", proof.get("protectedRoomStudies")
        )
        if protected_rooms is None:
            # LRB's verifier emits this only after an explicit35-room count and
            # exact before/after room and campus-membership comparison.
            assert proof.get("all35RoomsAndOriginalSceneProtected") is True, code
            protected_rooms = 35
        assert proof["passed"] and protected_rooms == 35, code
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
        base=baseline,
        destination=ROOT / "result/blender/LSE_campus_detailed_v258.blend",
        proof=ROOT / "result/blender/stage258",
        version=258,
        baseline_proof=ROOT / "result/blender/stage257",
        reports=[
            (code, f"result/blender/{name}/audit.json", collection)
            for code, name, collection in COMPONENTS
        ],
        scope="Bounded source-guided corrections: MAR north concrete fins retain geometry and optical properties while correcting their documented darker tone relationship; the registered southern third-floor deck becomes a closed slab with its existing top coordinates, UV pairs and three lift holes retained. The 0.32m slab thickness remains an inherited display estimate. LRB Watkins Plaza facade divisions, window groups, wide Library portal and visible roof transitions follow the registered2025 As Existing elevation; hidden return depths remain estimates. All original objects, material graphs and35 independent rooms remain protected; higher-floor completion and measured engineering accuracy are not asserted.",
    )
    path = ROOT / "result/blender/stage258/building-refinement.json"
    record = json.loads(path.read_text())
    prior = json.loads(
        (ROOT / "result/blender/stage257/building-refinement.json").read_text()
    )
    for key in ["libraryNativeViewRouting", "librarySourceArchiveScene"]:
        record[key] = prior[key]
    path.write_text(json.dumps(record, indent=2) + "\n")


if __name__ == "__main__":
    main()
