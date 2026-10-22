"""Integrate reviewed Houghton window boxes without changing retained architecture."""

import hashlib
import json
import sys
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "web/tools"))
from integrate_exterior_round194 import integrate

COMPONENTS = [("OLD", "old259", "OLD_EXTERIOR")]
BASE_SHA = "46a6d58baf708af45c8a8669f85fa6b24efdbfb1d3721cd4aca315e85ba0d835"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def accepted_components():
    records = {}
    for code, name, owner in COMPONENTS:
        folder = ROOT / "result/blender" / name
        audit = json.loads((folder / "audit.json").read_text())
        proof = json.loads((folder / "verification.json").read_text())
        accepted = json.loads((folder / "acceptance.json").read_text())
        assert audit["baselineSha256"] == BASE_SHA
        assert audit["destinationCollection"] == owner
        assert proof["passed"] and proof["protectedRoomStudies"] == 35
        assert accepted["status"] == "accepted_for_bounded_integration"
        assert (
            accepted["componentSha256"]
            == audit["componentSha256"]
            == sha(ROOT / audit["componentPath"])
        )
        assert accepted["verificationSha256"] == sha(folder / "verification.json")
        assert accepted["views"], code
        for image, expected in accepted["views"].items():
            assert sha(folder / image) == expected, image
        records[name] = audit
    return records


def main():
    baseline = ROOT / "result/blender/LSE_campus_detailed_v258.blend"
    assert sha(baseline) == BASE_SHA
    accepted_components()
    bpy.context.preferences.filepaths.save_version = 0
    integrate(
        base=baseline,
        destination=ROOT / "result/blender/LSE_campus_detailed_v259.blend",
        proof=ROOT / "result/blender/stage259",
        version=259,
        baseline_proof=ROOT / "result/blender/stage258",
        reports=[
            (code, f"result/blender/{name}/audit.json", owner)
            for code, name, owner in COMPONENTS
        ],
        scope="Restore eight photo-supported Houghton window boxes in three shared batches, using actual retained window axes and sills. Box dimensions and foliage remain display estimates from an undated photograph. No original objects or materials are changed or archived. Main portal, courtyard, attic, glazing and35 independent room studies are retained; whole-building completion is not asserted. Library exterior-only basement clipping is a separate temporary-export correction and never alters this native campus or its underground interior.",
    )
    path = ROOT / "result/blender/stage259/building-refinement.json"
    record = json.loads(path.read_text())
    previous = json.loads(
        (ROOT / "result/blender/stage258/building-refinement.json").read_text()
    )
    for key in ["libraryNativeViewRouting", "librarySourceArchiveScene"]:
        record[key] = previous[key]
    path.write_text(json.dumps(record, indent=2) + "\n")


if __name__ == "__main__":
    main()
