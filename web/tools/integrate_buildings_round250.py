"""Integrate accepted OLD approach geometry and MAR third-floor shaft openings."""

import hashlib
import json
import sys
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "web/tools"))
from integrate_exterior_round194 import integrate


def main():
    for name in ["old-approach250", "mar-third250"]:
        folder = ROOT / "result/blender" / name
        audit = json.loads((folder / "audit.json").read_text())
        acceptance = json.loads((folder / "acceptance.json").read_text())
        proof_path = folder / "saved-verification.json"
        proof = json.loads(proof_path.read_text())
        assert acceptance["status"] == "accepted_for_bounded_integration"
        assert acceptance["componentSha256"] == audit["componentSha256"]
        assert (
            acceptance["savedProofSha256"]
            == hashlib.sha256(proof_path.read_bytes()).hexdigest()
        )
        assert proof["savedComponentReopened"] and proof["protectedRooms"] == 35
        assert not audit["changedObjects"]
        for view, digest in acceptance["views"].items():
            assert hashlib.sha256((folder / view).read_bytes()).hexdigest() == digest
    bpy.context.preferences.filepaths.save_version = 0
    integrate(
        base=ROOT / "result/blender/LSE_campus_detailed_v249.blend",
        destination=ROOT / "result/blender/LSE_campus_detailed_v250.blend",
        proof=ROOT / "result/blender/stage250",
        version=250,
        baseline_proof=ROOT / "result/blender/stage249",
        reports=[
            ("OLD", "result/blender/old-approach250/audit.json", "OLD_EXTERIOR"),
            (
                "MAR",
                "result/blender/mar-third250/audit.json",
                "MAR_PUBLIC_INTERIOR_study",
            ),
        ],
        scope="OLD keeps four existing tread elevations, rail supports and thresholds while correcting its photographed long faceted corners. MAR opens three source-registered structural lift shafts in the existing17.5mthird-floor plate, retaining its outline, UVs and all other floors. Dimensions and floor datum remain estimates. All35room studies remain unchanged. COL is private pending roof coordination.",
    )
    path = ROOT / "result/blender/stage250/building-refinement.json"
    record = json.loads(path.read_text())
    prior = json.loads(
        (ROOT / "result/blender/stage249/building-refinement.json").read_text()
    )
    for key in ["libraryNativeViewRouting", "librarySourceArchiveScene"]:
        record[key] = prior[key]
    path.write_text(json.dumps(record, indent=2) + "\n")


if __name__ == "__main__":
    main()
