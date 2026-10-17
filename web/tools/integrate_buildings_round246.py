"""Integrate the verified CON frontage while retaining all source campus objects."""

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "web/tools"))
sys.dont_write_bytecode = True
from integrate_exterior_round194 import integrate


def main():
    folder = ROOT / "result/blender/con-registration244"
    audit = json.loads((folder / "audit.json").read_text())
    proof_path = folder / "saved-mesh-verification.json"
    proof = json.loads(proof_path.read_text())
    assert audit["status"] == "candidate_verified_for_integration"
    assert (
        audit["savedProofSha256"] == hashlib.sha256(proof_path.read_bytes()).hexdigest()
    )
    assert proof["componentSha256"] == audit["componentSha256"]
    assert (
        proof["clearHoleRayChecks"] == proof["assembledOpaqueFragmentRayChecks"] == 267
    )
    assert proof["sourceWindowModules"] == 80 and proof["opaqueUnverifiedOrDoorModules"] == 9
    assert proof["savedRoofVerticalRayChecks"] == 20
    assert proof["unchangedOtherFacadeFacesAndUVs"] == 6384
    assert proof["originalObjectsVerified"] == 8621 and proof["protectedRooms"] == 35
    registration_path = folder / "registration-plan.json"
    assert (
        audit["registrationPlanSha256"]
        == hashlib.sha256(registration_path.read_bytes()).hexdigest()
    )
    import bpy
    bpy.context.preferences.filepaths.save_version = 0
    integrate(
        base=ROOT / "result/blender/LSE_campus_detailed_v243.blend",
        destination=ROOT / "result/blender/LSE_campus_detailed_v246.blend",
        proof=ROOT / "result/blender/stage246",
        version=246,
        baseline_proof=ROOT / "result/blender/stage243",
        reports=[
            ("CON", "result/blender/con-registration244/audit.json", "CON_EXTERIOR")
        ],
        scope=audit["scope"]
        + ". All original objects remain intact; only eight listed original skin/roof objects are hidden. Horizontal frontage fit, flat side-door thresholds and unseen rear roof closure remain estimated. All roads, rooms, Aldwych access and neighbouring parcels retain the accepted geometry. COL source component is not integrated.",
    )
    path = ROOT / "result/blender/stage246/building-refinement.json"
    record = json.loads(path.read_text())
    prior = json.loads(
        (ROOT / "result/blender/stage243/building-refinement.json").read_text()
    )
    for key in ["libraryNativeViewRouting", "librarySourceArchiveScene"]:
        record[key] = prior[key]
    path.write_text(json.dumps(record, indent=2) + "\n")


if __name__ == "__main__":
    main()
