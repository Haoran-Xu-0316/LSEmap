"""Integrate the reviewed public court enclosure, preserving the full campus."""

import hashlib
import json
import sys
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "web/tools"))
sys.dont_write_bytecode = True
from integrate_exterior_round194 import integrate


def main():
    folder = ROOT / "result/blender/court-enclosure248"
    audit = json.loads((folder / "audit.json").read_text())
    proof_path = folder / "saved-verification.json"
    proof = json.loads(proof_path.read_text())
    assert audit["status"] == "candidate_verified_for_integration"
    assert (
        audit["savedProofSha256"] == hashlib.sha256(proof_path.read_bytes()).hexdigest()
    )
    assert proof["componentSha256"] == audit["componentSha256"]
    assert proof["clearEntrySceneRayChecks"] == 15 and proof["closedPostSolids"] == 60
    assert proof["originalObjectsVerified"] == 8634 and proof["protectedRooms"] == 35
    bpy.context.preferences.filepaths.save_version = 0
    integrate(
        base=ROOT / "result/blender/LSE_campus_detailed_v246.blend",
        destination=ROOT / "result/blender/LSE_campus_detailed_v248.blend",
        proof=ROOT / "result/blender/stage248",
        version=248,
        baseline_proof=ROOT / "result/blender/stage246",
        reports=[
            ("SITE", "result/blender/court-enclosure248/audit.json", "03_PUBLIC_REALM")
        ],
        scope=audit["scope"]
        + " The height, coated posts, rectangular wire grid and generous mapped-corner opening remain estimates, not a current as-built gate survey.",
    )
    path = ROOT / "result/blender/stage248/building-refinement.json"
    record = json.loads(path.read_text())
    prior = json.loads(
        (ROOT / "result/blender/stage246/building-refinement.json").read_text()
    )
    for key in ["libraryNativeViewRouting", "librarySourceArchiveScene"]:
        record[key] = prior[key]
    path.write_text(json.dumps(record, indent=2) + "\n")


if __name__ == "__main__":
    main()
