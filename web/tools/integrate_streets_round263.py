"""Integrate reviewed Clare Market fixtures and Sheffield cycle stands without changing retained architecture."""

import hashlib
import json
import sys
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "web/tools"))
from integrate_exterior_round194 import integrate

COMPONENTS = [
    ("OLD", "houghton263", "OLD_EXTERIOR"),
    ("LANDSCAPE", "sheffield263", "03_PUBLIC_REALM"),
]
BASE_SHA = "35547bb32309adcd934df8845c71e672e3dc7b3ca519ad5154ec9a65f143cb75"


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
    baseline = ROOT / "result/blender/LSE_campus_detailed_v262.blend"
    assert sha(baseline) == BASE_SHA
    accepted_components()
    bpy.context.preferences.filepaths.save_version = 0
    integrate(
        base=baseline,
        destination=ROOT / "result/blender/LSE_campus_detailed_v263.blend",
        proof=ROOT / "result/blender/stage263",
        version=263,
        baseline_proof=ROOT / "result/blender/stage262",
        reports=[
            (code, f"result/blender/{name}/audit.json", owner)
            for code, name, owner in COMPONENTS
        ],
        scope="Two photographed Clare Market hooded wall fixtures and the visible left conduit; five double-sided cycle stands inferred from the retained Sheffield OSM ten-bicycle node, with same-street form references. Original geometry, material graphs and35rooms remain protected. Fixture sections, rack pitch and exact individual positions are estimates; the cycle-group photograph is not claimed to be the same mapped group.",
    )
    path = ROOT / "result/blender/stage263/building-refinement.json"
    record = json.loads(path.read_text())
    previous = json.loads(
        (ROOT / "result/blender/stage262/building-refinement.json").read_text()
    )
    for key in ["libraryNativeViewRouting", "librarySourceArchiveScene"]:
        record[key] = previous[key]
    path.write_text(json.dumps(record, indent=2) + "\n")


if __name__ == "__main__":
    main()
