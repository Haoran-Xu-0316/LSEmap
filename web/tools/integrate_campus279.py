"""Publish only the reviewed Lindsey frontage over the protected275 campus.

The SAW construction candidate remains private. A pinned root review binds the
component, fresh actual-mesh proof and complete-scene comparison images.
"""

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "result/blender/LSE_campus_detailed_v275.blend"
BASE_SHA = "18a60235fd7c71c6c2864690c574f97b66a9d05577e0c584c626dee41829a4f9"
DESTINATION = ROOT / "result/blender/LSE_campus_detailed_v279.blend"
OUT = ROOT / "result/blender/stage279"
ACCEPTANCE = ROOT / "result/blender/street277/acceptance.json"
ACCEPTANCE_SHA = "6a739b6aab5ac4ebf35e4c30fed18735fd9cb81e5f5d8fba1ceb8b539937cc71"


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def accepted_component():
    assert sha(ACCEPTANCE) == ACCEPTANCE_SHA
    review = json.loads(ACCEPTANCE.read_text())
    folder = ROOT / "result/blender/street277"
    audit = json.loads((folder / "audit.json").read_text())
    proof_path = folder / "fresh-process-verification.json"
    proof = json.loads(proof_path.read_text())
    assert review["status"] == "accepted_for_bounded_integration"
    assert (
        review["componentSha256"]
        == audit["componentSha256"]
        == proof["componentSha256"]
    )
    assert sha(ROOT / audit["componentPath"]) == audit["componentSha256"]
    assert sha(proof_path) == review["verificationSha256"]
    assert (
        proof["freshBlenderProcess"] and proof["status"] == "passed-bounded-candidate"
    )
    assert audit["baselineSha256"] == proof["baselineSha256"] == BASE_SHA
    assert len(audit["addedObjects"]) == 4 and len(audit["archivedObjects"]) == 2
    assert audit["changedObjects"] == [] and audit["newMaterials"] == 2
    assert audit["destinationCollection"] == "01_CITY_CONTEXT_estimated_heights"
    assert sha(ROOT / audit["sourcePlan"]) == audit["sourcePlanSha256"]
    assert all(sha(ROOT / p) == h for p, h in audit["sourceHashes"].items())
    assert all(sha(ROOT / p) == h for p, h in review["scriptHashes"].items())
    assert review["views"] and all(
        sha(ROOT / p) == h for p, h in review["views"].items()
    )
    actual = proof["actualMeshProof"]
    assert actual["actualLoadedMeshesUsed"] and actual["blenderExecuted"]
    assert (
        actual["trueWallOpenings"] == 16 and actual["allGeometryInsideExistingParcel"]
    )
    return audit


def main():
    sys.path.insert(0, str(ROOT / "web/tools"))
    from integrate_exterior_round194 import integrate

    assert sha(BASE) == BASE_SHA
    audit = accepted_component()
    manifest = {
        "version": 279,
        "baseline": str(BASE.relative_to(ROOT)),
        "baselineSha256": BASE_SHA,
        "destination": str(DESTINATION.relative_to(ROOT)),
        "acceptedComponent": "street277",
        "componentSha256": audit["componentSha256"],
        "rootAcceptanceSha256": ACCEPTANCE_SHA,
        "unlistedComponentsExcluded": True,
        "authoringScriptSha256": sha(Path(__file__)),
        "verificationScriptSha256": sha(ROOT / "web/tests/verify_campus279.py"),
    }
    integrate(
        base=BASE,
        destination=DESTINATION,
        proof=OUT,
        version=279,
        baseline_proof=ROOT / "result/blender/stage275",
        reports=[
            (
                "CONTEXT",
                "result/blender/street277/audit.json",
                audit["destinationCollection"],
            )
        ],
        scope=audit["scope"],
    )
    path = OUT / "building-refinement.json"
    record = json.loads(path.read_text())
    prior = json.loads(
        (ROOT / "result/blender/stage275/building-refinement.json").read_text()
    )
    for key in ("libraryNativeViewRouting", "librarySourceArchiveScene"):
        record[key] = prior[key]
    path.write_text(json.dumps(record, indent=2) + "\n")
    manifest["sourceModelSha256"] = record["sourceModelSha256"]
    (OUT / "accepted-components.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print("CAMPUS279_INTEGRATED", manifest["sourceModelSha256"], flush=True)


if __name__ == "__main__":
    main()
