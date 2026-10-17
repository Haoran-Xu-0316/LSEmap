"""Integrate the reviewed level Houghton paving support into the full campus."""

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "web/tools"))
sys.dont_write_bytecode = True
from integrate_exterior_round194 import integrate


def main():
    folder = ROOT / "result/blender/houghton-footway243"
    audit = json.loads((folder / "audit.json").read_text())
    proof_path = folder / "saved-contact-verification.json"
    proof = json.loads(proof_path.read_text())
    assert audit["status"] == "candidate_verified_for_integration"
    assert (
        audit["savedContactProofSha256"]
        == hashlib.sha256(proof_path.read_bytes()).hexdigest()
    )
    assert proof["componentSha256"] == audit["componentSha256"]
    partition_path = folder / "saved-partition-verification.json"
    assert (
        audit["savedPartitionProofSha256"]
        == hashlib.sha256(partition_path.read_bytes()).hexdigest()
    )
    partition = json.loads(partition_path.read_text())
    assert partition["componentSha256"] == audit["componentSha256"]
    assert partition["maximumOverlappingInteriorM2"] == 0
    assert partition["removedDuplicateTops"] == 266
    assert (
        proof["originalEntryAndFurnitureLevelsPreserved"]
        and proof["relativeGradeCandidateExcluded"]
    )
    integrate(
        base=ROOT / "result/blender/LSE_campus_detailed_v242.blend",
        destination=ROOT / "result/blender/LSE_campus_detailed_v243.blend",
        proof=ROOT / "result/blender/stage243",
        version=243,
        baseline_proof=ROOT / "result/blender/stage242",
        reports=[("SITE", "result/blender/houghton-footway243/audit.json", "00_SITE")],
        scope=audit["scope"]
        + ". All original meshes remain intact in the native archive; only the listed original paving batch is hidden. Source finishes, rooms, street levels and entry geometry remain intact. Historical relative-grade candidate remains excluded pending coordinated facade and access work.",
    )
    path = ROOT / "result/blender/stage243/building-refinement.json"
    record = json.loads(path.read_text())
    prior = json.loads(
        (ROOT / "result/blender/stage242/building-refinement.json").read_text()
    )
    for key in ["libraryNativeViewRouting", "librarySourceArchiveScene"]:
        record[key] = prior[key]
    path.write_text(json.dumps(record, indent=2) + "\n")


if __name__ == "__main__":
    main()
