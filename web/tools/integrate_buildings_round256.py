"""Integrate independently reviewed KGS lettering, PAN fascia and forecourt corrections."""

import hashlib
import json
import sys
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "web/tools"))
from integrate_exterior_round194 import integrate

COMPONENTS = [
    ("KGS", "kgs256", "KGS_EXTERIOR"),
    ("PAN", "pan256", "PAN_EXTERIOR"),
    ("PAN", "forecourt256", "PAN_EXTERIOR"),
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
        base=ROOT / "result/blender/LSE_campus_detailed_v255.blend",
        destination=ROOT / "result/blender/LSE_campus_detailed_v256.blend",
        proof=ROOT / "result/blender/stage256",
        version=256,
        baseline_proof=ROOT / "result/blender/stage255",
        reports=[
            (code, f"result/blender/{name}/audit.json", collection)
            for code, name, collection in COMPONENTS
        ],
        scope="KGS entrance lettering follows the photographed shallow arc with bounded photographic scale estimates; the title and unchanged-size portal numbers seat close to the retained opaque mosaic. PAN entrance fascia retains its original grid and material while correcting the photographed aperture type and closing unsupported per-cell grid gaps. PAN forecourt furniture adopts photo-guided stone planting pools and low seats, with doorway access checked; mislocated inherited cycle stands are archived without inventing a new unregistered position. All other geometry, colors, glazing, roofs and35room studies are protected; these local corrections do not establish current measured whole-building accuracy.",
    )
    path = ROOT / "result/blender/stage256/building-refinement.json"
    record = json.loads(path.read_text())
    prior = json.loads(
        (ROOT / "result/blender/stage255/building-refinement.json").read_text()
    )
    for key in ["libraryNativeViewRouting", "librarySourceArchiveScene"]:
        record[key] = prior[key]
    path.write_text(json.dumps(record, indent=2) + "\n")


if __name__ == "__main__":
    main()
