"""Integrate reviewed CLM upper sash corrections without changing retained architecture."""

import hashlib
import json
import sys
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "web/tools"))
from integrate_exterior_round194 import integrate

COMPONENTS = [("CLM", "clm261", "CLM_EXTERIOR")]
BASE_SHA = "c208a1086482bcc1bf20ec25ccdd9c684a0ea88a4891e5a007439c1076c1eec2"


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
    baseline = ROOT / "result/blender/LSE_campus_detailed_v260.blend"
    assert sha(baseline) == BASE_SHA
    accepted_components()
    bpy.context.preferences.filepaths.save_version = 0
    integrate(
        base=baseline,
        destination=ROOT / "result/blender/LSE_campus_detailed_v261.blend",
        proof=ROOT / "result/blender/stage261",
        version=261,
        baseline_proof=ROOT / "result/blender/stage260",
        reports=[
            (code, f"result/blender/{name}/audit.json", owner)
            for code, name, owner in COMPONENTS
        ],
        scope="CLM seven upper sashes use paired two-column leaves, with stronger meeting stiles. The meeting stile at the curved GIS join follows its actual retained glass surface. Original glass, horizontal rails, stone, roof, all materials and35room studies remain protected. Photo-guided sections and GIS proportions remain estimates; whole-building and complete interior reconstruction are not asserted.",
    )
    path = ROOT / "result/blender/stage261/building-refinement.json"
    record = json.loads(path.read_text())
    previous = json.loads(
        (ROOT / "result/blender/stage260/building-refinement.json").read_text()
    )
    for key in ["libraryNativeViewRouting", "librarySourceArchiveScene"]:
        record[key] = previous[key]
    path.write_text(json.dumps(record, indent=2) + "\n")


if __name__ == "__main__":
    main()
