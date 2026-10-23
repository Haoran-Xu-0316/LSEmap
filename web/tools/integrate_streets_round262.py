"""Integrate reviewed Houghton and Sheffield street furniture without changing retained architecture."""

import hashlib
import json
import sys
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "web/tools"))
from integrate_exterior_round194 import integrate

COMPONENTS = [
    ("OLD", "houghton262", "OLD_EXTERIOR"),
    ("SAW", "sheffield262", "SAW_EXTERIOR"),
]
BASE_SHA = "9890521a376afabfbb3d6c130d20ce40988315c49b8adea4c00749960a97482a"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def accepted_components():
    records = {}
    for code, name, owner in COMPONENTS:
        folder = ROOT / "result/blender" / name
        audit = json.loads((folder / "audit.json").read_text())
        proof_name = (
            "verification.json"
            if code == "OLD"
            else "independent-geometry-verification.json"
        )
        proof = json.loads((folder / proof_name).read_text())
        accepted = json.loads((folder / "acceptance.json").read_text())
        assert audit["baselineSha256"] == BASE_SHA
        assert audit["destinationCollection"] == owner
        assert proof.get("passed") or proof.get("status") == "passed"
        assert (
            proof.get(
                "protectedIndependentRooms", proof.get("independentRoomsPreserved")
            )
            == 35
        )
        assert accepted["status"] == "accepted_for_bounded_integration"
        assert (
            accepted["componentSha256"]
            == audit["componentSha256"]
            == sha(ROOT / audit["componentPath"])
        )
        assert accepted["verificationSha256"] == sha(folder / proof_name)
        assert accepted["views"], code
        for image, expected in accepted["views"].items():
            assert sha(folder / image) == expected, image
        records[name] = audit
    return records


def main():
    baseline = ROOT / "result/blender/LSE_campus_detailed_v261.blend"
    assert sha(baseline) == BASE_SHA
    accepted_components()
    bpy.context.preferences.filepaths.save_version = 0
    integrate(
        base=baseline,
        destination=ROOT / "result/blender/LSE_campus_detailed_v262.blend",
        proof=ROOT / "result/blender/stage262",
        version=262,
        baseline_proof=ROOT / "result/blender/stage261",
        reports=[
            (code, f"result/blender/{name}/audit.json", owner)
            for code, name, owner in COMPONENTS
        ],
        scope="Houghton wall-mounted notice cabinets and a photographed entrance camera; two Sheffield Street planter and seat units registered to retained native trees and paving. All original objects, material graphs and35room studies remain protected. Furniture sections and location estimates are guided by undated/historical photographs, not a current site survey.",
    )
    path = ROOT / "result/blender/stage262/building-refinement.json"
    record = json.loads(path.read_text())
    previous = json.loads(
        (ROOT / "result/blender/stage261/building-refinement.json").read_text()
    )
    for key in ["libraryNativeViewRouting", "librarySourceArchiveScene"]:
        record[key] = previous[key]
    path.write_text(json.dumps(record, indent=2) + "\n")


if __name__ == "__main__":
    main()
